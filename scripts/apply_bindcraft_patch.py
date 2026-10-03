"""Deterministically apply (or verify) the pinned STAGE2 relax-tolerance patch.

The scientific BindCraft tree is pinned at commit 7713aa0 (DECISIONS D-015).
DECISIONS D-019 (explicit user directive 2026-10-03) narrowly permits ONE
auditable patch: per-model PyRosetta relaxation failures must be recorded
(relax_failures.jsonl), the unrelaxed PDB retained, and the trajectory/run
continued instead of dying on a missing relaxed PDB / clean_pdb() call.

This script is the ONLY supported way to modify the BindCraft checkout:
- verifies the checkout is exactly the pinned commit (fail loudly otherwise);
- applies the committed unified diff with `git apply` (idempotent);
- refuses to touch a partially-patched tree;
- records pre/post file SHA256 to persistent metadata.

Stdlib only. Exit codes: 0 applied/already-applied/verified; 1 hard failure.
"""
import argparse
import json
import os
import subprocess
import sys
import time

try:
    from stage2_paths import sha256_file
except ImportError:  # standalone execution outside scripts/ on sys.path
    import hashlib

    def sha256_file(path):
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()

BINDCRAFT_COMMIT = "7713aa0d0d351e4117a8befeb8541f3a8ebd3368"

# marker substrings that MUST appear in each patched file after application
REQUIRED_MARKERS = {
    "bindcraft.py": ["STAGE2-PATCH", "record_stage2_relax_failure",
                     "STAGE2_RELAX_FAILURE"],
    "functions/colabdesign_utils.py": ["STAGE2-PATCH",
                                       "record_stage2_relax_failure",
                                       "STAGE2_RELAX_FAILURE"],
    "functions/generic_utils.py": ["STAGE2-PATCH",
                                   "def record_stage2_relax_failure"],
    "functions/pyrosetta_utils.py": ["STAGE2-PATCH",
                                    "class RelaxationFailure",
                                    "BEFORE clean_pdb"],
}
PATCH_REL = os.path.join("patches",
                         "bindcraft-7713aa0-relax-tolerance.patch")


def _git(bindcraft_dir, *args):
    p = subprocess.run(["git", *args], cwd=bindcraft_dir,
                       capture_output=True, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def current_commit(bindcraft_dir):
    rc, out, err = _git(bindcraft_dir, "rev-parse", "HEAD")
    if rc != 0:
        return None, err or "not a git checkout"
    return out, None


def marker_state(bindcraft_dir):
    """Return dict[file] -> bool: every required marker present."""
    state = {}
    for rel, markers in REQUIRED_MARKERS.items():
        path = os.path.join(bindcraft_dir, rel)
        if not os.path.isfile(path):
            state[rel] = False
            continue
        try:
            with open(path, errors="replace") as fh:
                text = fh.read()
        except OSError:
            state[rel] = False
            continue
        state[rel] = all(m in text for m in markers)
    return state


def file_hashes(bindcraft_dir):
    out = {}
    for rel in REQUIRED_MARKERS:
        path = os.path.join(bindcraft_dir, rel)
        out[rel] = sha256_file(path) if os.path.isfile(path) else None
    return out


def _metadata(status, bindcraft_dir, patch_path, commit, pre=None, note=None):
    meta = {
        "status": status,
        "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "bindcraft_commit_expected": BINDCRAFT_COMMIT,
        "bindcraft_commit_observed": commit,
        "patch_path": os.path.abspath(patch_path),
        "patch_sha256": (sha256_file(patch_path)
                         if os.path.isfile(patch_path) else None),
        "files": file_hashes(bindcraft_dir),
    }
    if pre is not None:
        meta["files_pre"] = pre
    if note:
        meta["note"] = note
    return meta


def apply_or_verify(*, bindcraft_dir, patch_path, verify_only=False):
    """Returns (metadata, exit_code). Never raises for expected failure modes."""
    if not os.path.isdir(bindcraft_dir):
        return (_metadata("BINDCRAFT_DIR_MISSING", bindcraft_dir, patch_path,
                          None), 1)
    if not os.path.isfile(patch_path):
        return (_metadata("PATCH_MISSING", bindcraft_dir, patch_path, None), 1)

    commit, err = current_commit(bindcraft_dir)
    if commit is None:
        return (_metadata("NOT_A_GIT_CHECKOUT", bindcraft_dir, patch_path,
                          None, note=err), 1)
    if commit != BINDCRAFT_COMMIT:
        return (_metadata("COMMIT_MISMATCH", bindcraft_dir, patch_path,
                          commit,
                          note=f"expected {BINDCRAFT_COMMIT}; refusing to patch"),
                1)

    state = marker_state(bindcraft_dir)
    n_patched = sum(1 for v in state.values() if v)
    pre = file_hashes(bindcraft_dir)

    if n_patched == len(REQUIRED_MARKERS):
        return (_metadata("ALREADY_APPLIED" if not verify_only
                          else "VERIFIED", bindcraft_dir, patch_path,
                          commit, pre=pre), 0)
    if n_patched != 0:
        return (_metadata("PATCH_STATE_AMBIGUOUS", bindcraft_dir, patch_path,
                          commit, pre=pre,
                          note=f"markers present in only {n_patched}/"
                               f"{len(REQUIRED_MARKERS)} files; manual "
                               f"inspection required; tree left untouched"),
                1)

    if verify_only:
        return (_metadata("NOT_PATCHED", bindcraft_dir, patch_path, commit,
                          pre=pre), 1)

    rc, out, err = _git(bindcraft_dir, "apply", "--check", patch_path)
    if rc != 0:
        return (_metadata("APPLY_CHECK_FAILED", bindcraft_dir, patch_path,
                          commit, pre=pre, note=(err or out)[:1000]), 1)

    rc, out, err = _git(bindcraft_dir, "apply", "--verbose", patch_path)
    if rc != 0:
        return (_metadata("APPLY_FAILED", bindcraft_dir, patch_path, commit,
                          pre=pre, note=(err or out)[:1000]), 1)

    post_state = marker_state(bindcraft_dir)
    if not all(post_state.values()):
        return (_metadata("POST_APPLY_MARKERS_MISSING", bindcraft_dir,
                          patch_path, commit, pre=pre,
                          note=f"marker state after apply: {post_state}"), 1)

    return (_metadata("APPLIED", bindcraft_dir, patch_path, commit, pre=pre),
            0)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    default_patch = os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), os.pardir, PATCH_REL))
    ap.add_argument("--bindcraft-dir", required=True)
    ap.add_argument("--patch", default=default_patch)
    ap.add_argument("--out", help="write metadata JSON to this path")
    ap.add_argument("--verify-only", action="store_true")
    args = ap.parse_args(argv)

    meta, rc = apply_or_verify(bindcraft_dir=args.bindcraft_dir,
                               patch_path=args.patch,
                               verify_only=args.verify_only)
    print(f"BINDCRAFT PATCH {meta['status']} "
          f"(commit {meta.get('bindcraft_commit_observed')})")
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)),
                    exist_ok=True)
        with open(args.out, "w") as fh:
            json.dump(meta, fh, indent=1, sort_keys=True)
            fh.write("\n")
        print(f"metadata -> {args.out}")
    if rc != 0 and meta.get("note"):
        print(meta["note"], file=sys.stderr)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
