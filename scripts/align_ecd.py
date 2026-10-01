"""Stage 1.5 Part A - competition-relevant ECD human/mouse alignment.

Replaces the provisional full-length comparison. Aligns the human
competition construct (P00533-1 25..645, 621 aa) against the mouse ECD
(Q01279 25..647, 623 aa; boundary source: USER_PROVIDED_OFFICIAL_
COMPETITION_SLACK 2026-10-01; challenge page Mouse tab still empty).
No constant offset is assumed - positions come from the actual alignment.

Output:
- data/processed/human_mouse_ecd_alignment.csv  (one row per aligned column,
  including gap-only columns at either end)
- data/processed/human_mouse_ecd_alignment.meta.json

Run: .venv/bin/python scripts/align_ecd.py
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from Bio import Align, SeqIO
from Bio.Align import substitution_matrices

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"

HUMAN_BEGIN, HUMAN_END = 25, 645
MOUSE_BEGIN, MOUSE_END = 25, 647  # Slack-provided, challenge page still empty
PARAMS = {"matrix": "BLOSUM62", "mode": "global",
          "open_gap_score": -10.0, "extend_gap_score": -0.5}


def main() -> int:
    human_full = str(SeqIO.read(RAW / "P00533.fasta", "fasta").seq)
    mouse_full = str(SeqIO.read(RAW / "Q01279.fasta", "fasta").seq)
    human = human_full[HUMAN_BEGIN - 1:HUMAN_END]
    mouse = mouse_full[MOUSE_BEGIN - 1:MOUSE_END]

    aligner = Align.PairwiseAligner()
    aligner.substitution_matrix = substitution_matrices.load(PARAMS["matrix"])
    aligner.mode = PARAMS["mode"]
    aligner.open_gap_score = PARAMS["open_gap_score"]
    aligner.extend_gap_score = PARAMS["extend_gap_score"]
    aln = aligner.align(human, mouse)[0]
    matrix = substitution_matrices.load(PARAMS["matrix"])

    rows = []
    stats = {"identical": 0, "conservative": 0, "nonconservative": 0,
             "gap": 0, "human_only": 0, "mouse_only": 0}
    for h_i, m_i in zip(*aln.indices):
        if h_i == -1:
            rows.append({
                "human_uniprot_pos": "", "human_aa": "-",
                "human_construct_pos": "",
                "mouse_uniprot_pos": int(m_i) + MOUSE_BEGIN, "mouse_aa": mouse[m_i],
                "mouse_construct_pos": int(m_i) + 1,
                "class": "mouse_only",
            })
            stats["mouse_only"] += 1
            continue
        if m_i == -1:
            rows.append({
                "human_uniprot_pos": int(h_i) + HUMAN_BEGIN, "human_aa": human[h_i],
                "human_construct_pos": int(h_i) + 1,
                "mouse_uniprot_pos": "", "mouse_aa": "-",
                "mouse_construct_pos": "",
                "class": "human_only",
            })
            stats["human_only"] += 1
            stats["gap"] += 1
            continue
        h_aa, m_aa = human[h_i], mouse[m_i]
        if m_aa == h_aa:
            cls = "identical"
        elif matrix[h_aa, m_aa] > 0:
            cls = "conservative"
        else:
            cls = "nonconservative"
        stats[cls] += 1
        rows.append({
            "human_uniprot_pos": int(h_i) + HUMAN_BEGIN, "human_aa": h_aa,
            "human_construct_pos": int(h_i) + 1,
            "mouse_uniprot_pos": int(m_i) + MOUSE_BEGIN, "mouse_aa": m_aa,
            "mouse_construct_pos": int(m_i) + 1,
            "class": cls,
        })

    csv_path = OUT / "human_mouse_ecd_alignment.csv"
    with csv_path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    paired = stats["identical"] + stats["conservative"] + stats["nonconservative"]
    meta = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "params": PARAMS,
        "human": {"acc": "P00533-1", "begin": HUMAN_BEGIN, "end": HUMAN_END,
                  "length": len(human), "source": "competition challenge page"},
        "mouse": {"acc": "Q01279", "begin": MOUSE_BEGIN, "end": MOUSE_END,
                  "length": len(mouse),
                  "source": "USER_PROVIDED_OFFICIAL_COMPETITION_SLACK 2026-10-01; "
                            "challenge page Mouse tab empty on 2026-09-30 and 2026-10-01"},
        "aligned_columns": len(rows),
        "class_counts": stats,
        "identity_fraction_vs_paired_columns": round(stats["identical"] / paired, 4),
        "note": "Positions taken from the actual alignment; no constant offset. "
                "Mouse construct boundary is Slack-derived and must be replaced "
                "if the challenge page later publishes a different construct.",
    }
    (OUT / "human_mouse_ecd_alignment.meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
