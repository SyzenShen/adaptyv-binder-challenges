"""Analyse a BindCraft run directory against the approved B epitope envelope.

Stdlib-only (runs in the Colab kernel and locally). Target numbering in the
BindCraft output PDBs is the cropped-PDB numbering (UniProt 310-481, chain A);
the hallucinated binder is chain B.

Metrics per trajectory PDB:
- binder length; heavy-atom interface pairs <4.5 A; Cbeta pairs <8 A
- target residues contacted; how many/which are inside envelope B (390-403,
  421-431); fraction of interface residue-pairs landing on B
- minimum binder distance to B and to the rest of the target
- severe cross-chain clashes <2.3 A; contacts to crop-edge residues
  (310-314 / 477-481) as an edge-artefact screen
- best matching row(s) from trajectory_stats.csv / mpnn_design_stats.csv

A completed trajectory is NOT a successful binder; this script only reports
geometry. Acceptance is BindCraft's own filter decision plus visual review.
"""
import argparse
import csv
import json
import math
import re
from pathlib import Path

ENVELOPE_B = list(range(390, 404)) + list(range(421, 432))
EDGE_ZONES = list(range(310, 315)) + list(range(477, 482))
HEAVY_CUTOFF = 4.5
CB_CUTOFF = 8.0
CLASH_CUTOFF = 2.3
NAME_RE = re.compile(r"^(?P<prefix>.+)_l(?P<length>\d+)_s(?P<seed>\d+)(?:_model(?P<model>\d+))?$")


def parse_pdb(path):
    """Return {chain: {resseq: {"aa": str, "atoms": {name: (x,y,z,elem)}}}}."""
    chains = {}
    with open(path) as fh:
        for line in fh:
            if not line.startswith(("ATOM  ", "HETATM")):
                continue
            atom_name = line[12:16].strip()
            altloc = line[16:17]
            if altloc not in (" ", "A", "1"):
                continue
            chain = line[21:22].strip() or " "
            try:
                resseq = int(line[22:26])
            except ValueError:
                continue
            elem = (line[76:78].strip() or atom_name.lstrip("0123456789"))[:1]
            if elem == "H":
                continue
            xyz = (float(line[30:38]), float(line[38:46]), float(line[46:54]))
            res = chains.setdefault(chain, {}).setdefault(
                resseq, {"aa": line[17:20].strip(), "atoms": {}})
            if atom_name not in res["atoms"]:  # first altloc wins
                res["atoms"][atom_name] = (xyz[0], xyz[1], xyz[2], elem)
    return chains


def dist(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def cb(res):
    if "CB" in res["atoms"]:
        return res["atoms"]["CB"][:3]
    return res["atoms"].get("CA", (None,))[:3] if "CA" in res["atoms"] else None


def analyse_pdb(path, folder):
    chains = parse_pdb(path)
    if "A" not in chains or "B" not in chains:
        return {"pdb": path.name, "folder": folder, "status": "parse_error: chains A/B missing"}
    target, binder = chains["A"], chains["B"]

    t_atoms = {res: [(n, v) for n, v in d["atoms"].items()]
               for res, d in target.items()}
    b_atoms = [(res, n, v) for res, d in binder.items()
               for n, v in d["atoms"].items()]

    pairs_heavy = set()
    pairs_cb = set()
    clashes = []
    min_b, min_off = 1e9, 1e9
    for bres, bname, bv in b_atoms:
        for tres, atoms in t_atoms.items():
            dmin = min(dist(bv[:3], av[:3]) for _, av in atoms)
            if tres in ENVELOPE_B:
                min_b = min(min_b, dmin)
            else:
                min_off = min(min_off, dmin)
            if dmin < HEAVY_CUTOFF:
                pairs_heavy.add((tres, bres))
            if dmin < CLASH_CUTOFF:
                clashes.append((tres, bres, bname, round(dmin, 2)))
    for bres, bd in binder.items():
        bc = cb(bd)
        if bc is None:
            continue
        for tres, td in target.items():
            tc = cb(td)
            if tc is not None and dist(bc, tc) < CB_CUTOFF:
                pairs_cb.add((tres, bres))

    t_contacted = sorted({t for t, _ in pairs_heavy})
    b_contacted = sorted({b for _, b in pairs_heavy})
    on_b = [(t, b) for t, b in pairs_heavy if t in ENVELOPE_B]
    edge = [(t, b) for t, b in pairs_heavy if t in EDGE_ZONES]
    m = NAME_RE.match(Path(path).stem)
    info = m.groupdict() if m else {"length": None, "seed": None, "model": None}
    return {
        "pdb": path.name,
        "folder": folder,
        "status": "ok",
        "seed": int(info["seed"]) if info["seed"] else None,
        "binder_length": int(info["length"]) if info["length"] else len(binder),
        "model": info["model"],
        "n_interface_pairs_heavy": len(pairs_heavy),
        "n_interface_pairs_cb8": len(pairs_cb),
        "n_binder_res_in_contact": len(b_contacted),
        "n_target_res_contacted": len(t_contacted),
        "target_res_contacted": t_contacted,
        "n_B_res_contacted": len({t for t, _ in on_b}),
        "B_res_contacted": sorted({t for t, _ in on_b}),
        "fraction_interface_pairs_on_B": round(len(on_b) / len(pairs_heavy), 3)
        if pairs_heavy else 0.0,
        "min_dist_binder_to_B_A": None if min_b > 1e8 else round(min_b, 2),
        "min_dist_binder_to_offtarget_A": None if min_off > 1e8 else round(min_off, 2),
        "n_severe_clashes_lt2p3": len(clashes),
        "crop_edge_contact_pairs": len(edge),
        "crop_edge_res_contacted": sorted({t for t, _ in edge}),
        "migrated_off_B": (len(on_b) == 0)
        or (pairs_heavy and len(on_b) / len(pairs_heavy) < 0.5),
    }


def attach_csv_rows(run_dir, names):
    out = {}
    for name in names:
        p = run_dir / name
        if p.exists():
            with open(p, newline="") as fh:
                out[name] = list(csv.DictReader(fh))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    run_dir = Path(args.run_dir)

    folders = {"Trajectory/Relaxed": "relaxed",
               "Trajectory/LowConfidence": "low_confidence",
               "Trajectory/Clashing": "clashing",
               "Accepted": "accepted"}
    records = []
    for folder, tag in folders.items():
        d = run_dir / folder
        if not d.is_dir():
            continue
        for pdb in sorted(d.glob("*.pdb")):
            r = analyse_pdb(pdb, tag)
            records.append(r)

    tables = attach_csv_rows(
        run_dir, ["trajectory_stats.csv", "mpnn_design_stats.csv",
                  "failure_csv.csv", "final_design_stats.csv"])
    for r in records:
        stem = Path(r["pdb"]).stem
        for table, rows in tables.items():
            hits = [row for row in rows
                    if row.get("Design", "").split("_model")[0] == stem
                    or stem.startswith(row.get("Design", ""))]
            if hits:
                r[table] = hits

    completed = [r for r in records if r.get("status") == "ok"]
    summary = {
        "run_dir": str(run_dir),
        "n_pdbs_analysed": len(records),
        "n_completed_relaxed": len([r for r in records if r["folder"] == "relaxed"]),
        "n_accepted": len([r for r in records if r["folder"] == "accepted"]),
        "n_contacted_B": len([r for r in completed if r["n_B_res_contacted"] > 0]),
        "n_migrated_off_B": len([r for r in completed if r["migrated_off_B"]]),
        "n_with_edge_contacts": len([r for r in completed
                                     if r["crop_edge_contact_pairs"] > 0]),
        "n_with_severe_clashes": len([r for r in completed
                                      if r["n_severe_clashes_lt2p3"] > 0]),
        "csv_tables_present": sorted(tables),
        "envelope_B": [390, 403, 421, 431],
    }
    out = {"summary": summary, "trajectories": records}
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")

    flat = Path(args.out).with_suffix(".csv")
    keys = ["pdb", "folder", "seed", "binder_length", "status",
            "n_B_res_contacted", "fraction_interface_pairs_on_B",
            "min_dist_binder_to_B_A", "min_dist_binder_to_offtarget_A",
            "n_interface_pairs_heavy", "n_severe_clashes_lt2p3",
            "crop_edge_contact_pairs", "migrated_off_B",
            "B_res_contacted", "crop_edge_res_contacted"]
    with open(flat, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in records:
            w.writerow({k: (";".join(map(str, r[k])) if isinstance(r.get(k), list)
                            else r.get(k)) for k in keys})
    print(json.dumps(summary, indent=2))
    print(f"wrote {args.out} and {flat}")


if __name__ == "__main__":
    main()
