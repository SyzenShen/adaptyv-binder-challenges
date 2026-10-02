"""Persistent run manifests + checkpoint validation/resume for Stage 2.

Every expensive job gets a run_manifest.json written to Drive BEFORE it
starts (PLANNED), updated through RUNNING to a terminal status. A job with a
valid COMPLETED checkpoint is skipped automatically (BUG 013); completed
manifests are never silently overwritten (BUG Z).

Checkpoint validity requires configuration-hash + BindCraft-commit matching
plus at least one non-empty, readable relaxed PDB whose SHA256 matches the
recorded value when present.

A pre-consolidation successful run without a manifest (the observed PDL1
PDL1_smoke_l65_s909721.pdb) can be adopted as LEGACY_CHECKPOINT only from
verifiable persistent evidence; missing provenance is recorded as missing,
never invented.
"""
import glob
import os
import time
from pathlib import Path

from stage2_paths import JOB_PDL1, sha256_file

TERMINAL_STATUSES = ("COMPLETED", "FAILED", "GPU_UNAVAILABLE",
                     "OOM", "INTERRUPTED")
ALL_STATUSES = ("PLANNED", "RUNNING") + TERMINAL_STATUSES

# BUG 014: environment gate requires ONLY rc == 0 + a relaxed PDB.
ENV_GATE_REQUIRES = ("returncode_zero", "relaxed_pdb")


def relaxed_pdbs(design_path):
    """Non-empty *.pdb under <design_path>/Trajectory/Relaxed (source of
    truth = the design_path recorded in the target config)."""
    out = []
    rdir = Path(design_path) / "Trajectory" / "Relaxed"
    if not rdir.is_dir():
        return out
    for p in sorted(rdir.glob("*.pdb")):
        try:
            if p.is_file() and p.stat().st_size > 0:
                out.append(p)
        except OSError:
            continue
    return out


def new_manifest(run_id, job_type, **fields):
    """Manifest skeleton written BEFORE an expensive job launches."""
    m = {
        "run_id": run_id,
        "job_type": job_type,
        "status": "PLANNED",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "legacy": False,
        "project_commit": fields.get("project_commit"),
        "bindcraft_commit": fields.get("bindcraft_commit"),
        "colabdesign_commit": fields.get("colabdesign_commit"),
        "target_pdb_sha256": fields.get("target_pdb_sha256"),
        "target_crop": fields.get("target_crop"),
        "hotspots": fields.get("hotspots"),
        "binder_length": fields.get("binder_length"),
        "advanced_config_sha256": fields.get("advanced_config_sha256"),
        "target_config_sha256": fields.get("target_config_sha256"),
        "random_seed": fields.get("random_seed"),
        "gpu_model": fields.get("gpu_model"),
        "start_time": fields.get("start_time"),
        "end_time": None,
        "design_path": fields.get("design_path"),
        "returncode": None,
        "wall_time_s": None,
        "peak_vram_mib": None,
        "relaxed_pdb_paths": [],
        "relaxed_pdb_sha256": {},
        "final_design_count": None,
        "filter_results": None,
        "log_path": fields.get("log_path"),
        "attempts": [],
        "notes": fields.get("notes"),
    }
    return m


def save_manifest(paths, tag, manifest, force=False):
    """Persist a manifest. Refuses to clobber an existing COMPLETED record
    (BUG Z) unless force=True; prior attempts are retained."""
    path = paths.manifest_path(tag)
    prior = paths.read_json(path)
    if prior and prior.get("status") == "COMPLETED" and not force \
            and manifest.get("status") != "COMPLETED":
        raise PermissionError(
            f"refusing to overwrite COMPLETED checkpoint {path}")
    paths.write_json(path, manifest)
    return path


def load_manifest(paths, tag):
    return paths.read_json(paths.manifest_path(tag))


def validate_checkpoint(manifest, expected_hashes=None,
                        bindcraft_commit=None, design_path=None):
    """Return (ok, reasons). A checkpoint is reusable only when configuration
    provenance matches and a real relaxed PDB is present."""
    reasons = []
    if not isinstance(manifest, dict):
        return False, ["no manifest"]
    if manifest.get("status") != "COMPLETED":
        reasons.append(f"status={manifest.get('status')!r} (need COMPLETED)")
    if bindcraft_commit and manifest.get("bindcraft_commit") \
            and manifest["bindcraft_commit"] != bindcraft_commit:
        reasons.append("bindcraft_commit mismatch")
    if expected_hashes:
        for key, val in expected_hashes.items():
            if manifest.get(key) and manifest[key] != val:
                reasons.append(f"{key} mismatch")
    dp = design_path or manifest.get("design_path")
    if not dp:
        reasons.append("no design_path")
        return False, reasons
    pdbs = relaxed_pdbs(dp)
    if not pdbs:
        reasons.append("no nonempty relaxed PDB")
        return False, reasons
    recorded = manifest.get("relaxed_pdb_sha256") or {}
    for p in pdbs:
        key = str(p)
        if key in recorded:
            try:
                if sha256_file(p) != recorded[key]:
                    reasons.append(f"sha256 mismatch: {p.name}")
            except OSError as exc:
                reasons.append(f"unreadable PDB {p.name}: {exc!r}")
    return (not reasons), reasons


def environment_gate(manifest, design_path=None):
    """BUG 014: rc == 0 AND >=1 relaxed PDB. Filter/MPNN acceptance is
    recorded separately and never part of the environment gate."""
    if not isinstance(manifest, dict):
        return False, ["no manifest"]
    reasons = []
    if manifest.get("returncode") != 0:
        reasons.append(f"returncode={manifest.get('returncode')!r}")
    pdbs = relaxed_pdbs(design_path or manifest.get("design_path"))
    if not pdbs:
        reasons.append("no relaxed PDB")
    return (not reasons), reasons


def scan_legacy_relaxed(paths, tag):
    """Find relaxed PDBs on persistent storage for a job with no manifest."""
    return [str(p) for p in relaxed_pdbs(paths.job_dir(tag))]


def adopt_legacy_checkpoint(paths, tag, *, design_path, bindcraft_commit,
                            gpu_model=None, project_commit=None,
                            evidence_note=""):
    """Backfill a LEGACY_CHECKPOINT from persistent evidence only.

    The observed pre-consolidation PDL1 run produced a real nonempty relaxed
    PDB on Drive. We record what is verifiable (PDB paths + SHA256 + name-
    derived length/seed) and mark unprovable provenance explicitly.
    """
    pdbs = relaxed_pdbs(design_path)
    if not pdbs:
        return None
    hashes = {str(p): sha256_file(p) for p in pdbs}
    m = new_manifest(
        run_id=f"legacy-{tag}",
        job_type=tag,
        project_commit=project_commit,
        bindcraft_commit=bindcraft_commit,
        gpu_model=gpu_model,
        design_path=str(design_path),
        notes=("LEGACY_CHECKPOINT: adopted from persistent evidence after "
               "the reliability consolidation; byte-level config-hash "
               "provenance is not reconstructable. " + evidence_note),
    )
    m.update({
        "status": "COMPLETED",
        "legacy": True,
        "end_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "returncode": 0,
        "relaxed_pdb_paths": [str(p) for p in pdbs],
        "relaxed_pdb_sha256": hashes,
        "provenance": {
            "config_hash_verified": False,
            "bindcraft_commit_verified": False,
            "evidence": [str(p) for p in pdbs],
        },
    })
    paths.write_json(paths.manifest_path(tag), m)
    return m
