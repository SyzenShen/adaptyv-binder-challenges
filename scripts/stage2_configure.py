"""Deterministic Stage-2 target/advanced configuration generation.

Science is FROZEN (see reports/stage2_reliability_consolidation.md §0); this
module only materialises the approved JSONs and records their SHA256. The
advanced smoke file is derived from BindCraft's OWN
default_4stage_multimer.json with exactly one permitted change:
max_trajectories false -> N.

design_path inside the target JSON is the source of truth for output
locations (BUG 010); gates read it back from the persisted config rather
than rebuilding paths from notebook variables.

Stdlib only.
"""
import json
import os

from stage2_paths import JOB_EGFR, JOB_PDL1, EGFR_DIR, BINDCRAFT_DIR

# --- frozen scientific specification (do NOT edit without approval) ------
TARGET_SPEC = {
    JOB_PDL1: {
        "binder_name": "PDL1_smoke",
        "starting_pdb": f"{BINDCRAFT_DIR}/example/PDL1.pdb",
        "chains": "A",
        "target_hotspot_residues": "56",
        "lengths": [65, 65],
        "number_of_final_designs": 1,
        "max_trajectories": 1,
    },
    JOB_EGFR: {
        "binder_name": "EGFR_D3_Bcons",
        "starting_pdb": f"{EGFR_DIR}/6ARU_chainA_domain3_310-481.pdb",
        "chains": "A",
        "target_hotspot_residues": "390,393,399,421,424,431",
        "lengths": [80, 80],
        "number_of_final_designs": 1,
        "max_trajectories": 3,
    },
}

TARGET_FIELDS = ("binder_name", "starting_pdb", "chains",
                 "target_hotspot_residues", "lengths",
                 "number_of_final_designs")

ADVANCED_FOR_TAG = {JOB_PDL1: 1, JOB_EGFR: 3}
ADVANCED_NAME = {1: "advanced_smoke_max1.json",
                 3: "advanced_smoke_max3.json"}


def target_config(tag, design_path):
    """Build the target settings JSON for a job from the frozen spec."""
    spec = TARGET_SPEC[tag]
    cfg = {k: spec[k] for k in TARGET_FIELDS}
    cfg = {"design_path": str(design_path), **cfg}
    return cfg


def build_advanced(default_advanced, max_trajectories):
    """Clone the official advanced default, changing ONLY max_trajectories."""
    base = dict(default_advanced)
    if base.get("max_trajectories") is not False:
        raise ValueError("official default max_trajectories must be false")
    if base.get("predict_initial_guess") is not False:
        raise ValueError("refusing to derive smoke config from a non-default "
                         "advanced settings file")
    base["max_trajectories"] = max_trajectories
    return base


def advanced_diff(default_advanced, smoke_advanced):
    """Only max_trajectories (False -> N) may differ from the official file."""
    return {k: (default_advanced[k], smoke_advanced[k])
            for k in default_advanced
            if default_advanced[k] != smoke_advanced[k]}


def _load_official_default(bindcraft_dir):
    path = os.path.join(
        bindcraft_dir, "settings_advanced", "default_4stage_multimer.json")
    with open(path) as fh:
        return json.load(fh)


def write_all(paths, bindcraft_dir=BINDCRAFT_DIR):
    """Materialise target + advanced configs in the BindCraft tree, persist
    verified copies + hashes, and return the config manifest."""
    settings_target = os.path.join(bindcraft_dir, "settings_target")
    os.makedirs(settings_target, exist_ok=True)

    default_advanced = _load_official_default(bindcraft_dir)
    manifest = {}

    for tag in (JOB_PDL1, JOB_EGFR):
        design_path = str(paths.job_dir(tag)).rstrip("/") + "/"
        tcfg = target_config(tag, design_path)
        tname = f"{tag}.json"
        with open(os.path.join(settings_target, tname), "w") as fh:
            json.dump(tcfg, fh, indent=4)

        n = ADVANCED_FOR_TAG[tag]
        acfg = build_advanced(default_advanced, n)
        diff = advanced_diff(default_advanced, acfg)
        assert diff == {"max_trajectories": (False, n)}, diff
        aname = ADVANCED_NAME[n]
        with open(os.path.join(bindcraft_dir, aname), "w") as fh:
            json.dump(acfg, fh, indent=4)

        # persist verified copies
        t_persist = paths.configs_dir / tname
        a_persist = paths.configs_dir / aname
        with open(t_persist, "w") as fh:
            json.dump(tcfg, fh, indent=4, sort_keys=True)
        with open(a_persist, "w") as fh:
            json.dump(acfg, fh, indent=4, sort_keys=True)

        manifest[tag] = {
            "target_config_name": tname,
            "target_config_sha256": _file_sha(t_persist),
            "advanced_config_name": aname,
            "advanced_config_sha256": _file_sha(a_persist),
            "design_path": tcfg["design_path"],
            "max_trajectories": n,
            "hotspots": tcfg["target_hotspot_residues"],
            "lengths": tcfg["lengths"],
            "only_change_vs_official_default": {"max_trajectories": [False, n]},
        }

    paths.write_json(paths.config_manifest, manifest)
    return manifest


def expected_hashes(manifest, tag):
    """Hash bundle a checkpoint must match for a given job."""
    m = manifest[tag]
    return {"target_config_sha256": m["target_config_sha256"],
            "advanced_config_sha256": m["advanced_config_sha256"]}


def _file_sha(path):
    from stage2_paths import sha256_file
    return sha256_file(path)
