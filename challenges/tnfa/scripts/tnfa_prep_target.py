"""P2: prepare the TNF-alpha trimer target from 1TNF and map the protomer interfaces.

Inputs : data/1TNF.pdb, P01375.fasta, P06804_mouse.fasta
Outputs: data/1TNF_ABC_protein.pdb (protein ATOM only, chains A-C)
         data/interface_residues.json
Interface = residue with any heavy atom within 5 A of a different chain (by chain pair).
"""
import json
from pathlib import Path

import numpy as np

D = Path(__file__).resolve().parents[1] / "data"
CUT = 5.0
AA3 = {"ALA":"A","ARG":"R","ASN":"N","ASP":"D","CYS":"C","GLN":"Q","GLU":"E","GLY":"G","HIS":"H","ILE":"I",
       "LEU":"L","LYS":"K","MET":"M","PHE":"F","PRO":"P","SER":"S","THR":"T","TRP":"W","TYR":"Y","VAL":"V"}


def read_pdb(path):
    atoms, lines = [], []
    for ln in Path(path).read_text().splitlines():
        if ln.startswith("ATOM") and ln[21] in "ABC" and ln[17:20] in AA3 and ln[76:78].strip() != "H":
            atoms.append((ln[21], int(ln[22:26]), ln[17:20], np.array([float(ln[30:38]), float(ln[38:46]), float(ln[46:54])])))
            lines.append(ln)
    return atoms, lines


def main():
    atoms, lines = read_pdb(D / "1TNF.pdb")
    (D / "1TNF_ABC_protein.pdb").write_text("\n".join(lines) + "\nEND\n")
    chains = {c: [a for a in atoms if a[0] == c] for c in "ABC"}
    res = {}  # (chain, resnum) -> {"aa", "partners"}
    for a in "ABC":
        for b in "ABC":
            if a == b:
                continue
            xb = np.array([x[3] for x in chains[b]])
            for ch, rn, rname, xyz in chains[a]:
                if (np.linalg.norm(xb - xyz, axis=1) < CUT).any():
                    r = res.setdefault((ch, rn), {"aa": AA3[rname], "partners": set()})
                    r["partners"].add(b)
    out = {"cutoff_A": CUT, "numbering": "1TNF residue number = mature TNF numbering (1 = V77 of P01375)",
           "chains": {}}
    for c in "ABC":
        rows = sorted((rn, v["aa"], "".join(sorted(v["partners"]))) for (ch, rn), v in res.items() if ch == c)
        out["chains"][c] = [{"res": rn, "aa": aa, "contacts": p} for rn, aa, p in rows]
        print(c, len(rows), "interface residues")
    (D / "interface_residues.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
