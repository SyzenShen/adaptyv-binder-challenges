"""Align human EGFR competition construct to mouse EGFR reference (Q01279).

PROVISIONAL analysis: the official mouse construct is still unknown
(HUMAN_ACTIONS A2). This aligns the human competition construct
(UniProt 25..645) against the full-length Q01279 canonical sequence with a
documented substitution matrix and gap model, purely as a reference-level
human/mouse comparison. No mouse construct boundary is assumed.

Output: data/processed/human_mouse_alignment.csv with one row per human
construct residue: mouse aligned position/aa (Q01279 numbering) and the
per-column class identical / conservative / nonconservative / gap.

Run: .venv/bin/python scripts/align_species.py
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

PARAMS = {
    "matrix": "BLOSUM62",
    "mode": "global",
    "open_gap_score": -10.0,
    "extend_gap_score": -0.5,
}


def main() -> int:
    human = str(SeqIO.read(OUT / "human_construct_25_645.fasta", "fasta").seq)
    mouse_full = str(SeqIO.read(RAW / "Q01279.fasta", "fasta").seq)

    aligner = Align.PairwiseAligner()
    aligner.substitution_matrix = substitution_matrices.load(PARAMS["matrix"])
    aligner.mode = PARAMS["mode"]
    aligner.open_gap_score = PARAMS["open_gap_score"]
    aligner.extend_gap_score = PARAMS["extend_gap_score"]

    aln = aligner.align(human, mouse_full)[0]
    matrix = substitution_matrices.load(PARAMS["matrix"])

    rows = []
    h_pos = m_pos = 0  # 0-based offsets into human construct / mouse full seq
    m_start = aln.indices[1][0]  # mouse index of first aligned column
    stats = {"identical": 0, "conservative": 0, "nonconservative": 0, "gap": 0}
    for h_c, m_c in zip(*aln.indices):
        if h_c == -1:
            m_pos += 1  # insertion in mouse, no human row
            continue
        h_pos += 1
        h_aa = human[h_c]
        if m_c == -1:
            m_aa, mouse_uniprot_pos, cls = "-", "", "gap"
        else:
            m_aa = mouse_full[m_c]
            mouse_uniprot_pos = m_c + 1  # Q01279 canonical numbering
            if m_aa == h_aa:
                cls = "identical"
            elif matrix[h_aa, m_aa] > 0:
                cls = "conservative"
            else:
                cls = "nonconservative"
        stats[cls] += 1
        rows.append(
            {
                "human_uniprot_pos": h_c + 25,  # construct starts at UniProt 25
                "human_aa": h_aa,
                "construct_pos": h_c + 1,
                "mouse_uniprot_pos": mouse_uniprot_pos,
                "mouse_aa": m_aa,
                "class": cls,
            }
        )

    csv_path = OUT / "human_mouse_alignment.csv"
    with csv_path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    meta = {
        "status": "PROVISIONAL - mouse official construct unknown (A2 pending); "
                  "aligned against full-length Q01279 canonical sequence",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "params": PARAMS,
        "human_construct": "P00533-1 25..645",
        "mouse_reference": "Q01279 full length",
        "mouse_aligned_span": [
            int(m_start) + 1,
            int(aln.indices[1][-1]) + 1,
        ],
        "alignment_score": float(aln.score),
        "class_counts": stats,
        "identity_fraction": round(stats["identical"] / len(rows), 4),
    }
    (OUT / "human_mouse_alignment.meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
