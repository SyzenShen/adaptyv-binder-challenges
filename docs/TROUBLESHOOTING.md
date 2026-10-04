# Troubleshooting

Full solutions with the real error output we hit. README gives quick
pointers; this file holds the details. Ordered roughly by where in a run
they appear.

**Will I lose my results?** — the first thing to check is almost always
"no": every expensive artifact is written to Google Drive
(`persistent/`), so a runtime reset costs you setup time, not results.

---

## 1. `AttributeError: module 'jax.lib' has no attribute 'xla_bridge'`

### Symptom
Deep inside ColabDesign, during `clear_mem()`:
```
AttributeError: module 'jax.lib' has no attribute 'xla_bridge'
```

### Cause
Colab's preinstalled JAX (0.11.x at the time) removed `jax.lib.xla_bridge`,
which ColabDesign's memory cleanup still uses. BindCraft's own installer
pins `jax<=0.6.0` for exactly this reason.

### Confirm it
Inside the **kernel** python: `import jax; jax.__version__` → newer than
0.6.0. That is the system python, not the isolated env.

### Fix
Rebuild the isolated env (notebook Cell D): Python 3.10 + `jax=0.6.0`,
`jaxlib=0.6.0=*cuda*` from conda-forge. Run everything through `BINDPY`,
never the kernel python.

### Do not do this
Do not "fix" it by monkey-patching `clear_mem()` or upgrading ColabDesign.
Upstream guidance pins the environment; the pinned combination is what was
tested.

### Will I lose my results?
No. The env is rebuildable; Drive artifacts are untouched.

---

## 2. `TypeError: 'set' object is not subscriptable`

### Symptom
Preflight dies at the GPU-residency check:
```
TypeError: 'set' object is not subscriptable
```

### Cause
JAX `Array.devices()` returns a **set** of devices. Older preflight code
indexed it like a list (`devices()[0]`).

### Confirm it
`type(jax.numpy.ones(1).devices())` → `set`.

### Fix
Iterate the set (or `sorted(...)`) instead of indexing. Fixed in
`stage2_preflight.py` and covered by a regression test with a set-valued
fake.

### Do not do this
Do not cast blindly to list and take `[0]` without checking residency
semantics — the point of the check is that the result lives on a GPU
device.

### Will I lose my results?
No.

---

## 3. Weight download hangs for 30 minutes with zero files

### Symptom
Cell F prints a progress line every interval, `params/` stays empty, no
error is ever raised.

### Cause
The old code launched a downloader with an unobserved `subprocess.Popen`
and looped on a timeout. stderr was lost; a dead download looked identical
to a slow one.

### Confirm it
The old design had no returncode/log capture; the current
`ensure_af2_weights.py` writes a downloader log and returncode — if those
are absent, you ran the old code.

### Fix
Cell F now uses the observable downloader chain (`aria2c -c` → `curl -C -`
→ `wget -c`) with per-tool logs, byte counts, elapsed time, and a hard
failure when the child exits non-zero. Partial files are resumed.

### Do not do this
Do not "wait another 30 minutes". Do not delete a partial tarball unless
validation proved it corrupt.

### Will I lose my results?
No — partial downloads resume from where they stopped.

---

## 4. `assert 14 == 15` — wrong `.npz` count after download

### Symptom
Weight validation fails with 14 (or 16) `.npz` files, or an old
`done.txt` claims success while files are missing.

### Cause
A stale or wrong expected count / a `done.txt` from a previous incomplete
run. `done.txt` alone was never a reliable authority.

### Confirm it
`ls params/*.npz | wc -l` and compare against the official 15-file list
inside `ensure_af2_weights.py`.

### Fix
Delete only the incomplete set, re-run Cell F (it resumes the download).
The tool validates the exact official file set and ignores stale
`done.txt`.

### Do not do this
Do not edit `done.txt` by hand or lower the expected count.

### Will I lose my results?
No.

---

## 5. `unrecognized arguments: --out`

### Symptom
A notebook cell fails when calling a script:
```
unrecognized arguments: --out
```

### Cause
CLI drift: the notebook passed a flag the script had stopped accepting
(this actually happened to the analyzer).

### Confirm it
`python3 scripts/<script>.py --help`. A contract test
(`TestNotebookCLIContract`) now parses the notebook AST and asserts every
flag is accepted, so this fails in CI first.

### Fix
Update the script's `build_parser()` (or the caller) and re-run tests.

### Do not do this
Do not add a catch-all `parse_known_args` — silent flag swallowing hides
real drift.

### Will I lose my results?
No.

---

## 6. `NameError: name 'RUNROOT' is not defined`

### Symptom
A later notebook cell references a variable that "was definitely defined
earlier".

### Cause
Runtime reset: Colab wiped `/content` and all kernel variables. The
notebook depended on implicit session state.

### Confirm it
The variable is only defined in another cell; the runtime just restarted.

### Fix
The notebook reconstructs paths from disk
(`persistent/metadata/runtime_config.json`, written before any gate). Re-run
cells A→B, then the failing cell.

### Do not do this
Do not hardcode `/content/...` paths that assume the old session.

### Will I lose my results?
No — Drive artifacts survive; only kernel variables vanish.

---

## 7. "PDL1 output is missing" (it usually is not)

### Symptom
You cannot find the PDL1 relaxed PDB where you guessed it would be.

### Cause
Guessed paths. The design directory is recorded in the job manifest, not
fixed by convention.

### Confirm it
```
python3 - <<'PY'
import json
m = json.load(open('persistent/manifests/PDL1.json'))
print(m['status'], m.get('design_path'))
PY
```

### Fix
Use `manifest['design_path']`. The orchestrator and Cell H already do.

### Do not do this
Do not re-run the ~30-minute PDL1 gate just because you could not find the
file. Checkpoint validation will skip it if it is valid.

### Will I lose my results?
No — and re-running would skip the completed checkpoint anyway.

---

## 8. `Cannot connect to GPU backend` / quota exhausted

### Symptom
Colab refuses to allocate a GPU runtime (usage-limit dialog).

### Cause
Colab compute quota. Not a bug in this repo.

### Confirm it
The dialog itself; or Cell A prints `COMPUTE_QUOTA_BLOCKED`.

### Fix
Stop for now; reconnect a GPU runtime later and re-run cells A→G. The
orchestrator treats GPU loss as a normal recoverable event (exit code 2,
`GPU_UNAVAILABLE` / `COMPUTE_QUOTA_BLOCKED`).

### Do not do this
**Never** run BindCraft generation on CPU "just this once" — it is slower
by orders of magnitude and produces unvalidated noise. There is no CPU
fallback in this workflow, by design.

### Will I lose my results?
No. Completed checkpoints on Drive are skipped on resume.

---

## 9. Manifest stuck at `RUNNING` forever

### Symptom
`persistent/manifests/EGFR.json` says `RUNNING` although nothing is
running.

### Cause
The child process crashed before the finalizer ran (old code wrote the
final status only on the happy path).

### Confirm it
`persistent/logs/<tag>.log` ends abruptly mid-step.

### Fix
The job wrapper now finalizes the manifest in a `finally` block: crash →
`FAILED` / `OOM` / `INTERRUPTED` (or `PARTIAL` when accepted designs
survived, with `raw_status` preserved). Delete nothing; re-run Cell G and
the corrected finalizer writes the true terminal status.

### Do not do this
Do not hand-edit the manifest to `COMPLETE` to "unblock" the pipeline.

### Will I lose my results?
No — designs already on Drive are retained and re-counted.

---

## 10. `mpnn9_model2` relaxed PDB missing → whole run died

### Symptom (pre-D-019)
One candidate's relaxation fails and the entire BindCraft process exits;
all subsequent candidates are lost.

### Cause
Per-model PyRosetta relaxation failure was treated as a run-fatal error.

### Confirm it
`persistent/reports/relax_failures.jsonl` (after the patch) or a traceback
ending in the relax step in the job log.

### Fix
Applied `patches/bindcraft-7713aa0-relax-tolerance.patch` (DECISIONS
D-019): the failure is recorded, the unrelaxed PDB retained, the next MPNN
candidate continues, already-Accepted candidates are untouched, and the
manifest finalizes.

### Do not do this
Do not re-run the whole trajectory to "replace" one failed model, and do
not accept a candidate whose relaxed PDB is missing.

### Will I lose my results?
No — that is the point of the patch.

---

## 11. Hotspot 390 "not present" in the output PDB

### Symptom
Analysis claims the approved hotspot 390 (also 393/399/421/424/431) is
absent from every generated structure.

### Cause
**BUG 017.** BindCraft output renumbers the target chain to local
`1..172`; the analysis read resseq as the biological UniProt number.
Hotspot 390 is local 81.

### Confirm it
`grep "^ATOM" <output>.pdb | awk '{print $6}' | sort -n | head` → small
numbers, not 310..481.

### Fix
All target-numbering statements go through
`data/processed/target_residue_map.json`
(`scripts/build_target_residue_map.py` derives it; the analyzer refuses to
run without it). Cell H converts epitope numbers the same way for 3D
highlighting.

### Do not do this
Do not conclude the hotspot was ignored, and do not "fix" it by adding a
guessed constant offset to the code.

### Will I lose my results?
No — existing outputs become interpretable after re-analysis.

---

## 12. BindCraft says Accepted, but the contacts look wrong

### Symptom
A design passes BindCraft's filters yet interface contacts sit outside the
approved epitope, at the crop edge, or the binder C-terminus is buried in
the interface.

### Cause
"Accepted" evaluates BindCraft's own model/filter objectives (pLDDT, ipTM,
PAE, per-design heuristics) — not epitope fidelity, not full-target
context, not assay behaviour.

### Confirm it
Run `scripts/analyze_bindcraft_run.py` on the run directory and
`scripts/audit_full_ecd_context.py` per candidate; read the
`lifecycle`/flags.

### Fix
Post-generation scientific QC is now part of the pipeline. A candidate
stays **on hold** until the full-target and assay-context checks complete.

### Do not do this
Do not treat a computed pass as experimental validation, and do not relax
filters to make suspicious candidates pass.

### Will I lose my results?
No.

---

## 13. `/bin/sh: 1: aria2c: not found`

### Symptom
Download fails instantly with `aria2c: command not found`.

### Cause
aria2c is not preinstalled everywhere; assuming it exists was a bug.

### Confirm it
`shutil.which('aria2c')`.

### Fix
The downloader chain detects available tools (`aria2c` → `curl` → `wget`),
attempts one apt install, records every attempt, and fails loudly only
when nothing usable exists. `wget` is always the last resort and is
installed on virtually every image.

### Do not do this
Do not install random binaries into the kernel environment.

### Will I lose my results?
No.
