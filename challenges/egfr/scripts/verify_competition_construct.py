"""Verify the competition-page human construct sequence char-by-char.

Re-fetches the official challenge page, extracts the embedded 621 aa human
EGFR target sequence, and compares it against the UniProt P00533 slice
25..645 built by build_residue_map.py. Writes a machine-readable verdict to
data/processed/competition_construct_check.json. If the page structure has
changed and extraction fails, the failure is recorded (never guessed).

Run: .venv/bin/python scripts/verify_competition_construct.py
"""
from __future__ import annotations

import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from Bio import SeqIO

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "processed"
URL = "https://proteinbase.com/competitions/anthropic-adaptyv-2026/challenges/egfr"
EXPECTED_LEN = 621


def extract_page_sequence(page: str) -> str | None:
    """Find the longest all-caps protein-like run in the page payload."""
    text = html.unescape(page)
    candidates = re.findall(r"[A-Z]{400,}", text)
    candidates = [c for c in candidates if set(c) <= set("ACDEFGHIKLMNPQRSTVWY")]
    if not candidates:
        return None
    return max(candidates, key=len)


def main() -> int:
    local = str(SeqIO.read(OUT / "human_construct_25_645.fasta", "fasta").seq)
    verdict = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "page_url": URL,
        "local_construct": "data/processed/human_construct_25_645.fasta",
        "local_length": len(local),
        "page_sequence_extracted": False,
        "page_sequence_length": None,
        "char_by_char_identical": None,
        "first_mismatch": None,
        "note": None,
    }
    try:
        resp = requests.get(URL, timeout=60)
        resp.raise_for_status()
    except Exception as exc:  # network failure is a real, recorded outcome
        verdict["note"] = f"fetch_failed:{type(exc).__name__}"
        (OUT / "competition_construct_check.json").write_text(json.dumps(verdict, indent=2) + "\n")
        print(verdict["note"])
        return 1

    page_seq = extract_page_sequence(resp.text)
    if page_seq is None:
        verdict["note"] = "extraction_failed:no_protein_sequence_run_in_page"
    else:
        verdict["page_sequence_extracted"] = True
        verdict["page_sequence_length"] = len(page_seq)
        verdict["char_by_char_identical"] = page_seq == local
        if page_seq != local:
            for i, (a, b) in enumerate(zip(local, page_seq)):
                if a != b:
                    verdict["first_mismatch"] = {"pos_1based": i + 1, "local": a, "page": b}
                    break
            else:
                verdict["first_mismatch"] = {"pos_1based": min(len(local), len(page_seq)) + 1,
                                             "local": "<end>", "page": "<end>"}
        if verdict["char_by_char_identical"]:
            verdict["note"] = "page sequence identical to UniProt P00533-1 slice 25..645"
        else:
            verdict["note"] = "MISMATCH between page sequence and UniProt slice"

    (OUT / "competition_construct_check.json").write_text(json.dumps(verdict, indent=2) + "\n")
    print(json.dumps(verdict, indent=2))
    return 0 if verdict["char_by_char_identical"] else 1


if __name__ == "__main__":
    sys.exit(main())
