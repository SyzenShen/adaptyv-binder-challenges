"""Stage 1.5 structural audit (Parts B/D/E + C geometry inputs).

Parses data/raw/6ARU.cif directly and computes:
- Shrake-Rupley SASA (numpy, 96-point sphere, 1.4 A probe) per EGFR residue
  in four contexts: A alone, A+glycan, A+Fab, A+Fab+glycan;
- minimum HEAVY-atom distances (with closest atom pair) per EGFR residue to
  Cetuximab Fab (chains B/C) and to each observed glycan (D-H);
- epitope residue x glycosylation-site distance matrix (to Asn and to glycan);
- patch-to-patch 3D continuity metrics and hypothetical hotspot windows;
- H370/H418/H433 exposure, secondary structure (from _struct_conf),
  ionizable neighborhoods and reachability.

Outputs:
- data/processed/domain3_geometry.csv
- results/epitope_glycan_distances.csv
- data/processed/geometry_audit.json

Run: .venv/bin/python scripts/audit_geometry.py
"""
from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from Bio import SeqIO
from Bio.PDB.MMCIF2Dict import MMCIF2Dict

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
RES = ROOT / "results"

OFFSET = 24  # 6ARU chain A: UniProt = label_seq_id + 24 (residue_map.meta.json)
EGFR_CHAIN = "A"
FAB_CHAINS = {"B", "C"}
GLYCAN_CHAINS = ["D", "E", "F", "G", "H"]
GLYCAN_SITE_UNIPROT = {"N352": 352, "N361": 361, "N413": 413, "N444": 444}
HISTIDINES = [370, 418, 433]
DOMAIN3 = (310, 481)
PROBE = 1.4
N_SPHERE = 96
VDW = {"C": 1.70, "N": 1.65, "O": 1.61, "S": 1.80}
# Tien et al. 2013 empirical maximal residue ASA (A^2)
MAX_ASA = {"A": 129.0, "R": 274.0, "N": 195.0, "D": 193.0, "C": 167.0,
           "Q": 225.0, "E": 223.0, "G": 104.0, "H": 224.0, "I": 197.0,
           "L": 201.0, "K": 236.0, "M": 224.0, "F": 240.0, "P": 159.0,
           "S": 155.0, "T": 172.0, "W": 285.0, "Y": 263.0, "V": 174.0}
THREE_TO_ONE = {"ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C",
                "GLN": "Q", "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I",
                "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F", "PRO": "P",
                "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V"}
ACIDIC, BASIC, POLAR = set("DE"), set("KRH"), set("STNQ")


def golden_sphere(n):
    idx = np.arange(n)
    z = 1 - 2 * (idx + 0.5) / n
    r = np.sqrt(1 - z * z)
    phi = math.pi * (1 + 5 ** 0.5) * idx
    return np.stack([r * np.cos(phi), r * np.sin(phi), z], axis=1)


SPHERE = golden_sphere(N_SPHERE)


def sasa(coords, radii, mask, score_idx, chunk=256):
    """Shrake-Rupley per-atom SASA. Neighbors come from mask==1 atoms;
    SASA is computed only for atoms in score_idx."""
    out = np.zeros(len(coords))
    neigh_idx = np.nonzero(mask)[0]
    nc = coords[neigh_idx]
    nr = radii[neigh_idx] + PROBE
    for i in score_idx:
        i = int(i)
        ri = radii[i] + PROBE
        d = np.linalg.norm(nc - coords[i], axis=1)
        close = neigh_idx[(d < ri + nr) & (neigh_idx != i)]
        pts = coords[i] + ri * SPHERE
        blocked = np.zeros(N_SPHERE, dtype=bool)
        for j in close:
            rj = radii[j] + PROBE
            v = pts - coords[j]
            dd = np.einsum("ij,ij->i", v, v)
            # test sphere center buried by neighbor (classic SR cutoff)
            hit = dd < rj * rj
            blocked |= hit
        out[i] = 4 * math.pi * ri * ri / N_SPHERE * (N_SPHERE - blocked.sum())
    return out


def main() -> int:
    d = MMCIF2Dict(str(RAW / "6ARU.cif"))
    a = d

    def col(name):
        return a[name]

    asym = col("_atom_site.label_asym_id")
    comp = col("_atom_site.label_comp_id")
    atom_name = col("_atom_site.label_atom_id")
    label_seq = col("_atom_site.label_seq_id")
    elem = col("_atom_site.type_symbol")
    xs = np.array([float(x) for x in col("_atom_site.Cartn_x")])
    ys = np.array([float(x) for x in col("_atom_site.Cartn_y")])
    zs = np.array([float(x) for x in col("_atom_site.Cartn_z")])
    coords = np.stack([xs, ys, zs], axis=1)
    radii = np.array([VDW.get(e, 1.70) for e in elem])

    is_egfr = np.array([c == EGFR_CHAIN for c in asym])
    is_fab = np.array([c in FAB_CHAINS for c in asym])
    gly_masks = {g: np.array([c == g for c in asym]) for g in GLYCAN_CHAINS}
    is_gly = np.array([c in set(GLYCAN_CHAINS) for c in asym])
    is_ca = np.array([n == "CA" for n in atom_name])

    egfr_idx = np.nonzero(is_egfr)[0]
    seq_of_atom = {}
    for i in egfr_idx:
        if label_seq[i] not in (".", "?"):
            seq_of_atom[i] = int(label_seq[i])
    residues = sorted(set(seq_of_atom.values()))
    atoms_of_res = defaultdict(list)
    for i, s in seq_of_atom.items():
        atoms_of_res[s].append(i)

    # --- secondary structure from _struct_conf (label_seq numbering) ---
    ss = {}
    for k in ("_struct_conf.beg_label_seq_id",):
        n = len(d.get(k, []))
        for i in range(n):
            b = int(d["_struct_conf.beg_label_seq_id"][i])
            e = int(d["_struct_conf.end_label_seq_id"][i])
            kind = "helix" if "HELX" in d["_struct_conf.conf_type_id"][i] else "sheet"
            for s in range(b, e + 1):
                ss[s] = kind

    # --- SASA in four contexts (EGFR atoms scored) ---
    contexts = {
        "A_only": is_egfr,
        "A_glycan": is_egfr | is_gly,
        "A_fab": is_egfr | is_fab,
        "A_fab_glycan": is_egfr | is_fab | is_gly,
    }
    sasa_res = {}
    for cname, mask in contexts.items():
        sa = sasa(coords, radii, mask, egfr_idx)
        per_res = {}
        for s, ats in atoms_of_res.items():
            per_res[s] = float(sa[ats].sum())
        sasa_res[cname] = per_res

    human_seq = str(SeqIO.read(OUT / "human_construct_25_645.fasta", "fasta").seq)

    def min_dist(res_atoms, target_idx, want_pair=False):
        """min heavy-atom distance from residue atom set to target atom set."""
        if not len(target_idx):
            return (math.nan, None) if want_pair else math.nan
        best = math.inf
        pair = None
        tc = coords[target_idx]
        for i in res_atoms:
            dd = np.linalg.norm(tc - coords[i], axis=1)
            k = int(dd.argmin())
            if dd[k] < best:
                best = float(dd[k])
                pair = (i, int(target_idx[k]))
        return (best, pair) if want_pair else best

    fab_idx = np.nonzero(is_fab)[0]
    gly_idx = {g: np.nonzero(m)[0] for g, m in gly_masks.items()}
    ca_coord = {}
    for s, ats in atoms_of_res.items():
        for i in ats:
            if is_ca[i]:
                ca_coord[s] = coords[i]

    rows = []
    for s in residues:
        upos = s + OFFSET
        if not (DOMAIN3[0] <= upos <= DOMAIN3[1]):
            continue
        ats = atoms_of_res[s]
        one = THREE_TO_ONE.get(comp[ats[0]], "X")
        d_fab, pair_fab = min_dist(ats, fab_idx, want_pair=True)
        gly_best = math.inf
        gly_chain_best = ""
        for g, gi in gly_idx.items():
            v = min_dist(ats, gi)
            if v < gly_best:
                gly_best, gly_chain_best = v, g
        d_other_gly = {g: min_dist(ats, gi) for g, gi in gly_idx.items()}
        sa = {c: sasa_res[c][s] for c in contexts}
        rel = sa["A_only"] / MAX_ASA.get(one, 200.0)
        rows.append({
            "uniprot_pos": upos,
            "label_seq_id": s,
            "residue": one,
            "ss": ss.get(s, "coil"),
            "sasa_A_only": round(sa["A_only"], 1),
            "rel_sasa": round(rel, 3),
            "sasa_occluded_by_glycan": round(sa["A_only"] - sa["A_glycan"], 1),
            "sasa_occluded_by_fab": round(sa["A_only"] - sa["A_fab"], 1),
            "dist_fab_min_heavy_A": round(d_fab, 2),
            "dist_glycan_min_heavy_A": round(gly_best, 2),
            "closest_glycan_chain": gly_chain_best,
            **{f"dist_glycan_{g}": round(v, 2) for g, v in d_other_gly.items()},
            "fab_closest_atom_pair": f"{comp[pair_fab[0]]}{upos}.{atom_name[pair_fab[0]]}"
                                     f"-{asym[pair_fab[1]]}{comp[pair_fab[1]]}.{atom_name[pair_fab[1]]}"
                                     if pair_fab else "",
        })
    rows.sort(key=lambda r: r["uniprot_pos"])
    geo_csv = OUT / "domain3_geometry.csv"
    with geo_csv.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    by_pos = {r["uniprot_pos"]: r for r in rows}

    # --- ECD alignment annotation (Part A conservation) ---
    aln_rows = list(csv.DictReader(open(OUT / "human_mouse_ecd_alignment.csv")))
    aln = {int(r["human_uniprot_pos"]): r for r in aln_rows if r["human_uniprot_pos"]}

    # --- glycosylation evidence from UniProt flat text ---
    def uniprot_carbohyd(acc):
        text = (RAW / f"{acc}.txt").read_text()
        sites, cur = set(), None
        for ln in text.splitlines():
            if ln.startswith("FT   CARBOHYD"):
                spec = ln[17:].strip().rstrip(".")
                cur = int(spec) if spec.isdigit() else None
            elif ln.startswith("FT                   /note") and cur is not None:
                sites.add(cur)
        return sites
    h_carb = uniprot_carbohyd("P00533")
    m_carb = uniprot_carbohyd("Q01279")
    structural = {352: "D", 361: "F", 413: "G", 444: "E"}  # from struct_conn, label+24

    # --- Part B: epitope x glycan distance matrix ---
    epi_csv = list(csv.DictReader(open(OUT / "epitope_candidates.csv")))
    patches = {c["candidate_id"]: (int(c["uniprot_begin"]), int(c["uniprot_end"]))
               for c in epi_csv}
    dist_rows = []
    for epi_id, (lo, hi) in patches.items():
        for p in range(lo, hi + 1):
            ats = atoms_of_res[p - OFFSET]
            for site_name, site_up in GLYCAN_SITE_UNIPROT.items():
                site_ats = atoms_of_res[site_up - OFFSET]
                d_asn = min_dist(ats, np.array(site_ats, dtype=int))
                d_gly = min_dist(ats, gly_idx[structural[site_up]])
                mrow = aln.get(site_up, {})
                dist_rows.append({
                    "epitope": epi_id,
                    "epitope_residue_uniprot": p,
                    "epitope_residue_aa": human_seq[p - 25],
                    "glycan_site": site_name,
                    "dist_to_Asn_heavy_A": round(d_asn, 2),
                    "dist_to_observed_glycan_heavy_A": round(d_gly, 2),
                    "site_human_uniprot_annotation": "CARBOHYD" if site_up in h_carb else "none",
                    "site_structurally_glycosylated_6ARU": "yes(" + structural[site_up] + ")",
                    "site_mouse_Q01279": mrow.get("mouse_aa", ""),
                    "site_mouse_uniprot_pos": mrow.get("mouse_uniprot_pos", ""),
                    "site_mouse_CARBOHYD_annotation":
                        "CARBOHYD" if mrow.get("mouse_uniprot_pos") and
                        int(mrow["mouse_uniprot_pos"]) in m_carb
                        else ("no_sequon" if mrow.get("mouse_aa") != "N" else "sequon_only"),
                })
    RES.mkdir(exist_ok=True)
    with (RES / "epitope_glycan_distances.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(dist_rows[0].keys()))
        w.writeheader()
        w.writerows(dist_rows)

    # patch summaries for glycan
    gly_summary = {}
    for epi_id, (lo, hi) in patches.items():
        sub = [r for r in dist_rows if r["epitope"] == epi_id]
        gly_summary[epi_id] = {
            site: {
                "min_dist_to_Asn_A": min(r["dist_to_Asn_heavy_A"] for r in sub
                                         if r["glycan_site"] == site),
                "min_dist_to_glycan_A": min(r["dist_to_observed_glycan_heavy_A"] for r in sub
                                            if r["glycan_site"] == site),
                "closest_residue": min((r for r in sub if r["glycan_site"] == site),
                                       key=lambda r: r["dist_to_observed_glycan_heavy_A"])
                ["epitope_residue_uniprot"],
            } for site in GLYCAN_SITE_UNIPROT
        }

    # --- Part D: cetuximab functional-epitope residue audit ---
    # Literature list (Tydings 2024 Protein Sci / cetuximab crystal structures)
    # is in PDB-auth numbering; 6ARU auth = label = UniProt - 24.
    lit_auth = [("Q", 384), ("P", 387), ("Q", 408), ("H", 409), ("F", 412),
                ("V", 417), ("S", 418), ("K", 443)]
    cetux = []
    for aa, auth_n in lit_auth:
        up = auth_n + OFFSET
        ats = atoms_of_res[auth_n]
        dv, pair = min_dist(ats, fab_idx, want_pair=True)
        cetux.append({
            "literature_auth_residue": f"{aa}{auth_n}",
            "uniprot_pos": up,
            "uniprot_aa": human_seq[up - 25],
            "aa_matches": human_seq[up - 25] == aa,
            "dist_fab_min_heavy_A": round(dv, 2),
            "closest_atom_pair": f"{comp[pair[0]]}{up}.{atom_name[pair[0]]}"
                                 f"-{asym[pair[1]]}{comp[pair[1]]}.{atom_name[pair[1]]}",
        })
    patch_fab = {}
    for epi_id, (lo, hi) in patches.items():
        vals = [(p, by_pos[p]["dist_fab_min_heavy_A"]) for p in range(lo, hi + 1)]
        patch_fab[epi_id] = {"min": min(v for _, v in vals),
                             "closest_residue": min(vals, key=lambda x: x[1])[0],
                             "residues_within_5A": [p for p, v in vals if v < 5.0],
                             "residues_within_8A": [p for p, v in vals if v < 8.0]}

    # --- Part E: patch continuity / windows ---
    p1lo, p1hi = patches["EPI_H_2"]
    p2lo, p2hi = patches["EPI_H_3"]

    def seg_metrics(a_lo, a_hi, b_lo=None, b_hi=None):
        ats_a = [i for p in range(a_lo, a_hi + 1) for i in atoms_of_res[p - OFFSET]]
        m = {
            "exposed_SASA_sum_A2": round(sum(by_pos[p]["sasa_A_only"]
                                             for p in range(a_lo, a_hi + 1) if p in by_pos), 1),
            "fab_min_A": min(by_pos[p]["dist_fab_min_heavy_A"]
                             for p in range(a_lo, a_hi + 1) if p in by_pos),
            "glycan_min_A": min(by_pos[p]["dist_glycan_min_heavy_A"]
                                for p in range(a_lo, a_hi + 1) if p in by_pos),
            "n_exposed_relSASA_gt_0.2": sum(1 for p in range(a_lo, a_hi + 1)
                                            if p in by_pos and by_pos[p]["rel_sasa"] > 0.2),
        }
        if b_lo is not None:
            ats_b = [i for p in range(b_lo, b_hi + 1) for i in atoms_of_res[p - OFFSET]]
            d, pair = min_dist(ats_a, np.array(ats_b, dtype=int), want_pair=True)
            cas_a = np.array([ca_coord[p - OFFSET] for p in range(a_lo, a_hi + 1)
                              if p - OFFSET in ca_coord])
            cas_b = np.array([ca_coord[p - OFFSET] for p in range(b_lo, b_hi + 1)
                              if p - OFFSET in ca_coord])
            ca_d = float(np.min(np.linalg.norm(cas_a[:, None, :] - cas_b[None, :, :], axis=2)))
            cross5 = []
            for pa in range(a_lo, a_hi + 1):
                for pb in range(b_lo, b_hi + 1):
                    dd = min_dist(atoms_of_res[pa - OFFSET],
                                  np.array(atoms_of_res[pb - OFFSET], dtype=int))
                    if dd < 5.0:
                        cross5.append([pa, pb, round(dd, 2)])
            cent_a, cent_b = cas_a.mean(0), cas_b.mean(0)
            m.update({
                "inter_patch_min_heavy_A": round(d, 2),
                "inter_patch_min_CA_A": round(ca_d, 2),
                "centroid_CA_distance_A": round(float(np.linalg.norm(cent_a - cent_b)), 2),
                "cross_patch_pairs_lt_5A": cross5,
                "heavy_closest_pair": f"{comp[pair[0]]}{seq_of_atom[pair[0]]+OFFSET}.{atom_name[pair[0]]}"
                                      f"-{comp[pair[1]]}{seq_of_atom[pair[1]]+OFFSET}.{atom_name[pair[1]]}",
                "combined_exposed_SASA_A2": m["exposed_SASA_sum_A2"]
                + round(sum(by_pos[p]["sasa_A_only"] for p in range(b_lo, b_hi + 1)
                            if p in by_pos), 1),
                "max_CA_extent_A": round(float(max(
                    np.linalg.norm(ca_coord[a - OFFSET] - ca_coord[b - OFFSET])
                    for a in range(a_lo, a_hi + 1) for b in range(b_lo, b_hi + 1))), 1),
            })
        return m

    continuity = {
        "EPI_H_2_vs_EPI_H_3": seg_metrics(p1lo, p1hi, p2lo, p2hi),
        "window_416_431": seg_metrics(416, 431),
        "window_416_433_incl_H433": seg_metrics(416, 433),
        "window_416_436_incl_F436": seg_metrics(416, 436),
        "window_385_433_combined_with_gap": None,  # filled below
    }
    # full 385..433 span metrics
    full = seg_metrics(385, 433)
    continuity["window_385_433_combined_with_gap"] = full
    # residues inside the sequence gap 404..415 bridging both segments
    gap_rows = [{"uniprot_pos": p, **{k: by_pos[p][k] for k in
                 ("residue", "ss", "rel_sasa", "dist_fab_min_heavy_A",
                  "dist_glycan_min_heavy_A", "closest_glycan_chain")}}
                for p in range(404, 416) if p in by_pos]
    continuity["gap_residues_404_415"] = gap_rows
    # does the gap bring surfaces adjacent? gap residues within 6.5 A of both segs
    bridge = []
    seg1_at = [i for p in range(p1lo, p1hi + 1) for i in atoms_of_res[p - OFFSET]]
    seg2_at = [i for p in range(p2lo, p2hi + 1) for i in atoms_of_res[p - OFFSET]]
    for p in range(404, 416):
        ats = atoms_of_res[p - OFFSET]
        d1 = min_dist(ats, np.array(seg1_at, dtype=int))
        d2 = min_dist(ats, np.array(seg2_at, dtype=int))
        if d1 < 6.5 and d2 < 6.5:
            bridge.append({"uniprot_pos": p, "d_to_seg1": round(d1, 2),
                           "d_to_seg2": round(d2, 2)})
    continuity["gap_residues_bridging_both_within_6.5A"] = bridge

    # --- Part C: histidine audit geometry ---
    his_geo = {}
    for hp in HISTIDINES:
        s = hp - OFFSET
        ats = atoms_of_res[s]
        ca = ca_coord.get(s)
        # neighborhood: residues within 8 A heavy-atom
        nb = defaultdict(list)
        for t_s, t_ats in atoms_of_res.items():
            if t_s == s:
                continue
            dd = min_dist(ats, np.array(t_ats, dtype=int))
            if dd <= 8.0:
                aa1 = THREE_TO_ONE.get(comp[t_ats[0]], "X")
                grp = ("acidic" if aa1 in ACIDIC else "basic" if aa1 in BASIC
                       else "polar" if aa1 in POLAR else "hydrophobic")
                nb[grp].append(t_s + OFFSET)
        patch_d = {}
        for epi_id, (lo, hi) in patches.items():
            ds = [min_dist(ats, np.array(atoms_of_res[p - OFFSET], dtype=int))
                  for p in range(lo, hi + 1)]
            patch_d[epi_id] = round(min(ds), 2)
        within12 = [u for u, r in by_pos.items()
                    if ca is not None and (u - OFFSET) in ca_coord
                    and np.linalg.norm(ca_coord[u - OFFSET] - ca) <= 12
                    and r["rel_sasa"] > 0.2]
        gly_d = {g: round(min_dist(ats, gi), 2) for g, gi in gly_idx.items()}
        mr = aln.get(hp, {})
        his_geo[f"H{hp}"] = {
            "uniprot_pos": hp,
            "mouse_aa": mr.get("mouse_aa", ""),
            "mouse_uniprot_pos": mr.get("mouse_uniprot_pos", ""),
            "mouse_class": mr.get("class", ""),
            "ss": ss.get(s, "coil"),
            "rel_sasa": by_pos[hp]["rel_sasa"],
            "sasa_A2": by_pos[hp]["sasa_A_only"],
            "sasa_occluded_by_fab": by_pos[hp]["sasa_occluded_by_fab"],
            "dist_fab_min_heavy_A": by_pos[hp]["dist_fab_min_heavy_A"],
            "dist_glycan_min_heavy_A": by_pos[hp]["dist_glycan_min_heavy_A"],
            "dist_to_each_glycan": gly_d,
            "dist_to_patches": patch_d,
            "neighborhood_8A": {k: sorted(v) for k, v in nb.items()},
            "exposed_surface_residues_within_12A_CA": within12,
            "within_EPI_H_3": p2lo <= hp <= p2hi,
        }

    meta = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "method": {
            "sasa": "Shrake-Rupley numpy, 96-point golden sphere, probe 1.4 A",
            "distances": "minimum heavy-atom distance (all deposited atoms are heavy)",
            "chains": {"egfr": "A", "fab": sorted(FAB_CHAINS), "glycans": GLYCAN_CHAINS},
            "numbering": "UniProt P00533-1; 6ARU label_seq_id = auth_seq_id = UniProt - 24",
        },
        "glycan_evidence": {
            "human_uniprot_CARBOHYD_sites": sorted(h_carb),
            "mouse_uniprot_CARBOHYD_sites": sorted(m_carb),
            "structurally_glycosylated_in_6ARU": structural,
        },
        "glycan_patch_summary": gly_summary,
        "cetuximab_lit_residues_audit": cetux,
        "patch_fab_distances": patch_fab,
        "patch_continuity": continuity,
        "histidines": his_geo,
    }
    (OUT / "geometry_audit.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps({k: meta[k] for k in
                      ("glycan_evidence", "patch_fab_distances", "cetuximab_lit_residues_audit")},
                     indent=2))
    print("continuity:", json.dumps({k: v for k, v in continuity.items()
                                     if k.startswith(("EPI", "window"))}, indent=2))
    print("histidines:", json.dumps(his_geo, indent=2)[:2000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
