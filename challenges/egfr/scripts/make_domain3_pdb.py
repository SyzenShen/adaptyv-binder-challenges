"""Build the BindCraft Domain III target crop from 6ARU chain A.

Stage 1 approved crop: UniProt P00533-1 residues 310-481 = auth seq 286-457
(auth = UniProt - 24 in 6ARU chain A, derived from struct_ref_seq; see
residue_map.csv). The output PDB keeps UniProt numbering (resseq 310..481)
on chain A so BindCraft/ColabDesign hotspot numbers are directly traceable
to the approved biological epitope envelope.

Protein atoms only (glycan chains D-H and HOH are not part of the design
target). Coordinates are unchanged. No residues are added, removed or
mutated.
"""
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from Bio.PDB import MMCIFParser, PDBIO, Select
from Bio.PDB.Atom import Atom
from Bio.PDB.Residue import Residue

ROOT = Path(__file__).resolve().parent.parent
CIF = ROOT / "data" / "raw" / "6ARU.cif"
RESMAP = ROOT / "data" / "processed" / "residue_map.csv"
OUT_PDB = ROOT / "data" / "processed" / "6ARU_chainA_domain3_310-481.pdb"
OUT_META = ROOT / "data" / "processed" / "domain3_pdb_manifest.json"

UNIPROT_LO, UNIPROT_HI = 310, 481
OFFSET = 24  # uniprot = auth_seq_id + 24 for 6ARU chain A (struct_ref_seq derived)


class _ProteinSelect(Select):
    def accept_residue(self, residue):
        return residue.id[0] == " "

    def accept_atom(self, atom):
        return atom.altloc in (" ", "A", "1")


def main():
    expected = {}
    with open(RESMAP, newline="") as fh:
        for r in csv.DictReader(fh):
            p = int(r["uniprot_pos"])
            if UNIPROT_LO <= p <= UNIPROT_HI:
                expected[p] = (r["uniprot_aa"], r["pdb_aa"], r["coord_status"])

    structure = MMCIFParser(QUIET=True).get_structure("6ARU", CIF)
    src = list(structure.get_models())[0]["A"]

    out = structure.__class__("EGFR_D3")
    model = list(structure.get_models())[0].__class__(0)
    out.add(model)
    chain = src.__class__("A")
    model.add(chain)

    seen = {}
    for auth in range(UNIPROT_LO - OFFSET, UNIPROT_HI - OFFSET + 1):
        res = src[(" ", auth, " ")]
        uni = auth + OFFSET
        new = Residue((" ", uni, " "), res.resname, res.segid)
        for at in res.get_unpacked_list():
            if at.altloc not in (" ", "A", "1"):
                continue
            element = at.element or at.name.strip("0123456789")[0]
            new.add(Atom(at.name, at.coord.copy(), at.bfactor, at.occupancy,
                         at.altloc, at.fullname, uni, element=element))
        chain.add(new)
        seen[uni] = res.resname

    aa3 = {
        "A": "ALA", "R": "ARG", "N": "ASN", "D": "ASP", "C": "CYS",
        "E": "GLU", "Q": "GLN", "G": "GLY", "H": "HIS", "I": "ILE",
        "L": "LEU", "K": "LYS", "M": "MET", "F": "PHE", "P": "PRO",
        "S": "SER", "T": "THR", "W": "TRP", "Y": "TYR", "V": "VAL",
    }
    problems = []
    for p in range(UNIPROT_LO, UNIPROT_HI + 1):
        if p not in seen:
            problems.append(f"missing residue {p}")
            continue
        if "CA" not in chain[(" ", p, " ")].child_dict:
            problems.append(f"no CA for {p}")
        uni_aa, pdb_aa, coord = expected.get(p, ("?", "?", "?"))
        if coord != "coordinates" or aa3.get(uni_aa) != seen[p]:
            problems.append(f"identity mismatch {p}: map={uni_aa}/{pdb_aa}/{coord} got={seen[p]}")
    if problems:
        raise SystemExit("crop validation failed:\n" + "\n".join(problems))

    io = PDBIO()
    io.set_structure(out)
    io.save(str(OUT_PDB), _ProteinSelect())

    meta = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "6ARU.cif chain A (Cetuximab Fab complex; target atoms only)",
        "source_uniprot": "P00533-1",
        "crop_uniprot_range": [UNIPROT_LO, UNIPROT_HI],
        "crop_auth_range_6ARU": [UNIPROT_LO - OFFSET, UNIPROT_HI - OFFSET],
        "n_residues": UNIPROT_HI - UNIPROT_LO + 1,
        "numbering_scheme": "resseq equals UniProt P00533-1 position; chain A",
        "numbering_basis": "6ARU chain A auth_seq_id + 24 = UniProt (struct_ref_seq derived; no insertions)",
        "contents": "protein atoms only; glycans D-H, waters, Fab chains B-C and His6 tag excluded",
        "coordinates_modified": False,
        "residues_added_or_mutated": False,
        "ssbond_records_written": False,
        "ssbond_note": "Disulfides are encoded geometrically (unmodified SG coordinates): "
                       "C311-C326, C329-C333, C337-C362 fully inside crop; C470 inside with "
                       "partner C499 outside crop (broken edge bond, distant from B envelope).",
        "cysteines_uniprot_in_crop": [311, 326, 329, 333, 337, 362, 470],
        "approved_envelope_B": [[390, 403], [421, 431]],
    }
    OUT_META.write_text(json.dumps(meta, indent=2) + "\n")
    print(f"wrote {OUT_PDB}")
    print(f"wrote {OUT_META}")


if __name__ == "__main__":
    main()
