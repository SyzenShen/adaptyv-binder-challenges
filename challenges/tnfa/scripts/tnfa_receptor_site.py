"""P4: receptor-defined functional epitope on the TNF trimer, expressed on 1TNF chains.

7KP7 (mouse TNF + human TNFR1, TNF chains A-C, receptor chains D-F) gives, per receptor chain, which TNF protomer
contributes which residues (mature numbering via alignment). The two contributing protomers of the best receptor are then
superposed (CA Kabsch) onto every ordered chain pair of 1TNF; the pair with the lowest RMSD carries the labels.
Output: data/receptor_site.json.
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tnfa_complex_epitopes as T

D = T.D
CUT = T.CUT


def kabsch_rmsd(P, Q):
    P0, Q0 = P - P.mean(0), Q - Q.mean(0)
    U, S, Vt = np.linalg.svd(P0.T @ Q0)
    d = np.sign(np.linalg.det(U @ Vt))
    R = U @ np.diag([1, 1, d]) @ Vt
    return float(np.sqrt(((P0 @ R - Q0) ** 2).sum() / len(P)))


def main():
    cx = T.chains(D / "7KP7.pdb")
    maps = {c: T.tnf_map(cx[c])[1] for c in "ABC"}
    cons = {r["res"]: r for r in json.load(open(D / "conservation_interface.json"))}
    site = {}
    for rc in "DEF":
        rxyz = np.array([a[3] for a in cx[rc]])
        per = {}
        for c in "ABC":
            hits = {}
            for rn, ic, name, xyz in cx[c]:
                if rn in maps[c] and (np.linalg.norm(rxyz - xyz, axis=1) < CUT).any():
                    hits[maps[c][rn]] = T.AA3[name]
            if hits:
                per[c] = hits
        site[rc] = per
        print("receptor", rc, {c: len(v) for c, v in per.items()})
    # best receptor: the one with two contributing protomers and most contacts
    best = max(site, key=lambda r: (len(site[r]) >= 2, sum(len(v) for v in site[r].values())))
    per = site[best]
    main_c, other_c = sorted(per, key=lambda c: -len(per[c]))[:2]
    print("best receptor", best, "protomers", main_c, other_c)

    # CA coordinates keyed by mature number
    def ca(atoms_by_chain, mp, c):
        d = {}
        for ln in open(atoms_by_chain):
            if ln.startswith("ATOM") and ln[12:16].strip() == "CA" and ln[21] == c and ln[17:20] in T.AA3:
                rn = int(ln[22:26])
                if mp is None: d[rn] = np.array([float(ln[30:38]), float(ln[38:46]), float(ln[46:54])])
                elif rn in mp: d[mp[rn]] = np.array([float(ln[30:38]), float(ln[38:46]), float(ln[46:54])])
        return d
    ref = {c: ca(D / "7KP7.pdb", maps[c], c) for c in (main_c, other_c)}
    one = {c: ca(D / "1TNF_ABC_protein.pdb", None, c) for c in "ABC"}
    best_pair = None
    for a, b in itertools.permutations("ABC", 2):
        common_a = sorted(set(ref[main_c]) & set(one[a])); common_b = sorted(set(ref[other_c]) & set(one[b]))
        P = np.array([ref[main_c][r] for r in common_a] + [ref[other_c][r] for r in common_b])
        Q = np.array([one[a][r] for r in common_a] + [one[b][r] for r in common_b])
        rm = kabsch_rmsd(P, Q)
        print("1TNF pair", a, b, "rmsd", round(rm, 2), "n", len(P))
        if best_pair is None or rm < best_pair[0]:
            best_pair = (rm, a, b)
    rm, a, b = best_pair
    out = {"receptor_structure": "7KP7 (mouse TNF + human TNFR1)", "receptor_chain": best, "rmsd_to_1TNF_A": round(rm, 2),
           "map": {"main": a, "other": b}, "residues": {}}
    for role, c1tnf, c7 in (("main", a, main_c), ("other", b, other_c)):
        rows = []
        for r, aa in sorted(per[c7].items()):
            k = cons[r]
            rows.append({"res": r, "aa_mouse_struct": aa, "human": k["human"], "mouse": k["mouse"], "conserved": k["conserved"]})
        out["residues"][f"{role}_chain_{c1tnf}"] = rows
        print(role, c1tnf, " ".join(f"{x['human']}{x['res']}{'' if x['conserved'] else '*'}" for x in rows))
    json.dump(out, open(D / "receptor_site.json", "w"), indent=1)


if __name__ == "__main__":
    main()
