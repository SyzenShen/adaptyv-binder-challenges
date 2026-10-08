"""P3: exposed-groove epitope candidates on the TNF-alpha trimer.

Shrake-Rupley SASA per residue in the trimer and in each isolated chain. A position is a groove/rim candidate if it is
partly buried by trimerization (dSASA > 10 A^2) and still exposed in the trimer (SASA >= 20 A^2).
Outputs data/epitope_candidates.json (per chain, with human/mouse conservation).
"""
import json
from pathlib import Path

import numpy as np

D = Path(__file__).resolve().parents[1] / "data"
R = {"C": 1.70, "N": 1.55, "O": 1.52, "S": 1.80}
PROBE, NPT = 1.4, 400


def sphere(n):
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    th = np.pi * (1 + 5 ** 0.5) * i
    return np.c_[np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)]


def load():
    at = []
    for ln in (D / "1TNF_ABC_protein.pdb").read_text().splitlines():
        if ln.startswith("ATOM"):
            at.append((ln[21], int(ln[22:26]), ln[12:16].strip(), ln[76:78].strip() or ln[12:16].strip()[0],
                       [float(ln[30:38]), float(ln[38:46]), float(ln[46:54])]))
    return at


def sasa(at, mask):
    xyz = np.array([a[4] for a in at]); rad = np.array([R[a[3]] + PROBE for a in at])
    out = np.zeros(len(at)); sp = sphere(NPT); idx = np.where(mask)[0]
    for i in idx:
        pts = xyz[i] + rad[i] * sp
        near = [j for j in idx if j != i and np.linalg.norm(xyz[j] - xyz[i]) < rad[i] + rad[j]]
        free = np.ones(NPT, bool)
        for j in near:
            free &= np.linalg.norm(pts - xyz[j], axis=1) >= rad[j]
        out[i] = 4 * np.pi * rad[i] ** 2 * free.mean()
    return out


def per_res(at, s):
    d = {}
    for a, v in zip(at, s):
        d[(a[0], a[1])] = d.get((a[0], a[1]), 0) + v
    return d


def main():
    at = load()
    tri = per_res(at, sasa(at, np.ones(len(at), bool)))
    mono = {}
    for c in "ABC":
        mono.update({k: v for k, v in per_res(at, sasa(at, np.array([a[0] == c for a in at]))).items() if k[0] == c})
    cons = {r["res"]: r for r in json.load(open(D / "conservation_interface.json"))}
    out = {"rule": "dSASA>10 and trimer SASA>=20 (A^2)", "chains": {}}
    for c in "ABC":
        rows = []
        for (ch, rn), t in sorted(tri.items()):
            if ch == c and mono[(ch, rn)] - t > 10 and t >= 20:
                k = cons[rn]
                rows.append({"res": rn, "aa": k["human"], "mouse": k["mouse"], "conserved": k["conserved"],
                             "sasa_trimer": round(t, 1), "dsasa": round(mono[(ch, rn)] - t, 1)})
        out["chains"][c] = rows
        print(c, len(rows), " ".join(f"{r['aa']}{r['res']}{'' if r['conserved'] else '*'}" for r in rows))
    json.dump(out, open(D / "epitope_candidates.json", "w"), indent=1)


if __name__ == "__main__":
    main()
