"""Build the per-residue map for the human EGFR competition construct.

Reads data/raw/P00533.fasta and data/raw/6ARU.cif (downloaded by
download_targets.py, hashes in data/raw/targets.manifest.json) and writes:

- data/processed/residue_map.csv       one row per UniProt 25..645 residue
- data/processed/residue_map.meta.json evidence: spans, conflicts, counts
- data/processed/human_construct_25_645.fasta  competition construct slice

Numbering rules (all derived from the mmCIF, not hardcoded):
- struct_ref_seq aligns PDB entity sequence to UniProt; offset is computed
  from db_align_beg - seq_align_beg and asserted contiguous for entity 1.
- label_seq_id / auth_seq_id come from _pdbx_poly_seq_scheme (chain A).
- Missing-in-density = in poly_seq_scheme but absent from _atom_site.
- Conflicts and expression tags come from _struct_ref_seq_dif.

Run: .venv/bin/python scripts/build_residue_map.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from Bio import SeqIO
from Bio.PDB.MMCIF2Dict import MMCIF2Dict
from Bio.Data.IUPACData import protein_letters_3to1_extended as TO1

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"

CONSTRUCT_BEGIN = 25   # competition page, verified 2026-09-30
CONSTRUCT_END = 645    # competition page, verified 2026-09-30
PDB_ID = "6ARU"
TARGET_AUTH_CHAIN = "A"

THREE_TO_ONE = {k.upper(): v for k, v in TO1.items()}


def one(mon_id: str) -> str:
    return THREE_TO_ONE.get(mon_id.upper(), "X")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    rec = SeqIO.read(RAW / "P00533.fasta", "fasta")
    uniprot_seq = str(rec.seq)
    construct = uniprot_seq[CONSTRUCT_BEGIN - 1 : CONSTRUCT_END]
    assert len(construct) == CONSTRUCT_END - CONSTRUCT_BEGIN + 1

    d = MMCIF2Dict(str(RAW / "6ARU.cif"))

    # --- struct_ref_seq: entity 1 -> UniProt P00533, compute offset from data
    ref_ids = d["_struct_ref_seq.ref_id"]
    ent_of_ref = {r: e for r, e in zip(d["_struct_ref.id"], d["_struct_ref.entity_id"])}
    spans = []
    for i, rid in enumerate(ref_ids):
        if ent_of_ref[rid] != "1":
            continue
        spans.append(
            (
                int(d["_struct_ref_seq.seq_align_beg"][i]),
                int(d["_struct_ref_seq.seq_align_end"][i]),
                int(d["_struct_ref_seq.db_align_beg"][i]),
                int(d["_struct_ref_seq.db_align_end"][i]),
            )
        )
    assert len(spans) == 1, f"expected one contiguous UNP span for entity 1, got {spans}"
    sb, se, db_b, db_e = spans[0]
    offset = db_b - sb
    assert se - sb == db_e - db_b, "non-contiguous entity/UniProt alignment"

    # --- struct_ref_seq_dif for entity 1 (conflicts, tags)
    dif = {}
    n = len(d["_struct_ref_seq_dif.align_id"])
    for i in range(n):
        if d["_struct_ref_seq_dif.pdbx_pdb_strand_id"][i] != TARGET_AUTH_CHAIN:
            continue
        label = int(d["_struct_ref_seq_dif.seq_num"][i])
        dif[label] = {
            "pdb_mon": d["_struct_ref_seq_dif.mon_id"][i],
            "db_mon": d["_struct_ref_seq_dif.db_mon_id"][i],
            "db_pos": d["_struct_ref_seq_dif.pdbx_seq_db_seq_num"][i],
            "details": d["_struct_ref_seq_dif.details"][i],
        }

    # --- poly_seq_scheme for the target chain: label<->auth numbering
    scheme = []
    for i in range(len(d["_pdbx_poly_seq_scheme.asym_id"])):
        if d["_pdbx_poly_seq_scheme.pdb_strand_id"][i] != TARGET_AUTH_CHAIN:
            continue
        scheme.append(
            {
                "label_asym": d["_pdbx_poly_seq_scheme.asym_id"][i],
                "label_seq": int(d["_pdbx_poly_seq_scheme.seq_id"][i]),
                "mon": d["_pdbx_poly_seq_scheme.mon_id"][i],
                "auth_asym": d["_pdbx_poly_seq_scheme.pdb_strand_id"][i],
                "auth_seq": d["_pdbx_poly_seq_scheme.pdb_seq_num"][i],
                "ins": d["_pdbx_poly_seq_scheme.pdb_ins_code"][i],
            }
        )
    by_label = {r["label_seq"]: r for r in scheme}
    label_asym = scheme[0]["label_asym"]

    # --- residues with coordinates (atom_site, label asym of target chain)
    have = set()
    for i in range(len(d["_atom_site.label_asym_id"])):
        if d["_atom_site.label_asym_id"][i] == label_asym:
            have.add(int(d["_atom_site.label_seq_id"][i]))

    # --- struct_conn annotations touching the target chain
    disulf = {}   # label_seq -> partner label_seq
    glycan = {}   # label_seq -> glycan chain asym
    if "_struct_conn.id" in d:
        for i in range(len(d["_struct_conn.id"])):
            t = d["_struct_conn.conn_type_id"][i]
            p1 = (
                d["_struct_conn.ptnr1_label_asym_id"][i],
                d["_struct_conn.ptnr1_label_comp_id"][i],
                d["_struct_conn.ptnr1_label_seq_id"][i],
            )
            p2 = (
                d["_struct_conn.ptnr2_label_asym_id"][i],
                d["_struct_conn.ptnr2_label_comp_id"][i],
                d["_struct_conn.ptnr2_label_seq_id"][i],
            )
            if t == "disulf":
                for a, b in ((p1, p2), (p2, p1)):
                    if a[0] == label_asym and b[0] == label_asym:
                        disulf[int(a[2])] = int(b[2])
            elif t == "covale":
                for a, b in ((p1, p2), (p2, p1)):
                    if a[0] == label_asym and b[0] != label_asym:
                        glycan[int(a[2])] = b[0]

    # --- N-glycosylation sequons on the UniProt sequence (N-X-S/T, X != P)
    sequon = set()
    for pos0 in range(len(uniprot_seq) - 2):
        if (
            uniprot_seq[pos0] == "N"
            and uniprot_seq[pos0 + 1] != "P"
            and uniprot_seq[pos0 + 2] in "ST"
        ):
            sequon.add(pos0 + 1)  # 1-based UniProt position of the Asn

    # --- emit rows for the competition construct UniProt 25..645
    rows = []
    for upos in range(CONSTRUCT_BEGIN, CONSTRUCT_END + 1):
        label = upos - offset  # entity/label numbering, valid only if inside span
        # strictly inside the UniProt-aligned span; labels beyond it are
        # expression-tag residues (dif detail "expression tag"), NOT UniProt
        # positions, and must not be mapped onto the construct tail.
        in_pdb_construct = sb <= label <= se
        row = {
            "species": "human",
            "uniprot_acc": "P00533-1",
            "uniprot_pos": upos,
            "uniprot_aa": uniprot_seq[upos - 1],
            "construct_pos": upos - CONSTRUCT_BEGIN + 1,
            "pdb_id": PDB_ID,
            "in_pdb_construct": "yes" if in_pdb_construct else "no",
            "pdb_label_asym_id": "",
            "pdb_label_seq_id": "",
            "pdb_auth_asym_id": "",
            "pdb_auth_seq_id": "",
            "pdb_ins_code": "",
            "pdb_aa": "",
            "pdb_vs_uniprot": "na",
            "coord_status": "not_in_construct",
            "disulfide_partner_uniprot": "",
            "glycan_observed_chain": "",
            "n_glyc_sequon": "yes" if upos in sequon else "no",
        }
        if in_pdb_construct and label in by_label:
            s = by_label[label]
            row.update(
                pdb_label_asym_id=s["label_asym"],
                pdb_label_seq_id=label,
                pdb_auth_asym_id=s["auth_asym"],
                pdb_auth_seq_id=s["auth_seq"],
                pdb_ins_code="" if s["ins"] in ("?", ".") else s["ins"],
                pdb_aa=one(s["mon"]),
                coord_status="coordinates" if label in have else "missing",
            )
            if label in dif:
                dd = dif[label]
                row["pdb_vs_uniprot"] = (
                    f"{dd['details']}:{dd['db_mon']}{dd['db_pos']}->{one(dd['pdb_mon'])}"
                    if dd["db_mon"] not in ("?", ".")
                    else f"{dd['details']}:{one(dd['pdb_mon'])}"
                )
            elif row["pdb_aa"] == row["uniprot_aa"]:
                row["pdb_vs_uniprot"] = "identical"
            else:
                row["pdb_vs_uniprot"] = "mismatch_unannotated"
            if label in disulf:
                row["disulfide_partner_uniprot"] = disulf[label] + offset
            if label in glycan:
                row["glycan_observed_chain"] = glycan[label]
        rows.append(row)

    csv_path = OUT / "residue_map.csv"
    with csv_path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    meta = {
        "inputs": {
            "uniprot_fasta": "data/raw/P00533.fasta",
            "mmcif": "data/raw/6ARU.cif",
            "hashes": "data/raw/targets.manifest.json",
        },
        "competition_construct": {
            "uniprot_begin": CONSTRUCT_BEGIN,
            "uniprot_end": CONSTRUCT_END,
            "length": len(construct),
        },
        "pdb": {
            "id": PDB_ID,
            "auth_chain": TARGET_AUTH_CHAIN,
            "label_asym": label_asym,
            "struct_ref_seq_span": {
                "seq_align_beg": sb, "seq_align_end": se,
                "db_align_beg": db_b, "db_align_end": db_e,
                "offset_uniprot_minus_label": offset,
            },
            "differences": {str(k): v for k, v in dif.items()},
            "expression_tag_labels": sorted(
                k for k, v in dif.items() if v["details"] == "expression tag"
            ),
            "residues_with_coordinates": len(have),
            "missing_in_density_uniprot": sorted(
                l + offset
                for l in by_label
                if l not in have and CONSTRUCT_BEGIN <= l + offset <= CONSTRUCT_END
            ),
            "glycan_links_uniprot": {str(k + offset): v for k, v in glycan.items()},
        },
        "rows": len(rows),
    }
    (OUT / "residue_map.meta.json").write_text(json.dumps(meta, indent=2) + "\n")

    fasta_path = OUT / "human_construct_25_645.fasta"
    fasta_path.write_text(
        f">human_EGFR_competition_construct|P00533-1:{CONSTRUCT_BEGIN}-{CONSTRUCT_END}\n"
        + "\n".join(construct[i : i + 60] for i in range(0, len(construct), 60))
        + "\n"
    )

    print(f"rows: {len(rows)}  construct len: {len(construct)}")
    print(f"offset (uniprot - label): {offset}")
    print(f"coordinates: {len(have)}; missing in density: {meta['pdb']['missing_in_density_uniprot']}")
    print(f"differences: {json.dumps(meta['pdb']['differences'])}")
    print(f"glycan links (uniprot): {meta['pdb']['glycan_links_uniprot']}")
    print(f"wrote {csv_path}, residue_map.meta.json, human_construct_25_645.fasta")
    return 0


if __name__ == "__main__":
    sys.exit(main())
