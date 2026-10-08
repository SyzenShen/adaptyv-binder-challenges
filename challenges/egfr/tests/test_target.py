"""Phase 1 consistency tests for the target mapping pipeline.

Reads the tracked light artifacts in data/processed/ (CSV/JSON/FASTA).
Heavy raw inputs (6ARU.cif) are NOT required for these tests.
"""
import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"

CONSTRUCT_LEN = 621  # competition page: P00533-1 residues 25..645


def read_csv(name):
    with open(PROC / name, newline="") as fh:
        return list(csv.DictReader(fh))


class TestCompetitionConstruct(unittest.TestCase):
    def test_construct_length_and_page_match(self):
        fasta = (PROC / "human_construct_25_645.fasta").read_text().splitlines()
        seq = "".join(l for l in fasta if not l.startswith(">"))
        self.assertEqual(len(seq), CONSTRUCT_LEN)
        self.assertTrue(seq.startswith("LEEKKV"))
        self.assertTrue(seq.endswith("GPKIPS"))

    def test_page_verification_verdict(self):
        v = json.loads((PROC / "competition_construct_check.json").read_text())
        self.assertTrue(v["page_sequence_extracted"], "page sequence extraction failed")
        self.assertEqual(v["page_sequence_length"], CONSTRUCT_LEN)
        self.assertTrue(v["char_by_char_identical"], v["note"])


class TestResidueMap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = read_csv("residue_map.csv")

    def test_row_count_and_unique_numbering(self):
        self.assertEqual(len(self.rows), CONSTRUCT_LEN)
        upos = [int(r["uniprot_pos"]) for r in self.rows]
        self.assertEqual(upos, list(range(25, 646)))
        self.assertEqual(len(set(upos)), CONSTRUCT_LEN)

    def test_round_trip_construct_pos(self):
        for r in self.rows:
            self.assertEqual(int(r["construct_pos"]), int(r["uniprot_pos"]) - 24)

    def test_identity_column_consistent(self):
        for r in self.rows:
            if r["pdb_vs_uniprot"] == "identical":
                self.assertEqual(r["pdb_aa"], r["uniprot_aa"], r["uniprot_pos"])

    def test_conflicts_flagged(self):
        by_pos = {int(r["uniprot_pos"]): r for r in self.rows}
        self.assertIn("conflict", by_pos[540]["pdb_vs_uniprot"])
        self.assertIn("conflict", by_pos[634]["pdb_vs_uniprot"])

    def test_tail_not_in_construct(self):
        for r in self.rows:
            if int(r["uniprot_pos"]) >= 641:
                self.assertEqual(r["coord_status"], "not_in_construct")

    def test_glycan_sites_have_sequon(self):
        for r in self.rows:
            if r["glycan_observed_chain"]:
                self.assertEqual(r["n_glyc_sequon"], "yes")
                self.assertEqual(r["uniprot_aa"], "N")


class TestAlignment(unittest.TestCase):
    def test_alignment_covers_construct(self):
        rows = read_csv("human_mouse_alignment.csv")
        self.assertEqual(len(rows), CONSTRUCT_LEN)
        valid = {"identical", "conservative", "nonconservative", "gap"}
        self.assertTrue(all(r["class"] in valid for r in rows))
        meta = json.loads((PROC / "human_mouse_alignment.meta.json").read_text())
        self.assertIn("PROVISIONAL", meta["status"])


class TestEpitopeCandidates(unittest.TestCase):
    def test_hotspots_have_coordinates(self):
        res = {int(r["uniprot_pos"]): r for r in read_csv("residue_map.csv")}
        cands = read_csv("epitope_candidates.csv")
        self.assertGreaterEqual(len(cands), 1)
        for c in cands:
            lo, hi = int(c["uniprot_begin"]), int(c["uniprot_end"])
            self.assertGreaterEqual(hi - lo + 1, 10)
            self.assertEqual(c["domain"], "III")
            for p in (lo, hi):
                self.assertEqual(res[p]["coord_status"], "coordinates",
                                 f"hotspot endpoint {p} lacks coordinates")
            for p in range(lo, hi + 1):
                self.assertTrue(310 <= p <= 481, f"candidate residue {p} outside Domain III")


if __name__ == "__main__":
    unittest.main()
