"""Download official target files into data/raw/ with a verifiable manifest.

Uses requests (locked in .venv, certifi CA bundle) because the python.org
macOS interpreter lacks system root certificates. Idempotent: a file is
re-downloaded only if missing or its SHA256 differs from the manifest.
Every entry records source URL, UTC retrieval time, byte size and SHA256.

Run: .venv/bin/python scripts/download_targets.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
MANIFEST = RAW / "targets.manifest.json"

# url, local name, role. Mouse FASTA is the Q01279 reference only; the
# official mouse construct boundaries remain unknown (HUMAN_ACTIONS A2).
TARGETS = [
    (
        "https://rest.uniprot.org/uniprotkb/P00533.fasta",
        "P00533.fasta",
        "human EGFR UniProt canonical isoform P00533-1",
    ),
    (
        "https://rest.uniprot.org/uniprotkb/Q01279.fasta",
        "Q01279.fasta",
        "mouse EGFR UniProt reference (provisional; official construct unknown)",
    ),
    (
        "https://files.rcsb.org/download/6ARU.cif",
        "6ARU.cif",
        "PDB 6ARU mmCIF, competition-recommended human structure reference",
    ),
]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(url: str, dest: Path) -> None:
    with requests.get(url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with dest.open("wb") as out:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                out.write(chunk)


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = {"entries": []}
    if MANIFEST.exists():
        manifest = json.loads(MANIFEST.read_text())
    by_name = {e["file"]: e for e in manifest["entries"]}

    for url, name, role in TARGETS:
        dest = RAW / name
        known = by_name.get(name, {})
        if dest.exists() and known.get("sha256") == sha256_of(dest):
            print(f"SKIP  {name} (sha256 matches manifest)")
            continue
        print(f"GET   {url}")
        fetch(url, dest)
        entry = {
            "file": name,
            "url": url,
            "role": role,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "bytes": dest.stat().st_size,
            "sha256": sha256_of(dest),
        }
        by_name[name] = entry
        print(f"      -> {entry['bytes']} bytes, sha256 {entry['sha256'][:16]}...")

    manifest["entries"] = [by_name[n] for _, n, _ in TARGETS if n in by_name]
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"manifest written: {MANIFEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
