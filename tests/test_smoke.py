"""Phase 0 smoke tests - runnable with system Python 3, zero third-party deps.

Run from repository root:
    python3 -m unittest discover -s tests -v

All inline strings below are synthetic_fixture test constants. They are NOT
candidate designs and must never be copied into results/ or submission/.
"""
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import seqvalidate  # noqa: E402

# --- synthetic_fixture: format-check constants only, no biological claim ---
SYN_OK_MINIBINDER = "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQANTPTKELYRKKQ"  # 49 aa, canonical
SYN_BAD = "MKTAYIBXQ"  # contains B and X (non-canonical for this project)
SYN_SHORT = "MK"

REQUIRED_FILES = [
    "README.md",
    "MASTER_PROMPT.md",
    "STATE.md",
    "DECISIONS.md",
    "ASK_SUPERVISOR.md",
    "HUMAN_ACTIONS.md",
    "RUNBOOK.md",
    "configs/competition.json",
    "configs/budget.yaml",
    ".gitignore",
    ".trae/rules/egfr-project.md",
    "scripts/seqvalidate.py",
]

REQUIRED_DIRS = [
    "configs", "scripts", "notebooks",
    "data/raw", "data/processed", "data/inbox",
    "results", "reports", "submission", "tests",
]


class EnvironmentTests(unittest.TestCase):
    def test_python_version(self):
        self.assertGreaterEqual(sys.version_info[:2], (3, 10))


class ProjectScaffoldTests(unittest.TestCase):
    def test_required_dirs_exist(self):
        missing = [d for d in REQUIRED_DIRS if not os.path.isdir(os.path.join(ROOT, d))]
        self.assertEqual(missing, [])

    def test_required_files_exist(self):
        missing = [f for f in REQUIRED_FILES if not os.path.isfile(os.path.join(ROOT, f))]
        self.assertEqual(missing, [])


class CompetitionConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, "configs", "competition.json"), encoding="utf-8") as fh:
            cls.cfg = json.load(fh)

    def test_track3_limits(self):
        self.assertEqual(self.cfg["track"], 3)
        self.assertEqual(self.cfg["submission"]["max_designs_track2_3"], 20)

    def test_length_and_class_schema(self):
        sub = self.cfg["submission"]
        self.assertEqual(sub["single_chain_length_min"], 10)
        self.assertEqual(sub["single_chain_length_max"], 250)
        self.assertEqual(sub["minibinder_category_inclusive"], [40, 100])
        self.assertEqual(
            sub["molecule_class_allowed"],
            ["protein", "nanobody", "scfv", "fab_kappa", "fab_lambda"],
        )
        self.assertEqual(sub["csv_required_columns"], ["name", "sequence", "molecule_class"])

    def test_human_target(self):
        h = self.cfg["targets"]["human"]
        self.assertEqual(h["uniprot_isoform"], "P00533-1")
        self.assertEqual(h["ecd_residues_uniprot"], [25, 645])
        self.assertEqual(h["ecd_length_aa"], 621)
        self.assertIn("6ARU", h["structure_reference"])

    def test_mouse_construct_marked_unknown_not_guessed(self):
        m = self.cfg["targets"]["mouse"]
        self.assertIsNone(m["uniprot_isoform"])
        self.assertIn("blocker", m)


class SeqValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, "configs", "competition.json"), encoding="utf-8") as fh:
            cls.cfg = json.load(fh)

    def test_valid_minibinder_passes(self):
        errs = seqvalidate.validate_row("syn_test_1", SYN_OK_MINIBINDER, "protein", self.cfg)
        self.assertEqual(errs, [])

    def test_illegal_characters_rejected(self):
        errs = seqvalidate.validate_row("syn_test_2", SYN_BAD, "protein", self.cfg)
        self.assertTrue(any(e.startswith("illegal_characters") for e in errs))

    def test_too_short_rejected(self):
        errs = seqvalidate.validate_row("syn_test_3", SYN_SHORT, "protein", self.cfg)
        self.assertTrue(any(e.startswith("length_out_of_range") for e in errs))

    def test_bad_class_rejected(self):
        errs = seqvalidate.validate_row("syn_test_4", SYN_OK_MINIBINDER, "peptide", self.cfg)
        self.assertIn("bad_molecule_class", errs)

    def test_uniqueness_check(self):
        dup_names, dup_seqs = seqvalidate.check_uniqueness([
            ("a", SYN_OK_MINIBINDER),
            ("a", "MKTA"),
            ("b", "MKTA"),
        ])
        self.assertEqual(dup_names, ["a"])
        self.assertEqual(dup_seqs, ["MKTA"])


if __name__ == "__main__":
    unittest.main()
