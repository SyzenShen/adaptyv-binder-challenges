# Patches to pinned upstream code

Every modification of a pinned upstream checkout lives here as a committed
unified diff, applied by `scripts/apply_bindcraft_patch.py` — the only
supported way to touch a pinned tree. No hand edits, ever.

## bindcraft-7713aa0-relax-tolerance.patch

- **Upstream:** BindCraft at `7713aa0d0d351e4117a8befeb8541f3a8ebd3368`
- **Authorization:** DECISIONS **D-019** (explicit user directive,
  2026-10-03). This is the single narrow exception to "never modify the
  pinned scientific tree".
- **Purpose:** a per-model PyRosetta relaxation failure must not kill a whole
  trajectory or run. Before this patch, one missing relaxed PDB crashed the
  run and `clean_pdb()` could delete work that was already on disk.

What the patch does, per candidate/model:

1. verifies the expected per-model PDB exists **BEFORE** `clean_pdb()` runs;
2. records a structured line to `relax_failures.jsonl` (stage, model, error
   type, whether the unrelaxed PDB was retained);
3. retains the unrelaxed PDB when relaxation produced nothing usable;
4. continues to the next MPNN candidate instead of terminating the
   trajectory;
5. already-Accepted candidates and completed trajectories are untouched;
6. the run finalizes its manifest even after a child-process failure.

Handbook-side readers for that JSONL live in
`scripts/stage2_relax_failures.py` (corrupt lines are counted, not fatal).

**Application:** automatic, idempotent, in notebook Cell D —
`git apply --check` first, refusal on drift/partial patch/wrong commit,
pre/post file SHA256 recorded to `persistent/metadata/bindcraft_patch.json`.

**Scope guard:** if you believe upstream needs another change, stop and
record a decision first. Do not extend this patch silently.
