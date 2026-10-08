# Reproducibility & provenance

The rule: given any candidate produced by this workflow, you must be able to
say exactly which code, environment and inputs produced it. Versions are
**pinned**, observed values are **recorded per run**, and nothing is
inferred after the fact.

## Pinned inputs (checked into the repo)

| Item | Value | Where enforced |
|---|---|---|
| BindCraft commit | `7713aa0d0d351e4117a8befeb8541f3a8ebd3368` | notebook Cell D + `apply_bindcraft_patch.py` |
| ColabDesign commit | `e31a56fe1d9b4de25c8697f3a28b75892941cc72` | notebook Cell D (`pip --no-deps`) |
| Project pin (`PROJECT_PIN`) | the notebook Cell C literal; bumped to the final code commit of each checkpoint series | notebook Cell C + `tests/test_stage2.py::test_frozen_pins_present` |
| Python | `3.10.x` in the isolated env | conda spec, preflight check 1 |
| JAX / jaxlib | `0.6.0` / `0.6.0=*cuda*` (CUDA 12.6 override) | conda spec, preflight checks 2–3 |
| numpy / flax | `<2.0.0` / `<0.10.0` | conda spec, preflight |
| PyRosetta | quarterly release wheel (`--find-links west.rosettacommons.org/...release.cxx11thread.serialization`); exact version is **observed and recorded**, not pinned | notebook Cell D + preflight JSON |
| AF2 parameters | `alphafold_params_2022-12-06.tar`, exactly the 15 official `.npz` files | `ensure_af2_weights.py` (validates the exact set; `done.txt` alone is never trusted) |
| Patch | `patches/bindcraft-7713aa0-relax-tolerance.patch` (DECISIONS D-019) | `apply_bindcraft_patch.py`, see [PATCHES.md](../patches/PATCHES.md) |
| Target sequences | `data/raw/targets.manifest.json` (URL + bytes + SHA256 per file) | `download_targets.py` |
| Target structure | 6ARU chain A; crop `data/processed/6ARU_chainA_domain3_310-481.pdb` (UniProt 310–481, 172 residues) | `build_target_residue_map.py` cross-checks against `residue_map.csv` |
| Residue maps | `data/processed/residue_map.csv` (UniProt↔6ARU auth), `data/processed/target_residue_map.json` (BindCraft local↔biological, SHA256-stamped) | analyzer refuses to run without them |

## What every run records (in Google Drive, `persistent/`)

- `metadata/runtime_config.json` — persistent root, repo dir, BindCraft dir,
  isolated python, jobs mapping. Written before any gate so a dead runtime
  can be reconstructed from disk.
- `metadata/preflight.json` — observed Python/JAX/jaxlib/numpy/flax/
  ColabDesign/PyRosetta versions, GPU name + VRAM, driver, CUDA backend,
  matmul check result.
- `metadata/weights.json` — downloader tool chain attempts, URL, byte count,
  elapsed, SHA-validated 15-file set.
- `metadata/bindcraft_patch.json` — pre/post SHA256 of every patched file.
- `manifests/<tag>.json` — per job: status (`COMPLETE / PARTIAL / FAILED /
  OOM / INTERRUPTED`, with `raw_status`), target + advanced-config SHA256,
  BindCraft commit, `final_design_count`, relax-failure summary.
- `logs/` — full child-process stdout/stderr.
- `reports/stage2_smoke_report.json` (+ `.md`) — the human-readable summary.

Env versions are observed, never assumed: the preflight gate reads what is
actually installed and refuses to continue on mismatch.

## How to reproduce one candidate

1. Check out the repo at the `PROJECT_PIN` recorded in the report.
2. Recreate the env (notebook Cell D) — conda spec + pinned commits above.
3. Confirm `preflight.json` matches the versions in the candidate's manifest.
4. Re-run the smoke (Cell G); checkpoint validation adopts a prior PDL1 run
   only if manifest status, config SHA256s and BindCraft commit all match.

If any provenance file is missing, treat the candidate as
`LEGACY_CHECKPOINT` with unverified source — do not promote it.

## Known gaps

- PyRosetta's quarterly wheel means relaxation runs are not bit-reproducible
  across install dates; the installed version is recorded per run so the
  difference is at least visible.
- The Colab host GPU is whatever Colab assigns (T4 during all runs so far);
  it is recorded, not controllable.
