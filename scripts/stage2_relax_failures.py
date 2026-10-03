"""Parse and summarize per-model PyRosetta relaxation failure records.

The D-019 upstream patch (patches/bindcraft-7713aa0-relax-tolerance.patch)
appends one JSON object per line to ``<design_path>/relax_failures.jsonl``
whenever relaxation of a trajectory or MPNN model fails:
the failure is recorded, the unrelaxed PDB is retained, and BindCraft
continues instead of terminating.

This module is the local/harness-side reader. Stdlib only; a corrupt line
is counted (``corrupt_lines``) instead of aborting the summary.
"""
import json
import os

RELAX_FAILURE_LOG = "relax_failures.jsonl"
_STAGES = ("trajectory_relax", "mpnn_relax", "mpnn_finalize")


def failure_log_path(design_path):
    return os.path.join(design_path, RELAX_FAILURE_LOG)


def load_records(design_path):
    """Return (records, corrupt_lines). Missing log -> ([], 0)."""
    path = failure_log_path(design_path)
    records, corrupt = [], 0
    if not os.path.isfile(path):
        return records, corrupt
    with open(path, errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                corrupt += 1
                continue
            if isinstance(obj, dict):
                records.append(obj)
            else:
                corrupt += 1
    return records, corrupt


def unrelaxed_without_relaxed(design_path):
    """Unrelaxed MPNN complex PDBs with no same-named relaxed counterpart.

    Informational: after a failed relaxation the unrelaxed PDB is retained.
    Upstream may also retain unrelaxed PDBs when ``remove_unrelaxed_complex``
    is disabled, so this list is not by itself a failure count.
    """
    mpnn_dir = os.path.join(design_path, "MPNN")
    relaxed_dir = os.path.join(design_path, "MPNN", "Relaxed")
    if not os.path.isdir(mpnn_dir):
        return []
    relaxed_names = set()
    if os.path.isdir(relaxed_dir):
        relaxed_names = {f for f in os.listdir(relaxed_dir)
                         if f.endswith(".pdb")}
    retained = []
    for name in sorted(os.listdir(mpnn_dir)):
        if not name.endswith(".pdb"):
            continue
        if name not in relaxed_names:
            retained.append(os.path.join(mpnn_dir, name))
    return retained


def summarize(design_path):
    """Read-only summary embedded in run_manifest.json."""
    records, corrupt = load_records(design_path)
    by_stage = {s: 0 for s in _STAGES}
    by_error_type = {}
    for rec in records:
        stage = rec.get("stage")
        if stage in by_stage:
            by_stage[stage] += 1
        err = rec.get("error_type") or "Unknown"
        by_error_type[err] = by_error_type.get(err, 0) + 1
    return {
        "log_path": failure_log_path(design_path),
        "log_present": os.path.isfile(failure_log_path(design_path)),
        "relax_failure_count": len(records),
        "relax_failures_by_stage": by_stage,
        "relax_failures_by_error_type": by_error_type,
        "relax_failures_corrupt_lines": corrupt,
        "relax_failures": records,
        "unrelaxed_without_relaxed": unrelaxed_without_relaxed(design_path),
    }
