#!/usr/bin/env python3
"""Observable, restart-safe AlphaFold2 weight provisioning for Stage 2.

Resolution order (no network is touched unless necessary):

  1. bindcraft/params already has the exact official 15-file set  -> use it
  2. persistent Drive cache (extracted files)                    -> restore
  3. persistent Drive cache archive                               -> extract
  4. observable `wget -c` download into the Drive cache, verify, extract

Why the cache stores EXTRACTED FILES (not only the tar): after a Colab
runtime reset the common path is a plain file copy back into
bindcraft/params followed by the exact-set validation; there is no
extraction step or tar dependency on that path. The archive is kept
alongside only so the set can be rebuilt/re-audited without a re-download;
its SHA256 is recorded as an *observed* digest — we do not claim
authenticity (the upstream tar ships no signature we verify).

Correctness rule (BUG 006/007): authority is the exact set of 15 .npz
filenames, each non-empty and readable. A stale done.txt is NEVER
authoritative. Counting alone is insufficient: 14 missing one file and 16
containing an extra file are both rejected.

Stdlib only.
"""
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import time
from pathlib import Path

WEIGHT_URL = ("https://storage.googleapis.com/alphafold/"
              "alphafold_params_2022-12-06.tar")
ARCHIVE_NAME = "alphafold_params_2022-12-06.tar"
ARCHIVE_SUBDIR = "archive"
PART_SUFFIX = ".part"
RECORD_NAME = "download_record.json"
DONE_NAME = "done.txt"            # recorded as non-authoritative only


def required_weights():
    """Official alphafold_params_2022-12-06 set: 5 base + 5 pTM + 5
    multimer-v3 = exactly 15 .npz files."""
    names = []
    for i in range(1, 6):
        names.append(f"params_model_{i}.npz")
        names.append(f"params_model_{i}_ptm.npz")
        names.append(f"params_model_{i}_multimer_v3.npz")
    return frozenset(names)


REQUIRED_SET = required_weights()
REQUIRED_COUNT = len(REQUIRED_SET)
assert REQUIRED_COUNT == 15


def validate_weights(directory, min_bytes=1):
    """Exact-set validation. done.txt, extra npz, empty files all count."""
    d = Path(directory)
    present = {p.name for p in d.glob("*.npz")} if d.is_dir() else set()
    nonempty = {p.name for p in d.glob("*.npz")
                if _safe_size(p) >= min_bytes}
    missing = sorted(REQUIRED_SET - present)
    empty = sorted(present - nonempty)
    unexpected = sorted(present - REQUIRED_SET)
    ok = not missing and not empty and not unexpected
    return ok, {
        "ok": ok,
        "directory": str(d),
        "present_count": len(present),
        "required_count": REQUIRED_COUNT,
        "missing": missing,
        "empty_or_small": empty,
        "unexpected": unexpected,
        "done_txt_present": (d / DONE_NAME).exists() if d.is_dir() else False,
        "authority": "exact 15-file .npz set; done.txt is never authoritative",
    }


def _safe_size(p):
    try:
        return p.stat().st_size
    except OSError:
        return 0


def _sha256(path, buf=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(buf), b""):
            h.update(chunk)
    return h.hexdigest()


def _copy_set(src_dir, dst_dir, min_bytes=1):
    dst_dir = Path(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)
    for name in sorted(REQUIRED_SET):
        shutil.copy2(Path(src_dir) / name, dst_dir / name)


def _extract_tar(archive, dst_dir):
    """Extract ONLY the required members; an archive containing extra .npz
    or missing files fails validation afterwards rather than being trusted.
    """
    dst_dir = Path(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r") as tf:
        members = tf.getmembers()
        npz_members = {Path(m.name).name for m in members
                       if m.name.endswith(".npz")}
        wanted = [m for m in members
                  if Path(m.name).name in REQUIRED_SET]
        by_name = {}
        for m in wanted:
            by_name.setdefault(Path(m.name).name, m)
        if len(npz_members) != REQUIRED_COUNT or \
                npz_members != set(REQUIRED_SET):
            return False, {
                "ok": False,
                "archive_npz_count": len(npz_members),
                "missing_in_archive": sorted(REQUIRED_SET - npz_members),
                "unexpected_in_archive": sorted(npz_members - REQUIRED_SET),
            }
        for name, m in by_name.items():
            src = tf.extractfile(m)
            if src is None:
                return False, {"ok": False, "error": f"unreadable {name}"}
            with open(dst_dir / name, "wb") as out:
                shutil.copyfileobj(src, out)
    return True, {"ok": True}


def guarantee_wget(allow_install=True):
    """Return a wget executable path, installing wget once if allowed.
    Raises if no guaranteed downloader is available (BUG 005)."""
    wget = shutil.which("wget")
    if wget:
        return wget
    if allow_install and shutil.which("apt-get"):
        for cmd in (["apt-get", "update", "-qq"],
                    ["apt-get", "install", "-y", "wget"]):
            p = subprocess.run(cmd, capture_output=True, text=True)
            if p.returncode != 0:
                raise RuntimeError(
                    f"could not guarantee wget via {' '.join(cmd)}: "
                    f"{p.stderr[-500:]}")
        wget = shutil.which("wget")
    if not wget:
        raise RuntimeError(
            "no guaranteed downloader: wget not found (aria2c is never "
            "assumed present)")
    return wget


def observed_download(wget_exe, url, archive_path, log_path):
    """Blocking, observed, resumable download (BUG 004).

    Downloads to `<archive>.part` with `wget -c` (resume survives a reset),
    then atomically renames on rc==0. Returns a full provenance record.
    """
    archive_path = Path(archive_path)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    part = archive_path.with_name(archive_path.name + PART_SUFFIX)
    t0 = time.time()
    with open(log_path, "w") as log:
        proc = subprocess.Popen(
            [wget_exe, "-c", "--progress=dot:giga",
             "-o", str(log_path), "-O", str(part), url],
            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
            text=True)
        pid = proc.pid
        rc = proc.wait()
    elapsed = round(time.time() - t0, 1)
    record = {"pid": pid, "returncode": rc, "elapsed_s": elapsed,
              "log_path": str(log_path), "url": url,
              "part_path": str(part)}
    if rc != 0:
        record["bytes_on_disk"] = _safe_size(part)
        record["error"] = "wget exited non-zero; .part retained for resume"
        return False, record
    os.replace(part, archive_path)
    size = _safe_size(archive_path)
    record.update({"bytes_on_disk": size, "archive_path": str(archive_path),
                   "archive_sha256": _sha256(archive_path),
                   "sha256_note": ("observed byte digest only; upstream tar "
                                   "signature/authenticity is not verified")})
    return True, record


def _write_record(cache_dir, record):
    path = Path(cache_dir) / RECORD_NAME
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(record, indent=2))
    os.replace(tmp, path)
    return path


def ensure_weights(*, params_dir, cache_dir, log_dir, url=WEIGHT_URL,
                   dry_run=False, allow_install=True, min_bytes=1):
    """Provision the exact 15-file AF2 set into params_dir. Returns a
    result dict; `action` in LOCAL_VALID / CACHE_RESTORED /
    ARCHIVE_EXTRACTED / DOWNLOADED / WOULD_DOWNLOAD / FAIL."""
    params_dir, cache_dir = Path(params_dir), Path(cache_dir)
    cache_npz = cache_dir
    cache_archive_dir = cache_dir / ARCHIVE_SUBDIR
    cache_archive = cache_archive_dir / ARCHIVE_NAME
    log_dir = Path(log_dir)
    params_dir.mkdir(parents=True, exist_ok=True)

    # 1. local
    ok, rep = validate_weights(params_dir, min_bytes)
    if ok:
        return {"action": "LOCAL_VALID", "ok": True, "validation": rep}

    # 2. extracted-files cache
    okc, crep = validate_weights(cache_npz, min_bytes)
    if okc:
        _copy_set(cache_npz, params_dir, min_bytes)
        ok2, rep2 = validate_weights(params_dir, min_bytes)
        if ok2:
            return {"action": "CACHE_RESTORED", "ok": True,
                    "cache_validation": crep, "validation": rep2}

    # 3. cached archive
    if cache_archive.is_file():
        okx, xrep = _extract_tar(cache_archive, cache_npz)
        okx2, crep2 = (validate_weights(cache_npz, min_bytes) if okx
                       else (False, xrep))
        if okx2:
            _copy_set(cache_npz, params_dir, min_bytes)
            ok3, rep3 = validate_weights(params_dir, min_bytes)
            if ok3:
                return {"action": "ARCHIVE_EXTRACTED", "ok": True,
                        "archive_sha256": _sha256(cache_archive),
                        "validation": rep3}

    if dry_run:
        return {"action": "WOULD_DOWNLOAD", "ok": True, "url": url,
                "note": "dry-run: no network; local/cache had no valid set",
                "local_validation": rep}

    # 4. observable download into the persistent cache
    try:
        wget_exe = guarantee_wget(allow_install=allow_install)
    except RuntimeError as exc:
        return {"action": "FAIL", "ok": False, "stage": "downloader",
                "error": str(exc)}

    log_path = log_dir / "af2_weights_download.log"
    okd, drec = observed_download(wget_exe, url, cache_archive, log_path)
    _write_record(cache_dir, drec)
    if not okd:
        return {"action": "FAIL", "ok": False, "stage": "download",
                **drec}

    okx, xrep = _extract_tar(cache_archive, cache_npz)
    if not okx:
        return {"action": "FAIL", "ok": False, "stage": "extract", **xrep,
                **drec}
    okc2, crep3 = validate_weights(cache_npz, min_bytes)
    if not okc2:
        return {"action": "FAIL", "ok": False, "stage": "cache_validation",
                "validation": crep3, **drec}
    _copy_set(cache_npz, params_dir, min_bytes)
    okf, repf = validate_weights(params_dir, min_bytes)
    if not okf:
        return {"action": "FAIL", "ok": False, "stage": "restore",
                "validation": repf, **drec}
    return {"action": "DOWNLOADED", "ok": True, "validation": repf,
            "download": drec}


if __name__ == "__main__":
    import argparse
    import sys
    ap = argparse.ArgumentParser()
    ap.add_argument("--params-dir", required=True)
    ap.add_argument("--cache-dir", required=True)
    ap.add_argument("--log-dir", required=True)
    ap.add_argument("--out", help="also persist the JSON result here")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    result = ensure_weights(params_dir=args.params_dir,
                            cache_dir=args.cache_dir,
                            log_dir=args.log_dir, dry_run=args.dry_run)
    text = json.dumps(result, indent=2)
    print(text)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_suffix(out.suffix + ".tmp")
        tmp.write_text(text)
        os.replace(tmp, out)
    raise SystemExit(0 if result.get("ok") else 1)
