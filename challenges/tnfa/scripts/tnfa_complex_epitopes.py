"""P4: map receptor (TNFR1, 7KP7) and antibody (adalimumab 3WD5, infliximab 4G3Y) contacts onto TNF 1TNF numbering.

TNF chains are identified by sequence (global alignment against the 157-aa mature domain), never by chain letter.
Contact = any heavy atom of a TNF residue within 4.5 A of a non-TNF protein chain. Output: data/complex_epitopes.json.
"""
import json
from pathlib import Path

import numpy as np

D = Path(__file__).resolve().parents[1] / "data"
AA3 = {"ALA":"A","ARG":"R","ASN":"N","ASP":"D","CYS":"C","GLN":"Q","GLU":"E","GLY":"G","HIS":"H","ILE":"I","LEU":"L",
       "LYS":"K","MET":"M","PHE":"F","PRO":"P","SER":"S","THR":"T","TRP":"W","TYR":"Y","VAL":"V"}
CUT = 4.5
MATURE = "".join(l.strip() for l in open(D / "P01375.fasta") if not l.startswith(">"))[76:233]


def chains(path):
    ch = {}
    for ln in open(path):
        if ln.startswith("ATOM") and ln[17:20] in AA3 and ln[76:78].strip() != "H":
            ch.setdefault(ln[21], []).append((int(ln[22:26]), ln[26], ln[17:20], np.array([float(ln[30:38]), float(ln[38:46]), float(ln[46:54])])))
    return ch


def nw_map(seq, ref, g=-2):
    """Needleman-Wunsch (identity +1, mismatch -1, gap -2). Returns {index in seq (0-based): index in ref (1-based)}."""
    M, N = len(seq), len(ref)
    S = [[0] * (N + 1) for _ in range(M + 1)]
    for i in range(M + 1): S[i][0] = g * i
    for j in range(N + 1): S[0][j] = g * j
    sc = lambda x, y: 1 if x == y else -1
    for i in range(1, M + 1):
        for j in range(1, N + 1):
            S[i][j] = max(S[i-1][j-1] + sc(seq[i-1], ref[j-1]), S[i-1][j] + g, S[i][j-1] + g)
    i, j, mp = M, N, {}
    while i and j:
        if S[i][j] == S[i-1][j-1] + sc(seq[i-1], ref[j-1]):
            mp[i-1] = j; i -= 1; j -= 1
        elif S[i][j] == S[i-1][j] + g:
            i -= 1
        else:
            j -= 1
    return mp


def tnf_map(atoms):
    """Residue order of a chain -> mature TNF number via alignment. Returns (identity, {pdb resnum: mature number})."""
    order, seen = [], set()
    for rn, ic, name, _ in atoms:
        if (rn, ic) not in seen:
            seen.add((rn, ic)); order.append((rn, ic, AA3[name]))
    seq = "".join(a for _, _, a in order)
    mp = nw_map(seq, MATURE)
    ident = sum(MATURE[j - 1] == seq[i] for i, j in mp.items())
    return ident / len(seq), {order[i][0]: j for i, j in mp.items() if MATURE[j - 1] == seq[i]}


def main():
    out = {"cutoff_A": CUT, "entries": {}}
    for pid in ("7KP7", "3WD5", "4G3Y"):
        ch = chains(D / f"{pid}.pdb")
        tnf = {}
        for c, at in ch.items():
            ident, mp = tnf_map(at)
            if len(mp) > 100 and ident > 0.75:  # 7KP7 TNF is mouse (~79-81% identical to human)
                tnf[c] = mp
        partners = np.array([a[3] for c, at in ch.items() if c not in tnf for a in at])
        entry = {"tnf_chains": {}, "note": ""}
        for c, mp in tnf.items():
            res = {}
            for rn, ic, name, xyz in ch[c]:
                if rn in mp and (np.linalg.norm(partners - xyz, axis=1) < CUT).any():
                    res[mp[rn]] = AA3[name]
            entry["tnf_chains"][c] = {"contacts": {str(k): v for k, v in sorted(res.items())}}
            print(pid, "TNF chain", c, len(res), " ".join(f"{v}{k}" for k, v in sorted(res.items())))
        out["entries"][pid] = entry
    json.dump(out, open(D / "complex_epitopes.json", "w"), indent=1)


if __name__ == "__main__":
    main()
