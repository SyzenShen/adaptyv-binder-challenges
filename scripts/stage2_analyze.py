"""Geometry analysis wrapper for Stage 2.

The geometry engine remains analyze_bindcraft_run.py (no logic duplicated).
This wrapper runs it for one job directory, writes the JSON into the
persistent reports dir, and returns the parsed summary. Stdlib only.
"""
import json
import os
import subprocess
import sys


def analyze_job(tag, paths, repo_scripts_dir, python_exe=None):
    """Return (ok, payload_or_error). Never raises on analysis failure so an
    unanalysable structure does not abort orchestration."""
    design_path = None
    manifest = paths.read_json(paths.manifest_path(tag))
    if manifest:
        design_path = manifest.get("design_path")
    run_dir = design_path or str(paths.job_dir(tag))
    out = paths.reports_dir / f"{tag}_geometry.json"
    engine = os.path.join(repo_scripts_dir, "analyze_bindcraft_run.py")
    cmd = [python_exe or sys.executable, engine,
           "--run-dir", run_dir, "--out", str(out)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        return False, {"analysis_error": p.stderr[-2000:] or p.stdout[-2000:]}
    try:
        return True, json.loads(out.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return False, {"analysis_error": repr(exc)}
