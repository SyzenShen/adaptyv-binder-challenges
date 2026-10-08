#!/usr/bin/env python3
"""Stage-2 smoke orchestrator: one reproducible, restart-safe command.

    python scripts/stage2_orchestrate.py \
        --repo-dir /content/adaptyv-binder-challenges \
        --bindcraft-dir /content/bindcraft \
        --bindpy /content/bindcraft_env/bin/python

Flow (reports/stage2_reliability_consolidation.md §12):

  1. GPU gate (GPU_UNAVAILABLE = controlled blocked state, never CPU)
  2. persistent root + configs
  3. project commit verification
  4. isolated env python must exist (notebook Cell D builds it)
  4b. pinned BindCraft relax-tolerance patch applied/verified (D-019)
  5. preflight gate
  6. AF2 weights (local -> Drive cache -> observable download)
  7. deterministic configs
  8. PDL1 checkpoint valid -> skip; legacy evidence -> adopt; else run once
  9. environment gate: rc==0 AND >=1 relaxed PDB, else STOP (no EGFR)
 10. EGFR smoke (max 3 trajectories), resumable
 11. geometry analysis
 12. persistent JSON+MD report; STOP for human review

No production sampling is ever launched by this script.
Stdlib only.
"""
import argparse
import importlib.util
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from stage2_paths import (Paths, JOB_PDL1, JOB_EGFR, JOBS, BINDPY,
                          BINDCRAFT_DIR, sha256_file)
import stage2_checkpoint as ckpt
import stage2_configure as configure
import stage2_run_job as runner
from stage2_analyze import analyze_job

GPU_BLOCKED_MESSAGE = (
    "No NVIDIA GPU is currently available.\n"
    "This is a compute-allocation/quota condition, not a BindCraft failure.\n"
    "Do not continue on CPU. Reconnect a GPU runtime and re-run this cell; "
    "all completed work is checkpointed on Drive and will be skipped."
)


def query_gpu():
    """nvidia-smi probe -> dict or None. None includes Colab quota denial."""
    if runner.query_nvidia_smi("name") is None:
        return None
    return {
        "name": runner.query_nvidia_smi("name"),
        "vram_total_mib": _int(runner.query_nvidia_smi("memory.total")),
        "vram_free_mib": _int(runner.query_nvidia_smi("memory.free")),
    }


def _int(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def git_commit(repo_dir):
    try:
        p = subprocess.run(["git", "-C", repo_dir, "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=30)
        return p.stdout.strip() if p.returncode == 0 else None
    except OSError:
        return None


def gpu_gate_ok(gpu):
    return bool(gpu) and gpu.get("name")


def pdl1_allows_egfr(manifest, design_path=None):
    """BUG 014/V: environment gate = rc 0 + relaxed PDB only."""
    ok, _ = ckpt.environment_gate(manifest, design_path)
    return ok


def settings_persist_ok(paths, settings_path):
    try:
        with open(settings_path) as fh:
            design_path = json.load(fh)["design_path"]
    except (OSError, KeyError, json.JSONDecodeError):
        return False
    return paths.is_persistent(design_path)


def render_report_md(rep):
    L = ["# Stage 2 smoke report", "",
         f"- generated_utc: {rep['generated_utc']}",
         f"- project_commit: `{rep.get('project_commit')}`",
         f"- bindcraft_commit: `{rep.get('bindcraft_commit')}`",
         f"- bindcraft relax-tolerance patch (D-019): "
         f"{rep.get('bindcraft_patch')}",
         f"- gpu: {rep.get('gpu', {}).get('name')} "
         f"({rep.get('gpu', {}).get('vram_total_mib')} MiB)",
         f"- environment: {rep['flags']['ENVIRONMENT_PASS']}",
         f"- compute_blocked: {rep['flags']['COMPUTE_BLOCKED']}",
         f"- model_run_completed: {rep['flags']['MODEL_RUN_COMPLETED']}",
         f"- computational_filter_pass: "
         f"{rep['flags']['COMPUTATIONAL_FILTER_PASS']}",
         f"- experimentally_validated: "
         f"{rep['flags']['EXPERIMENTALLY_VALIDATED']} (no wet lab; always "
         f"false in this project)", "",
         "## AF2 weights",
         f"- {rep.get('weights', {}).get('action', 'not run')}", "",
         "## Jobs", ""]
    for tag, j in rep.get("jobs", {}).items():
        L += [f"### {tag}",
              f"- status: {j.get('status')}",
              f"- action: {j.get('action')}",
              f"- returncode: {j.get('returncode')}",
              f"- wall_time_s: {j.get('wall_time_s')}",
              f"- peak_vram_mib: {j.get('peak_vram_mib')}",
              f"- relaxed PDBs: {len(j.get('relaxed_pdb_paths', []))}",
              f"- relax failures recorded (per model/trajectory; run "
              f"continues): {j.get('relax_failure_count', 0)}",
              f"- final_design_count (accepted dir; null=not produced): "
              f"{j.get('final_design_count')}",
              f"- legacy: {j.get('legacy', False)}", ""]
    L += ["completed trajectory != successful binder; BindCraft filters and "
          "human review decide acceptance. pLDDT/ipTM/PAE are not affinity.",
          "", "## Geometry", ""]
    for tag, g in rep.get("geometry", {}).items():
        L.append(f"- {tag}: see persistent/reports/{tag}_geometry.json")
    return "\n".join(L) + "\n"


class Orchestrator:
    def __init__(self, *, repo_dir, bindcraft_dir=BINDCRAFT_DIR,
                 bindpy=BINDPY, root=None, dry_run=False,
                 colabdesign_commit=None):
        self.paths = Paths(root)
        self.repo_dir = repo_dir
        self.bindcraft_dir = bindcraft_dir
        self.bindpy = bindpy
        self.dry_run = dry_run
        self.colabdesign_commit = colabdesign_commit
        self.state = {}
        self.jobs = {}

    # -- steps -------------------------------------------------------------
    def step_gpu(self):
        gpu = query_gpu()
        self.state["gpu"] = gpu
        if not gpu_gate_ok(gpu):
            self.state["status"] = "GPU_UNAVAILABLE"
            self._persist_state()
            print(GPU_BLOCKED_MESSAGE)
            return False
        print(f"GPU AVAILABLE: {gpu['name']} "
              f"({gpu['vram_total_mib']} MiB total, "
              f"{gpu['vram_free_mib']} MiB free)")
        return True

    def _persist_state(self):
        self.paths.ensure()
        self.paths.write_json(self.paths.state_file, self.state)

    def step_runtime_config(self):
        """Item 7: persist the resolved runtime paths so every orchestration
        cell can reconstruct them from disk — no cell may depend on a
        variable defined in an earlier interactive cell (the historic
        undefined-name NameError class)."""
        cfg = {
            "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                         time.gmtime()),
            "persistent_root": str(self.paths.root),
            "repo_dir": self.repo_dir,
            "bindcraft_dir": self.bindcraft_dir,
            "bindpy": self.bindpy,
            "dry_run": self.dry_run,
            "env": {
                "STAGE2_PERSISTENT_ROOT":
                    os.environ.get("STAGE2_PERSISTENT_ROOT"),
                "STAGE2_ALLOW_PRODUCTION":
                    os.environ.get(configure.PRODUCTION_ENV_FLAG),
            },
            "jobs": {tag: str(self.paths.job_dir(tag)) for tag in JOBS},
            "note": ("Reconstruct paths from this file (or stage2_paths.py); "
                     "notebook cells must not rely on earlier-cell "
                     "variables."),
        }
        self.paths.write_json(self.paths.runtime_config_file, cfg)
        self.state["runtime_config"] = str(self.paths.runtime_config_file)
        return cfg

    def step_project(self):
        commit = git_commit(self.repo_dir)
        self.state["project_commit"] = commit
        if not commit:
            raise RuntimeError(
                f"cannot determine exact project commit in {self.repo_dir}; "
                "refusing to run unpinned")
        print("PROJECT PIN:", commit)
        return commit

    def step_env(self):
        if not os.path.isfile(self.bindpy):
            self.state["status"] = "ENV_NEEDS_BUILD"
            self._persist_state()
            raise RuntimeError(
                f"isolated env python missing: {self.bindpy}. Run notebook "
                "Cell D (environment build) first.")
        self.bindcraft_commit = git_commit(self.bindcraft_dir)
        self.state["bindcraft_commit"] = self.bindcraft_commit
        print("ENV READY:", self.bindpy, "| BindCraft", self.bindcraft_commit)

    def step_bindcraft_patch(self):
        """Apply (idempotently) / verify the pinned D-019 relax-tolerance patch."""
        if self.dry_run:
            self.state["bindcraft_patch"] = "SKIPPED_DRY_RUN"
            return True
        script = os.path.join(self.repo_dir, "scripts",
                              "apply_bindcraft_patch.py")
        out = self.paths.metadata_dir / "bindcraft_patch.json"
        p = subprocess.run(
            [sys.executable, script,
             "--bindcraft-dir", self.bindcraft_dir,
             "--out", str(out)],
            capture_output=True, text=True)
        print(p.stdout[-2000:])
        if p.returncode != 0:
            print(p.stderr[-4000:])
            self.state["status"] = "BINDCRAFT_PATCH_FAIL"
            self.state["bindcraft_patch"] = "FAIL"
            self._persist_state()
            return False
        try:
            self.state["bindcraft_patch"] = json.loads(
                out.read_text()).get("status")
        except OSError:
            self.state["bindcraft_patch"] = "APPLIED"
        print("BINDCRAFT PATCH:", self.state["bindcraft_patch"])
        return True

    def step_preflight(self):
        out = self.paths.metadata_dir / "preflight.json"
        if self.dry_run:
            self.state["preflight"] = "SKIPPED_DRY_RUN"
            return True
        script = os.path.join(self.repo_dir, "scripts",
                              "stage2_preflight.py")
        p = subprocess.run([self.bindpy, script, "--out", str(out)],
                           capture_output=True, text=True)
        print(p.stdout[-4000:])
        if p.returncode != 0:
            print(p.stderr[-4000:])
            self.state["status"] = "PREFLIGHT_FAIL"
            self._persist_state()
            return False
        self.state["preflight"] = "PASS"
        return True

    def step_weights(self):
        spec = importlib.util.find_spec("ensure_af2_weights")
        if spec is None:
            spec = importlib.util.spec_from_file_location(
                "ensure_af2_weights",
                os.path.join(self.repo_dir, "scripts",
                             "ensure_af2_weights.py"))
        if spec is None or not os.path.exists(spec.origin or ""):
            raise RuntimeError("ensure_af2_weights.py missing in repo")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        params_dir = os.path.join(self.bindcraft_dir, "params")
        result = mod.ensure_weights(
            params_dir=params_dir,
            cache_dir=str(self.paths.af_cache_dir),
            log_dir=str(self.paths.logs_dir),
            dry_run=self.dry_run)
        self.state["weights"] = result
        print("AF2 WEIGHTS:", result.get("action"))
        return result["action"] != "FAIL"

    def step_configure(self):
        self.config_manifest = configure.write_all(
            self.paths, bindcraft_dir=self.bindcraft_dir)
        self.state["configs"] = self.config_manifest
        print("configs written; only max_trajectories differs from defaults")

    def _settings_paths(self, tag):
        m = self.config_manifest[tag]
        return (os.path.join(self.bindcraft_dir, "settings_target",
                             m["target_config_name"]),
                os.path.join(self.bindcraft_dir, m["advanced_config_name"]))

    def step_pdl1(self):
        tag = JOB_PDL1
        sp, ap = self._settings_paths(tag)
        design_path = self.config_manifest[tag]["design_path"]
        expected = configure.expected_hashes(self.config_manifest, tag)

        manifest = ckpt.load_manifest(self.paths, tag)
        if manifest:
            ok, _ = ckpt.validate_checkpoint(
                manifest, expected_hashes=expected,
                bindcraft_commit=self.bindcraft_commit,
                design_path=design_path)
            if ok:
                print("PDL1: CHECKPOINT REUSED")
                self.jobs[tag] = {**manifest, "action": "CHECKPOINT_REUSED"}
                return

        # BUG 013/§13: adopt verifiable pre-consolidation PDL1 evidence.
        # Adoption applies ONLY to a pre-consolidation run that has no
        # manifest at all; a manifest with mismatching config hashes forces a
        # rerun (it is not silently legitimised via legacy adoption).
        if not manifest and ckpt.relaxed_pdbs(design_path):
            manifest = ckpt.adopt_legacy_checkpoint(
                self.paths, tag, design_path=design_path,
                bindcraft_commit=self.bindcraft_commit,
                project_commit=self.state.get("project_commit"),
                evidence_note=("Observed successful PDL1 run persisted to "
                               "Drive, e.g. PDL1_smoke_l65_s909721.pdb; "
                               "environment-gate eligible."))
            if manifest:
                print("PDL1: LEGACY CHECKPOINT ADOPTED -> SKIPPING RERUN")
                self.jobs[tag] = {**manifest, "action": "LEGACY_ADOPTED"}
                return

        print("PDL1: RUNNING (official control, 1 trajectory)")
        manifest, action = runner.run_job(
            tag=tag, settings_path=sp, advanced_path=ap,
            paths=self.paths, bindcraft_dir=self.bindcraft_dir,
            bindpy=self.bindpy,
            project_commit=self.state.get("project_commit"),
            bindcraft_commit=self.bindcraft_commit,
            colabdesign_commit=self.colabdesign_commit,
            gpu_model=(self.state.get("gpu") or {}).get("name"),
            dry_run=self.dry_run)
        self.jobs[tag] = {**manifest, "action": action}

    def step_pdl1_gate(self):
        tag = JOB_PDL1
        m = self.jobs.get(tag) or ckpt.load_manifest(self.paths, tag)
        design_path = self.config_manifest[tag]["design_path"]
        ok = pdl1_allows_egfr(m, design_path)
        self.state["pdl1_environment_gate"] = "PASS" if ok else "FAIL"
        if not ok:
            print("PDL1: FAIL (environment gate) -> EGFR BLOCKED. "
                  "Zero accepted MPNN designs alone is NOT a failure; "
                  "rc==0 + relaxed PDB are required.")
            return False
        print("PDL1: PASS (rc==0 and relaxed PDB present); filter/MPNN "
              "acceptance recorded separately")
        return True

    def step_egfr(self):
        tag = JOB_EGFR
        sp, ap = self._settings_paths(tag)
        assert settings_persist_ok(self.paths, sp), \
            "EGFR design_path must be persistent before launch"
        print("EGFR: RUN OR RESUME (max 3 trajectories)")
        manifest, action = runner.run_job(
            tag=tag, settings_path=sp, advanced_path=ap,
            paths=self.paths, bindcraft_dir=self.bindcraft_dir,
            bindpy=self.bindpy,
            project_commit=self.state.get("project_commit"),
            bindcraft_commit=self.bindcraft_commit,
            colabdesign_commit=self.colabdesign_commit,
            target_pdb_sha256=self._crop_sha(),
            gpu_model=(self.state.get("gpu") or {}).get("name"),
            dry_run=self.dry_run)
        self.jobs[tag] = {**manifest, "action": action}
        print("EGFR:", action, manifest.get("status"))

    def _crop_sha(self):
        from stage2_paths import EGFR_DIR, CROP_PDB_NAME
        p = os.path.join(EGFR_DIR, CROP_PDB_NAME)
        return sha256_file(p) if os.path.exists(p) else None

    def step_analyze(self):
        geometry = {}
        for tag in (JOB_PDL1, JOB_EGFR):
            ok, payload = analyze_job(
                tag, self.paths,
                os.path.join(self.repo_dir, "scripts"))
            geometry[tag] = (payload.get("summary") if ok
                             else payload)
        self.geometry = geometry

    def step_report(self, env_blocked=False):
        jobs_out = {t: self.jobs.get(t) or ckpt.load_manifest(self.paths, t)
                    or {} for t in (JOB_PDL1, JOB_EGFR)}
        pdl1m = jobs_out.get(JOB_PDL1, {})
        egfrm = jobs_out.get(JOB_EGFR, {})
        env_pass = bool(pdl1m) and pdl1_allows_egfr(
            pdl1m, self.config_manifest[JOB_PDL1]["design_path"])
        model_completed = any(
            (m or {}).get("relaxed_pdb_paths") for m in jobs_out.values())
        accepted = egfrm.get("final_design_count")
        report = {
            "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                           time.gmtime()),
            "project_commit": self.state.get("project_commit"),
            "bindcraft_commit": self.state.get("bindcraft_commit"),
            "bindcraft_patch": self.state.get("bindcraft_patch"),
            "gpu": self.state.get("gpu"),
            "weights": self.state.get("weights"),
            "jobs": jobs_out,
            "geometry": {t: ("see persistent/reports/%s_geometry.json" % t)
                         for t in self.geometry},
            "flags": {
                "ENVIRONMENT_PASS": env_pass,
                "COMPUTE_BLOCKED": env_blocked,
                "MODEL_RUN_COMPLETED": model_completed,
                "COMPUTATIONAL_FILTER_PASS": (
                    accepted > 0 if isinstance(accepted, int) else None),
                "EXPERIMENTALLY_VALIDATED": False,
            },
            "notes": ("completed != accepted; pLDDT/ipTM/PAE are not "
                      "experimental affinity; zero accepted MPNN from one "
                      "control trajectory is not an environment failure."),
        }
        self.paths.write_json(self.paths.reports_dir /
                              "stage2_smoke_report.json", report)
        (self.paths.reports_dir / "stage2_smoke_report.md").write_text(
            render_report_md(report))
        return report

    def run(self):
        self.paths.ensure()
        self.step_runtime_config()      # before any gating: survives reset
        if not self.step_gpu():
            self.state.update({"status": "GPU_UNAVAILABLE",
                               "compute_blocked": True})
            self._persist_state()
            return 2                       # controlled blocked state
        self.step_project()
        self.step_env()
        if not self.step_bindcraft_patch():
            return 1
        if not self.step_preflight():
            return 1
        if not self.step_weights():
            return 1
        self.step_configure()
        self.step_pdl1()
        if not self.step_pdl1_gate():
            self._persist_state()
            return 1
        self.step_egfr()
        self.step_analyze()
        rep = self.step_report()
        self.state["status"] = "COMPLETE"
        self._persist_state()
        print("STAGE 2 SMOKE COMPLETE — report at",
              self.paths.reports_dir / "stage2_smoke_report.json")
        return 0


def build_parser():
    """CLI contract (item 4): notebook Cell G passes exactly these flags;
    tests/test_stage2.py asserts the contract stays in sync."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-dir", required=True)
    ap.add_argument("--bindcraft-dir", default=BINDCRAFT_DIR)
    ap.add_argument("--bindpy", default=BINDPY)
    ap.add_argument("--root", default=None)
    ap.add_argument("--dry-run", action="store_true",
                    help="validate everything without launching BindCraft "
                         "or downloading weights")
    ap.add_argument("--colabdesign-commit", default=None)
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)

    orch = Orchestrator(repo_dir=args.repo_dir,
                        bindcraft_dir=args.bindcraft_dir,
                        bindpy=args.bindpy, root=args.root,
                        dry_run=args.dry_run,
                        colabdesign_commit=args.colabdesign_commit)
    return orch.run()


if __name__ == "__main__":
    sys.exit(main())
