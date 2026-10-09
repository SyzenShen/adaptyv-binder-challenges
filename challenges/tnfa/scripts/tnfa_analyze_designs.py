"""P5: TNF-specific CPU analysis of BoltzGen design complexes (.cif or .pdb).

For each file: find the binder (shortest chain) and the two target protomers, assign them to 1TNF chains B (main) and A (other)
by joint superposition (best of the two assignments), then report
  - hotspot contacts per protomer (heavy atoms within 4.5 A of the E3 core hotspots from boltz/tnfa_e3_core.yaml)
  - binder residues touching each protomer (a real site binder touches both)
  - interface histidines and the epitope residues they face (pH hypothesis only)
  - C-terminus distance to target (Twin-Strep tag), clash with the third protomer, distance to residue 143
Usage: python3 -I scripts/tnfa_analyze_designs.py DIR_OR_FILES... [--csv out.csv]
Not a pH or affinity predictor; it only reads geometry.
"""
import argparse
import csv
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tnfa_trimer_clash as TC  # noqa: E402

HERE = Path(__file__).resolve().parents[1]
AA3 = {"ALA":"A","ARG":"R","ASN":"N","ASP":"D","CYS":"C","GLN":"Q","GLU":"E","GLY":"G","HIS":"H","ILE":"I","LEU":"L","LYS":"K",
       "MET":"M","PHE":"F","PRO":"P","SER":"S","THR":"T","TRP":"W","TYR":"Y","VAL":"V"}
CORE = {"B": [21, 32, 67, 113, 115, 144, 146, 147], "A": [75, 87, 91, 92]}  # mature numbers, keep in sync with make_boltzgen_inputs
CUT = 4.5
TOK = re.compile(r"'[^']*'|\"[^\"]*\"|\S+")


def read_cif(path):
    """Minimal mmCIF atom_site reader. Returns {chain: [(order_index, resname, atom, xyz)]} (first model only)."""
    cols, rows, in_loop, hdr = [], [], False, True
    for ln in open(path):
        s = ln.strip()
        if s.startswith("loop_"):
            cols, in_loop, hdr = [], True, True
            continue
        if in_loop and hdr and s.startswith("_atom_site."):
            cols.append(s.split(".", 1)[1]); continue
        if in_loop and cols and not s.startswith(("_", "#", "loop_")) and s:
            hdr = False
            rows.append(TOK.findall(s)); continue
        if in_loop and not hdr and (s.startswith(("#", "loop_", "_")) or not s):
            if cols and rows:
                break
    ix = {c: i for i, c in enumerate(cols)}
    chain_key = "label_asym_id" if "label_asym_id" in ix else "auth_asym_id"
    out, seen = {}, {}
    for r in rows:
        if r[ix["group_PDB"]] != "ATOM" or r[ix["label_comp_id"]] not in AA3:
            continue
        if "pdbx_PDB_model_num" in ix and r[ix["pdbx_PDB_model_num"]] != "1":
            continue
        if r[ix.get("type_symbol", ix["label_atom_id"])] == "H":
            continue
        if abs(float(r[ix["Cartn_x"]])) + abs(float(r[ix["Cartn_y"]])) + abs(float(r[ix["Cartn_z"]])) < 1e-3:
            continue  # BoltzGen writes atoms it did not generate at exactly (0, 0, 0); they are not real coordinates
        c = r[ix[chain_key]]
        rid = r[ix["label_seq_id"]] if "label_seq_id" in ix and r[ix["label_seq_id"]] != "." else r[ix["auth_seq_id"]]
        seen.setdefault(c, {})
        n = seen[c].setdefault(rid, len(seen[c]) + 1)
        out.setdefault(c, []).append((n, r[ix["label_comp_id"]], r[ix["label_atom_id"]].strip('"'),
                                      np.array([float(r[ix["Cartn_x"]]), float(r[ix["Cartn_y"]]), float(r[ix["Cartn_z"]])])))
    return out


def read_pdb(path):
    out, seen = {}, {}
    for ln in open(path):
        if ln.startswith("ATOM") and ln[17:20] in AA3 and ln[76:78].strip() != "H":
            c = ln[21]; seen.setdefault(c, {})
            n = seen[c].setdefault(int(ln[22:26]), len(seen[c]) + 1)
            out.setdefault(c, []).append((n, ln[17:20], ln[12:16].strip(), np.array([float(ln[30:38]), float(ln[38:46]), float(ln[46:54])])))
    return out


def load(path):
    return read_cif(path) if str(path).endswith(".cif") else read_pdb(path)


def seq_of(atoms):
    s = {}
    for n, rn, a, x in atoms:
        s[n] = AA3[rn]
    return "".join(s[k] for k in sorted(s))


def ca(atoms):
    d = {n: x for n, rn, a, x in atoms if a == "CA"}
    return [d[k] for k in sorted(d)]


def analyze(path, ref):
    cx = load(path)
    chains = sorted(cx, key=lambda c: len(ca(cx[c])))
    binder, tg = chains[0], chains[1:3]
    best = None
    for t1, t2 in ((tg[0], tg[1]), (tg[1], tg[0])):  # t1 plays chain B, t2 plays chain A
        P = np.array(ca(cx[t1]) + ca(cx[t2])); Q = np.array([a[3] for a in ref["B"] if a[2] == "CA"] + [a[3] for a in ref["A"] if a[2] == "CA"])
        n1 = min(len(ca(cx[t1])), len([a for a in ref["B"] if a[2] == "CA"])); n2 = min(len(ca(cx[t2])), len([a for a in ref["A"] if a[2] == "CA"]))
        P = np.array(ca(cx[t1])[:n1] + ca(cx[t2])[:n2]); Q = np.array([a[3] for a in ref["B"] if a[2] == "CA"][:n1] + [a[3] for a in ref["A"] if a[2] == "CA"][:n2])
        R, pc, qc = TC.kabsch(P, Q)
        rm = float(np.sqrt((((P - pc) @ R - (Q - qc)) ** 2).sum() / len(P)))
        if best is None or rm < best[0]:
            best = (rm, {"B": t1, "A": t2})
    rm, amap = best
    tgt = {r: [(n + 5, rn, a, x) for n, rn, a, x in cx[amap[r]]] for r in "BA"}  # position -> mature number (1TNF lacks residues 1-5)
    bind = cx[binder]
    bxyz = np.array([a[3] for a in bind])
    row = {"file": Path(path).name, "binder_chain": binder, "binder_len": len(set(a[0] for a in bind)),
           "binder_seq": seq_of(bind), "target_fit_rmsd": round(rm, 2)}
    tot = 0
    for r in "BA":
        txyz = np.array([a[3] for a in tgt[r]])
        d = np.linalg.norm(bxyz[:, None, :] - txyz[None, :, :], axis=2)
        touched = sorted({tgt[r][j][0] for j in np.where((d < CUT).any(0))[0]})
        hits = [n for n in CORE[r] if n in touched]
        row[f"hotspots_{r}"] = len(hits); row[f"hotspot_list_{r}"] = " ".join(map(str, hits))
        row[f"binder_res_touching_{r}"] = len({bind[i][0] for i in np.where((d < CUT).any(1))[0]})
        tot += len(hits)
    row["hotspots_total"] = tot
    row["touches_both_protomers"] = int(row["binder_res_touching_B"] > 0 and row["binder_res_touching_A"] > 0)
    # interface histidines and the target residues they face
    allt = [(r, a) for r in "BA" for a in tgt[r]]
    txyz_all = np.array([a[3] for r, a in allt])
    his = []
    for n in sorted({a[0] for a in bind if a[1] == "HIS"}):
        sc = np.array([a[3] for a in bind if a[0] == n and a[2] not in ("N", "C", "O", "CA")])
        if not len(sc): continue
        d = np.linalg.norm(sc[:, None, :] - txyz_all[None, :, :], axis=2)
        near = sorted({(allt[j][0], allt[j][1][0], AA3[allt[j][1][1]]) for j in np.where((d < CUT).any(0))[0]})
        if near:
            his.append(f"H{n}->" + ",".join(f"{aa}{m}({c})" for c, m, aa in near))
    row["interface_His"] = len(his); row["interface_His_faces"] = "; ".join(his)
    # tag, clash with protomer C, residue 143
    cter = np.array([a[3] for a in bind if a[0] >= max(x[0] for x in bind) - 4])
    row["cterm_min_dist"] = round(float(np.linalg.norm(cter[:, None, :] - txyz_all[None, :, :], axis=2).min()), 1)
    P = np.array(ca(cx[amap["B"]])[:len([a for a in ref["B"] if a[2] == "CA"])] + ca(cx[amap["A"]])[:len([a for a in ref["A"] if a[2] == "CA"])])
    Q = np.array([a[3] for a in ref["B"] if a[2] == "CA"][:len(ca(cx[amap["B"]]))] + [a[3] for a in ref["A"] if a[2] == "CA"][:len(ca(cx[amap["A"]]))])
    R, pc, qc = TC.kabsch(P[:len(Q)], Q[:len(P)])
    bref = (bxyz - pc) @ R + qc
    third = np.array([a[3] for a in ref["C"]])
    row["clash_atoms_with_C"] = int((np.linalg.norm(bref[:, None, :] - third[None, :, :], axis=2) < 2.5).sum())
    l143 = np.array([a[3] for a in tgt["B"] + tgt["A"] if a[0] == 143 and a[2] not in ("N", "C", "O", "CA")])
    row["min_dist_res143_sidechain"] = round(float(np.linalg.norm(bxyz[:, None, :] - l143[None, :, :], axis=2).min()), 1) if len(l143) else ""
    return row


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("paths", nargs="+"); ap.add_argument("--csv")
    a = ap.parse_args(argv)
    files = []
    for p in a.paths:
        pp = Path(p)
        files += sorted(pp.glob("*.cif")) + sorted(pp.glob("*.pdb")) if pp.is_dir() else [pp]
    ref = read_pdb(HERE / "data" / "1TNF_ABC_protein.pdb")
    rows = []
    for f in files:
        try:
            rows.append(analyze(f, ref))
        except Exception as e:  # keep going; report the failing file
            print("FAILED", f, repr(e))
    for r in rows:
        print({k: r[k] for k in ("file", "binder_len", "hotspots_total", "touches_both_protomers", "interface_His", "cterm_min_dist", "clash_atoms_with_C", "target_fit_rmsd")})
    if a.csv and rows:
        with open(a.csv, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    main()
