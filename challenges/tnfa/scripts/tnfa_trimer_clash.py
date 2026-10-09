"""P5: CPU check that a designed binder (made against protomers B+A) does not collide with the third protomer.

Usage: python3 -I scripts/tnfa_trimer_clash.py complex.pdb --target-chains B A --binder-chain X
The target chains of the design complex are superposed (CA Kabsch, matched by residue order) onto 1TNF chains B and A, the
same transform is applied to the binder, and binder heavy atoms closer than 2.5 A to 1TNF chain C are counted.
Also reports the distance of the binder's last 5 residues to the target (the C-terminus carries the Twin-Strep tag in the assay and must stay free) and binder atoms within 4 A of residue 143 (1TNF has Leu where wild type has Asp).
"""
import argparse
import sys
from pathlib import Path

import numpy as np

D = Path(__file__).resolve().parents[1] / "data"


def read(path, chains=None):
    out = {}
    for ln in open(path):
        if ln.startswith(("ATOM", "HETATM")) and ln[76:78].strip() != "H":
            c = ln[21]
            if chains is None or c in chains:
                out.setdefault(c, []).append((int(ln[22:26]), ln[12:16].strip(), np.array([float(ln[30:38]), float(ln[38:46]), float(ln[46:54])])))
    return out


def kabsch(P, Q):
    pc, qc = P.mean(0), Q.mean(0)
    U, S, Vt = np.linalg.svd((P - pc).T @ (Q - qc))
    d = np.sign(np.linalg.det(U @ Vt))
    R = U @ np.diag([1, 1, d]) @ Vt
    return R, pc, qc


def trimer_clash(complex_pdb, target_chains, binder_chain, ref_pdb=None, cutoff=2.5):
    ref = read(ref_pdb or D / "1TNF_ABC_protein.pdb")
    cx = read(complex_pdb)
    P, Q = [], []
    for tc, rc in zip(target_chains, ("B", "A")):
        ca_x = [a[2] for a in cx[tc] if a[1] == "CA"]
        ca_r = [a[2] for a in ref[rc] if a[1] == "CA"]
        n = min(len(ca_x), len(ca_r))
        P += ca_x[:n]; Q += ca_r[:n]
    R, pc, qc = kabsch(np.array(P), np.array(Q))
    binder = (np.array([a[2] for a in cx[binder_chain]]) - pc) @ R + qc
    third = np.array([a[2] for a in ref["C"]])
    dmin = np.linalg.norm(binder[:, None, :] - third[None, :, :], axis=2)
    l143 = np.array([a[2] for a in ref["B"] + ref["A"] if a[0] == 143])
    d143 = np.linalg.norm(binder[:, None, :] - l143[None, :, :], axis=2).min() if len(l143) else float("nan")
    cterm = np.array([a[2] for a in cx[binder_chain] if a[0] >= max(x[0] for x in cx[binder_chain]) - 4])
    tgt = np.array([a[2] for c in target_chains for a in cx[c]])
    d_cterm = float(np.linalg.norm(cterm[:, None, :] - tgt[None, :, :], axis=2).min())
    return {"cterm_min_dist_to_target": d_cterm, "clash_atoms_with_chain_C": int((dmin < cutoff).sum()), "min_dist_to_C": float(dmin.min()),
            "min_dist_to_res143": float(d143)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("complex_pdb"); ap.add_argument("--target-chains", nargs=2, default=["B", "A"]); ap.add_argument("--binder-chain", default="X")
    a = ap.parse_args(argv)
    print(trimer_clash(a.complex_pdb, a.target_chains, a.binder_chain))


if __name__ == "__main__":
    main()
