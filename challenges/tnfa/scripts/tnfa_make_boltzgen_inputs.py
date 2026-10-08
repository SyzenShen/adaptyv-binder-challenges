"""P5: build BoltzGen inputs for the TNF-alpha receptor site (E3) from data/receptor_site.json.

Target = two protomers only (1TNF chains B = main, A = other; 314 tokens) to keep GPU memory and time low. The third
protomer is checked afterwards on CPU (tnfa_trimer_clash.py), not designed against.
BoltzGen residue indices are 1-based positions among the resolved residues of a chain, NOT mature TNF numbers
(1TNF has 152 of 157 residues resolved per chain), so numbers are mapped through the chain's residue order.
Outputs: boltz/target_AB.pdb and boltz/tnfa_e3_core.yaml, tnfa_e3_wide.yaml, plus a mapping table printed for the log.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
D, OUT = HERE / "data", HERE / "boltz"
AA3 = {"ALA":"A","ARG":"R","ASN":"N","ASP":"D","CYS":"C","GLN":"Q","GLU":"E","GLY":"G","HIS":"H","ILE":"I","LEU":"L",
       "LYS":"K","MET":"M","PHE":"F","PRO":"P","SER":"S","THR":"T","TRP":"W","TYR":"Y","VAL":"V"}
# core subset: densest receptor/antibody contacts on both protomers (main chain B, other chain A)
CORE = {"main": [21, 32, 67, 113, 115, 144, 146, 147], "other": [75, 87, 91, 92]}
# 1TNF carries Leu at 143 where wild-type P01375 (the assay construct) has Asp. D143 is a receptor and adalimumab contact,
# so it is never used as a hotspot and designs must be re-checked against the wild-type sequence.
KNOWN_VARIANT = {143: ("L", "D")}


def main():
    site = json.load(open(D / "receptor_site.json"))
    main_c, other_c = site["map"]["main"], site["map"]["other"]
    lines = [l for l in (D / "1TNF_ABC_protein.pdb").read_text().splitlines() if l.startswith("ATOM") and l[21] in (main_c, other_c)]
    order = {}
    for l in lines:
        c, rn = l[21], int(l[22:26])
        order.setdefault(c, [])
        if rn not in order[c]:
            order[c].append(rn)
    seq = {c: {} for c in order}
    for l in lines:
        seq[l[21]][int(l[22:26])] = AA3[l[17:20]]
    OUT.mkdir(exist_ok=True)
    (OUT / "target_AB.pdb").write_text("\n".join(l for l in sorted(lines, key=lambda x: (x[21], int(x[22:26])))) + "\nEND\n")

    def pos(c, mature):
        return order[c].index(mature) + 1  # mature number == PDB residue number in 1TNF

    def spec(role_chain, nums):
        keep = [n for n in nums if n in order[role_chain]]
        miss = [n for n in nums if n not in order[role_chain]]
        assert not miss, f"unresolved in 1TNF chain {role_chain}: {miss}"
        return ",".join(str(pos(role_chain, n)) for n in keep)

    exp = {r["res"]: r["human"] for r in json.load(open(D / "conservation_interface.json"))}
    for role, c in (("main", main_c), ("other", other_c)):  # self-check amino acids
        for n in CORE[role]:
            assert n not in KNOWN_VARIANT
            assert seq[c][n] == exp[n], (c, n, seq[c][n], exp[n])
        diff = {n: (a, exp[n]) for n, a in seq[c].items() if a != exp[n]}
        assert diff == {n: (v[0], v[1]) for n, v in KNOWN_VARIANT.items()}, f"unexpected target/UniProt differences {diff}"
    wide = {"main": [int(k) for k in {r["res"] for r in site["residues"][f"main_chain_{main_c}"]}],
            "other": [int(k) for k in {r["res"] for r in site["residues"][f"other_chain_{other_c}"]}]}
    wide = {k: [n for n in sorted(v) if n not in KNOWN_VARIANT and n in order[main_c if k == "main" else other_c]]
            for k, v in wide.items()}
    for name, sel in (("tnfa_e3_core", CORE), ("tnfa_e3_wide", wide)):
        y = f"""entities:
  - protein:
      id: X
      sequence: 70..130
  - file:
      path: target_AB.pdb
      include:
        - chain:
            id: {main_c}
        - chain:
            id: {other_c}
      binding_types:
        - chain:
            id: {main_c}
            binding: {spec(main_c, sel["main"])}
        - chain:
            id: {other_c}
            binding: {spec(other_c, sel["other"])}
"""
        (OUT / f"{name}.yaml").write_text(y)
        print(name, "main", sel["main"], "other", sel["other"])
    print("chain B resolved residues:", len(order[main_c]), "chain A:", len(order[other_c]))
    print("mapping main (mature->position):", {n: pos(main_c, n) for n in CORE["main"]})
    print("mapping other:", {n: pos(other_c, n) for n in CORE["other"]})


if __name__ == "__main__":
    main()
