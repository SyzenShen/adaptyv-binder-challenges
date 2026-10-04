"""Build data/processed/target_residue_map.json (directive item 12).

The generation crop  data/processed/6ARU_chainA_domain3_310-481.pdb  uses
resseq == UniProt biological numbering (6ARU auth numbering + 24, verified
through residue_map.csv). BindCraft output renumbers the target chain to
1..N local indices, so ANY post-generation geometry question must go
local index -> this map -> biological number. Guessing a fixed offset is
forbidden (BUG 017: "hotspot 390 not present" was this exact analysis bug).

The map is DERIVED, not assumed:
- crop PDB chain A resseq set must be exactly contiguous 310..481;
- every row is cross-checked against data/processed/residue_map.csv
  (UniProt position, residue identity) and the crop PDB itself;
- any mismatch aborts loudly — never emits a guessed map.

Stdlib only. Run: python scripts/build_target_residue_map.py [--out ...]
"""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CROP_PDB = ROOT / "data" / "processed" / "6ARU_chainA_domain3_310-481.pdb"
RESIDUE_MAP_CSV = ROOT / "data" / "processed" / "residue_map.csv"
DEFAULT_OUT = ROOT / "data" / "processed" / "target_residue_map.json"

TARGET_NAME = "human_EGFR_domainIII_310-481"
SOURCE_CHAIN = "A"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def crop_residues(path):
    """{resseq: resname} for chain A ATOM records (altloc ' '/A/1 only)."""
    res = {}
    with open(path) as fh:
        for line in fh:
            if not line.startswith("ATOM  "):
                continue
            if line[21:22] != SOURCE_CHAIN:
                continue
            if line[16:17] not in (" ", "A", "1"):
                continue
            try:
                resseq = int(line[22:26])
            except ValueError:
                continue
            res.setdefault(resseq, line[17:20].strip())
    return res


def load_uniprot_rows(csv_path):
    """uniprot_pos -> {aa, auth_seq} from the verified residue_map.csv."""
    rows = {}
    with open(csv_path, newline="") as fh:
        for row in csv.DictReader(fh):
            rows[int(row["uniprot_pos"])] = {
                "aa": row["uniprot_aa"],
                "auth_seq": row["pdb_auth_seq_id"],
                "in_pdb_construct": row["in_pdb_construct"],
                "pdb_aa": row["pdb_aa"],
                "coord_status": row["coord_status"],
            }
    return rows


THREE2ONE = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C",
    "GLN": "Q", "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I",
    "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F", "PRO": "P",
    "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V",
}


def build(crop_pdb=CROP_PDB, csv_path=RESIDUE_MAP_CSV):
    residues = crop_residues(crop_pdb)
    if not residues:
        raise SystemExit(f"FAIL LOUDLY: no chain {SOURCE_CHAIN} ATOM records "
                         f"in {crop_pdb}")
    lo, hi = min(residues), max(residues)
    missing = [r for r in range(lo, hi + 1) if r not in residues]
    if missing:
        raise SystemExit(
            f"FAIL LOUDLY: crop PDB numbering is not contiguous "
            f"({lo}..{hi}); gaps at {missing[:10]} — refusing to emit a "
            "guessed local index mapping")

    uniprot = load_uniprot_rows(csv_path)
    entries, conflicts = [], []
    for resseq in range(lo, hi + 1):
        resname = residues[resseq]
        aa1 = THREE2ONE.get(resname)
        row = uniprot.get(resseq)
        if row is None:
            conflicts.append({"input_pdb_residue": resseq,
                              "error": "absent from residue_map.csv"})
            continue
        if row["aa"] != aa1:
            conflicts.append({"input_pdb_residue": resseq,
                              "error": f"identity mismatch: crop PDB "
                                       f"{resname} vs UniProt {row['aa']}"})
            continue
        entries.append({
            "input_pdb_residue": resseq,          # == biological (verified)
            "biological_number": resseq,          # UniProt P00533 numbering
            "output_local_index": resseq - lo + 1,  # BindCraft output frame
            "residue_name": resname,
            "residue_aa1": aa1,
            "pdb_auth_seq_id": row["auth_seq"],   # 6ARU numbering (bio - 24)
        })
    if conflicts:
        raise SystemExit("FAIL LOUDLY: residue map cross-check conflicts: "
                         f"{conflicts[:10]}")
    return {
        "target_name": TARGET_NAME,
        "source_chain": SOURCE_CHAIN,
        "source_pdb": str(crop_pdb),
        "source_pdb_sha256": sha256_file(crop_pdb),
        "cross_checked_against": {
            "residue_map_csv": str(csv_path),
            "residue_map_csv_sha256": sha256_file(csv_path),
        },
        "numbering_note": (
            "crop input PDB resseq == UniProt biological numbering "
            "(6ARU auth + 24, verified via residue_map.csv); BindCraft "
            "output renumbers the target chain 1..N. Analysis must "
            "translate output_local_index -> biological_number via this "
            "artifact; guessing a constant offset is forbidden."),
        "local_index_span": [1, len(entries)],
        "biological_span": [lo, hi],
        "residues": entries,
        "counts": {"mapped": len(entries),
                   "conflicts": len(conflicts)},
    }


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    artifact = build()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(json.dumps(artifact, indent=2) + "\n")
    import os
    os.replace(tmp, out)
    print(f"wrote {out}: {artifact['counts']['mapped']} residues, "
          f"local 1..{artifact['local_index_span'][1]} <-> biological "
          f"{artifact['biological_span'][0]}..{artifact['biological_span'][1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
