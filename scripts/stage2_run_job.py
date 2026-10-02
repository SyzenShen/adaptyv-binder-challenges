"""Run one BindCraft job observably, with persistent checkpoint lifecycle.

- Refuses to launch unless the target config's design_path is on persistent
  storage (BUG: losing an expensive run to a runtime reset).
- Writes run_manifest.json (PLANNED -> RUNNING -> terminal) BEFORE/AFTER the
  process; logs and VRAM samples land on Drive.
- A valid COMPLETED checkpoint means the expensive job is skipped.
- Process is fully observed (returncode, wall time, peak VRAM, log); OOM is
  classified from the log; failed/interrupted history is retained.

Stdlib only. The actual BindCraft subprocess uses the isolated env python.
"""
import csv
import json
import os
import re
import subprocess
import threading
import time

from stage2_paths import BINDPY, BINDCRAFT_DIR, sha256_file
import stage2_checkpoint as ckpt

OOM_PATTERNS = ("out of memory", "resource exhausted", "cuda_error_out_of_memory")
SEED_RE = re.compile(r"_s(\d+)(?:_model\d+)?\.pdb$")


def query_nvidia_smi(field):
    try:
        p = subprocess.run(
            ["nvidia-smi", f"--query-gpu={field}",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if p.returncode != 0:
        return None
    lines = p.stdout.strip().splitlines()
    return lines[0].strip() if lines else None


def _poll_vram(csv_path, stop_evt):
    with open(csv_path, "w", newline="") as fh:
        w = csv.writer(fh)
        while not stop_evt.is_set():
            used = query_nvidia_smi("memory.used")
            w.writerow([int(time.time()), used or ""])
            fh.flush()
            stop_evt.wait(2)


def _peak_vram(csv_path):
    peak = None
    try:
        with open(csv_path) as fh:
            for row in csv.reader(fh):
                if len(row) >= 2 and row[1].strip().isdigit():
                    v = int(row[1])
                    peak = v if peak is None else max(peak, v)
    except OSError:
        pass
    return peak


def _classify(returncode, log_text):
    if returncode == 0:
        return "COMPLETED"
    low = (log_text or "").lower()
    if any(p in low for p in OOM_PATTERNS):
        return "OOM"
    if returncode and returncode < 0:
        return "INTERRUPTED"          # killed by signal
    return "FAILED"


def _seed_from(path):
    m = SEED_RE.search(os.path.basename(path))
    return int(m.group(1)) if m else None


def _count_final_designs(design_path):
    """Count BindCraft-accepted designs without inventing acceptance logic.
    Returns None when no accepted-design directory exists."""
    accepted = os.path.join(design_path, "Accepted")
    if not os.path.isdir(accepted):
        return None
    n = 0
    for _root, _dirs, files in os.walk(accepted):
        n += sum(1 for f in files
                 if f.endswith((".pdb", ".fasta", ".fa")))
    return n or 0


def run_job(*, tag, settings_path, advanced_path, paths,
            bindcraft_dir=BINDCRAFT_DIR, bindpy=BINDPY, env=None,
            project_commit=None, bindcraft_commit=None,
            colabdesign_commit=None, target_pdb_sha256=None,
            gpu_model=None, force=False, dry_run=False):
    """Run/resume one job. Returns (manifest, action) with action in
    {SKIPPED, DRY_RUN, RAN}."""
    with open(settings_path) as fh:
        tcfg = json.load(fh)
    with open(advanced_path) as fh:
        acfg = json.load(fh)
    design_path = tcfg["design_path"]

    # BUG X: expensive output must be persistent BEFORE launch.
    if not paths.is_persistent(design_path):
        raise PermissionError(
            f"design_path {design_path!r} is NOT under persistent root "
            f"{paths.root}; refusing to run {tag}")
    os.makedirs(design_path, exist_ok=True)

    expected = {"target_config_sha256": sha256_file(settings_path),
                "advanced_config_sha256": sha256_file(advanced_path)}

    prior = ckpt.load_manifest(paths, tag)
    if prior and not force:
        ok, reasons = ckpt.validate_checkpoint(
            prior, expected_hashes=expected,
            bindcraft_commit=bindcraft_commit, design_path=design_path)
        if ok:
            print(f"{tag.upper()} CHECKPOINT VALID\n"
                  f"SKIPPING EXPENSIVE {tag.upper()} RERUN")
            return prior, "SKIPPED"

    lengths = tcfg.get("lengths") or []
    manifest = ckpt.new_manifest(
        run_id=tag,
        job_type=tag,
        project_commit=project_commit,
        bindcraft_commit=bindcraft_commit,
        colabdesign_commit=colabdesign_commit,
        target_pdb_sha256=target_pdb_sha256,
        target_crop="310-481" if tag != "pdl1_official_smoke" else None,
        hotspots=tcfg.get("target_hotspot_residues"),
        binder_length=lengths[0] if lengths else None,
        advanced_config_sha256=expected["advanced_config_sha256"],
        target_config_sha256=expected["target_config_sha256"],
        gpu_model=gpu_model,
        design_path=design_path,
        log_path=str(paths.job_log(tag)),
    )
    if prior:
        manifest["attempts"].append({"previous_status": prior.get("status"),
                                     "previous_manifest": dict(prior)})
    manifest["status"] = "RUNNING"
    manifest["start_time"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    ckpt.save_manifest(paths, tag, manifest, force=True)

    if dry_run:
        manifest["status"] = "PLANNED"
        manifest["notes"] = "dry_run: BindCraft subprocess not launched"
        ckpt.save_manifest(paths, tag, manifest, force=True)
        return manifest, "DRY_RUN"

    log_path, vram_path = paths.job_log(tag), paths.job_vram(tag)
    stop = threading.Event()
    th = threading.Thread(target=_poll_vram, args=(vram_path, stop),
                          daemon=True)
    th.start()
    t0 = time.time()
    with open(log_path, "w") as lf:
        proc = subprocess.run(
            [bindpy, "-u", "bindcraft.py",
             "--settings", settings_path,
             "--filters", "./settings_filters/default_filters.json",
             "--advanced", advanced_path],
            cwd=bindcraft_dir, stdout=lf, stderr=subprocess.STDOUT,
            text=True, env=env or os.environ.copy())
    wall = round(time.time() - t0, 1)
    stop.set()
    th.join(timeout=5)

    log_text = ""
    try:
        with open(log_path, errors="replace") as fh:
            log_text = fh.read()[-200000:]
    except OSError:
        pass

    relaxed = [str(p) for p in ckpt.relaxed_pdbs(design_path)]
    status = _classify(proc.returncode, log_text)
    manifest.update({
        "status": status,
        "end_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "returncode": proc.returncode,
        "wall_time_s": wall,
        "peak_vram_mib": _peak_vram(vram_path),
        "relaxed_pdb_paths": relaxed,
        "relaxed_pdb_sha256": {p: sha256_file(p) for p in relaxed},
        "random_seed": _seed_from(relaxed[0]) if relaxed else None,
        "final_design_count": _count_final_designs(design_path),
    })
    ckpt.save_manifest(paths, tag, manifest, force=True)
    return manifest, "RAN"
