"""Stage 2 tests: Domain III crop PDB, BindCraft config translation,
hotspot-envelope containment, smoke notebook validity, isolated-environment
fix for failure 001 (Colab JAX 0.11.1 / xla_bridge removal), pre-flight gate,
run analyzer.

Stdlib only (no third-party dependency at test time).
"""
import ast
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
CFG = ROOT / "configs" / "bindcraft"
CLOUD = ROOT / "cloud"
SCRIPTS = ROOT / "scripts"
PATCHES = ROOT / "patches"
PRISTINE = (ROOT / "tests" / "fixtures" / "bindcraft_7713aa0_pristine")

sys.path.insert(0, str(SCRIPTS))
import stage2_paths as sp
import stage2_checkpoint as ckpt
import stage2_configure as configure
import stage2_run_job as runner
import stage2_orchestrate as orchestrate
import stage2_relax_failures as srf
import apply_bindcraft_patch as abp
import ensure_af2_weights as eaw

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


class TestThinNotebook(unittest.TestCase):
    """Consolidation Checkpoint C: the notebook is a thin A-H front end.
    All executable science/orchestration lives in pinned scripts."""

    @classmethod
    def setUpClass(cls):
        cls.nb = json.loads((CLOUD / "stage2_bindcraft_smoke.ipynb").read_text())
        cls.code = ["".join(c["source"]) for c in cls.nb["cells"]
                    if c["cell_type"] == "code"]
        cls.text = "\n".join(cls.code)

    def indices(self, needle):
        return [i for i, s in enumerate(self.code) if needle in s]

    def test_structure_and_compile(self):
        self.assertEqual(self.nb["nbformat"], 4)
        self.assertEqual(len(self.code), 8)           # exactly A..H
        for i, s in enumerate(self.code):
            ast.parse(s, filename=f"cell-{chr(65+i)}")

    def test_cells_A_to_H_in_order(self):
        idx = [self.indices(f"Cell {x}") for x in "ABCDEFGH"]
        missing = [x for x, j in zip("ABCDEFGH", idx) if not j]
        self.assertFalse(missing, missing)
        first = [j[0] for j in idx]
        self.assertEqual(first, sorted(first))

    def test_frozen_pins_present(self):
        for needle in ("7713aa0d0d351e4117a8befeb8541f3a8ebd3368",
                       "e31a56fe1d9b4de25c8697f3a28b75892941cc72",
                       "452ac95c810614ad5c7602ef652644a4c63382c6"):
            self.assertIn(needle, self.text)
        self.assertNotIn("hardtarget", self.text.lower())

    def test_gpu_gate_first_controlled_no_cpu(self):
        gate = self.indices("GPU_UNAVAILABLE")[0]
        self.assertEqual(gate, 0)
        self.assertIn("COMPUTE_QUOTA_BLOCKED", self.code[gate])
        self.assertIn("raise SystemExit(2)", self.code[gate])
        self.assertIn("Do NOT continue on CPU", self.code[gate])
        self.assertLess(gate, self.indices("drive.mount")[0])

    def test_drive_before_project_before_env(self):
        mount = self.indices("drive.mount")[0]
        project = self.indices("PROJECT_PIN")[0]
        env = self.indices("Miniforge3-Linux-x86_64.sh")[0]
        self.assertLess(mount, project)
        self.assertLess(project, env)

    def test_private_project_pinned_and_token_never_printed(self):
        self.assertIn("SyzenShen/egfr-binder-challenge.git", self.text)
        self.assertIn("userdata.get('GITHUB_TOKEN')", self.text)
        self.assertIn("http.extraheader=AUTHORIZATION: bearer {token}",
                      self.text)
        self.assertNotIn("x-access-token", self.text)
        self.assertNotIn("print(token", self.text)
        self.assertIn("project_commit == PROJECT_PIN", self.text)
        self.assertIn("files.upload()", self.text)
        self.assertIn("missing project artifacts", self.text)
        self.assertIn("6ARU_chainA_domain3_310-481.pdb", self.text)

    def test_upstream_env_spec_present(self):
        for needle in ("Miniforge3-Linux-x86_64.sh", "python=3.10",
                       "jax=0.6.0", "jaxlib=0.6.0=*cuda*",
                       "CONDA_OVERRIDE_CUDA", "'12.6'", "numpy<2.0.0",
                       "flax<0.10.0", "-c", "conda-forge", "nvidia"):
            self.assertIn(needle, self.text, needle)

    def test_colabdesign_pinned_and_no_deps_inside_env(self):
        self.assertIn("e31a56fe1d9b4de25c8697f3a28b75892941cc72", self.text)
        self.assertRegex(
            self.text,
            r"bin/pip', 'install', '--no-deps',\s*"
            r"f?'git\+https://github\.com/sokrypton/ColabDesign\.git@")
        self.assertNotIn(
            "pip install -q git+https://github.com/sokrypton/ColabDesign.git",
            self.text)

    def test_kernel_never_imports_jax_or_colabdesign(self):
        for i, src in enumerate(self.code):
            self.assertIsNone(
                re.search(r"^\s*(?:import|from)\s+(jax|colabdesign)\b",
                          src, re.M),
                f"system-kernel jax/colabdesign import in cell {i}")

    def test_isolated_python_and_orchestrator_launch(self):
        self.assertIn("BINDPY = f'{ENV_PREFIX}/bin/python'", self.text)
        self.assertIn("scripts/stage2_orchestrate.py", self.text)
        self.assertIn("'--root', PERSISTENT_ROOT", self.text)
        self.assertNotIn("'bindcraft.py'", self.text)

    def test_preflight_weights_orchestrator_order_and_exit_codes(self):
        pf = self.indices("stage2_preflight.py', '--out'")[0]
        wf = self.indices("'--params-dir'")[0]
        go = self.indices("'--repo-dir', REPO_DIR")[0]
        self.assertLess(pf, wf)
        self.assertLess(wf, go)
        run_cell = self.code[go]
        self.assertIn("g.returncode == 2", run_cell)
        self.assertIn("COMPUTE_BLOCKED", run_cell)
        self.assertIn("SystemExit(g.returncode)", run_cell)

    def test_weights_cell_is_thin_and_persistent(self):
        wf = self.code[self.indices("'--params-dir'")[0]]
        self.assertIn("ensure_af2_weights.py", wf)
        self.assertIn("persistent/cache/alphafold", wf)
        self.assertIn("present_count'] == 15", wf)
        self.assertNotIn("alphafold_params_2022-12-06.tar", self.text)
        self.assertNotIn("wget -c", self.text)
        self.assertNotIn("proc.poll()", self.text)

    def test_science_lives_in_scripts_not_notebook(self):
        self.assertNotIn("target_hotspot_residues", self.text)
        cfg = (SCRIPTS / "stage2_configure.py").read_text()
        self.assertIn("390,393,399,421,424,431", cfg)
        self.assertIn("[80, 80]", cfg)

    def test_report_cell_and_no_runroot(self):
        self.assertIn("persistent/reports/stage2_smoke_report.json", self.text)
        self.assertIn("flags", self.text)
        self.assertNotIn("RUNROOT", self.text)

    def test_persistent_root_only(self):
        self.assertIn("STAGE2_PERSISTENT_ROOT", self.text)
        self.assertNotIn("/content/output", self.text)

    def test_cell_d_applies_pinned_relax_patch(self):
        hits = self.indices("apply_bindcraft_patch.py")
        self.assertEqual(len(hits), 1)                  # only Cell D
        cell_d = self.code[hits[0]]
        self.assertIn("bindcraft-7713aa0-relax-tolerance.patch", cell_d)
        self.assertIn("persistent/metadata/bindcraft_patch.json", cell_d)
        self.assertIn("'ALREADY_APPLIED'", cell_d)
        self.assertIn("relax_failures.jsonl", cell_d)
        # applied AFTER the pinned checkout is verified, BEFORE the env build
        self.assertLess(cell_d.index("assert sha == PINNED"),
                        cell_d.index("apply_bindcraft_patch.py"))
        self.assertLess(cell_d.index("apply_bindcraft_patch.py"),
                        cell_d.index("Miniforge3-Linux-x86_64.sh"))
        # per-model failure semantics are documented in the cell
        self.assertIn("STAGE2_RELAX_FAILURE", cell_d)
        self.assertIn("retain", cell_d.lower())


class TestPreflightVersionPolicy(unittest.TestCase):
    """Regression guard for environment failure 001:
    Colab image Python 3.13.15 + JAX 0.11.1 removed jax.lib.xla_bridge
    (removed upstream in JAX 0.8.0), crashing ColabDesign.clear_mem().
    """
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "bindcraft_preflight", SCRIPTS / "bindcraft_preflight.py")
        cls.pf = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.pf)

    def test_supported_versions_accepted(self):
        for v in ("0.4.35", "0.6.0"):
            ok, _ = self.pf.check_bounded(
                "jax", v, self.pf.JAX_MIN, self.pf.JAX_MAX)
            self.assertTrue(ok, v)

    def test_unsupported_jax_versions_rejected(self):
        for v in ("0.6.1", "0.7.2", "0.8.0", "0.10.2", "0.11.1"):
            ok, msg = self.pf.check_bounded(
                "jax", v, self.pf.JAX_MIN, self.pf.JAX_MAX)
            self.assertFalse(ok, v)
            self.assertIn("0.8.0", msg)

    def test_exact_observed_bad_version_rejected_as_001(self):
        ok, msg = self.pf.check_bounded(
            "jax", "0.11.1", self.pf.JAX_MIN, self.pf.JAX_MAX)
        self.assertFalse(ok)
        self.assertIn("0.11.1", msg)
        self.assertIn("xla_bridge", msg)

    def test_python_required_is_310(self):
        self.assertEqual(self.pf.PYTHON_REQUIRED, (3, 10))

    def test_numpy_and_flax_upper_pins(self):
        self.assertTrue(self.pf.check_upper("numpy", "1.26.4", (2, 0))[0])
        self.assertFalse(self.pf.check_upper("numpy", "2.2.6", (2, 0))[0])
        self.assertTrue(self.pf.check_upper("flax", "0.9.3", (0, 10))[0])
        self.assertFalse(self.pf.check_upper("flax", "0.10.0", (0, 10))[0])

    def test_gate_exits_nonzero_and_reports_json_when_jax_absent(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "pf.json"
            p = subprocess.run([sys.executable,
                                str(SCRIPTS / "bindcraft_preflight.py"),
                                "--out", str(out)],
                               capture_output=True, text=True)
            self.assertNotEqual(p.returncode, 0)
            report = json.loads(out.read_text())
            self.assertFalse(report["passed"])
            names = [c["check"] for c in report["checks"]]
            skip_names = [s["check"] for s in report["skipped"]]
            # the exact failure-001 probes exist in the gate and really ran
            self.assertIn("clear_mem", names)
            self.assertIn("xla_bridge_get_backend", names)
            self.assertIn("jax_import", names)
            # downstream probes that could not run are SKIP, not extra failures
            self.assertIn("trivial_gpu_matmul", skip_names)
            self.assertIn("gpu_visible", skip_names)
            self.assertNotIn("trivial_gpu_matmul", names)
            self.assertTrue(all(s["status"] == "SKIP"
                                for s in report["skipped"]))
            # no duplicate or cascading root-failure entries
            self.assertEqual(len(names), len(set(names)))
            self.assertEqual(len(skip_names), len(set(skip_names)))
            self.assertFalse(set(names) & set(skip_names))


class TestPreflightDeviceSemantics(unittest.TestCase):
    """Regression for the attempt-002 harness bug (2026-10-01): the isolated
    env was healthy (jax 0.6.0 GPU stack verified) but the gate crashed with
    TypeError: 'set' object is not subscriptable because it indexed
    jax.Array.devices()[0]; Array.devices() returns set[Device].
    """
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "bindcraft_preflight", SCRIPTS / "bindcraft_preflight.py")
        cls.pf = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.pf)

    class FakeDevice:
        def __init__(self, platform):
            self.platform = platform

        def __str__(self):
            return f"{self.platform}-device"

    class FakeArray:
        def __init__(self, platforms):
            self._devices = {TestPreflightDeviceSemantics.FakeDevice(p)
                             for p in platforms}

        def devices(self):
            return self._devices           # set, like jax.Array.devices()

    def test_source_never_indexes_devices_collection(self):
        src = (SCRIPTS / "bindcraft_preflight.py").read_text()
        self.assertNotIn("devices()[0]", src)
        self.assertNotIn("devices()[", src)

    def test_array_on_gpu_accepts_set_valued_devices(self):
        self.assertTrue(self.pf.array_on_gpu(self.FakeArray(["gpu"])))
        self.assertTrue(self.pf.array_on_gpu(self.FakeArray(["cpu", "gpu"])))
        self.assertFalse(self.pf.array_on_gpu(self.FakeArray(["cpu"])))
        self.assertFalse(self.pf.array_on_gpu(self.FakeArray([])))

    def _fake_jax_stack(self, backend, platforms, element=2048.0):
        class FakeScalar:
            def __float__(self):
                return float(element)

        class FakeResult:
            def __getitem__(self, idx):
                return FakeScalar()       # EACH element of ones@ones == 2048

            def block_until_ready(self):
                return self

            def devices(self):
                return {TestPreflightDeviceSemantics.FakeDevice(p)
                        for p in platforms}    # set-valued, like real JAX

        class FakeMat:
            def __matmul__(self, other):
                return FakeResult()

        class FakeJNP:
            float32 = "float32"

            @staticmethod
            def ones(shape, dtype=None):
                return FakeMat()

        class FakeJax:
            @staticmethod
            def default_backend():
                return backend

        return FakeJax, FakeJNP

    def test_matmul_check_passes_on_healthy_fake_gpu(self):
        jax, jnp = self._fake_jax_stack("gpu", ["gpu"])
        ok, detail, info = self.pf.run_gpu_matmul_check(jax, jnp)
        self.assertTrue(ok, detail)
        self.assertTrue(info["element_ok"])
        self.assertEqual(info["backend"], "gpu")
        self.assertAlmostEqual(info["element_value"], 2048.0)
        self.assertEqual(info["expected_element"], 2048)
        # the sum (2048**3) is recorded for reference but is NOT the criterion
        self.assertEqual(info["expected_sum"], float(2048 ** 3))
        self.assertTrue(info["gpu_devices"])

    def test_matmul_check_verifies_each_element_not_sum(self):
        """Consolidation §9: ones @ ones gives EACH element == 2048. A probe
        that only checked the sum (2048**3) would miss per-element error."""
        jax, jnp = self._fake_jax_stack("gpu", ["gpu"], element=1.0)
        ok, detail, info = self.pf.run_gpu_matmul_check(jax, jnp)
        self.assertFalse(ok)
        self.assertIn("element", detail)
        self.assertFalse(info["element_ok"])

    def test_matmul_check_rejects_cpu_default_backend(self):
        jax, jnp = self._fake_jax_stack("cpu", ["cpu"])
        ok, detail, _ = self.pf.run_gpu_matmul_check(jax, jnp)
        self.assertFalse(ok)
        self.assertIn("backend", detail)

    def test_matmul_check_rejects_cpu_resident_result(self):
        jax, jnp = self._fake_jax_stack("gpu", ["cpu"])
        ok, detail, _ = self.pf.run_gpu_matmul_check(jax, jnp)
        self.assertFalse(ok)
        self.assertIn("not resident", detail)


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


# ===========================================================================
# Reliability consolidation — Checkpoint A regressions (reports/...§17)
# ===========================================================================

OFFICIAL_ADV = {
    "design_algorithm": "4stage", "use_multimer_design": True,
    "predict_initial_guess": False, "rm_template_sc_design": False,
    "omit_AAs": "C", "max_trajectories": False,
}


def make_fake_bindcraft(td):
    bd = Path(td) / "bindcraft"
    (bd / "settings_advanced").mkdir(parents=True)
    (bd / "settings_advanced" /
     "default_4stage_multimer.json").write_text(json.dumps(OFFICIAL_ADV))
    (bd / "example").mkdir(parents=True)
    (bd / "example" / "PDL1.pdb").write_text("FAKE-PDL1")
    return bd


def make_relaxed(design_path, name="PDL1_smoke_l65_s909721.pdb",
                 content="ATOM relaxed placeholder\nEND\n"):
    rdir = Path(design_path) / "Trajectory" / "Relaxed"
    rdir.mkdir(parents=True, exist_ok=True)
    p = rdir / name
    p.write_text(content)
    return p


class TestStage2Paths(unittest.TestCase):
    def test_env_override_and_layout(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "drive"
            os.environ["STAGE2_PERSISTENT_ROOT"] = str(root)
            try:
                paths = sp.Paths()
                self.assertEqual(paths.root, root)
                paths.ensure()
                for d in ("checkpoints", "configs", "logs", "metadata",
                          "reports", "cache"):
                    self.assertTrue((root / "persistent" / d).is_dir())
                self.assertTrue((root / sp.JOB_PDL1).is_dir())
                self.assertTrue((root / sp.JOB_EGFR).is_dir())
                self.assertEqual(
                    paths.manifest_path(sp.JOB_PDL1),
                    root / "persistent" / "checkpoints" / sp.JOB_PDL1
                    / "run_manifest.json")
                self.assertEqual(
                    paths.af_cache_dir,
                    root / "persistent" / "cache" / "alphafold")
            finally:
                del os.environ["STAGE2_PERSISTENT_ROOT"]

    def test_persistence_predicate(self):
        with tempfile.TemporaryDirectory() as td:
            paths = sp.Paths(root=td)
            self.assertTrue(paths.is_persistent(Path(td) / "job" / "x.pdb"))
            self.assertFalse(paths.is_persistent("/tmp/somewhere-else/x"))

    def test_atomic_json_and_hashes(self):
        with tempfile.TemporaryDirectory() as td:
            paths = sp.Paths(root=td)
            p = paths.write_json(paths.metadata_dir / "m.json", {"a": 1})
            self.assertEqual(paths.read_json(p), {"a": 1})
            self.assertIsNone(paths.read_json(Path(td) / "missing.json"))
            (Path(td) / "bad.json").write_text("{not json")
            self.assertIsNone(paths.read_json(Path(td) / "bad.json"))
            f = Path(td) / "f"; f.write_bytes(b"abc")
            self.assertEqual(sp.sha256_file(f), sp.sha256_text("abc"))
            self.assertEqual(sp.sha256_json({"b": 2, "a": 1}),
                             sp.sha256_json({"a": 1, "b": 2}))

    def test_relaxed_dir_uses_design_path_Q(self):
        with tempfile.TemporaryDirectory() as td:
            paths = sp.Paths(root=td)
            custom = Path(td) / "custom_job"
            self.assertEqual(paths.relaxed_dir(sp.JOB_PDL1, str(custom)),
                             custom / "Trajectory" / "Relaxed")
            # default falls back to job dir, never to a notebook RUNROOT
            self.assertEqual(paths.relaxed_dir(sp.JOB_PDL1),
                             paths.job_dir(sp.JOB_PDL1) / "Trajectory"
                             / "Relaxed")


class TestDeterministicConfigure(unittest.TestCase):
    def test_write_all_is_deterministic_and_only_changes_cap(self):
        with tempfile.TemporaryDirectory() as td:
            bd = make_fake_bindcraft(td)
            paths = sp.Paths(root=Path(td) / "drive"); paths.ensure()
            m1 = configure.write_all(paths, bindcraft_dir=str(bd))
            h1 = {t: (m1[t]["target_config_sha256"],
                      m1[t]["advanced_config_sha256"]) for t in m1}
            # regenerate into a fresh ephemeral checkout -> identical hashes
            bd2 = make_fake_bindcraft(Path(td) / "ephemeral2")
            m2 = configure.write_all(paths, bindcraft_dir=str(bd2))
            for t in m2:
                self.assertEqual(m2[t]["target_config_sha256"], h1[t][0])
                self.assertEqual(m2[t]["advanced_config_sha256"], h1[t][1])
            # frozen science
            self.assertEqual(m1[sp.JOB_PDL1]["hotspots"], "56")
            self.assertEqual(m1[sp.JOB_PDL1]["lengths"], [65, 65])
            self.assertEqual(m1[sp.JOB_EGFR]["hotspots"],
                             "390,393,399,421,424,431")
            self.assertEqual(m1[sp.JOB_EGFR]["lengths"], [80, 80])
            self.assertEqual(m1[sp.JOB_EGFR]["max_trajectories"], 3)
            # design_path is persistent and per-job
            for t, cap in ((sp.JOB_PDL1, 1), (sp.JOB_EGFR, 3)):
                self.assertTrue(m1[t]["design_path"].endswith(t + "/"))
                self.assertTrue(paths.is_persistent(m1[t]["design_path"]))
                adv = json.loads((bd / m1[t]["advanced_config_name"]).read_text())
                diff = configure.advanced_diff(OFFICIAL_ADV, adv)
                self.assertEqual(diff, {"max_trajectories": (False, cap)})
                # manifest on disk
                self.assertEqual(paths.read_json(paths.config_manifest), m1)

    def test_build_advanced_refuses_non_default_base(self):
        bad = dict(OFFICIAL_ADV, predict_initial_guess=True)
        with self.assertRaises(ValueError):
            configure.build_advanced(bad, 1)


class TestCheckpointSemantics(unittest.TestCase):
    def _completed(self, design_path, rc=0, accepted=0, hashes=None,
                   commit="7713aa0d0d351e4117a8befeb8541f3a8ebd3368"):
        m = ckpt.new_manifest(
            "run", sp.JOB_PDL1, design_path=str(design_path),
            bindcraft_commit=commit,
            advanced_config_sha256=(hashes or {}).get("a", "hA"),
            target_config_sha256=(hashes or {}).get("t", "hT"))
        m.update(status="COMPLETED", returncode=rc,
                 final_design_count=accepted)
        return m

    def test_relaxed_discovery_uses_config_path_Q(self):
        with tempfile.TemporaryDirectory() as td:
            paths = sp.Paths(root=Path(td) / "drive")
            custom = Path(td) / "elsewhere" / sp.JOB_PDL1
            p = make_relaxed(custom)
            self.assertEqual(ckpt.relaxed_pdbs(str(custom)), [p])
            self.assertEqual(ckpt.relaxed_pdbs(paths.job_dir(sp.JOB_PDL1)),
                             [])           # guessing the default path fails
            (p.parent / "EMPTY.pdb").write_text("")
            self.assertEqual(ckpt.relaxed_pdbs(str(custom)), [p])

    def test_valid_checkpoint_T_and_sha_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            paths = sp.Paths(root=Path(td) / "drive"); paths.ensure()
            dp = paths.job_dir(sp.JOB_PDL1)
            p = make_relaxed(dp)
            m = self._completed(dp)
            m["relaxed_pdb_paths"] = [str(p)]
            m["relaxed_pdb_sha256"] = {str(p): sp.sha256_file(p)}
            ok, reasons = ckpt.validate_checkpoint(m)
            self.assertTrue(ok, reasons)
            p.write_text("TAMPERED\n")
            ok, reasons = ckpt.validate_checkpoint(m)
            self.assertFalse(ok)
            self.assertTrue(any("sha256 mismatch" in r for r in reasons))

    def test_config_hash_mismatch_forces_rerun_U(self):
        with tempfile.TemporaryDirectory() as td:
            paths = sp.Paths(root=Path(td) / "drive"); paths.ensure()
            dp = paths.job_dir(sp.JOB_PDL1)
            make_relaxed(dp)
            m = self._completed(dp, hashes={"a": "hA", "t": "hT"})
            ok, _ = ckpt.validate_checkpoint(
                m, expected_hashes={"advanced_config_sha256": "DIFFERENT",
                                    "target_config_sha256": "hT"})
            self.assertFalse(ok)

    def test_environment_gate_zero_mpnn_still_passes_V(self):
        with tempfile.TemporaryDirectory() as td:
            dp = Path(td) / sp.JOB_PDL1
            make_relaxed(dp)
            m = self._completed(dp, rc=0, accepted=0)
            self.assertTrue(orchestrate.pdl1_allows_egfr(m, str(dp)))

    def test_environment_gate_failures_block_W(self):
        with tempfile.TemporaryDirectory() as td:
            dp = Path(td) / sp.JOB_PDL1
            make_relaxed(dp)
            bad = self._completed(dp, rc=1)
            self.assertFalse(orchestrate.pdl1_allows_egfr(bad, str(dp)))
            empty = Path(td) / "emptyjob"; (empty).mkdir()
            self.assertFalse(
                orchestrate.pdl1_allows_egfr(self._completed(empty, rc=0),
                                             str(empty)))

    def test_completed_manifest_never_silently_overwritten_Z(self):
        with tempfile.TemporaryDirectory() as td:
            paths = sp.Paths(root=Path(td) / "drive"); paths.ensure()
            dp = paths.job_dir(sp.JOB_PDL1)
            done = self._completed(dp)
            ckpt.save_manifest(paths, sp.JOB_PDL1, done)
            with self.assertRaises(PermissionError):
                ckpt.save_manifest(paths, sp.JOB_PDL1,
                                   self._completed(dp, rc=9) if False else
                                   {**done, "status": "RUNNING"})
            # force keeps the state machine honest for a new recorded attempt
            rerun = {**done, "status": "FAILED", "returncode": 1}
            ckpt.save_manifest(paths, sp.JOB_PDL1, rerun, force=True)
            self.assertEqual(
                ckpt.load_manifest(paths, sp.JOB_PDL1)["status"], "FAILED")

    def test_legacy_adoption_is_evidence_bounded(self):
        with tempfile.TemporaryDirectory() as td:
            paths = sp.Paths(root=Path(td) / "drive"); paths.ensure()
            dp = paths.job_dir(sp.JOB_PDL1)
            self.assertIsNone(
                ckpt.adopt_legacy_checkpoint(
                    paths, sp.JOB_PDL1, design_path=str(dp),
                    bindcraft_commit="pin"))
            p = make_relaxed(dp)
            m = ckpt.adopt_legacy_checkpoint(
                paths, sp.JOB_PDL1, design_path=str(dp),
                bindcraft_commit="pin")
            self.assertTrue(m["legacy"])
            self.assertEqual(m["status"], "COMPLETED")
            self.assertFalse(m["provenance"]["config_hash_verified"])
            self.assertEqual(m["relaxed_pdb_sha256"][str(p)],
                             sp.sha256_file(p))
            self.assertIn("LEGACY_CHECKPOINT", m["notes"])


class TestRunJobSafety(unittest.TestCase):
    def test_non_persistent_design_path_refused_X(self):
        with tempfile.TemporaryDirectory() as td:
            paths = sp.Paths(root=Path(td) / "drive"); paths.ensure()
            outside = Path(td) / "ephemeral_out" / "pdl1"
            settings = Path(td) / "s.json"
            settings.write_text(json.dumps({
                "design_path": str(outside) + "/",
                "lengths": [65, 65]}))
            with self.assertRaises(PermissionError):
                runner.run_job(tag=sp.JOB_PDL1, settings_path=settings,
                               advanced_path=settings, paths=paths,
                               bindcraft_dir=Path(td) / "bindcraft",
                               bindpy=sys.executable, dry_run=True)

    def test_dry_run_writes_planned_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            bd = make_fake_bindcraft(td)
            paths = sp.Paths(root=Path(td) / "drive"); paths.ensure()
            man = configure.write_all(paths, bindcraft_dir=str(bd))
            sp_path = bd / "settings_target" / man[sp.JOB_PDL1]["target_config_name"]
            ap_path = bd / man[sp.JOB_PDL1]["advanced_config_name"]
            out, action = runner.run_job(
                tag=sp.JOB_PDL1, settings_path=sp_path, advanced_path=ap_path,
                paths=paths, bindcraft_dir=str(bd), bindpy=sys.executable,
                dry_run=True)
            self.assertEqual(action, "DRY_RUN")
            self.assertEqual(out["status"], "PLANNED")
            self.assertEqual(ckpt.load_manifest(paths, sp.JOB_PDL1)["run_id"],
                             sp.JOB_PDL1)


class TestOrchestratorGating(unittest.TestCase):
    def _orch(self, td, **kw):
        return orchestrate.Orchestrator(
            repo_dir=str(Path(td) / "repo"),
            bindcraft_dir=str(Path(td) / "bindcraft"),
            bindpy=str(Path(td) / "env" / "bin" / "python"),
            root=str(Path(td) / "drive"), **kw)

    def test_gpu_absent_is_controlled_blocked_Y(self):
        with tempfile.TemporaryDirectory() as td:
            orig = orchestrate.query_gpu
            orchestrate.query_gpu = lambda: None
            try:
                o = self._orch(td)
                rc = o.run()
            finally:
                orchestrate.query_gpu = orig
            self.assertEqual(rc, 2)
            self.assertEqual(o.state["status"], "GPU_UNAVAILABLE")
            self.assertTrue(o.state["compute_blocked"])
            # stopped BEFORE env build: missing bindpy never raised
            self.assertTrue(o.paths.state_file.exists())

    def test_missing_env_blocks_before_weights(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "repo").mkdir()
            o = self._orch(td)
            orig_gpu, orig_git = orchestrate.query_gpu, orchestrate.git_commit
            orchestrate.query_gpu = lambda: {"name": "T4",
                                             "vram_total_mib": 15000,
                                             "vram_free_mib": 15000}
            orchestrate.git_commit = lambda d: "project-sha"
            try:
                with self.assertRaises(RuntimeError):
                    o.run()
            finally:
                orchestrate.query_gpu, orchestrate.git_commit = orig_gpu, orig_git
            self.assertEqual(o.state["status"], "ENV_NEEDS_BUILD")

    def test_settings_persist_ok(self):
        with tempfile.TemporaryDirectory() as td:
            paths = sp.Paths(root=Path(td) / "drive"); paths.ensure()
            good = Path(td) / "g.json"
            good.write_text(json.dumps(
                {"design_path": str(paths.job_dir(sp.JOB_EGFR)) + "/"}))
            self.assertTrue(orchestrate.settings_persist_ok(paths, good))
            bad = Path(td) / "b.json"
            bad.write_text(json.dumps({"design_path": "/content/ephemeral/"}))
            self.assertFalse(orchestrate.settings_persist_ok(paths, bad))


class TestResumeAfterReset(unittest.TestCase):
    """S/T/U across a simulated Colab reset: ephemeral /content wiped,
    Drive persists; determinism + checkpoint must make the rerun a skip."""

    def _setup_legacy_pdl1(self, td):
        bd = make_fake_bindcraft(td)
        paths = sp.Paths(root=Path(td) / "drive"); paths.ensure()
        manifest_cfg = configure.write_all(paths, bindcraft_dir=str(bd))
        make_relaxed(manifest_cfg[sp.JOB_PDL1]["design_path"])
        return bd, paths, manifest_cfg

    def test_legacy_then_reuse_after_simulated_reset(self):
        with tempfile.TemporaryDirectory() as td:
            bd, paths, cfg = self._setup_legacy_pdl1(td)
            bindpy = Path(td) / "env" / "bin" / "python"
            bindpy.parent.mkdir(parents=True); bindpy.write_text("#!")
            o1 = orchestrate.Orchestrator(
                repo_dir=td, bindcraft_dir=str(bd), bindpy=str(bindpy),
                root=str(paths.root), dry_run=True)
            o1.state["project_commit"] = "proj-1"
            o1.bindcraft_commit = "bin-1"
            o1.step_configure()
            o1.step_pdl1()
            self.assertEqual(o1.jobs[sp.JOB_PDL1]["action"], "LEGACY_ADOPTED")

            # ---- Colab runtime reset: /content erased, Drive untouched ----
            bd2 = make_fake_bindcraft(Path(td) / "fresh_content_bindcraft")
            o2 = orchestrate.Orchestrator(
                repo_dir=td, bindcraft_dir=str(bd2), bindpy=str(bindpy),
                root=str(paths.root), dry_run=True)
            cfg2 = configure.write_all(paths, bindcraft_dir=str(bd2))
            o2.bindcraft_commit = "bin-1"
            o2.config_manifest = cfg2
            o2.jobs = {}
            o2.step_pdl1()
            self.assertEqual(o2.jobs[sp.JOB_PDL1]["action"],
                             "CHECKPOINT_REUSED")

    def test_hash_mismatch_after_reset_does_not_skip_U(self):
        with tempfile.TemporaryDirectory() as td:
            bd, paths, cfg = self._setup_legacy_pdl1(td)
            bindpy = Path(td) / "env2" / "bin" / "python"
            bindpy.parent.mkdir(parents=True); bindpy.write_text("#!")
            o1 = orchestrate.Orchestrator(
                repo_dir=td, bindcraft_dir=str(bd), bindpy=str(bindpy),
                root=str(paths.root), dry_run=True)
            o1.bindcraft_commit = "bin-1"
            o1.step_configure()
            o1.step_pdl1()
            # tamper the recorded advanced hash (simulating changed protocol)
            mpath = paths.manifest_path(sp.JOB_PDL1)
            m = paths.read_json(mpath)
            m["advanced_config_sha256"] = "stale-hash"
            paths.write_json(mpath, m)
            _, action = runner.run_job(
                tag=sp.JOB_PDL1,
                settings_path=bd / "settings_target"
                / cfg[sp.JOB_PDL1]["target_config_name"],
                advanced_path=bd / cfg[sp.JOB_PDL1]["advanced_config_name"],
                paths=paths, bindcraft_dir=str(bd), bindpy=str(bindpy),
                bindcraft_commit="bin-1", dry_run=True)
            self.assertEqual(action, "DRY_RUN")   # rerun, NOT skipped

    def test_pdl1_failure_blocks_egfr_orchestration_W(self):
        with tempfile.TemporaryDirectory() as td:
            bd, paths, cfg = self._setup_legacy_pdl1(td)
            o = orchestrate.Orchestrator(
                repo_dir=td, bindcraft_dir=str(bd), bindpy=sys.executable,
                root=str(paths.root), dry_run=True)
            o.config_manifest = cfg
            o.jobs = {sp.JOB_PDL1: {"status": "FAILED", "returncode": 1}}
            self.assertFalse(o.step_pdl1_gate())
            self.assertEqual(o.state["pdl1_environment_gate"], "FAIL")

    def test_report_flags_and_persistence(self):
        with tempfile.TemporaryDirectory() as td:
            bd, paths, cfg = self._setup_legacy_pdl1(td)
            o = orchestrate.Orchestrator(
                repo_dir=td, bindcraft_dir=str(bd), bindpy=sys.executable,
                root=str(paths.root), dry_run=True)
            o.config_manifest = cfg
            o.state = {"project_commit": "p", "bindcraft_commit": "b",
                       "gpu": {"name": "T4", "vram_total_mib": 15000},
                       "weights": {"action": "CACHE_HIT"}}
            m = ckpt.adopt_legacy_checkpoint(
                paths, sp.JOB_PDL1,
                design_path=cfg[sp.JOB_PDL1]["design_path"],
                bindcraft_commit="b")
            o.jobs = {sp.JOB_PDL1: m}
            o.geometry = {sp.JOB_PDL1: {}}
            rep = o.step_report()
            self.assertTrue(rep["flags"]["ENVIRONMENT_PASS"])
            self.assertFalse(rep["flags"]["EXPERIMENTALLY_VALIDATED"])
            self.assertIn(None, [rep["flags"]["COMPUTATIONAL_FILTER_PASS"]])
            out = paths.reports_dir / "stage2_smoke_report.json"
            self.assertTrue(json.loads(out.read_text())["flags"] is not None)
            self.assertIn("experimentally_validated",
                          (paths.reports_dir / "stage2_smoke_report.md")
                          .read_text())


class TestAF2WeightExactSet(unittest.TestCase):
    """BUG 006/007: authority is the exact 15-file set, never done.txt."""

    def _populate(self, d, names, content=b"NPZ"):
        d = Path(d); d.mkdir(parents=True, exist_ok=True)
        for n in names:
            (d / n).write_bytes(content)
        return d

    @property
    def names(self):
        return sorted(eaw.REQUIRED_SET)

    def test_exact_15_accepted_K(self):
        with tempfile.TemporaryDirectory() as td:
            d = self._populate(Path(td) / "p", self.names)
            ok, rep = eaw.validate_weights(d)
            self.assertTrue(ok, rep)
            self.assertEqual(rep["present_count"], 15)

    def test_14_rejected_L(self):
        with tempfile.TemporaryDirectory() as td:
            d = self._populate(Path(td) / "p", self.names[:-1])
            ok, rep = eaw.validate_weights(d)
            self.assertFalse(ok)
            self.assertEqual(len(rep["missing"]), 1)
            self.assertEqual(rep["present_count"], 14)

    def test_16_with_extra_rejected_M(self):
        with tempfile.TemporaryDirectory() as td:
            d = self._populate(Path(td) / "p",
                               self.names + ["params_model_6_ptm.npz"])
            ok, rep = eaw.validate_weights(d)
            self.assertFalse(ok)
            self.assertEqual(rep["unexpected"],
                             ["params_model_6_ptm.npz"])

    def test_empty_member_and_stale_done_txt_rejected_N(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "p"; d.mkdir()
            (d / "done.txt").write_text("true\n")   # legacy stale marker
            for n in self.names[:-1]:
                (d / n).write_bytes(b"NPZ")
            (d / self.names[-1]).write_bytes(b"")   # truncated download
            ok, rep = eaw.validate_weights(d)
            self.assertFalse(ok)
            self.assertTrue(rep["done_txt_present"])
            self.assertEqual(rep["missing"] or rep["empty_or_small"],
                             rep["missing"] or [self.names[-1]])
            self.assertIn("never authoritative", rep["authority"])


class TestAF2WeightProvisioning(unittest.TestCase):
    NAMES = sorted(eaw.REQUIRED_SET)

    def _npz_dir(self, d, names=None, content=b"NPZBYTES"):
        d = Path(d); d.mkdir(parents=True, exist_ok=True)
        for n in (names if names is not None else self.NAMES):
            (d / n).write_bytes(content)
        return d

    def _tar_of(self, path, names):
        path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(path, "w") as tf:
            for n in names:
                f = path.parent / n
                f.write_bytes(b"TAR" + n.encode())
                tf.add(f, arcname=f"params/{n}")
                f.unlink()
        return path

    def test_local_valid_skips_network_O(self):
        with tempfile.TemporaryDirectory() as td:
            params = self._npz_dir(Path(td) / "params")
            binp = Path(td) / "fakebin"; binp.mkdir()
            poison = binp / "wget"
            poison.write_text("#!/bin/sh\nexit 42\n")
            poison.chmod(0o755)
            env_path = binp / "CALLED"
            poison.write_text(
                "#!/bin/sh\ntouch \"$CALLED_MARKER\"\nexit 42\n")
            os.environ["CALLED_MARKER"] = str(env_path)
            old = os.environ["PATH"]
            os.environ["PATH"] = f"{binp}:{old}"
            try:
                r = eaw.ensure_weights(
                    params_dir=params, cache_dir=Path(td) / "cache",
                    log_dir=Path(td) / "logs")
            finally:
                os.environ["PATH"] = old
                os.environ.pop("CALLED_MARKER", None)
            self.assertEqual(r["action"], "LOCAL_VALID")
            self.assertFalse(env_path.exists())   # network never touched

    def test_drive_cache_restore_P(self):
        with tempfile.TemporaryDirectory() as td:
            cache = self._npz_dir(Path(td) / "cache" / "alphafold")
            params = Path(td) / "params"
            r = eaw.ensure_weights(
                params_dir=params, cache_dir=cache,
                log_dir=Path(td) / "logs")
            self.assertEqual(r["action"], "CACHE_RESTORED")
            ok, rep = eaw.validate_weights(params)
            self.assertTrue(ok, rep)

    def test_cached_archive_extracted(self):
        with tempfile.TemporaryDirectory() as td:
            cache = Path(td) / "cache" / "alphafold"
            arch_dir = cache / "archive"
            self._tar_of(arch_dir / eaw.ARCHIVE_NAME, self.NAMES)
            params = Path(td) / "params"
            r = eaw.ensure_weights(
                params_dir=params, cache_dir=cache,
                log_dir=Path(td) / "logs")
            self.assertEqual(r["action"], "ARCHIVE_EXTRACTED")
            ok, rep = eaw.validate_weights(params)
            self.assertTrue(ok, rep)
            self.assertRegex(r["archive_sha256"], r"^[0-9a-f]{64}$")

    def test_archive_with_extra_npz_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            cache = Path(td) / "cache" / "alphafold"
            self._tar_of(cache / "archive" / eaw.ARCHIVE_NAME,
                         self.NAMES + ["params_model_9_multimer_v3.npz"])
            r = eaw.ensure_weights(
                params_dir=Path(td) / "params", cache_dir=cache,
                log_dir=Path(td) / "logs", dry_run=True)
            # dry-run surfaces WOULD_DOWNLOAD only when no local/cache;
            # a corrupt cached archive must not be treated as valid cache
            self.assertEqual(r["action"], "WOULD_DOWNLOAD")

    def test_dry_run_does_not_download(self):
        with tempfile.TemporaryDirectory() as td:
            binp = Path(td) / "fakebin"; binp.mkdir()
            poison = binp / "wget"
            poison.write_text("#!/bin/sh\ntouch \"$CALLED_MARKER\"\nexit 0\n")
            poison.chmod(0o755)
            marker = Path(td) / "called"
            os.environ["CALLED_MARKER"] = str(marker)
            old = os.environ["PATH"]
            os.environ["PATH"] = f"{binp}:{old}"
            try:
                r = eaw.ensure_weights(
                    params_dir=Path(td) / "params",
                    cache_dir=Path(td) / "cache",
                    log_dir=Path(td) / "logs", dry_run=True)
            finally:
                os.environ["PATH"] = old
                os.environ.pop("CALLED_MARKER", None)
            self.assertEqual(r["action"], "WOULD_DOWNLOAD")
            self.assertFalse(marker.exists())

    def _install_fake_wget(self, binp, fixture_tar, fail=False,
                           marker=None):
        binp.mkdir(parents=True, exist_ok=True)
        wget = binp / "wget"
        if fail:
            body = ("#!/usr/bin/env python3\nimport sys, os\n"
                    "open(os.environ['WGET_MARKER'],'w').close()\n"
                    "sys.exit(7)\n")
        else:
            body = (
                "#!/usr/bin/env python3\n"
                "import sys, shutil, os\n"
                "a = sys.argv[1:]\n"
                "out = a[a.index('-O') + 1]\n"
                "shutil.copyfile(os.environ['FIXTURE_TAR'], out)\n"
                "open(os.environ['WGET_MARKER'], 'w').close()\n"
                "sys.exit(0)\n")
        wget.write_text(body)
        wget.chmod(0o755)
        os.environ["FIXTURE_TAR"] = str(fixture_tar)
        os.environ["WGET_MARKER"] = str(marker or (binp / "called"))

    def test_observed_download_full_flow(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            fixture = td / "fixture.tar"
            with tarfile.open(fixture, "w") as tf:
                for n in self.NAMES:
                    f = td / n
                    f.write_bytes(b"DOWNLOADED-" + n.encode())
                    tf.add(f, arcname=n)
                    f.unlink()
            binp = td / "fakebin"
            marker = td / "called"
            self._install_fake_wget(binp, fixture, marker=marker)
            old = os.environ["PATH"]
            os.environ["PATH"] = f"{binp}:{old}"
            try:
                r = eaw.ensure_weights(
                    params_dir=td / "bindcraft" / "params",
                    cache_dir=td / "drive" / "cache" / "alphafold",
                    log_dir=td / "drive" / "logs")
            finally:
                os.environ["PATH"] = old
            self.assertTrue(marker.exists())
            self.assertEqual(r["action"], "DOWNLOADED", r)
            d = r["download"]
            self.assertEqual(d["returncode"], 0)
            self.assertIsInstance(d["pid"], int)
            self.assertIn("elapsed_s", d)
            self.assertGreater(d["bytes_on_disk"], 0)
            self.assertTrue(Path(d["log_path"]).exists())
            self.assertRegex(d["archive_sha256"], r"^[0-9a-f]{64}$")
            self.assertIn("not verified", d["sha256_note"])
            # provenance persisted on Drive
            rec = json.loads((td / "drive" / "cache" / "alphafold"
                              / eaw.RECORD_NAME).read_text())
            self.assertEqual(rec["returncode"], 0)
            # archive retained + extracted cache + restored params
            self.assertTrue((td / "drive" / "cache" / "alphafold"
                             / "archive" / eaw.ARCHIVE_NAME).is_file())
            ok, rep = eaw.validate_weights(
                td / "bindcraft" / "params")
            self.assertTrue(ok, rep)

    def test_failed_download_is_observed_and_retains_part(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            binp = td / "fakebin"
            marker = td / "called"
            self._install_fake_wget(binp, td / "nope.tar", fail=True,
                                    marker=marker)
            old = os.environ["PATH"]
            os.environ["PATH"] = f"{binp}:{old}"
            try:
                r = eaw.ensure_weights(
                    params_dir=td / "params",
                    cache_dir=td / "cache" / "alphafold",
                    log_dir=td / "logs")
            finally:
                os.environ["PATH"] = old
            self.assertEqual(r["action"], "FAIL")
            self.assertEqual(r["stage"], "download")
            self.assertEqual(r["returncode"], 7)
            self.assertIn(".part", r["part_path"])
            self.assertTrue(Path(r["log_path"]).exists())

    def test_orchestrator_dry_run_weights_step(self):
        with tempfile.TemporaryDirectory() as td:
            o = orchestrate.Orchestrator(
                repo_dir=str(ROOT),
                bindcraft_dir=str(Path(td) / "bindcraft"),
                bindpy=str(Path(td) / "py"), root=str(Path(td) / "drive"),
                dry_run=True)
            self.assertTrue(o.step_weights())
            self.assertEqual(o.state["weights"]["action"], "WOULD_DOWNLOAD")


class TestReliabilityStaticGuards(unittest.TestCase):
    STAGE_MODULES = [
        "stage2_paths.py", "stage2_preflight.py", "stage2_configure.py",
        "stage2_checkpoint.py", "stage2_run_job.py", "stage2_analyze.py",
        "stage2_orchestrate.py", "bindcraft_preflight.py",
        "ensure_af2_weights.py", "apply_bindcraft_patch.py",
        "stage2_relax_failures.py",
    ]

    def test_forbidden_patterns_absent(self):
        for name in self.STAGE_MODULES:
            src = (SCRIPTS / name).read_text()
            self.assertNotIn("devices()[", src, name)       # BUG 002
            self.assertNotIn("== 14", src, name)            # BUG 006
            self.assertNotIn("time.sleep(1800)", src, name)  # BUG 004
            self.assertNotIn("RUNROOT", src, name)          # BUG 009/R
            self.assertNotIn("aria2c -q -x 16", src, name)  # BUG 005

    def test_no_cpu_fallback_language(self):
        src = (SCRIPTS / "stage2_orchestrate.py").read_text()
        self.assertIn("GPU_UNAVAILABLE", src)
        self.assertNotIn("cpu fallback", src.lower())


def _git(args, cwd):
    p = subprocess.run(["git", *args], cwd=str(cwd),
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    return p.stdout.strip()


class TestRelaxFailureRecords(unittest.TestCase):
    """D-019 harness-side reader for the upstream patch's JSONL log."""

    def _write_design(self, td, records, corrupt=False):
        dp = Path(td) / "design"
        log = dp / srf.RELAX_FAILURE_LOG
        log.parent.mkdir(parents=True)
        lines = [json.dumps(r, sort_keys=True) for r in records]
        if corrupt:
            lines.append("{this is not valid json")
        log.write_text("\n".join(lines) + "\n")
        return dp

    def test_missing_log_is_empty_not_error(self):
        with tempfile.TemporaryDirectory() as td:
            recs, corrupt = srf.load_records(td)
            self.assertEqual(recs, [])
            self.assertEqual(corrupt, 0)
            summ = srf.summarize(td)
            self.assertFalse(summ["log_present"])
            self.assertEqual(summ["relax_failure_count"], 0)
            self.assertEqual(summ["unrelaxed_without_relaxed"], [])
            self.assertEqual(summ["relax_failures_by_stage"], {
                "trajectory_relax": 0, "mpnn_relax": 0, "mpnn_finalize": 0})

    def test_counts_by_stage_and_error_type_corrupt_tolerated(self):
        recs = [
            {"stage": "mpnn_relax", "model": 2,
             "error_type": "RelaxationFailure",
             "retained_unrelaxed": True,
             "action": "skipped_model_continue"},
            {"stage": "trajectory_relax", "model": None,
             "error_type": "FileNotFoundError",
             "action": "skipped_trajectory_continue"},
            {"stage": "mpnn_finalize",
             "error_type": "RelaxedPDBMissing",
             "action": "skipped_candidate_continue"},
        ]
        with tempfile.TemporaryDirectory() as td:
            dp = self._write_design(td, recs, corrupt=True)
            loaded, corrupt = srf.load_records(str(dp))
            self.assertEqual(len(loaded), 3)
            self.assertEqual(corrupt, 1)
            summ = srf.summarize(str(dp))
            self.assertTrue(summ["log_present"])
            self.assertEqual(summ["relax_failure_count"], 3)
            self.assertEqual(summ["relax_failures_corrupt_lines"], 1)
            self.assertEqual(summ["relax_failures_by_stage"], {
                "trajectory_relax": 1, "mpnn_relax": 1,
                "mpnn_finalize": 1})
            self.assertEqual(summ["relax_failures_by_error_type"], {
                "RelaxationFailure": 1, "FileNotFoundError": 1,
                "RelaxedPDBMissing": 1})
            # records carry the exact six-directive semantics
            self.assertTrue(all(r.get("retained_unrelaxed") is not False
                                for r in loaded if "model" in r and r))

    def test_unrelaxed_without_relaxed_listing(self):
        with tempfile.TemporaryDirectory() as td:
            dp = Path(td) / "design"
            mpnn = dp / "MPNN"
            rel = mpnn / "Relaxed"
            rel.mkdir(parents=True)
            (mpnn / "cand_s1_model1.pdb").write_text("UNRELAXED-1")
            (mpnn / "cand_s1_model2.pdb").write_text("UNRELAXED-2")
            (rel / "cand_s1_model2.pdb").write_text("RELAXED-2")
            (mpnn / "notes.txt").write_text("ignored")
            retained = srf.unrelaxed_without_relaxed(str(dp))
            self.assertEqual(retained,
                             [str(mpnn / "cand_s1_model1.pdb")])


class TestBindCraftRelaxTolerancePatch(unittest.TestCase):
    """The one authorized upstream patch (D-019) applies deterministically to
    the pristine pinned tree and refuses every other state."""

    PATCH = PATCHES / "bindcraft-7713aa0-relax-tolerance.patch"
    FILES = {
        "bindcraft.py":
            "cc1103a96ac4b414d9e765c0ba58302914aacc3f47504a2b669a5a47f0deb33a",
        "functions/colabdesign_utils.py":
            "151af44170f1450c01144d6a3b4f1becc7dfea86ba37eb0d3ee0c158d9e667d9",
        "functions/generic_utils.py":
            "e95f9fdaf2a4ccd3263c4234ab26e0e404027ff6ece00e79bcd05f63d1d59cf9",
        "functions/pyrosetta_utils.py":
            "227ea5a11434f56c858d9662974eccc1341e51b28a932a418a70de2b2b7392f4",
    }

    def _pristine_repo(self, td):
        """Copy the pristine oracle into a temp GIT repo; temp HEAD cannot be
        the upstream SHA, so tests point expected_commit at it via the module
        constant (the commit-equality logic itself is the thing under test)."""
        bc = Path(td) / "bindcraft"
        shutil.copytree(PRISTINE, bc,
                        ignore=shutil.ignore_patterns("PROVENANCE.txt"))
        _git(["init", "-q"], bc)
        _git(["config", "user.email", "test@example.invalid"], bc)
        _git(["config", "user.name", "Test"], bc)
        _git(["add", "-A"], bc)
        _git(["commit", "-q", "-m", "pristine bindcraft pin"], bc)
        return bc, _git(["rev-parse", "HEAD"], bc)

    def setUp(self):
        self._orig_const = abp.BINDCRAFT_COMMIT
        self.addCleanup(setattr, abp, "BINDCRAFT_COMMIT", self._orig_const)

    def _point_at(self, head):
        abp.BINDCRAFT_COMMIT = head

    def test_pristine_oracle_hashes_match_provenance(self):
        for rel, digest in self.FILES.items():
            self.assertEqual(abp.sha256_file(str(PRISTINE / rel)), digest,
                             rel)

    def test_patch_artifact_encodes_the_six_directives(self):
        text = self.PATCH.read_text()
        for rel in self.FILES:
            self.assertIn(f"diff --git a/{rel} b/{rel}", text)
        for needle in ("STAGE2-PATCH", "STAGE2_RELAX_FAILURE",
                       "class RelaxationFailure", "record_stage2_relax_failure",
                       "relax_failures.jsonl", "BEFORE clean_pdb",
                       "retained_unrelaxed", "skipped_model_continue",
                       "skipped_trajectory_continue",
                       "skipped_candidate_continue"):
            self.assertIn(needle, text)
        # preamble comment lines must not break git apply (checked e2e below)
        self.assertTrue(text.startswith("# BindCraft per-model"))

    def test_apply_idempotence_verify_and_compilability(self):
        with tempfile.TemporaryDirectory() as td:
            bc, head = self._pristine_repo(td)
            self._point_at(head)

            meta, rc = abp.apply_or_verify(
                bindcraft_dir=str(bc), patch_path=str(self.PATCH),
                verify_only=True)
            self.assertEqual(rc, 1)
            self.assertEqual(meta["status"], "NOT_PATCHED")

            meta, rc = abp.apply_or_verify(
                bindcraft_dir=str(bc), patch_path=str(self.PATCH))
            self.assertEqual(rc, 0, meta)
            self.assertEqual(meta["status"], "APPLIED")
            self.assertEqual(meta["bindcraft_commit_observed"], head)
            self.assertEqual(meta["patch_sha256"],
                             abp.sha256_file(str(self.PATCH)))
            self.assertTrue(all(abp.marker_state(str(bc)).values()))
            # patched python parses (never imported: pyrosetta is absent here)
            for rel in self.FILES:
                ast.parse((bc / rel).read_text(), filename=rel)
            # pre/post metadata captured
            self.assertIn("files_pre", meta)
            self.assertNotEqual(meta["files"], meta["files_pre"])

            meta, rc = abp.apply_or_verify(
                bindcraft_dir=str(bc), patch_path=str(self.PATCH))
            self.assertEqual(rc, 0)
            self.assertEqual(meta["status"], "ALREADY_APPLIED")
            meta, rc = abp.apply_or_verify(
                bindcraft_dir=str(bc), patch_path=str(self.PATCH),
                verify_only=True)
            self.assertEqual(rc, 0)
            self.assertEqual(meta["status"], "VERIFIED")

    def test_drifted_tree_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            bc, head = self._pristine_repo(td)
            self._point_at(head)
            target = bc / "functions" / "colabdesign_utils.py"
            target.write_text(target.read_text().replace(
                "            pr_relax(complex_pdb, mpnn_relaxed)\n",
                "            pr_relax(complex_pdb, mpnn_relaxed)  # drift\n"))
            meta, rc = abp.apply_or_verify(
                bindcraft_dir=str(bc), patch_path=str(self.PATCH))
            self.assertEqual(rc, 1)
            self.assertEqual(meta["status"], "APPLY_CHECK_FAILED")
            # tree left untouched
            self.assertFalse(any(abp.marker_state(str(bc)).values()))

    def test_partially_patched_tree_is_ambiguous_and_untouched(self):
        with tempfile.TemporaryDirectory() as td:
            bc, head = self._pristine_repo(td)
            self._point_at(head)
            meta, rc = abp.apply_or_verify(
                bindcraft_dir=str(bc), patch_path=str(self.PATCH))
            self.assertEqual(rc, 0)
            # revert ONE of the four files to pristine
            shutil.copy2(PRISTINE / "functions" / "generic_utils.py",
                         bc / "functions" / "generic_utils.py")
            meta, rc = abp.apply_or_verify(
                bindcraft_dir=str(bc), patch_path=str(self.PATCH))
            self.assertEqual(rc, 1)
            self.assertEqual(meta["status"], "PATCH_STATE_AMBIGUOUS")
            self.assertIn("3/4", meta["note"])

    def test_commit_mismatch_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            bc, head = self._pristine_repo(td)
            self._point_at("0" * 40)          # deliberately wrong pin
            meta, rc = abp.apply_or_verify(
                bindcraft_dir=str(bc), patch_path=str(self.PATCH))
            self.assertEqual(rc, 1)
            self.assertEqual(meta["status"], "COMMIT_MISMATCH")
            self.assertEqual(meta["bindcraft_commit_observed"], head)
            self.assertFalse(any(abp.marker_state(str(bc)).values()))

    def test_missing_dirs_and_non_git(self):
        with tempfile.TemporaryDirectory() as td:
            meta, rc = abp.apply_or_verify(
                bindcraft_dir=str(Path(td) / "nope"),
                patch_path=str(self.PATCH))
            self.assertEqual(rc, 1)
            self.assertEqual(meta["status"], "BINDCRAFT_DIR_MISSING")
            plain = Path(td) / "plain"
            plain.mkdir()
            meta, rc = abp.apply_or_verify(
                bindcraft_dir=str(plain), patch_path=str(self.PATCH))
            self.assertEqual(rc, 1)
            self.assertEqual(meta["status"], "NOT_A_GIT_CHECKOUT")
            bc, head = self._pristine_repo(td)
            self._point_at(head)
            meta, rc = abp.apply_or_verify(
                bindcraft_dir=str(bc),
                patch_path=str(Path(td) / "nope.patch"))
            self.assertEqual(rc, 1)
            self.assertEqual(meta["status"], "PATCH_MISSING")

    def test_cli_writes_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            bc, head = self._pristine_repo(td)
            self._point_at(head)
            out = Path(td) / "meta" / "bindcraft_patch.json"
            rc = abp.main(["--bindcraft-dir", str(bc),
                           "--patch", str(self.PATCH), "--out", str(out)])
            self.assertEqual(rc, 0)
            meta = json.loads(out.read_text())
            self.assertEqual(meta["status"], "APPLIED")
            rc = abp.main(["--bindcraft-dir", str(Path(td) / "missing")])
            self.assertEqual(rc, 1)


class TestRunJobFinalizesManifestOnFailure(unittest.TestCase):
    """D-019 requirement 6: even a child-process/launch failure terminalizes
    the manifest, and per-model relax records are embedded."""

    def test_launch_failure_terminal_manifest_with_records(self):
        with tempfile.TemporaryDirectory() as td:
            bd = make_fake_bindcraft(td)
            paths = sp.Paths(root=Path(td) / "drive")
            paths.ensure()
            man = configure.write_all(paths, bindcraft_dir=str(bd))
            tag = sp.JOB_PDL1
            sp_path = bd / "settings_target" / man[tag]["target_config_name"]
            ap_path = bd / man[tag]["advanced_config_name"]
            design_path = json.loads(sp_path.read_text())["design_path"]

            # simulate one per-model relax failure already recorded on disk,
            # one retained unrelaxed PDB, plus a corrupt log line
            dp = Path(design_path)
            (dp / "MPNN").mkdir(parents=True)
            (dp / "MPNN" / "pdl1_s1_model1.pdb").write_text("UNRELAXED")
            (dp / srf.RELAX_FAILURE_LOG).write_text(
                json.dumps({
                    "time_utc": "2026-10-03T00:00:00Z",
                    "stage": "mpnn_relax", "candidate": "pdl1_s1",
                    "model": 1, "error_type": "RelaxationFailure",
                    "error": "missing relaxed pdb BEFORE clean_pdb",
                    "retained_unrelaxed": True,
                    "action": "skipped_model_continue"}) + "\n"
                + "CORRUPT-LINE\n")

            out, action = runner.run_job(
                tag=tag, settings_path=sp_path, advanced_path=ap_path,
                paths=paths, bindcraft_dir=str(bd),
                bindpy=str(Path(td) / "no-such-bindpython"),
                dry_run=False)
            self.assertEqual(action, "RAN")
            self.assertEqual(out["status"], "FAILED")
            self.assertIsNone(out["returncode"])
            self.assertIsNotNone(out["launch_error"])
            self.assertEqual(out["launch_error"]["error_type"],
                             "FileNotFoundError")
            self.assertTrue(out["end_time"])
            self.assertTrue(out["wall_time_s"] >= 0)
            # D-019 record embedding
            self.assertTrue(out["relax_failure_log_present"])
            self.assertEqual(out["relax_failure_count"], 1)
            self.assertEqual(out["relax_failures_by_stage"]["mpnn_relax"], 1)
            self.assertEqual(out["relax_failures_corrupt_lines"], 1)
            self.assertEqual(out["relax_failures"][0]["model"], 1)
            retained = [Path(p).name
                        for p in out["unrelaxed_without_relaxed"]]
            self.assertEqual(retained, ["pdl1_s1_model1.pdb"])
            # terminal manifest really persisted
            on_disk = ckpt.load_manifest(paths, tag)
            self.assertEqual(on_disk["status"], "FAILED")
            self.assertEqual(on_disk["launch_error"]["error_type"],
                             "FileNotFoundError")
            self.assertEqual(on_disk["relax_failure_count"], 1)


class TestOrchestratorPatchStep(unittest.TestCase):
    """D-019 patch is a first-class orchestrator step: dry-run skips it,
    real runs invoke the applier and fail the stage on non-zero rc."""

    def test_step_wired_into_run_and_report(self):
        src = (SCRIPTS / "stage2_orchestrate.py").read_text()
        for needle in ("apply_bindcraft_patch.py",
                       "bindcraft_patch.json",
                       "BINDCRAFT_PATCH_FAIL", "SKIPPED_DRY_RUN",
                       "step_bindcraft_patch"):
            self.assertIn(needle, src)
        # report payload carries patch status (renderer consumes it)
        self.assertIn('"bindcraft_patch": self.state.get("bindcraft_patch")',
                      src)

    def test_dry_run_skips_patch_step_but_records_it(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            repo.mkdir()
            o = orchestrate.Orchestrator(
                repo_dir=str(repo),
                bindcraft_dir=str(Path(td) / "bindcraft"),
                bindpy=sys.executable, root=str(Path(td) / "drive"),
                dry_run=True)
            self.assertTrue(o.step_bindcraft_patch())
            self.assertEqual(o.state["bindcraft_patch"], "SKIPPED_DRY_RUN")


if __name__ == "__main__":
    unittest.main()
