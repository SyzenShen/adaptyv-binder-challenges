"""Stage 2 tests: Domain III crop PDB, BindCraft config translation,
hotspot-envelope containment, smoke notebook validity, run analyzer.

Stdlib only (no third-party dependency at test time).
"""
import ast
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
CFG = ROOT / "configs" / "bindcraft"
CLOUD = ROOT / "cloud"
SCRIPTS = ROOT / "scripts"

ENVELOPE = list(range(390, 404)) + list(range(421, 432))
EXPOSED_12 = [390, 391, 393, 396, 399, 421, 422, 424, 427, 429, 430, 431]
AA3 = {"Q": "GLN", "E": "GLU", "D": "ASP", "K": "LYS",
       "R": "ARG", "N": "ASN", "T": "THR"}


def parse_ca(path):
    out = {}
    with open(path) as fh:
        for line in fh:
            if line.startswith("ATOM") and line[12:16].strip() == "CA":
                out[int(line[22:26])] = (line[21:22].strip(),
                                         line[17:20].strip())
    return out


def parse_hotspots(spec):
    pos = []
    for token in spec.split(","):
        token = token.strip()
        if token and token[0].isalpha():
            token = token[1:]
        if "-" in token:
            lo, hi = token.split("-")
            pos.extend(range(int(lo), int(hi) + 1))
        else:
            pos.append(int(token))
    return pos


class TestDomain3CropPDB(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ca = parse_ca(PROC / "6ARU_chainA_domain3_310-481.pdb")
        cls.meta = json.loads((PROC / "domain3_pdb_manifest.json").read_text())

    def test_coverage_and_numbering(self):
        self.assertEqual(sorted(self.ca), list(range(310, 482)))
        self.assertEqual(len(self.ca), 172)
        self.assertTrue(all(ch == "A" for ch, _ in self.ca.values()))

    def test_hotspot_identities(self):
        for p, one in {390: "Q", 393: "D", 399: "K", 421: "E",
                       424: "E", 431: "K"}.items():
            self.assertEqual(self.ca[p][1], AA3[one], p)

    def test_manifest(self):
        self.assertEqual(self.meta["crop_uniprot_range"], [310, 481])
        self.assertEqual(self.meta["crop_auth_range_6ARU"], [286, 457])
        self.assertFalse(self.meta["coordinates_modified"])
        self.assertFalse(self.meta["residues_added_or_mutated"])
        self.assertEqual(self.meta["cysteines_uniprot_in_crop"],
                         [311, 326, 329, 333, 337, 362, 470])


class TestBindCraftConfigs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cons = json.loads((CFG / "egfr_d3_B_conservative.json").read_text())
        cls.broad = json.loads((CFG / "egfr_d3_B_broad.json").read_text())
        cls.pdl1 = json.loads((CFG / "pdl1_official_smoke.json").read_text())
        cls.adv3 = json.loads((CFG / "advanced_smoke_max3.json").read_text())
        cls.adv1 = json.loads((CFG / "advanced_smoke_max1.json").read_text())

    def test_conservative_set(self):
        self.assertEqual(parse_hotspots(self.cons["target_hotspot_residues"]),
                         [390, 393, 399, 421, 424, 431])
        self.assertEqual(self.cons["chains"], "A")
        self.assertEqual(self.cons["lengths"], [80, 80])
        self.assertEqual(self.cons["number_of_final_designs"], 1)
        self.assertTrue(self.cons["starting_pdb"].endswith(
            "6ARU_chainA_domain3_310-481.pdb"))

    def test_broad_set_equals_12_verified_exposed(self):
        self.assertEqual(parse_hotspots(self.broad["target_hotspot_residues"]),
                         EXPOSED_12)

    def test_every_hotspot_inside_approved_envelope(self):
        for cfg in (self.cons, self.broad):
            for r in parse_hotspots(cfg["target_hotspot_residues"]):
                self.assertIn(r, ENVELOPE)

    def test_pdl1_official_minimal(self):
        self.assertEqual(self.pdl1["target_hotspot_residues"], "56")
        self.assertEqual(self.pdl1["lengths"], [65, 65])

    def test_advanced_is_default_protocol_not_hardtarget(self):
        for adv, cap in ((self.adv1, 1), (self.adv3, 3)):
            self.assertEqual(adv["design_algorithm"], "4stage")
            self.assertTrue(adv["use_multimer_design"])
            self.assertFalse(adv["predict_initial_guess"])
            self.assertFalse(adv["rm_template_sc_design"])
            self.assertEqual(adv["omit_AAs"], "C")
            self.assertEqual(adv["max_trajectories"], cap)
        d1 = {k: v for k, v in self.adv1.items()}
        d3 = {k: v for k, v in self.adv3.items()}
        d1.pop("max_trajectories"); d3.pop("max_trajectories")
        self.assertEqual(d1, d3)  # max1/max3 differ only by cap


class TestTranslationReport(unittest.TestCase):
    def test_required_sections_and_claims(self):
        txt = (ROOT / "reports" / "bindcraft_hotspot_translation.md").read_text()
        for needle in ("生物表位包络", "实际暴露残基", "实际 BindCraft hotspot",
                       "resseq 重写为 UniProt 位置 310–481",
                       "考虑过但排除",
                       "没有 F/W/Y/M",
                       "7713aa0d0d351e4117a8befeb8541f3a8ebd3368",
                       "390,393,399,421,424,431"):
            self.assertIn(needle, txt)


class TestSmokeNotebook(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nb = json.loads((CLOUD / "stage2_bindcraft_smoke.ipynb").read_text())

    def test_valid_and_pinned(self):
        self.assertEqual(self.nb["nbformat"], 4)
        text = "\n".join("".join(c["source"]) for c in self.nb["cells"])
        self.assertIn("7713aa0d0d351e4117a8befeb8541f3a8ebd3368", text)
        # official default filters/advanced used; no hard-target settings file
        self.assertIn("default_filters.json", text)
        self.assertIn("default_4stage_multimer.json", text)
        self.assertNotIn("hardtarget.json", text.lower())
        self.assertNotIn("_hardtarget", text.lower())
        self.assertIn("390,393,399,421,424,431", text)

    def test_code_cells_compile(self):
        for i, cell in enumerate(self.nb["cells"]):
            if cell["cell_type"] == "code":
                ast.parse("".join(cell["source"]), filename=f"cell{i}")


class TestAnalyzerOnSyntheticTemp(unittest.TestCase):
    def test_geometry_flags(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "Trajectory" / "Relaxed"
            d.mkdir(parents=True)

            def line(n, name, resn, chain, res, x, y, z, elem):
                return (f"ATOM  {n:5d} {name:<4s} {resn:>3s} {chain}{res:4d}    "
                        f"{x:8.3f}{y:8.3f}{z:8.3f}  1.00  0.00           {elem:>2s}\n")

            atoms, n = [], 0
            for res, resn, x in [(390, "GLY", 0.0), (393, "ALA", 3.0),
                                 (450, "ALA", 30.0)]:
                for name, elem, dx in [("N", "N", 0), ("CA", "C", 1.4),
                                       ("C", "C", 2.8)]:
                    n += 1
                    atoms.append(line(n, name, resn, "A", res, x + dx, 0, 0, elem))
            for res, resn, x in [(1, "ALA", 0.7), (2, "ALA", 3.0)]:
                for name, elem, dx, dy in [("N", "N", -1.4, 0), ("CA", "C", 0, 0),
                                           ("CB", "C", 0, 1.5), ("C", "C", 1.4, 0)]:
                    n += 1
                    atoms.append(line(n, name, resn, "B", res, x + dx, dy, 0, elem))
            (d / "EGFR_D3_Bcons_l80_s42.pdb").write_text("".join(atoms) + "END\n")

            out = Path(td) / "out.json"
            subprocess.run([sys.executable,
                            str(SCRIPTS / "analyze_bindcraft_run.py"),
                            "--run-dir", td, "--out", out], check=True)
            r = json.loads(out.read_text())["trajectories"][0]
            self.assertEqual(r["seed"], 42)
            self.assertEqual(r["binder_length"], 80)
            self.assertEqual(r["B_res_contacted"], [390, 393])
            self.assertFalse(r["migrated_off_B"])


if __name__ == "__main__":
    unittest.main()
