"""Canonical persistent/ephemeral path model for Stage 2.

Reliability consolidation (BUG 009/011): no executable stage may depend on a
variable defined in an earlier interactive notebook cell. Every path comes
from this module, overridable via the STAGE2_PERSISTENT_ROOT environment
variable for tests.

Persistent (survives Colab runtime resets)::

    <root>/
      persistent/{checkpoints,configs,logs,metadata,reports,cache}/
      pdl1_official_smoke/
      egfr_d3_B_conservative/

Ephemeral (erased on runtime reset; safe to rebuild)::

    /content/bindcraft  /content/bindcraft_env  /content/egfr

Stdlib only.
"""
import hashlib
import json
import os
import shutil
from pathlib import Path

DEFAULT_PERSISTENT_ROOT = "/content/drive/MyDrive/BindCraft/stage2_smoke"

BINDCRAFT_DIR = "/content/bindcraft"
ENV_PREFIX = "/content/bindcraft_env"
EGFR_DIR = "/content/egfr"
BINDPY = ENV_PREFIX + "/bin/python"

PERSISTENT_SUBDIRS = ("checkpoints", "configs", "logs", "metadata",
                      "reports", "cache")

JOB_PDL1 = "pdl1_official_smoke"
JOB_EGFR = "egfr_d3_B_conservative"
JOBS = (JOB_PDL1, JOB_EGFR)

CROP_PDB_NAME = "6ARU_chainA_domain3_310-481.pdb"


class Paths:
    """Resolves every Stage-2 location from one persistent root."""

    def __init__(self, root=None):
        root = root or os.environ.get("STAGE2_PERSISTENT_ROOT") \
            or DEFAULT_PERSISTENT_ROOT
        self.root = Path(root)

    # -- persistent directories -------------------------------------------
    @property
    def checkpoints_dir(self):
        return self.root / "persistent" / "checkpoints"

    @property
    def configs_dir(self):
        return self.root / "persistent" / "configs"

    @property
    def logs_dir(self):
        return self.root / "persistent" / "logs"

    @property
    def metadata_dir(self):
        return self.root / "persistent" / "metadata"

    @property
    def reports_dir(self):
        return self.root / "persistent" / "reports"

    @property
    def cache_dir(self):
        return self.root / "persistent" / "cache"

    @property
    def af_cache_dir(self):
        return self.cache_dir / "alphafold"

    @property
    def state_file(self):
        return self.metadata_dir / "orchestration_state.json"

    @property
    def config_manifest(self):
        return self.configs_dir / "config_manifest.json"

    def job_dir(self, tag):
        return self.root / tag

    def manifest_path(self, tag):
        return self.checkpoints_dir / tag / "run_manifest.json"

    def job_log(self, tag):
        return self.logs_dir / f"{tag}.log"

    def job_vram(self, tag):
        return self.logs_dir / f"{tag}_vram.csv"

    def relaxed_dir(self, tag, design_path=None):
        """Relaxed-PDB directory from the ACTUAL design_path (BUG 010: never
        reconstruct expensive-run output paths from notebook assumptions)."""
        base = Path(design_path) if design_path else self.job_dir(tag)
        return base / "Trajectory" / "Relaxed"

    def ensure(self):
        self.root.mkdir(parents=True, exist_ok=True)
        for d in (self.checkpoints_dir, self.configs_dir, self.logs_dir,
                  self.metadata_dir, self.reports_dir, self.cache_dir,
                  self.af_cache_dir):
            d.mkdir(parents=True, exist_ok=True)
        for tag in JOBS:
            self.job_dir(tag).mkdir(parents=True, exist_ok=True)
        return self

    # -- predicates / helpers ---------------------------------------------
    def is_persistent(self, path):
        """True iff path resolves underneath the persistent Drive root."""
        try:
            Path(path).resolve().relative_to(self.root.resolve())
            return True
        except (ValueError, OSError):
            return False

    def read_json(self, path, default=None):
        try:
            with open(path) as fh:
                return json.load(fh)
        except (OSError, json.JSONDecodeError):
            return default

    def write_json(self, path, payload):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w") as fh:
            json.dump(payload, fh, indent=2)
        os.replace(tmp, path)
        return path


def sha256_file(path, buf=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(buf), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text):
    return hashlib.sha256(text.encode()).hexdigest()


def sha256_json(obj):
    return sha256_text(json.dumps(obj, sort_keys=True, separators=(",", ":")))


def copy_file(src, dst):
    """Copy preserving metadata; parent dirs are created."""
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst
