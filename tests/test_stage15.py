"""Stage 1.5 checkpoint tests: ECD alignment, glycan and geometry audits.

Light tracked artifacts only (CSV/JSON under data/processed and results);
6ARU.cif itself is not required at test time.
"""
import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
RES = ROOT / "results"


def read_csv(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


class TestECDAlignment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = read_csv(PROC / "human_mouse_ecd_alignment.csv")
        cls.meta = json.loads((PROC / "human_mouse_ecd_alignment.meta.json").read_text())
        cls.byh = {int(r["human_uniprot_pos"]): r
                   for r in cls.rows if r["human_uniprot_pos"]}

    def test_construct_lengths_and_columns(self):
        self.assertEqual(self.meta["human"]["length"], 621)
        self.assertEqual(self.meta["mouse"]["length"], 623)
        self.assertEqual(len(self.rows), 623)
        self.assertEqual(self.meta["class_counts"]["mouse_only"], 2)

    def test_mouse_only_insertion_near_Cterm(self):
        mo = [r for r in self.rows if r["class"] == "mouse_only"]
        self.assertEqual([r["mouse_uniprot_pos"] for r in mo], ["639", "640"])
        self.assertEqual("".join(r["mouse_aa"] for r in mo), "WP")

    def test_no_constant_offset_assumed_key_sites(self):
        # mapping comes from the alignment; identity at the three pH His
        for p in (370, 418, 433):
            self.assertEqual(self.byh[p]["mouse_aa"], "H")
            self.assertEqual(int(self.byh[p]["mouse_uniprot_pos"]), p)
            self.assertEqual(self.byh[p]["class"], "identical")

    def test_mouse_lacks_N361_sequon(self):
        self.assertEqual(self.byh[361]["mouse_aa"], "Y")
        self.assertEqual(self.byh[361]["class"], "nonconservative")
        for p in (352, 413, 444):
            self.assertEqual(self.byh[p]["mouse_aa"], "N")

    def test_patch_conservation(self):
        def counts(lo, hi):
            c = {}
            for p in range(lo, hi + 1):
                c[self.byh[p]["class"]] = c.get(self.byh[p]["class"], 0) + 1
            return c
        self.assertEqual(counts(316, 343), {"identical": 25, "conservative": 3})
        self.assertEqual(counts(385, 403), {"identical": 17, "conservative": 2})
        self.assertEqual(counts(416, 431), {"identical": 16})
        self.assertEqual(counts(447, 460), {"identical": 14})


class TestGeometryAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.geo = {int(r["uniprot_pos"]): r
                   for r in read_csv(PROC / "domain3_geometry.csv")}
        cls.audit = json.loads((PROC / "geometry_audit.json").read_text())
        cls.gly = read_csv(RES / "epitope_glycan_distances.csv")

    def test_domain3_coverage(self):
        self.assertEqual(len(self.geo), 172)
        self.assertEqual(min(self.geo), 310)
        self.assertEqual(max(self.geo), 481)

    def test_sasa_sane(self):
        for r in self.geo.values():
            sasa = float(r["sasa_A_only"])
            self.assertGreaterEqual(sasa, 0.0)
            self.assertLess(sasa, 300.0)
            self.assertTrue(0.0 <= float(r["rel_sasa"]) <= 1.0)

    def test_patch_fab_distances(self):
        pf = self.audit["patch_fab_distances"]
        self.assertAlmostEqual(pf["EPI_H_2"]["min"], 12.77, places=1)
        self.assertAlmostEqual(pf["EPI_H_3"]["min"], 9.11, places=1)
        self.assertEqual(pf["EPI_H_3"]["residues_within_5A"], [])

    def test_histidine_exposure(self):
        self.assertLess(float(self.geo[418]["rel_sasa"]), 0.05)   # buried
        self.assertGreater(float(self.geo[433]["rel_sasa"]), 0.5)  # exposed
        self.assertLess(float(self.geo[370]["rel_sasa"]), 0.3)

    def test_cetuximab_numbering_audit(self):
        rows = self.audit["cetuximab_lit_residues_audit"]
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(r["aa_matches"] for r in rows))
        by_up = {r["uniprot_pos"]: r for r in rows}
        self.assertLess(by_up[433]["dist_fab_min_heavy_A"], 4.0)
        self.assertGreater(by_up[411]["dist_fab_min_heavy_A"], 10.0)

    def test_glycan_distance_matrix(self):
        # 77 patch residues x 4 sites
        self.assertEqual(len(self.gly), (28 + 19 + 16 + 14) * 4)
        k335_n361 = [r for r in self.gly
                     if r["epitope"] == "EPI_H_1"
                     and int(r["epitope_residue_uniprot"]) == 335
                     and r["glycan_site"] == "N361"][0]
        self.assertLess(float(k335_n361["dist_to_observed_glycan_heavy_A"]), 5.0)
        self.assertEqual(k335_n361["site_mouse_Q01279"], "Y")
        self.assertEqual(k335_n361["site_mouse_CARBOHYD_annotation"], "no_sequon")

    def test_patch_glycan_occlusion(self):
        # EPI_H_2/3/4: no residue SASA occluded by deposited glycans.
        for lo, hi in ((385, 403), (416, 431), (447, 460)):
            for p in range(lo, hi + 1):
                self.assertEqual(float(self.geo[p]["sasa_occluded_by_glycan"]), 0.0)
        # EPI_H_1: exactly K335 is partially occluded (11.3 A2, N361 glycan)
        occ = {p: float(self.geo[p]["sasa_occluded_by_glycan"])
               for p in range(316, 344)
               if float(self.geo[p]["sasa_occluded_by_glycan"]) > 0}
        self.assertEqual(occ, {335: 11.3})

    def test_continuity_one_face(self):
        c = self.audit["patch_continuity"]["EPI_H_2_vs_EPI_H_3"]
        self.assertLess(c["inter_patch_min_heavy_A"], 3.0)
        self.assertGreater(len(c["cross_patch_pairs_lt_5A"]), 20)
        self.assertGreater(c["combined_exposed_SASA_A2"], 1000.0)

    def test_glycan_evidence_sources(self):
        ev = self.audit["glycan_evidence"]
        for p in (352, 361, 413, 444):
            self.assertIn(p, ev["human_uniprot_CARBOHYD_sites"])
            self.assertIn(str(p), ev["structurally_glycosylated_in_6ARU"])
        self.assertNotIn(361, ev["mouse_uniprot_CARBOHYD_sites"])


if __name__ == "__main__":
    unittest.main()
