# Level 0 diagnosis: `challenges/tnfa/scripts/tnfa_trimer_clash.py`

Read the code below without running it. In the table at the end, list the line numbers for each mark and write the exact question you have about each. "I do not understand deep learning" is not a question; "what shape does line 49 return?" is.

Marks: **U** understood (could explain it to someone), **R** roughly (know what it is for, not how or why), **N** no idea.

```python
  1  """P5: CPU check that a designed binder (made against protomers B+A) does not collide with the third protomer.
  2  
  3  Usage: python3 -I scripts/tnfa_trimer_clash.py complex.pdb --target-chains B A --binder-chain X
  4  The target chains of the design complex are superposed (CA Kabsch, matched by residue order) onto 1TNF chains B and A, the
  5  same transform is applied to the binder, and binder heavy atoms closer than 2.5 A to 1TNF chain C are counted.
  6  Also reports the distance of the binder's last 5 residues to the target (the C-terminus carries the Twin-Strep tag in the assay and must stay free) and binder atoms within 4 A of residue 143 (1TNF has Leu where wild type has Asp).
  7  """
  8  import argparse
  9  import sys
 10  from pathlib import Path
 11  
 12  import numpy as np
 13  
 14  D = Path(__file__).resolve().parents[1] / "data"
 15  
 16  
 17  def read(path, chains=None):
 18      out = {}
 19      for ln in open(path):
 20          if ln.startswith(("ATOM", "HETATM")) and ln[76:78].strip() != "H":
 21              c = ln[21]
 22              if chains is None or c in chains:
 23                  out.setdefault(c, []).append((int(ln[22:26]), ln[12:16].strip(), np.array([float(ln[30:38]), float(ln[38:46]), float(ln[46:54])])))
 24      return out
 25  
 26  
 27  def kabsch(P, Q):
 28      pc, qc = P.mean(0), Q.mean(0)
 29      U, S, Vt = np.linalg.svd((P - pc).T @ (Q - qc))
 30      d = np.sign(np.linalg.det(U @ Vt))
 31      R = U @ np.diag([1, 1, d]) @ Vt
 32      return R, pc, qc
 33  
 34  
 35  def trimer_clash(complex_pdb, target_chains, binder_chain, ref_pdb=None, cutoff=2.5):
 36      ref = read(ref_pdb or D / "1TNF_ABC_protein.pdb")
 37      cx = read(complex_pdb)
 38      P, Q = [], []
 39      for tc, rc in zip(target_chains, ("B", "A")):
 40          ca_x = [a[2] for a in cx[tc] if a[1] == "CA"]
 41          ca_r = [a[2] for a in ref[rc] if a[1] == "CA"]
 42          n = min(len(ca_x), len(ca_r))
 43          P += ca_x[:n]; Q += ca_r[:n]
 44      R, pc, qc = kabsch(np.array(P), np.array(Q))
 45      binder = (np.array([a[2] for a in cx[binder_chain]]) - pc) @ R + qc
 46      third = np.array([a[2] for a in ref["C"]])
 47      dmin = np.linalg.norm(binder[:, None, :] - third[None, :, :], axis=2)
 48      l143 = np.array([a[2] for a in ref["B"] + ref["A"] if a[0] == 143])
 49      d143 = np.linalg.norm(binder[:, None, :] - l143[None, :, :], axis=2).min() if len(l143) else float("nan")
 50      cterm = np.array([a[2] for a in cx[binder_chain] if a[0] >= max(x[0] for x in cx[binder_chain]) - 4])
 51      tgt = np.array([a[2] for c in target_chains for a in cx[c]])
 52      d_cterm = float(np.linalg.norm(cterm[:, None, :] - tgt[None, :, :], axis=2).min())
 53      return {"cterm_min_dist_to_target": d_cterm, "clash_atoms_with_chain_C": int((dmin < cutoff).sum()), "min_dist_to_C": float(dmin.min()),
 54              "min_dist_to_res143": float(d143)}
 55  
 56  
 57  def main(argv=None):
 58      ap = argparse.ArgumentParser()
 59      ap.add_argument("complex_pdb"); ap.add_argument("--target-chains", nargs=2, default=["B", "A"]); ap.add_argument("--binder-chain", default="X")
 60      a = ap.parse_args(argv)
 61      print(trimer_clash(a.complex_pdb, a.target_chains, a.binder_chain))
 62  
 63  
 64  if __name__ == "__main__":
 65      main()
```

## My marks

| Mark | Line numbers | My exact questions |
|---|---|---|
| U | | |
| R | | |
| N | | |
