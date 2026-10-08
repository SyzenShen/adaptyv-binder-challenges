"""Full-ECD context audit for one Stage 2 binder candidate (item 15).

The generation crop covers EGFR Domain III only (UniProt 310-481), so the
Stage 2 geometry analyzer (analyze_bindcraft_run.py) can NEVER say whether a
binder would also touch the rest of the extracellular domain. This script
places the candidate into the full-ECD reference structure (default
data/raw/6ARU.cif, .pdb fallback supported) and reports pure geometry facts:

- Kabsch C-alpha superposition of the complex target chain (LOCAL frame,
  verified via target_residue_map.json + residue_map.csv auth conversion)
  onto the reference chain A; alignment RMSD and coverage.
- The hallucinated binder (chain B) is transformed into the reference frame
  with the SAME rigid transform.
- Per-domain minimum binder heavy-atom distance, contacts and severe clashes
  for Domain I (25-165), II (166-309), III (310-481), IV (482-640)
  (UniProt numbering, converted to 6ARU auth numbering via residue_map.csv).
- Glycan (non-water HETATM) contact screen.
- CROP_EDGE_RISK: binder contacts the first/last `--edge-window` crop
  residues judged in the full-ECD context.
- CONTACTS_OUTSIDE_CROP: binder contacts reference residues outside
  UniProt 310-481 (the approved crop) — a geometry fact, never a verdict.

Every statement here is geometric observation only. This tool computes the
FULL_ECD_QC lifecycle layer as geometry facts and explicitly does NOT judge
pH mechanism, assay behaviour, or developability.

Stdlib + numpy (guarded: missing numpy fails loudly, never silently degrades
to a guessed answer). Runs in the Colab kernel and locally.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

try:
    import numpy as np
except ImportError:  # guarded: Kabsch is impossible without numpy
    np = None

import analyze_bindcraft_run as abr

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MAP_JSON = ROOT / "data" / "processed" / "target_residue_map.json"
DEFAULT_MAP_CSV = ROOT / "data" / "processed" / "residue_map.csv"
DEFAULT_REF = ROOT / "data" / "raw" / "6ARU.cif"

DOMAINS_DEFAULT = "I:25-165,II:166-309,III:310-481,IV:482-640"
CROP_DEFAULT = (310, 481)
HEAVY_CUTOFF = 4.5
CLASH_CUTOFF = 2.3
EDGE_WINDOW_DEFAULT = 5
RMSD_FLAG_DEFAULT = 2.0
MIN_COMMON_CA_DEFAULT = 10
GLYCAN_EXCLUDE = {"HOH", "DOD"}


# --------------------------------------------------------------------------
# minimal mmCIF reading (stdlib only; handles quotes + ';' text fields)
# --------------------------------------------------------------------------

def cif_tokens(path):
    """Yield mmCIF tokens: whitespace split, respecting quoting and the
    multiline ';'-delimited text convention; '#' starts a comment."""
    with open(path, errors="replace") as fh:
        lines = fh.read().splitlines()
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if line.startswith(";"):
            buf = [line[1:]]
            i += 1
            while i < n and not lines[i].startswith(";"):
                buf.append(lines[i])
                i += 1
            i += 1
            yield "\n".join(buf)
            continue
        j, L = 0, len(line)
        while j < L:
            c = line[j]
            if c in " \t":
                j += 1
            elif c == "#":
                break
            elif c in "'\"":
                q = c
                j += 1
                start = j
                while j < L and not (line[j] == q and
                                     (j + 1 >= L or line[j + 1] in " \t")):
                    j += 1
                yield line[start:j]
                j += 1
            else:
                start = j
                while j < L and line[j] not in " \t":
                    j += 1
                yield line[start:j]
        i += 1


def cif_loops(path):
    """Yield (tags, rows) for every loop_ block in an mmCIF file."""
    toks = list(cif_tokens(path))
    i, n = 0, len(toks)
    while i < n:
        if toks[i].lower() != "loop_":
            i += 1
            continue
        i += 1
        tags = []
        while i < n and toks[i].startswith("_"):
            tags.append(toks[i])
            i += 1
        vals = []
        while i < n:
            low = toks[i].lower()
            if (toks[i].startswith("_") or low == "loop_" or
                    low.startswith("data_") or low.startswith("save_")):
                break  # stop token NOT consumed: it may start the next item
            vals.append(toks[i])
            i += 1
        if tags and vals and len(vals) % len(tags) == 0:
            width = len(tags)
            yield tags, [vals[k:k + width]
                         for k in range(0, len(vals), width)]


def parse_ref_cif(path):
    """Parse an mmCIF into (polymer, hetatms) for model 1.

    polymer: {auth_chain: {auth_seq_int: {"aa": str, "atoms": {name: xyz}}}}
    hetatms: [{"comp", "chain", "auth_seq", "atom", "xyz", "elem"}]
    """
    want = {"_atom_site.group_PDB": "group",
            "_atom_site.auth_asym_id": "achain",
            "_atom_site.auth_seq_id": "aseq",
            "_atom_site.label_comp_id": "comp",
            "_atom_site.label_atom_id": "atom",
            "_atom_site.type_symbol": "elem",
            "_atom_site.Cartn_x": "x",
            "_atom_site.Cartn_y": "y",
            "_atom_site.Cartn_z": "z",
            "_atom_site.pdbx_PDB_model_num": "model",
            "_atom_site.label_asym_id": "lchain",
            "_atom_site.label_seq_id": "lseq"}
    polymer, hetatms = {}, []
    for tags, rows in cif_loops(path):
        idx = {want[t]: i for i, t in enumerate(tags) if t in want}
        if "group" not in idx:
            continue
        for row in rows:
            if idx.get("model") is not None and row[idx["model"]] != "1":
                continue
            comp = row[idx["comp"]]
            xyz = (float(row[idx["x"]]), float(row[idx["y"]]),
                   float(row[idx["z"]]))
            atom = row[idx["atom"]].strip('"\'')
            elem = (row[idx["elem"]] if idx.get("elem") is not None
                    else atom[0]).upper()[:1]
            if elem == "H":
                continue
            try:
                aseq = int(row[idx["aseq"]])
            except (ValueError, KeyError, TypeError):
                aseq = None
            achain = (row[idx["achain"]] if idx.get("achain") is not None
                      else row[idx["lchain"]]).strip() or " "
            if row[idx["group"]] == "ATOM" and aseq is not None:
                res = polymer.setdefault(achain, {}).setdefault(
                    aseq, {"aa": comp, "atoms": {}})
                res["atoms"].setdefault(atom, xyz)
            else:  # HETATM (glycans, ligands, waters)
                hetatms.append({"comp": comp, "chain": achain,
                                "auth_seq": aseq, "atom": atom,
                                "xyz": xyz, "elem": elem})
    return polymer, hetatms


def parse_ref_pdb(path):
    """.pdb fallback reference: polymer chain A + other-chain HETATM-ish."""
    chains = abr.parse_pdb(path)
    polymer = {c: {r: {"aa": d["aa"], "atoms": d["atoms"]}
                   for r, d in res.items()}
               for c, res in chains.items() if c != "B"}
    hetatms = []
    for c, res in chains.items():
        if c == "A":
            continue
        for r, d in res.items():
            if d["aa"] in GLYCAN_EXCLUDE:
                continue
            for name, xyz in d["atoms"].items():
                hetatms.append({"comp": d["aa"], "chain": c, "auth_seq": r,
                                "atom": name, "xyz": xyz[:3],
                                "elem": xyz[3] if len(xyz) > 3 else name[:1]})
    return polymer, hetatms


def load_reference(path):
    path = Path(path)
    if not path.is_file():
        raise SystemExit(f"FAIL LOUDLY: reference structure not found: "
                         f"{path}")
    if path.suffix.lower() in (".cif", ".mmcif"):
        polymer, het = parse_ref_cif(path)
        fmt = "cif"
    else:
        polymer, het = parse_ref_pdb(path)
        fmt = "pdb"
    if "A" not in polymer:
        raise SystemExit(f"FAIL LOUDLY: no auth chain A polymer residues in "
                         f"reference {path}")
    return polymer, het, fmt, abr.sha256_file(path)


# --------------------------------------------------------------------------
# mapping: biological UniProt number <-> 6ARU auth_seq_id
# --------------------------------------------------------------------------

def load_bio_auth(csv_path):
    """bio UniProt pos -> auth_seq_id (int) for residues present in 6ARU.

    Derived ONLY from residue_map.csv (in_pdb_construct == yes, numeric
    auth id); no constant offset is ever assumed (item 12 policy).
    """
    bio_auth, auth_bio = {}, {}
    with open(csv_path, newline="") as fh:
        for row in csv.DictReader(fh):
            if row.get("in_pdb_construct") != "yes":
                continue
            auth = (row.get("pdb_auth_seq_id") or "").strip()
            try:
                auth_i = int(auth)
            except ValueError:
                continue
            bio = int(row["uniprot_pos"])
            bio_auth[bio] = auth_i
            auth_bio[auth_i] = bio
    if not bio_auth:
        raise SystemExit(f"FAIL LOUDLY: {csv_path} yielded no bio->auth "
                         "mapping rows")
    return bio_auth, auth_bio


# --------------------------------------------------------------------------
# Kabsch superposition (numpy guarded)
# --------------------------------------------------------------------------

def kabsch(P, Q):
    """Rigid transform taking row-vector points P onto Q.

    Returns (R, t, rmsd) with Q ~= P @ R + t. Requires numpy.
    """
    if np is None:
        raise SystemExit(
            "FAIL LOUDLY: numpy is required for the Kabsch alignment of "
            "this audit; install numpy instead of trusting an unaligned "
            "answer.")
    P = np.asarray(P, dtype=float)
    Q = np.asarray(Q, dtype=float)
    if len(P) < 3:
        raise SystemExit(
            f"FAIL LOUDLY: only {len(P)} common CA pairs — a rigid "
            "superposition needs at least 3; refusing to guess a frame")
    pc = P - P.mean(axis=0)
    qc = Q - Q.mean(axis=0)
    # row-vector convention: Q ~= P @ R + t. With the column-convention
    # covariance H = pc.T @ qc = U S Vt, the optimal row transform is
    # R = U diag(1,1,d) Vt (det d forces a proper rotation, never a mirror).
    u, _s, vt = np.linalg.svd(pc.T @ qc)
    d = np.sign(np.linalg.det(u @ vt))
    rot = u @ np.diag([1.0, 1.0, d if d != 0 else 1.0]) @ vt
    trans = Q.mean(axis=0) - P.mean(axis=0) @ rot
    rmsd = float(np.sqrt(((pc @ rot - qc) ** 2).sum(axis=1).mean()))
    return rot, trans, rmsd


def pair_min(A, B):
    """Full (n, m) euclidean distance matrix between (n,3) and (m,3) points.
    numpy availability is enforced by kabsch upstream."""
    diff = A[:, None, :] - B[None, :, :]
    return np.sqrt((diff ** 2).sum(axis=-1))


# --------------------------------------------------------------------------
# audit
# --------------------------------------------------------------------------

def audit(complex_pdb, ref_polymer, ref_het, ref_fmt, ref_sha, local_to_bio,
          bio_auth, auth_bio, cfg):
    chains = abr.parse_pdb(complex_pdb)
    if "A" not in chains or "B" not in chains:
        raise SystemExit(f"FAIL LOUDLY: {complex_pdb} must contain target "
                         "chain A (local frame) and binder chain B")
    target, binder = chains["A"], chains["B"]

    unmapped = sorted(loc for loc in target if loc not in local_to_bio)
    if unmapped and len(unmapped) == len(target):
        raise SystemExit(
            "FAIL LOUDLY: no chain-A residue of the complex PDB is in the "
            "residue map — numbering unverifiable; refusing to audit with "
            "guessed offsets")

    # ---- common CA pairs: complex local -> bio -> auth -> reference CA
    P, Q, common = [], [], []
    missing_in_ref, no_ca = [], []
    for loc, res in sorted(target.items()):
        bio = local_to_bio.get(loc)
        if bio is None:
            continue
        auth = bio_auth.get(bio)
        ref_res = ref_polymer["A"].get(auth) if auth is not None else None
        if ref_res is None:
            missing_in_ref.append({"local": loc, "bio": bio,
                                   "auth": auth})
            continue
        ca_c = res["atoms"].get("CA")
        ca_r = ref_res["atoms"].get("CA")
        if ca_c is None or ca_r is None:
            no_ca.append({"local": loc, "bio": bio})
            continue
        P.append(ca_c[:3])
        Q.append(ca_r[:3])
        common.append({"local": loc, "bio": bio, "auth": auth})
    rot, trans, rmsd = kabsch(P, Q)

    def to_ref(xyz):
        return (xyz[0] * rot[0][0] + xyz[1] * rot[0][1] + xyz[2] * rot[0][2]
                + trans[0],
                xyz[0] * rot[1][0] + xyz[1] * rot[1][1] + xyz[2] * rot[1][2]
                + trans[1],
                xyz[0] * rot[2][0] + xyz[1] * rot[2][1] + xyz[2] * rot[2][2]
                + trans[2])

    binder_atoms, binder_meta = [], []
    for bres, res in sorted(binder.items()):
        for bname, bv in res["atoms"].items():
            binder_atoms.append(to_ref(bv[:3]))
            binder_meta.append({"binder_res": bres, "atom": bname})
    B = np.asarray(binder_atoms)

    # ---- reference chain A heavy atoms with known UniProt number
    ref_atoms, ref_meta = [], []
    for auth, res in sorted(ref_polymer["A"].items()):
        bio = auth_bio.get(auth)
        if bio is None:
            continue  # expression tag / non-construct residue
        for name, xyz in res["atoms"].items():
            ref_atoms.append(xyz[:3])
            ref_meta.append({"auth": auth, "bio": bio, "aa": res["aa"],
                             "atom": name})
    R = np.asarray(ref_atoms)
    D = pair_min(B, R)

    crop_lo, crop_hi = cfg["crop"]
    edge_bio = set(range(crop_lo, crop_lo + cfg["edge_window"])) | \
        set(range(crop_hi - cfg["edge_window"] + 1, crop_hi + 1))
    domains = {}
    for tok in cfg["domains_spec"].split(","):
        name, span = tok.split(":")
        lo, hi = span.split("-")
        domains[name.strip()] = (int(lo), int(hi))

    contact_mask = D < cfg["contact_cutoff"]
    clash_mask = D < cfg["clash_cutoff"]

    def pairs_from_mask(mask, limit=20):
        out = []
        rows, cols = np.nonzero(mask)
        for i, j in zip(rows.tolist(), cols.tolist()):
            m = ref_meta[j]
            out.append({"binder_res": binder_meta[i]["binder_res"],
                        "binder_atom": binder_meta[i]["atom"],
                        "target_bio": m["bio"], "target_auth": m["auth"],
                        "target_aa": m["aa"], "target_atom": m["atom"],
                        "dist": round(float(D[i, j]), 2)})
        out.sort(key=lambda p: p["dist"])
        return out[:limit], len(out)

    domain_report = {}
    edge_pairs, outside_pairs = [], []
    n_outside = 0
    sample_cap = 20
    for name, (lo, hi) in sorted(domains.items()):
        cols = [j for j, m in enumerate(ref_meta) if lo <= m["bio"] <= hi]
        if not cols:
            domain_report[name] = {"span": [lo, hi],
                                   "n_ref_res_with_coords": 0,
                                   "min_binder_heavy_dist": None}
            continue
        sub = D[:, cols]
        n_res = len({ref_meta[j]["auth"] for j in cols})
        cont_mask = sub < cfg["contact_cutoff"]
        plist, ncont = [], 0
        rows, cols2 = np.nonzero(cont_mask)
        for i, j in zip(rows.tolist(), cols2.tolist()):
            jm = cols[j]
            m = ref_meta[jm]
            plist.append({"binder_res": binder_meta[i]["binder_res"],
                          "binder_atom": binder_meta[i]["atom"],
                          "target_bio": m["bio"], "target_auth": m["auth"],
                          "target_aa": m["aa"], "target_atom": m["atom"],
                          "dist": round(float(D[i, jm]), 2)})
        plist.sort(key=lambda p: p["dist"])
        ncont = len(plist)
        cl = int((sub < cfg["clash_cutoff"]).sum())
        domain_report[name] = {
            "span": [lo, hi],
            "n_ref_res_with_coords": n_res,
            "min_binder_heavy_dist": round(float(sub.min()), 2),
            "n_contact_pairs_lt_cutoff": ncont,
            "contact_pairs_sample": plist[:sample_cap],
            "n_severe_clashes_lt2p3": cl,
            "contacted_target_bio": sorted({p["target_bio"]
                                            for p in plist}),
        }
        if lo == crop_lo and hi == crop_hi:
            for p in plist:
                if p["target_bio"] in edge_bio:
                    edge_pairs.append(p)
        elif ncont:
            outside_pairs.extend(plist)
            n_outside += ncont
    n_edge = len(edge_pairs)

    # ---- glycan screen (non-water HETATM in the reference)
    gly = [h for h in ref_het if h["comp"].upper() not in GLYCAN_EXCLUDE]
    glycan_report = {"n_glycan_atoms": len(gly),
                     "comp_ids": sorted({h["comp"] for h in gly})}
    if gly:
        G = np.asarray([h["xyz"] for h in gly])
        Dg = pair_min(B, G)
        glycan_report["min_binder_heavy_dist"] = round(float(Dg.min()), 2)
        contacted = sorted({g["comp"] for g, row in
                            zip(gly, (Dg < cfg["contact_cutoff"]).any(axis=0))
                            if row})
        glycan_report["contacted_comp_ids"] = contacted
        glycan_report["flag"] = "GLYCAN_CONTACT" if contacted else "NONE"
    else:
        glycan_report["min_binder_heavy_dist"] = None
        glycan_report["contacted_comp_ids"] = []
        glycan_report["flag"] = "NO_GLYCAN_IN_REFERENCE"

    n_clashes = int(clash_mask.sum())
    clash_pairs, _ = pairs_from_mask(clash_mask)
    outside_pairs.sort(key=lambda p: p["dist"])
    edge_pairs.sort(key=lambda p: p["dist"])

    flags = {
        "CONTACTS_OUTSIDE_CROP": bool(n_outside),
        "CROP_EDGE_RISK": bool(n_edge),
        "GLYCAN_CONTACT": glycan_report["flag"] == "GLYCAN_CONTACT",
        "ALIGNMENT_POOR": rmsd > cfg["rmsd_flag"],
        "ALIGNMENT_UNRELIABLE": len(common) < cfg["min_common_ca"],
        "SEVERE_CLASH_WITH_FULL_ECD": n_clashes > 0,
    }

    return {
        "complex_pdb": str(complex_pdb),
        "reference": {"path": str(cfg["ref_path"]), "format": ref_fmt,
                      "sha256": ref_sha, "auth_chain": "A",
                      "model": 1},
        "numbering": {
            "frame": ("complex chain A LOCAL -> biological via "
                      "target_residue_map.json -> 6ARU auth via "
                      "residue_map.csv (no assumed offset)"),
            "n_target_local_residues": len(target),
            "unmapped_local": unmapped,
            "missing_in_reference": missing_in_ref,
            "no_ca_in_pair": no_ca,
        },
        "alignment": {"method": "kabsch_ca", "n_common_ca": len(common),
                      "coverage_of_crop": round(len(common) /
                                                max(len(target), 1), 3),
                      "rmsd": round(rmsd, 3)},
        "domains": domain_report,
        "crop_edge": {"window": cfg["edge_window"],
                      "edge_bio": sorted(edge_bio),
                      "n_contact_pairs": n_edge,
                      "pairs_sample": edge_pairs[:20]},
        "outside_crop": {"n_contact_pairs": n_outside,
                         "contacted_target_bio": sorted(
                             {p["target_bio"] for p in outside_pairs}),
                         "pairs_sample": outside_pairs[:20]},
        "glycans": glycan_report,
        "clashes": {"n_severe_lt2p3": n_clashes,
                    "pairs_sample": clash_pairs},
        "flags": flags,
        "notes": [
            "geometry facts only; no functional or developability verdict",
            "binder distances are computed in the reference frame after the "
            "Kabsch transform of the complex",
            "FULL_ECD_QC here is a geometry screen; it never validates "
            "binding, specificity, pH mechanism or assay behaviour",
        ],
    }


def write_viz_pdb(out_path, ref_polymer, binder, rot, trans):
    """Full ECD (reference CA trace, auth numbering) + transformed binder."""
    def fmt(serial, name, resname, chain, resseq, xyz, elem):
        return (f"ATOM  {serial:5d} {name:<4s} {resname:>3s} {chain}"
                f"{resseq:4d}    {xyz[0]:8.3f}{xyz[1]:8.3f}{xyz[2]:8.3f}"
                f"  1.00  0.00          {elem:>2s}")

    lines, s = [], 1
    three = {"A": "ALA", "R": "ARG", "N": "ASN", "D": "ASP", "C": "CYS",
             "Q": "GLN", "E": "GLU", "G": "GLY", "H": "HIS", "I": "ILE",
             "L": "LEU", "K": "LYS", "M": "MET", "F": "PHE", "P": "PRO",
             "S": "SER", "T": "THR", "W": "TRP", "Y": "TYR", "V": "VAL"}
    for auth, res in sorted(ref_polymer["A"].items()):
        ca = res["atoms"].get("CA")
        if ca is None:
            continue
        rn = res["aa"] if len(res["aa"]) == 3 else three.get(res["aa"],
                                                             "UNK")
        lines.append(fmt(s, "CA", rn, "A", auth, ca[:3], "C"))
        s += 1
    for bres, res in sorted(binder.items()):
        for name, xyz in sorted(res["atoms"].items()):
            elem = (xyz[3] if len(xyz) > 3 else name[:1]) or "C"
            lines.append(fmt(s, name, res.get("aa", "UNK"), "B", bres,
                             (xyz[0] * rot[0][0] + xyz[1] * rot[0][1]
                              + xyz[2] * rot[0][2] + trans[0],
                              xyz[0] * rot[1][0] + xyz[1] * rot[1][1]
                              + xyz[2] * rot[1][2] + trans[1],
                              xyz[0] * rot[2][0] + xyz[1] * rot[2][1]
                              + xyz[2] * rot[2][2] + trans[2]), elem))
            s += 1
    Path(out_path).write_text("\n".join(lines) + "\n")


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--complex-pdb", required=True,
                    help="BindCraft output PDB: chain A target (LOCAL), "
                         "chain B binder")
    ap.add_argument("--out", required=True, help="JSON audit output path")
    ap.add_argument("--residue-map", default=str(DEFAULT_MAP_JSON),
                    help="target_residue_map.json (local -> biological)")
    ap.add_argument("--residue-map-csv", default=str(DEFAULT_MAP_CSV),
                    help="residue_map.csv (biological <-> 6ARU auth)")
    ap.add_argument("--reference", default=str(DEFAULT_REF),
                    help="full-ECD reference (.cif preferred, .pdb fallback)")
    ap.add_argument("--domains", default=DOMAINS_DEFAULT,
                    help="domain spec NAME:lo-hi,... in UniProt numbering")
    ap.add_argument("--crop", default=f"{CROP_DEFAULT[0]}-{CROP_DEFAULT[1]}",
                    help="generation crop span, biological numbering")
    ap.add_argument("--contact-cutoff", type=float, default=HEAVY_CUTOFF)
    ap.add_argument("--clash-cutoff", type=float, default=CLASH_CUTOFF)
    ap.add_argument("--edge-window", type=int, default=EDGE_WINDOW_DEFAULT)
    ap.add_argument("--rmsd-flag", type=float, default=RMSD_FLAG_DEFAULT,
                    help="RMSD above which ALIGNMENT_POOR is flagged")
    ap.add_argument("--min-common-ca", type=int,
                    default=MIN_COMMON_CA_DEFAULT,
                    help="common CA count below which ALIGNMENT_UNRELIABLE "
                         "is flagged")
    ap.add_argument("--viz-pdb", default=None,
                    help="optional visualization PDB: full ECD CA trace "
                         "(reference frame) + transformed binder")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    cfg = {
        "ref_path": args.reference,
        "domains_spec": args.domains,
        "crop": (int(args.crop.split("-")[0]), int(args.crop.split("-")[1])),
        "contact_cutoff": args.contact_cutoff,
        "clash_cutoff": args.clash_cutoff,
        "edge_window": args.edge_window,
        "rmsd_flag": args.rmsd_flag,
        "min_common_ca": args.min_common_ca,
    }
    local_to_bio, map_meta = abr.load_residue_map(args.residue_map)
    bio_auth, auth_bio = load_bio_auth(args.residue_map_csv)
    ref_polymer, ref_het, ref_fmt, ref_sha = load_reference(args.reference)

    result = audit(args.complex_pdb, ref_polymer, ref_het, ref_fmt, ref_sha,
                   local_to_bio, bio_auth, auth_bio, cfg)
    result["mapping"] = {"residue_map_json": map_meta,
                         "residue_map_csv": {"path": args.residue_map_csv,
                                             "sha256": abr.sha256_file(
                                                 args.residue_map_csv)}}

    if args.viz_pdb:
        # recompute the transform for the visualization output
        chains = abr.parse_pdb(args.complex_pdb)
        P, Q = [], []
        for loc, res in sorted(chains["A"].items()):
            auth = bio_auth.get(local_to_bio.get(loc))
            ref_res = ref_polymer["A"].get(auth) if auth is not None else None
            ca_c = res["atoms"].get("CA")
            ca_r = ref_res["atoms"].get("CA") if ref_res else None
            if ca_c and ca_r:
                P.append(ca_c[:3])
                Q.append(ca_r[:3])
        rot, trans, _ = kabsch(P, Q)
        write_viz_pdb(args.viz_pdb, ref_polymer, chains["B"], rot, trans)
        result["visualization_pdb"] = args.viz_pdb

    Path(args.out).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"complex_pdb": result["complex_pdb"],
                      "alignment": result["alignment"],
                      "flags": result["flags"],
                      "domains_min_dist": {
                          k: v["min_binder_heavy_dist"]
                          for k, v in result["domains"].items()}},
                     indent=2))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
