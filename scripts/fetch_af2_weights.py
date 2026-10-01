#!/usr/bin/env python3
"""AlphaFold2 weight acquisition harness for the Stage 2 smoke notebook.

Replaces the old fire-and-forget `subprocess.Popen("aria2c ... && tar ...")`
+ blind 30-minute polling loop (attempt-003 download-harness bug: the child
exited immediately, nothing observed it, and the cell burned 30 minutes
before asserting on a missing done.txt).

Guarantees:

- Downloader precheck via shutil.which BEFORE launching anything
  (aria2c -> curl -> wget, or an explicitly requested one).
- The child process is fully observed: PID, return code, stdout/stderr
  captured to download.log, byte count and elapsed time reported.
- Progress printed at a fixed interval while the child runs.
- A non-zero child exit stops IMMEDIATELY with the real log tail --
  never a blind wait.
- Partial tarballs are kept and resumed (-c / -C -); nothing is deleted
  unless proven corrupt (and this script never deletes at all).
- After download: tarball must exist and pass a plausible-size check;
  extraction must yield exactly 14 .npz files; only then is done.txt
  written. A valid done.txt + 14 npz skips the download entirely.

Stdlib only; runs under the Colab kernel Python (any 3.x), not the isolated
BindCraft env. Unit-testable without network by pointing PATH at a fake
downloader.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time

OFFICIAL_URL = ("https://storage.googleapis.com/alphafold/"
                "alphafold_params_2022-12-06.tar")
TARBALL_NAME = "alphafold_params_2022-12-06.tar"
EXPECTED_NPZ = 14                     # official AF2 param set
MIN_TARBALL_BYTES = 5_000_000_000     # official tar is ~5.3e9 bytes
DOWNLOADER_ORDER = ("aria2c", "curl", "wget")


def find_downloader(preferred="auto", which=shutil.which):
    """Return (name, path) or (None, None). Explicit choice must exist."""
    if preferred != "auto":
        path = which(preferred)
        return (preferred, path) if path else (None, None)
    for name in DOWNLOADER_ORDER:
        path = which(name)
        if path:
            return name, path
    return None, None


def build_command(name, url, params_dir, tarball):
    """Downloader argv. Every supported downloader resumes partial files."""
    if name == "aria2c":
        return [name, "-x", "16", "-s", "16", "-c",
                "-d", params_dir, "-o", TARBALL_NAME, url]
    if name == "curl":
        return [name, "-fSL", "-C", "-", "-o", tarball, url]
    if name == "wget":
        return [name, "-c", "-O", tarball, url]
    raise ValueError(f"unsupported downloader: {name}")


def list_npz(params_dir):
    if not os.path.isdir(params_dir):
        return []
    return sorted(f for f in os.listdir(params_dir) if f.endswith(".npz"))


def weights_valid(params_dir, expected=EXPECTED_NPZ):
    """done.txt alone proves nothing; the payload must validate too."""
    return (os.path.isfile(os.path.join(params_dir, "done.txt"))
            and len(list_npz(params_dir)) == expected)


def run_observed(cmd, log_path, watch_path, progress_interval=15.0):
    """Run cmd with stdout/stderr captured to log_path; print progress.

    Returns dict(pid, returncode, elapsed_s, bytes). Raises nothing on
    child failure -- the non-zero rc is reported, not hidden.
    """
    t0 = time.time()
    with open(log_path, "ab") as log:
        log.write(("# " + " ".join(cmd) + "\n").encode())
        log.flush()
        proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
        pid = proc.pid
        print(f"downloader pid={pid}: {' '.join(cmd)}", flush=True)
        while True:
            rc = proc.poll()
            elapsed = time.time() - t0
            if rc is not None:
                break
            size = (os.path.getsize(watch_path)
                    if os.path.exists(watch_path) else 0)
            print(f"  ... {elapsed:6.0f}s  downloaded {size / 1e9:.2f} GB",
                  flush=True)
            time.sleep(progress_interval)
    size = (os.path.getsize(watch_path)
            if os.path.exists(watch_path) else 0)
    return {"pid": pid, "returncode": rc,
            "elapsed_s": round(elapsed, 1), "bytes": size}


def log_tail(log_path, n=2000):
    try:
        with open(log_path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - n))
            return fh.read().decode(errors="replace")
    except OSError:
        return "(log unavailable)"


def extract_tar(tarball, dest):
    """Stream-extract an uncompressed tar; return list of member names."""
    names = []
    with tarfile.open(tarball, "r|") as tf:
        for member in tf:
            try:
                tf.extract(member, dest, filter="data")
            except TypeError:            # Python < 3.12 lacks filter=
                tf.extract(member, dest)
            names.append(member.name)
    return names


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--params-dir", default="/content/bindcraft/params")
    ap.add_argument("--url", default=OFFICIAL_URL)
    ap.add_argument("--downloader", default="auto",
                    choices=["auto", *DOWNLOADER_ORDER])
    ap.add_argument("--expected", type=int, default=EXPECTED_NPZ)
    ap.add_argument("--min-bytes", type=int, default=MIN_TARBALL_BYTES)
    ap.add_argument("--progress-interval", type=float, default=15.0)
    args = ap.parse_args(argv)

    params_dir = args.params_dir
    tarball = os.path.join(params_dir, TARBALL_NAME)
    log_path = os.path.join(params_dir, "download.log")
    done_path = os.path.join(params_dir, "done.txt")
    os.makedirs(params_dir, exist_ok=True)

    # 1. skip path: valid existing weights -> no network at all
    if weights_valid(params_dir, args.expected):
        print(f"SKIP: {done_path} present and {args.expected} .npz files "
              f"validate; not downloading again")
        return 0
    if os.path.isfile(done_path):
        print("NOTE: done.txt exists but the payload does not validate "
              f"({len(list_npz(params_dir))} .npz != {args.expected}); "
              "ignoring done.txt and resuming/repairing the download")

    # 2. downloader precheck BEFORE launching anything
    name, path = find_downloader(args.downloader)
    if name is None:
        if args.downloader != "auto":
            print(f"ERROR: requested downloader {args.downloader!r} not found "
                  f"on PATH. Install it (e.g. apt-get install -y aria2) or "
                  f"rerun with --downloader auto/curl/wget.", file=sys.stderr)
        else:
            print(f"ERROR: no downloader found (tried "
                  f"{', '.join(DOWNLOADER_ORDER)}). Install one, e.g. "
                  f"apt-get install -y aria2", file=sys.stderr)
        return 1
    print(f"downloader: {name} ({path})")

    # 3. resume: a partial tarball is kept, never deleted
    partial = os.path.getsize(tarball) if os.path.exists(tarball) else 0
    if partial:
        print(f"resuming: keeping existing partial tarball "
              f"({partial:,} bytes); downloader invoked with resume flags")

    # 4. observed download -- non-zero exit stops here, immediately
    result = run_observed(build_command(name, args.url, params_dir, tarball),
                          log_path, tarball, args.progress_interval)
    print("download result: " + json.dumps(result))
    if result["returncode"] != 0:
        print(f"ERROR: {name} exited {result['returncode']} after "
              f"{result['elapsed_s']}s. Real error (log tail):\n"
              f"{log_tail(log_path)}", file=sys.stderr)
        return 1

    # 5. tarball plausibility
    if not os.path.exists(tarball) or result["bytes"] < args.min_bytes:
        print(f"ERROR: tarball missing or implausibly small "
              f"({result['bytes']:,} bytes < {args.min_bytes:,}). "
              f"Log tail:\n{log_tail(log_path)}", file=sys.stderr)
        return 1

    # 6. extract, then require exactly the expected payload
    print(f"extracting {tarball} ({result['bytes']:,} bytes) ...")
    try:
        extract_tar(tarball, params_dir)
    except (tarfile.TarError, OSError) as exc:
        print(f"ERROR: extraction failed: {exc!r}. The partial tarball is "
              f"kept at {tarball} for inspection.", file=sys.stderr)
        return 1
    npz = list_npz(params_dir)
    if len(npz) != args.expected:
        print(f"ERROR: expected {args.expected} .npz files, got {len(npz)}: "
              f"{npz}. Tarball kept at {tarball}; done.txt NOT written.",
              file=sys.stderr)
        return 1

    # 7. only now is the payload proven
    with open(done_path, "w") as fh:
        json.dump({"url": args.url, "downloader": name, **result,
                   "npz_files": npz}, fh, indent=2)
    print(f"OK: {args.expected} .npz files validated; {done_path} written "
          f"({result['bytes'] / 1e9:.2f} GB in {result['elapsed_s']}s "
          f"via {name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
