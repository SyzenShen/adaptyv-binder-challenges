"""Stage 2 tests: Domain III crop PDB, BindCraft config translation,
hotspot-envelope containment, smoke notebook validity, isolated-environment
fix for failure 001 (Colab JAX 0.11.1 / xla_bridge removal), pre-flight gate,
run analyzer.

Stdlib only (no third-party dependency at test time).
"""
import ast
import importlib.util
import json
import re
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
        cls.code_cells = [
            "".join(c["source"]) for c in cls.nb["cells"]
            if c["cell_type"] == "code"]
        cls.code_text = "\n".join(cls.code_cells)

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

    def _fake_jax_stack(self, backend, platforms, value=None):
        class FakeScalar:
            def block_until_ready(self):
                return self

            def __float__(self):
                return float(2048 ** 3) if value is None else value

            def devices(self):
                return {TestPreflightDeviceSemantics.FakeDevice(p)
                        for p in platforms}    # set-valued, like real JAX

        class FakeMat:
            def __matmul__(self, other):
                return self

            def sum(self):
                return FakeScalar()

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
        self.assertTrue(info["numerically_correct"])
        self.assertEqual(info["backend"], "gpu")
        self.assertEqual(info["sum"], float(2048 ** 3))
        self.assertTrue(info["gpu_devices"])

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

    def test_matmul_check_rejects_wrong_numbers(self):
        jax, jnp = self._fake_jax_stack("gpu", ["gpu"], value=1.0)
        ok, detail, info = self.pf.run_gpu_matmul_check(jax, jnp)
        self.assertFalse(ok)
        self.assertIn("numerically wrong", detail)
        self.assertFalse(info["numerically_correct"])


class TestNotebookIsolatedEnvFix(unittest.TestCase):
    """The notebook must create a fresh Colab runtimes reproducible env
    matching upstream; it must not accept the preinstalled JAX 0.11.x.
    """
    @classmethod
    def setUpClass(cls):
        nb = json.loads((CLOUD / "stage2_bindcraft_smoke.ipynb").read_text())
        cls.cells = nb["cells"]
        cls.code = [
            "".join(c["source"]) for c in cls.cells if c["cell_type"] == "code"]
        cls.text = "\n".join(cls.code)

    def indices(self, needle):
        return [i for i, s in enumerate(self.code) if needle in s]

    def test_upstream_env_spec_present(self):
        for needle in ("Miniforge3-Linux-x86_64.sh", "python=3.10",
                       "jax=0.6.0", "jaxlib=0.6.0=*cuda*",
                       "CONDA_OVERRIDE_CUDA", "'12.6'", "numpy<2.0.0",
                       "flax<0.10.0", "-c", "conda-forge", "nvidia"):
            self.assertIn(needle, self.text, needle)

    def test_colabdesign_pinned_and_no_deps_inside_env(self):
        self.assertIn(
            "e31a56fe1d9b4de25c8697f3a28b75892941cc72", self.text)
        self.assertRegex(
            self.text,
            r"ENV_PREFIX\}/bin/pip', 'install', '--no-deps',\s*"
            r"f?'git\+https://github\.com/sokrypton/ColabDesign\.git@")
        # the old broken attempt-001 command must never come back
        self.assertNotIn(
            "pip install -q git+https://github.com/sokrypton/ColabDesign.git",
            self.text)

    def test_kernel_never_uses_preinstalled_jax_or_colabdesign(self):
        for i, src in enumerate(self.code):
            self.assertIsNone(
                re.search(r"^\s*(?:import|from)\s+(jax|colabdesign)\b",
                          src, re.M),
                f"system-kernel jax/colabdesign import in code cell {i}")

    def test_compute_subprocesses_use_isolated_python(self):
        self.assertIn("BINDPY = f'{ENV_PREFIX}/bin/python'",
                      self.text)
        self.assertIn("[BINDPY, '-u', 'bindcraft.py'", self.text)

    def test_preflight_uploaded_and_runs_before_weights_and_pdl1(self):
        self.assertTrue(
            any("'/content/bindcraft_preflight.py'" in s for s in self.code))
        gate = self.indices("bindcraft_preflight.py")[0]
        weights = self.indices("alphafold_params_2022-12-06.tar")[0]
        pdl1 = self.indices("'pdl1_official_smoke'")[0]
        self.assertLess(gate, weights)
        self.assertLess(weights, pdl1)

    def test_preflight_gate_asserts_hard_stop(self):
        gate_cells = self.indices("PRE-FLIGHT FAILED")
        self.assertTrue(gate_cells)
        self.assertIn("assert pfp.returncode == 0 and pf['passed']",
                      self.code[gate_cells[0]])

    def test_pdl1_gate_blocks_egfr(self):
        pdl1_gate = self.indices("PDL1 relaxed trajectories")[0]
        egfr = self.indices("job_records['egfr_d3_B_conservative']")[0]
        self.assertLess(pdl1_gate, egfr)

    def test_scientific_settings_untouched(self):
        self.assertIn("'target_hotspot_residues': '390,393,399,421,424,431'",
                      self.text)
        self.assertIn("'lengths': [80, 80]", self.text)
        self.assertIn("'target_hotspot_residues': '56'", self.text)
        self.assertIn("'lengths': [65, 65]", self.text)
        self.assertIn("assert diff == {'max_trajectories': (False, n)}",
                      self.text)


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
