"""Scientific QC for BindCraft run output against the approved B epitope.

Runs in the Colab kernel and locally (stdlib only). Target numbering in
BindCraft output PDBs is the LOCAL renumbered frame (chain A 1..N); the
hallucinated binder is chain B. Every geometry statement about the target
MUST go through the explicit residue mapping artifact
(data/processed/target_residue_map.json, item 12): local index ->
biological UniProt number. Guessing a constant offset is forbidden and
unmapped contacted residues fail loudly (NUMBERING_QC FAIL), never as a
silent zero.

Per trajectory PDB (cutoffs all explicit, see build_parser defaults):
- A numbering: local -> biological per contact, aa, mapping confidence
- B contacts: heavy-atom interface pairs < contact-cutoff; Cbeta pairs
  < cb-cutoff; minimum heavy-atom distances
- C hotspots: per-hotspot minimum heavy-atom distance and contact bool
  (never an occupancy-only answer)
- D approved envelope B (390-403 + 421-431): contacts inside / outside
  the envelope and the inside fraction
- E EPITOPE_MIGRATION flag when main contacts leave the envelope
- F CROP_EDGE_CONTACT flag for contacts to the first/last `edge-window`
  crop residues (configurable; default 5 — the old hardcoded N=3 answer
  hid the mpnn4 C-terminal contact)
- G binder termini: min target distance and interface membership for the
  N- and C-terminal `term-window` residues (assay relevance)
- H H433: minimum binder distance, geometry fact ONLY — proximity is NOT
  pH-switch evidence (H433 is deliberately not an approved hotspot)
- C_TERMINAL_ASSAY_RISK: recorded flag, not an auto-reject (item 16)
- severe cross-chain clashes < clash-cutoff

Candidate lifecycle (item 13): GENERATED -> BINDCRAFT_ACCEPTED ->
NUMBERING_QC -> EPITOPE_QC -> CROP_EDGE_QC are computable here. The later
layers (FULL_ECD_QC, ASSAY_GEOMETRY_QC, HUMAN_MOUSE_QC, PH_MECHANISM_QC,
SUBMISSION_CANDIDATE) are reported as null in Stage 2 — this tool never
claims them.

A completed trajectory is NOT a successful binder; this script only
reports geometry. Acceptance is BindCraft's own filter decision plus
human review, and computed pass is not experimental validation.
"""
import argparse
import csv
import hashlib
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MAP = ROOT / "data" / "processed" / "target_residue_map.json"

ENVELOPE_B_DEFAULT = "390-403,421-431"
HOTSPOTS_DEFAULT = "390,393,399,421,424,431"
H433_BIO = 433
CROP_DEFAULT = (310, 481)

HEAVY_CUTOFF = 4.5
CB_CUTOFF = 8.0
CLASH_CUTOFF = 2.3
EDGE_WINDOW_DEFAULT = 5
TERM_WINDOW_DEFAULT = 5
CTERM_RISK_MIN_DIST = 6.0

NAME_RE = re.compile(
    r"^(?P<prefix>.+)_l(?P<length>\d+)_s(?P<seed>\d+)(?:_model(?P<model>\d+))?$")

LATER_QC_LAYERS = ("FULL_ECD_QC", "ASSAY_GEOMETRY_QC", "HUMAN_MOUSE_QC",
                   "PH_MECHANISM_QC", "SUBMISSION_CANDIDATE")


def parse_ranges(spec):
    """'390-403,421-431' or '390,393,399' -> sorted list of ints."""
    out = []
    for token in str(spec).split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            lo, hi = token.split("-")
            out.extend(range(int(lo), int(hi) + 1))
        else:
            out.append(int(token))
    return sorted(set(out))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_residue_map(path):
    """Load + verify the mapping artifact. Returns (local_to_bio, meta).

    Verification (item 12, FAIL LOUDLY policy):
    - required fields present on every row;
    - output_local_index unique and exactly 1..N contiguous;
    - biological_number strictly increasing with local index;
    - local 1 maps to the crop start recorded in the artifact.
    Any violation raises SystemExit — a guessed or corrupted map is never
    used for geometry claims.
    """
    path = Path(path)
    if not path.is_file():
        raise SystemExit(
            f"FAIL LOUDLY: residue mapping artifact not found: {path}. "
            "Generate it with scripts/build_target_residue_map.py. "
            "Refusing to guess target numbering.")
    raw = json.loads(path.read_text())
    rows = raw.get("residues")
    if not rows:
        raise SystemExit(f"FAIL LOUDLY: {path} has no residues")
    required = ("input_pdb_residue", "biological_number",
                "output_local_index", "residue_name")
    local_to_bio = {}
    prev_local = 0
    prev_bio = None
    for row in rows:
        for field in required:
            if field not in row:
                raise SystemExit(f"FAIL LOUDLY: {path} row missing {field}: "
                                 f"{row}")
        local, bio = row["output_local_index"], row["biological_number"]
        if local != prev_local + 1:
            raise SystemExit(
                f"FAIL LOUDLY: {path} local indices not contiguous at "
                f"{local} (expected {prev_local + 1})")
        if prev_bio is not None and bio <= prev_bio:
            raise SystemExit(
                f"FAIL LOUDLY: {path} biological numbers not strictly "
                f"increasing at local {local}")
        if local in local_to_bio:
            raise SystemExit(f"FAIL LOUDLY: {path} duplicate local {local}")
        local_to_bio[local] = bio
        prev_local, prev_bio = local, bio
    meta = {"path": str(path), "sha256": sha256_file(path),
            "target_name": raw.get("target_name"),
            "source_chain": raw.get("source_chain"),
            "biological_span": raw.get("biological_span"),
            "numbering_note": raw.get("numbering_note")}
    return local_to_bio, meta


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
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2
                     + (a[2] - b[2]) ** 2)


def cb(res):
    if "CB" in res["atoms"]:
        return res["atoms"]["CB"][:3]
    return res["atoms"].get("CA", (None,))[:3] if "CA" in res["atoms"] \
        else None


class _Target:
    """Chain A in the LOCAL output frame + verified biological mapping."""

    def __init__(self, chains, local_to_bio):
        if "A" not in chains:
            raise ValueError("target chain A missing")
        self.local = chains["A"]
        self.local_to_bio = local_to_bio
        self.bio_to_local = {bio: loc for loc, bio in local_to_bio.items()}
        unmapped = [loc for loc in self.local if loc not in local_to_bio]
        if len(unmapped) == len(self.local):
            raise SystemExit(
                "FAIL LOUDLY: no chain-A residue of the output PDB is in "
                "the residue map — numbering unverifiable (wrong map for "
                "this target?); refusing to analyse with guessed offsets")
        self.unmapped = sorted(unmapped)

    def bio(self, local):
        return self.local_to_bio.get(local)

    def atoms_with_bio(self):
        for loc, res in self.local.items():
            yield loc, self.bio(loc), res


def analyse_pdb(path, folder, mapper, cfg):
    """One candidate record. mapper = (local_to_bio, map_meta)."""
    local_to_bio, _map_meta = mapper
    chains = parse_pdb(path)
    if "A" not in chains or "B" not in chains:
        return {"pdb": path.name, "folder": folder,
                "status": "parse_error: chains A/B missing"}
    try:
        target = _Target(chains, local_to_bio)
    except SystemExit as exc:
        return {"pdb": path.name, "folder": folder,
                "status": f"numbering_error: {exc}"}
    binder = chains["B"]

    envelope = set(cfg["envelope"])
    hotspots = cfg["hotspots"]
    crop_lo, crop_hi = cfg["crop"]
    edge_w = cfg["edge_window"]
    edge_bio = set(range(crop_lo, crop_lo + edge_w)) | \
        set(range(crop_hi - edge_w + 1, crop_hi + 1))

    b_atoms = [(bres, bname, bv) for bres, d in binder.items()
               for bname, bv in d["atoms"].items()]

    pairs_heavy, pairs_cb, clashes = set(), set(), []
    min_b, min_off = 1e9, 1e9
    hotspot_min = {hs: 1e9 for hs in hotspots}
    h433_min = 1e9
    unmapped_contacted = set()
    for bres, bname, bv in b_atoms:
        for loc, bio, res in target.atoms_with_bio():
            dmin = min(dist(bv[:3], av[:3]) for _, av in res["atoms"].items())
            if bio is None:
                unmapped_contacted.add(loc)
                bio_key = None
            else:
                bio_key = bio
                if bio in envelope:
                    min_b = min(min_b, dmin)
                else:
                    min_off = min(min_off, dmin)
                if bio in hotspot_min:
                    hotspot_min[bio] = min(hotspot_min[bio], dmin)
                if bio == H433_BIO:
                    h433_min = min(h433_min, dmin)
            if dmin < cfg["contact_cutoff"]:
                pairs_heavy.add((bio_key, loc, bres))
            if dmin < cfg["clash_cutoff"]:
                clashes.append({"target_bio": bio_key, "target_local": loc,
                                "binder_res": bres, "binder_atom": bname,
                                "dist": round(dmin, 2)})
    for bres, bd in binder.items():
        bc = cb(bd)
        if bc is None:
            continue
        for loc, res in target.local.items():
            tc = cb(res)
            if tc is not None and dist(bc, tc) < cfg["cb_cutoff"]:
                pairs_cb.add((loc, bres))

    t_contacted_bio = sorted({bio for bio, _, _ in pairs_heavy
                              if bio is not None})
    t_contacted_local = sorted({loc for _, loc, _ in pairs_heavy})
    b_contacted = sorted({bres for _, _, bres in pairs_heavy})
    on_b = [(bio, loc, bres) for bio, loc, bres in pairs_heavy
            if bio in envelope]
    edge = [(bio, loc, bres) for bio, loc, bres in pairs_heavy
            if bio in edge_bio]

    # binder termini (item 14G) + C-terminal assay risk (item 16)
    binder_res_sorted = sorted(binder)
    term_w = cfg["term_window"]
    n_term = binder_res_sorted[:term_w]
    c_term = binder_res_sorted[-term_w:]
    target_atom_list = [(loc, bio, res) for loc, bio, res
                        in target.atoms_with_bio()]

    def term_stats(term_res):
        rows = []
        for bres in term_res:
            # heavy-atom minimum from this terminal residue to the target
            dmin, partner = 1e9, None
            for bname, bv in binder[bres]["atoms"].items():
                for _loc, bio, res in target_atom_list:
                    for _n, av in res["atoms"].items():
                        d = dist(bv[:3], av[:3])
                        if d < dmin:
                            dmin, partner = d, bio
            rows.append({"binder_res": bres,
                         "min_dist_to_target": (None if dmin > 1e8
                                                else round(dmin, 2)),
                         "closest_target_bio": partner,
                         "in_interface": bres in b_contacted})
        return rows

    n_term_rows, c_term_rows = term_stats(n_term), term_stats(c_term)
    c_min = min((r["min_dist_to_target"] for r in c_term_rows
                 if r["min_dist_to_target"] is not None), default=None)
    cterm_risk = any(r["in_interface"] for r in c_term_rows) or (
        c_min is not None and c_min < cfg["cterm_risk_min_dist"])

    hotspots_report = {}
    for hs in hotspots:
        loc = target.bio_to_local.get(hs)
        dmin = hotspot_min.get(hs, 1e9)
        present = loc is not None and loc in target.local
        hotspots_report[str(hs)] = {
            "local_index": loc,
            "present_in_output": bool(present),
            "contacted": bool(present and dmin < cfg["contact_cutoff"]),
            "min_heavy_dist": None if dmin > 1e8 else round(dmin, 2),
        }

    m = NAME_RE.match(Path(path).stem)
    info = m.groupdict() if m else {}
    n_pairs = len(pairs_heavy)
    frac_on_b = (len(on_b) / n_pairs) if n_pairs else 0.0
    migrated = (n_pairs == 0) or frac_on_b < 0.5

    inside_contacts = sorted({bio for bio, _, _ in on_b})
    outside_contacts = sorted(bio for bio, _, _ in pairs_heavy
                              if bio is not None and bio not in envelope)

    numbering_qc = "FAIL" if (target.unmapped or unmapped_contacted) \
        else "PASS"
    epitope_qc = "FLAG_EPITOPE_MIGRATION" if migrated else "PASS"
    crop_qc = "FLAG_CROP_EDGE_CONTACT" if edge else "PASS"
    lifecycle = {
        "GENERATED": "YES",
        "BINDCRAFT_ACCEPTED": "YES" if folder == "accepted" else
        ("NO" if folder in ("relaxed", "low_confidence", "clashing")
         else "NOT_EVALUATED"),
        "NUMBERING_QC": numbering_qc,
        "EPITOPE_QC": epitope_qc,
        "CROP_EDGE_QC": crop_qc,
        # Stage 2 never claims the layers below (item 13)
        **{layer: None for layer in LATER_QC_LAYERS},
    }

    return {
        "pdb": path.name,
        "folder": folder,
        "status": "ok",
        "seed": int(info["seed"]) if info.get("seed") else None,
        "binder_length": int(info["length"]) if info.get("length")
        else len(binder),
        "model": info.get("model"),
        # A. numbering
        "numbering_frame": "local(output) -> biological via residue map",
        "numbering_unmapped_local": sorted(unmapped_contacted),
        "target_res_contacted_biological": t_contacted_bio,
        "target_res_contacted_local": t_contacted_local,
        # B. contacts
        "n_interface_pairs_heavy": n_pairs,
        "n_interface_pairs_cb8": len(pairs_cb),
        "n_binder_res_in_contact": len(b_contacted),
        "n_target_res_contacted": len(t_contacted_bio),
        # C. hotspots (per-site distances, not occupancy-only)
        "hotspots": hotspots_report,
        "n_hotspots_contacted": sum(1 for h in hotspots_report.values()
                                    if h["contacted"]),
        # D. approved envelope
        "B_res_contacted": inside_contacts,
        "n_B_res_contacted": len(inside_contacts),
        "envelope_outside_contacts": outside_contacts,
        "fraction_interface_pairs_on_B": round(frac_on_b, 3),
        "min_dist_binder_to_B_A": None if min_b > 1e8 else round(min_b, 2),
        "min_dist_binder_to_offtarget_A": (None if min_off > 1e8
                                           else round(min_off, 2)),
        # E. epitope migration
        "migrated_off_B": migrated,
        # F. crop edge (configurable window)
        "crop_edge_contact_pairs": len(edge),
        "crop_edge_res_contacted": sorted({bio for bio, _, _ in edge}),
        "crop_edge_flag": "CROP_EDGE_CONTACT" if edge else "NONE",
        "edge_window": edge_w,
        # G. binder termini
        "n_terminal_residues": n_term_rows,
        "c_terminal_residues": c_term_rows,
        "c_term_min_dist": c_min,
        # H. H433 (geometry fact only; NOT pH evidence)
        "H433_min_heavy_dist": None if h433_min > 1e8 else round(h433_min, 2),
        "H433_note": ("geometry observation only; H433 is not an approved "
                      "hotspot and proximity is not pH-switch evidence"),
        # clashes
        "n_severe_clashes_lt2p3": len(clashes),
        "severe_clashes": clashes[:20],
        # assay-aware C-terminal risk (item 16): recorded, never auto-reject
        "C_TERMINAL_ASSAY_RISK": bool(cterm_risk),
        # lifecycle (item 13)
        "lifecycle": lifecycle,
    }


def attach_csv_rows(run_dir, names):
    out = {}
    for name in names:
        p = run_dir / name
        if p.exists():
            with open(p, newline="") as fh:
                out[name] = list(csv.DictReader(fh))
    return out


def build_parser():
    """CLI contract (item 4); asserted against callers by tests."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--residue-map", default=str(DEFAULT_MAP),
                    help="target_residue_map.json (item 12); required for "
                         "any target-numbering statement")
    ap.add_argument("--envelope", default=ENVELOPE_B_DEFAULT,
                    help="approved epitope envelope, biological numbering")
    ap.add_argument("--hotspots", default=HOTSPOTS_DEFAULT,
                    help="approved hotspot set, biological numbering")
    ap.add_argument("--crop", default=f"{CROP_DEFAULT[0]}-{CROP_DEFAULT[1]}",
                    help="generation crop span, biological numbering")
    ap.add_argument("--contact-cutoff", type=float, default=HEAVY_CUTOFF)
    ap.add_argument("--cb-cutoff", type=float, default=CB_CUTOFF)
    ap.add_argument("--clash-cutoff", type=float, default=CLASH_CUTOFF)
    ap.add_argument("--edge-window", type=int, default=EDGE_WINDOW_DEFAULT,
                    help="crop-edge contact screen window (item 14F)")
    ap.add_argument("--term-window", type=int, default=TERM_WINDOW_DEFAULT,
                    help="binder N/C terminal residue window (item 14G)")
    ap.add_argument("--cterm-risk-min-dist", type=float,
                    default=CTERM_RISK_MIN_DIST)
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    mapper = load_residue_map(args.residue_map)
    run_dir = Path(args.run_dir)

    folders = {"Trajectory/Relaxed": "relaxed",
               "Trajectory/LowConfidence": "low_confidence",
               "Trajectory/Clashing": "clashing",
               "Accepted": "accepted"}
    cfg = {
        "envelope": parse_ranges(args.envelope),
        "hotspots": parse_ranges(args.hotspots),
        "crop": (int(args.crop.split("-")[0]), int(args.crop.split("-")[1])),
        "contact_cutoff": args.contact_cutoff,
        "cb_cutoff": args.cb_cutoff,
        "clash_cutoff": args.clash_cutoff,
        "edge_window": args.edge_window,
        "term_window": args.term_window,
        "cterm_risk_min_dist": args.cterm_risk_min_dist,
        "residue_map": mapper[1],
        "envelope_spec": args.envelope,
        "hotspots_spec": args.hotspots,
        "crop_spec": args.crop,
    }

    records = []
    for folder, tag in folders.items():
        d = run_dir / folder
        if not d.is_dir():
            continue
        for pdb in sorted(d.glob("*.pdb")):
            records.append(analyse_pdb(pdb, tag, mapper, cfg))

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
    n_numbering_fail = len([r for r in completed
                            if r["lifecycle"]["NUMBERING_QC"] == "FAIL"])
    # whole-PDB numbering errors (chain A unverifiable) count too — a run
    # containing them must not exit 0 (item 12 fail-loudly policy)
    n_numbering_error = len([r for r in records
                             if str(r.get("status", "")).startswith(
                                 "numbering_error")])
    summary = {
        "run_dir": str(run_dir),
        "n_pdbs_analysed": len(records),
        "n_completed_relaxed": len([r for r in records
                                    if r["folder"] == "relaxed"]),
        "n_accepted": len([r for r in records if r["folder"] == "accepted"]),
        "n_contacted_B": len([r for r in completed
                              if r["n_B_res_contacted"] > 0]),
        "n_migrated_off_B": len([r for r in completed
                                 if r["migrated_off_B"]]),
        "n_with_edge_contacts": len([r for r in completed
                                     if r["crop_edge_contact_pairs"] > 0]),
        "n_with_severe_clashes": len([r for r in completed
                                      if r["n_severe_clashes_lt2p3"] > 0]),
        "n_cterm_assay_risk": len([r for r in completed
                                   if r["C_TERMINAL_ASSAY_RISK"]]),
        "n_numbering_fail": n_numbering_fail + n_numbering_error,
        "n_hotspots_contacted_max": (max((r["n_hotspots_contacted"]
                                          for r in completed), default=0)),
        "csv_tables_present": sorted(tables),
        "config": cfg,
        "envelope_B": [cfg["envelope"][0], cfg["envelope"][-1]] if
        cfg["envelope"] else [],
        "lifecycle_note": ("this tool computes GENERATED..CROP_EDGE_QC only; "
                           "FULL_ECD_QC and later layers are null in "
                           "Stage 2 (see scripts/audit_full_ecd_context.py "
                           "for the full-ECD geometry audit)"),
    }
    out = {"summary": summary, "config": cfg, "trajectories": records}
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")

    flat = Path(args.out).with_suffix(".csv")
    keys = ["pdb", "folder", "seed", "binder_length", "status",
            "n_B_res_contacted", "fraction_interface_pairs_on_B",
            "min_dist_binder_to_B_A", "min_dist_binder_to_offtarget_A",
            "n_hotspots_contacted", "H433_min_heavy_dist",
            "n_interface_pairs_heavy", "n_severe_clashes_lt2p3",
            "crop_edge_contact_pairs", "migrated_off_B",
            "C_TERMINAL_ASSAY_RISK", "NUMBERING_QC",
            "B_res_contacted", "crop_edge_res_contacted",
            "envelope_outside_contacts", "target_res_contacted_biological"]
    with open(flat, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in records:
            row = {}
            for k in keys:
                v = r.get(k)
                if isinstance(v, list):
                    v = ";".join(map(str, v))
                elif isinstance(v, dict):
                    v = json.dumps(v, sort_keys=True)
                row[k] = v
            w.writerow(row)
    print(json.dumps(summary, indent=2))
    print(f"wrote {args.out} and {flat}")
    n_fail_total = n_numbering_fail + n_numbering_error
    if n_fail_total:
        print(f"NUMBERING_QC FAIL on {n_fail_total} candidate(s): "
              "target residues outside the verified map or a chain A that "
              "cannot be mapped at all — results for those candidates are "
              "NOT interpretable",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
