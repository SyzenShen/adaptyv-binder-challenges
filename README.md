# EGFR pH-switch minibinder — a reproducible design workflow

> **中文版完整攻略在本文件底部（搜索「# 中文版完整攻略」）。**
> A complete Chinese version of this guide is at the bottom of this file.

This repo runs one real protein-design pipeline end to end: pick a target
region on human EGFR, generate small de novo minibinder candidates against it
on a free Google Colab GPU, then audit what actually came out — geometry,
residue numbering, crop artefacts, and the limits of what a computer can tell
you about binding.

It grew out of getting one real workflow to survive ordinary laptop hardware,
Colab resets, GPU quotas, and a JAX version update that broke a run mid-flight.
It is written for someone who has never used Colab, Git, or a command line
before. See [Problems you may hit](#problems-you-may-hit).

**Honesty up front.** Nothing in this repo proves that any binder binds EGFR,
works at pH 6.5, or would ever succeed in a lab. `Accepted` is BindCraft's own
filter decision, not a measurement. A completed trajectory is not a successful
binder. pLDDT, ipTM and PAE are model confidence scores, not affinity. If any
document here sounds confident about wet-lab success, it is wrong — check
[What this workflow can and cannot tell you](#what-this-workflow-can-and-cannot-tell-you).

## 10-minute orientation

If you read nothing else, read this.

- **What the repo does.** It prepares a small piece of the EGFR protein
  (Domain III, residues 310–481), then runs [BindCraft](https://github.com/martinpacesa/BindCraft)
  on a free Colab GPU to generate ~80-amino-acid binder candidates against one
  approved epitope patch. Then it checks the output: does the binder actually
  touch the intended epitope? Did the crop introduce artefacts? Can we trust
  the residue numbering?
- **What is expensive.** Three things: building the software environment
  (~10–25 min, once per session), downloading the AlphaFold2 weights
  (~5.3 GB, cached on Drive so you download once ever), and GPU generation
  itself (the PDL1 control run alone is ~30 min). Everything else is cheap.
- **What is safe.** Every expensive artifact (weights, checkpoints, reports,
  logs, structures) is written to your Google Drive. If Colab dies — and it
  will — you lose only the environment, which rebuilds automatically. You
  never pay for the same GPU work twice. That is what the checkpoint system
  is for.
- **What the repo will not do for you.** It will not prove binding, it will
  not produce a pH switch, and it will not give you KD. It produces
  *structures* and *geometry facts* that a human (you, or your supervisor)
  has to interpret.
- **The one rule.** The PDL1 control run must pass before the EGFR run starts.
  If PDL1 fails, the problem is your environment, not the science. Do not
  start changing the EGFR hotspot to "fix" it.

## The whole workflow at a glance

```
Target preparation (UniProt P00533, PDB 6ARU)
      |
      v
Residue mapping (biological numbering verified)
      |
      v
Epitope choice (envelope B: 390-403 + 421-431)
      |
      v
Crop a small target PDB (Domain III 310-481, 172 res)
      |
      v
Colab environment + preflight (notebook cells A-E)
      |
      v
PDL1 control run (notebook cell G, gate)
      |
      v
EGFR micro generation (BindCraft: MPNN + AF2 + filters)
      |
      v
Geometry + numbering QC (analyze_bindcraft_run.py)
      |
      v
Full-ECD context check (audit_full_ecd_context.py)
      |
      v
Human/mouse + pH mechanism checks
      |
      v
Shortlist / final candidate selection
      |
      v
Wet lab
```

This repo covers target preparation through the full-ECD context check. The
human/mouse structural check, the pH-mechanism layer, final shortlisting, and
wet-lab work are later stages and are not part of it.

## Quick start (first real run)

1. Get a GitHub personal access token (read access to this repo) and add it to
   Colab Secrets under the name `GITHUB_TOKEN`. See [Accounts/software](#4-accountssoftware-you-need).
2. Open `cloud/stage2_bindcraft_smoke.ipynb` in Google Colab.
3. Runtime → Change runtime type → **T4 GPU**. No GPU, no run — it will not
   fall back to CPU, by design.
4. Run cells **A → H top to bottom, changing nothing**. Cell D builds the
   environment (10–25 min). Cell F fetches the AF2 weights (cached on Drive).
   Cell G runs the PDL1 control (~30 min) then the tiny EGFR smoke.
5. If anything dies, see [How to resume after a runtime reset](#38-how-to-resume-after-runtime-reset).
   Re-running cells A→G skips everything already finished on Drive.
6. Read the report Cell H prints. That is the deliverable of a smoke run.

That's the whole run. The sections below explain what each piece is, why it
exists, and what to do when it breaks — and it will break, that is normal.

---

## 0. What this repo is

A small, honest pipeline for *computational* binder design against a
scientifically approved epitope on human EGFR Domain III. It contains the
target preparation scripts, the frozen scientific configuration, a
restart-safe Colab notebook, analysis/QC scripts, and tests that encode every
real failure we have hit so far. Its current job is a **smoke test**: prove
the pipeline works end to end at tiny scale before anyone spends real GPU
hours on production.

## 1. What this repo is not

- Not a binder guarantee. Zero accepted designs so far is a real possible
  outcome, and the repo treats it as information, not failure.
- Not an affinity predictor. No number in any report here is KD, kon, or koff.
- Not a wet-lab protocol. `experimentally_validated` is always `false` in this
  project; there is no wet lab.
- Not production-scale. Default caps are tiny (PDL1: 1 trajectory; EGFR: 3).
  If you are new here, do not raise them.

## 2. Who this is for

A biology student with no software-engineering background, a browser, and a
free Google account. Every tool term (PDB, residue numbering, hotspot,
checkpoint, manifest) is explained inline the first time it appears. If you
can follow a recipe, you can run this. The harder parts — interpreting
results, deciding whether the science is any good — are flagged as human
decisions, not hidden behind automation.

## 3. Very short quick start

See [Quick start](#quick-start-first-real-run) above. That is genuinely all
there is to a run: token into Colab Secrets, GPU runtime, run A→H, read the
report. Everything else in this README is explanation, recovery procedures,
and the reasoning behind the fences.

## 4. Accounts/software you need

| Thing | Why | Where |
|---|---|---|
| Google account | Colab + Drive | free |
| GitHub account + a personal access token (PAT) | the repo is private; the notebook clones it at a pinned commit | GitHub → Settings → Developer settings → Tokens (classic), `repo` read scope |
| A web browser | everything runs in Colab | — |
| Nothing installed locally | all heavy work is in the cloud | — |

The PAT goes into Colab **Secrets** (left sidebar key icon), named exactly
`GITHUB_TOKEN`. It is passed to git through a header and never printed. No
token? Cell C also accepts a manually uploaded zip/tarball of this repo as a
fallback.

## 5. Local machine preparation

Strictly optional — you can run everything from the browser. If you want to
run the local tests or the offline analysis scripts:

```bash
git clone https://github.com/SyzenShen/egfr-binder-challenge.git
cd egfr-binder-challenge
python3 -m unittest discover -s tests -v   # zero third-party dependencies
```

If the tests pass you will see `OK` at the end. If they fail, stop and report
it — do not run a science pipeline on top of a broken test suite.

## 6. Repository layout

| Path | What it is |
|---|---|
| `cloud/stage2_bindcraft_smoke.ipynb` | the Colab notebook (cells A–H) you will actually run |
| `scripts/` | all real logic: environment gate, preflight, weights, orchestrator, QC analyzers |
| `configs/` | frozen scientific configuration (epitope, hotspots, BindCraft filters) |
| `data/raw`, `data/processed` | downloaded targets, residue maps, the cropped target PDB |
| `patches/` | the single audited BindCraft patch (relaxation tolerance), its documentation |
| `docs/TROUBLESHOOTING.md` | full error-by-error repair guide |
| `docs/REPRODUCIBILITY.md` | every version pin, how to reproduce a run |
| `tests/` | regression tests — each one corresponds to a real incident |
| `reports/` | audit reports written so far |
| `STATE.md`, `RUNBOOK.md`, `DECISIONS.md` | project status, command manual, decision log |

## 7. Target preparation

The target is human EGFR (UniProt **P00533**), extracellular domain. We use
the crystal structure **6ARU** (EGFR ECD bound to the antibody cetuximab) from
the RCSB Protein Data Bank. Scripts in `scripts/` verified that the construct
in 6ARU matches the competition-provided sequence residue by residue, and
built `data/processed/residue_map.csv`: one row per residue, mapping PDB
numbering to UniProt biological numbering. Every numbering statement in this
project traces back to that file. Trust maps, not arithmetic.

## 8. PDB / numbering basics

A **PDB file** is the standard text format for 3D protein coordinates — you
can open it in a text editor and read it. The annoying part is numbering: the
same residue can carry different numbers in different files. In 6ARU, chain A
residue 286 is UniProt residue 310 (a constant +24 offset, verified, not
guessed). Why care? Because "residue 390" is only meaningful once you say
*which* numbering. This project always means UniProt numbering unless stated
otherwise, and every conversion goes through a checked mapping file.

## 9. Human/mouse mapping

The challenge asks for cross-reactivity with mouse EGFR, so we aligned human
and mouse ECD sequences (88.7% identity, 551/621 identical residues + 35
conservative substitutions, no internal gaps). All six chosen hotspots are
identical between the species. The full per-residue alignment is in
`data/processed/human_mouse_ecd_alignment.csv`. Note the honesty marker: the
alignment is real data, but the *human/mouse structural QC layer* of the
pipeline is still `null` — see section 34.

## 10. Epitope selection

An **epitope** is the target-surface patch a binder is meant to touch. After
a geometry audit (surface exposure, glycan risk, distance to cetuximab, pH
relevance), patch **B was approved**: UniProt residues **390–403 + 421–431**.
It is human/mouse conserved, relatively glycan-safe, and contains acidic
residues usable for later pH-hypothesis work. This choice is frozen by
decision D-013. Nobody — including the person running the notebook — may
widen it because a design "looks better" that way.

## 11. What a BindCraft hotspot is

A **hotspot** is a set of target residues used to *bias* BindCraft's
generation toward a region. It is not a proven binding site. Within the
approved envelope, six conservative hotspots are used: **390, 393, 399, 421,
424, 431**. Biasing is all it does — whether the final binder actually
contacts each hotspot is a geometry question answered *after* generation, by
the audit script, residue by residue.

## 12. Why generation target may be cropped

The full EGFR extracellular domain is ~620 residues. Generating against all
of it costs GPU memory and time, and most of it is irrelevant to our epitope.
So we crop Domain III (residues **310–481**, 172 residues) into
`data/processed/6ARU_chainA_domain3_310-481.pdb` — coordinates unchanged,
only a smaller piece. Cropping is a trade: much cheaper generation, at the
price of removing the target's natural context (sections 13 and 33).

## 13. Risks of cropping

A cropped target has artificial edges. A binder that "binds" the last residue
of the crop (481) may be gripping an edge that does not exist in the real
protein — an artefact. Also, an epitope patch might look available in the
crop but be blocked by Domain II or IV in the full protein. Both risks are
handled *after* generation: the geometry audit flags contacts near the crop
edges (`CROP_EDGE_CONTACT`), and the full-ECD audit (section 33) re-embeds
each candidate into the complete structure to check for clashes and
out-of-crop contacts.

## 14. Opening Colab

Go to [colab.research.google.com](https://colab.research.google.com) →
File → Upload notebook → upload `cloud/stage2_bindcraft_smoke.ipynb` from
this repo. The notebook is a thin front end: eight code cells (A–H), each
preceded by a markdown cell explaining what it does, what you should see, and
whether re-running it is safe. All the actual logic lives in the pinned
`scripts/` directory that the notebook fetches — the notebook holds no
science, so there is nothing to mis-edit.

## 15. Selecting a GPU

Runtime → Change runtime type → select **T4 GPU** → Save. The free tier gives
you a Tesla T4 (15 GB), which is what this workflow is tuned and tested on.
If Colab refuses with "Cannot connect to the GPU backend due to usage
limits", that is a **quota** condition: the account has used its share for
now. It is not an error you can fix by re-clicking, and the workflow will not
sneak onto CPU — see section 39.

## 16. Mounting Google Drive

Cell B does it. `drive.mount('/content/drive')` pops an authorization window;
approve it. Everything expensive is then written under
`MyDrive/BindCraft/stage2_smoke/`. If you skip this mount (or cancel it), the
workflow fails on purpose — writing GBs of weights and checkpoints to the
ephemeral disk is how runs get destroyed.

## 17. Why `/content` disappears

Colab gives your session a temporary Linux machine. `/content` is its local
disk, and it is **wiped on every reset**: runtime disconnect, idle timeout,
quota eviction, clicking "Restart runtime". The environment, the cloned code,
even downloaded weights — gone, every time. This is not a bug you can avoid;
it is the platform. The entire notebook design assumes it: anything valuable
lives on Drive (persistent), anything rebuildable lives in `/content`, and
the orchestrator re-derives everything from a small manifest file. If a
notebook cell ever references a variable defined "earlier in the session"
that no longer exists, you will get a `NameError` — re-run from cell A.

## 18. Building the isolated environment

Cell C fetches this repo at an exact pinned commit, then Cell D builds the
software environment. Why isolated? Because Colab's preinstalled JAX is too
new for BindCraft's pinned stack and breaks it mid-run (that was failure #1
in the problems table). Cell D builds its own Python 3.10 environment with
the exact versions BindCraft's installer expects — first time it takes
**10–25 minutes**. It is idempotent: after a reset it simply rebuilds.

## 19. Running preflight

Cell E runs the preflight gate *inside* the new environment, before anything
expensive happens: it checks Python/JAX/jaxlib/numpy/flax versions, that
ColabDesign imports, that the GPU is the active backend, and that a real
2048×2048 matrix multiply completes, returns correct numbers, and lives on
the GPU. Any failure = hard stop with an exact reason. We once skipped a
preflight and a JAX mismatch wasted a full run — that is why it exists, and
why it is a gate, not a suggestion.

## 20. AF2 weights

AlphaFold2 predicts structures; BindCraft needs its ~5.3 GB of parameter
files (**exactly 15 official `.npz` files**). Cell F provisions them. The
authority check is the file set itself — count and names, every run. A
`done.txt` flag from a previous attempt is never trusted (a stale one once
hid a broken 14-file download). Wrong count = rejected, loudly.

## 21. Drive cache

Cell F tries, in order: (1) files already in the runtime, (2) the Drive cache
from any previous run, (3) a fresh download with a resumable, observable
downloader (`wget -c`, live progress, recorded return code). After your first
successful download, every later session restores from cache in seconds —
zero download. If you see a download start on your second run, the cache
write failed; check `persistent/logs/`.

## 22. PDL1 control

Before spending GPU time on EGFR, cell G runs the same pipeline against
**PDL1** — a small, well-characterized control target (65-aa binder, 1
trajectory, ~30 min). Why? To separate *environment problems* from *science
problems*. PDL1 passing means the whole machine works. If PDL1 fails, the
EGFR run is blocked — by design, not as punishment. If the PDL1 control
fails, do not start changing the EGFR hotspot. At that point suspect the
environment first, the science never.

## 23. Running/resuming EGFR smoke

The same cell G then runs the real target: EGFR Domain III crop, 80-aa
binders, the six approved hotspots, **max 3 trajectories**. This is the only
expensive cell. It is also the resume cell: re-running it reads
`persistent/checkpoints/<job>/run_manifest.json` (a **manifest** is a small
JSON file recording what finished, with config hashes so a stale result can
never be silently reused) and skips completed stages. Zero accepted designs
at the end is a legitimate outcome and is reported as such — it is not an
error, and it is not silently converted into a "pass".

## 24. Understanding trajectory

One **trajectory** = one BindCraft generation attempt: it hallucinates a
protein backbone against the target, then hands it to ProteinMPNN (section
25), folds candidate sequences with AlphaFold2, applies filters (section 26),
and writes outputs. BindCraft's own output folders per job: `MPNN/` (designed
sequences and models), `Accepted/` (those passing filters), `Trajectory/`
(including `Relaxed/` — energy-minimized 3D structures of the target+binder
complex). "3 trajectories" means three such attempts — small on purpose.

## 25. Understanding ProteinMPNN

ProteinMPNN is a sequence-design tool: given a 3D backbone shape, it proposes
amino-acid sequences that should fold into that shape. In BindCraft it is
the step that turns one hallucinated backbone into several candidate binders
(you will see filenames like `..._mpnn4`). Each MPNN sequence is then
predicted/folded by AF2, model by model — which is why a candidate can have
per-model relax outcomes (and why a single model's relaxation can fail
without killing the run; see problem #10).

## 26. Understanding BindCraft filters

BindCraft applies numeric cutoffs to each AF2 prediction — confidence scores
(pLDDT: per-residue confidence; PAE: predicted alignment error; ipTM/pTM:
interface/global folding measures), interface shape measures, clash counts.
Designs passing all cutoffs land in `Accepted/`. This repo uses **BindCraft's
official default filters unchanged**; the only difference from upstream
defaults is the trajectory cap. The frozen config lives in `configs/bindcraft/`
and is re-derived deterministically each run — editing filter thresholds is a
scientific decision, not a knob.

## 27. What "Accepted" means

`Accepted` means: this design passed BindCraft's default filter cutoffs on
its AF2 prediction. That is the entire claim. It is a *model-internal*
statement — the model is confident about its own prediction.

## 28. What "Accepted" does NOT mean

It does not mean the binder binds EGFR. It does not mean it binds at pH 6.5
or fails at pH 7.4. It says nothing about mouse EGFR, expression, or
manufacturability. It does not even guarantee the binder touches the epitope
we asked for — the AF2 model can satisfy its confidence scores while
contacting a different patch, or the crop edge, or a glycan. That gap between
"model is confident" and "this is real" is exactly why sections 29–33 exist.
Accepted does not mean experimentally validated — nothing in this repo is.

## 29. Residue numbering after BindCraft

Here is a trap we actually fell into. BindCraft's output renumbers the target
chain to **local indices 1–172**, so "hotspot 390" simply does not exist in
the output PDB — querying it finds nothing, which once led us to believe a
hotspot was "not present" when it was there all along (problem #11). The fix
is `data/processed/target_residue_map.json`: a derived, cross-checked map
from local index → biological (UniProt) number. Every geometry claim in the
analysis goes through that file. If the map is missing or inconsistent, the
analysis **fails loudly** rather than guessing an offset. Bad habit to avoid:
"the offset is probably 309, just add it" — no.

## 30. Geometry audit

`scripts/analyze_bindcraft_run.py` reads every relaxed complex and reports,
per candidate: which target residues the binder contacts (converted to
biological numbering), per-hotspot minimum heavy-atom distances, the fraction
of contacts inside the approved envelope, off-envelope contacts
(`EPITOPE_MIGRATION`), and severe clashes. It reports geometry facts — it
never converts them into "this binder is good". Its full per-candidate record
plus lifecycle state lands in the run report JSON.

## 31. Crop-edge audit

The same script flags contacts to the first/last residues of the crop
(`CROP_EDGE_CONTACT`, configurable edge window, default 5). An earlier
version used a hardcoded window of 3 and *hid* a real C-terminal contact —
the window is now a checked parameter. Edge contact is a flag for human
review, not an automatic rejection.

## 32. C-terminal tag risk

Related but distinct: if the binder's own **C-terminus** (its last ~5
residues) participates in the interface, that is a risk for assay formats —
C-terminal tags (His6, Fc fusion) used in real experiments would sit right
in the binding interface. The script records `C_TERMINAL_ASSAY_RISK` with
the measured distance. Recorded, not auto-rejected: it is a design-review
input, and the human decides.

## 33. Full-ECD audit

`scripts/audit_full_ecd_context.py` re-embeds each candidate into the
**complete** EGFR ectodomain (from 6ARU, all four domains) via a Kabsch
least-squares superposition of the crop back onto the full structure, then
checks: does the binder contact residues *outside* the crop
(`CONTACTS_OUTSIDE_CROP`)? Does it clash with the full protein
(`SEVERE_CLASH_WITH_FULL_ECD`)? Does it touch a glycan (`GLYCAN_CONTACT`)?
This is the antidote to section 13's cropping risks. Run it after a run with
accepted candidates; usage is documented in its `--help` and in
`docs/REPRODUCIBILITY.md`.

## 34. Human/mouse check

The sequence-level alignment (section 9) is done. The **structural** QC
layer — does the binder's interface tolerate the mouse residues at the
contact positions, in 3D — is implemented **nowhere yet** and is reported as
`HUMAN_MOUSE_QC = null` in every candidate lifecycle. Do not trust any
document that claims mouse cross-reactivity. This is a planned stage, not a
done one.

## 35. pH check

The pH-switch hypothesis (binds pH 6.5, not pH 7.4) is the project's
long-term goal, and **nothing in this repo measures it**. `PH_MECHANISM_QC =
null`, always, in Stage 2. Protonation-state work (PROPKA-style reasoning
about histidines and acidic residues near the interface) is a later stage,
on real accepted candidates, with a supervisor in the loop. The approved
envelope was chosen partly because it *could* support such a mechanism — that
is a hypothesis, not a result.

## 36. Candidate promotion states

Every candidate carries a lifecycle, and each layer is either computed or
`null`:

| Layer | Meaning | Status in Stage 2 |
|---|---|---|
| GENERATED | structure exists | computed |
| BINDCRAFT_ACCEPTED | passed BindCraft filters | computed |
| NUMBERING_QC | numbering verified via the map | computed |
| EPITOPE_QC | contacts inside approved envelope | computed |
| CROP_EDGE_QC | crop-edge / C-terminal risk flags | computed |
| FULL_ECD_QC | full-context audit | computed (tool exists) |
| ASSAY_GEOMETRY_QC | assay-format geometry | **null** |
| HUMAN_MOUSE_QC | cross-species structural check | **null** |
| PH_MECHANISM_QC | pH-switch evidence | **null** (always, Stage 2) |
| SUBMISSION_CANDIDATE | human-approved shortlist | **null** |

A candidate is never promoted past a layer that was not computed. `Accepted`
designs currently sit "on hold" — that is a real state, and it is the honest
one.

## 37. Where results are saved

Everything lands on your Drive under `MyDrive/BindCraft/stage2_smoke/`:

```
persistent/
  checkpoints/<job>/run_manifest.json   # what finished; the resume authority
  configs/                              # exact configs used
  logs/<job>.log                        # full stdout/stderr
  metadata/                             # runtime_config, preflight, weights, patch records
  reports/                              # stage2_smoke_report.json (+ .md)
  cache/alphafold/                      # the 15 weight files (download once)
<job_name>/                             # e.g. PDL1_smoke_l65_s909721
  Trajectory/Relaxed/*.pdb              # 3D structures to inspect
  MPNN/  Accepted/                      # designs; Accepted/ may be empty
```

To get results back to your laptop: download that folder (or share it). To
analyze offline without a GPU, `scripts/analyze_bindcraft_run.py` runs
anywhere on plain Python.

## 38. How to resume after runtime reset

The scenario: your GPU session dies halfway through. Recovery:

1. Reconnect (Runtime → Change runtime type → GPU again).
2. Re-run cells **A → G** in order. Do not skip A: the GPU gate is cheap.
3. Cells A–D rebuild the ephemeral environment (~10–25 min if Miniforge was
   wiped). Nothing on Drive was touched.
4. Cell F restores weights from the Drive cache — no download.
5. Cell G reads the manifests. A valid completed PDL1 checkpoint prints
   `CHECKPOINT_REUSED` and skips the ~30-min control run; a finished-but-
   unmanifested legacy run is adopted as `LEGACY_CHECKPOINT` (explicitly
   marked, evidence-constrained). The EGFR smoke resumes from where it died.
6. Read the report (cell H) when it prints `STAGE 2 SMOKE COMPLETE`.

What you must **not** do: start changing cells or configs mid-recovery, or
delete Drive folders to "clean up". Checkpoints with `COMPLETED` status are
never silently overwritten.

## 39. What to do after GPU quota denial

The symptom: `Cannot connect to the GPU backend due to usage limits`, or
cell A prints `COMPUTE_QUOTA_BLOCKED` and exits. This is Colab saying your
account's free GPU allocation is exhausted for now. The workflow exits with
code 2 **before** building environments or downloading anything, and it
**never** falls back to CPU — CPU generation is slow enough to be useless and
would produce results we do not trust. The correct action: stop, keep the
Drive folder (all progress is safe), come back when quota resets (typically
within a day), re-run A→G. Completed stages are skipped automatically.

## 40. How to inspect logs

All logs are plain text on Drive. Priorities, in order: (1)
`persistent/reports/stage2_smoke_report.json` — the summary with statuses and
flags; (2) `persistent/checkpoints/<job>/run_manifest.json` — stage states,
config hashes, relaxation-failure counts; (3) `persistent/logs/<job>.log` —
the full stream; search it for `STAGE2_RELAX_FAILURE` (per-model relaxation
issues) and for the first `Traceback` from the bottom. A relaxation failure
line also lands per-candidate in `<job>/MPNN/relax_failures.jsonl`. If you
bring a problem to someone, bring these three files.

## 41. How to visualize a PDB

Cell H shows every relaxed complex in 3D inside the notebook (py3Dmol):
target in blue-grey, binder in rose, the approved epitope envelope highlighted
in yellow — converted to the *local* numbering of the output PDB through the
residue map, which is exactly the conversion naive highlighting gets wrong.
CPU is fine for this cell. Outside Colab, any PDB viewer works (PyMOL,
ChimeraX, or molstar.org in a browser — upload the file, no install).

## 42. Troubleshooting

Fast lanes: symptom → fix in [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
(thirteen real failures, each with symptom/cause/confirm/fix/do-not-do/what-
you-keep). The problems table below is the one-line version. Three highest-
frequency ones:

- `AttributeError: module 'jax.lib' has no attribute 'xla_bridge'` → you are
  on Colab's JAX, not the isolated env. Re-run from cell D; do not "upgrade
  or downgrade JAX" by hand.
- `COMPUTE_QUOTA_BLOCKED` → wait for quota, re-run A→G later. Never CPU.
- `FAIL LOUDLY: residue mapping artifact not found` → the repo checkout is
  incomplete or from the wrong commit; re-run cell C.

## 43. Cost/compute expectations

Everything above runs on the **free** Colab tier; this project uses no paid
compute. Realistic first-session shape: ~10–25 min
environment, ~5.3 GB weights download (once, then cached), ~30 min PDL1
control, and the EGFR micro-run (3 trajectories) — order of tens of minutes
on a T4. Exact per-trajectory wall time and success rate on this hardware
are not known yet; those numbers come from the first real smoke run. Expect
resets and quota days; the workflow is built around them, not against them.

## 44. Reproducibility/version pinning

Every moving part is pinned: this repo is fetched at an exact commit
(`PROJECT_PIN` inside the notebook), BindCraft at `7713aa0d0d351e4117a8befeb8541f3a8ebd3368`,
ColabDesign at `e31a56fe1d9b4de25c8697f3a28b75892941cc72`, Python 3.10 with
JAX/jaxlib 0.6.0, numpy<2, flax<0.10, and the single audited BindCraft patch.
Each run records all of these into `persistent/metadata/`. Full details and
the exact reproduction recipe: [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md).
Known limit, stated plainly: PyRosetta is installed from a quarterly release
channel, so an exact re-install is not bit-for-bit guaranteed — observed
versions are recorded per run instead.

## 45. Licenses / PyRosetta note

PyRosetta requires a **free academic (non-commercial) license** from
RosettaCommons — confirm your use qualifies; the wheel is installed from the
official academic release server. AlphaFold2 parameters are subject to
DeepMind's terms of use. BindCraft and ColabDesign are used as pinned
upstream projects (see each repository for its license). The single patch in
`patches/` is documented with its authorization (decision D-019) in
[patches/PATCHES.md](patches/PATCHES.md) — it changes failure handling only,
never scientific filters.

## 46. Citation / upstream projects

If you use or build on this workflow, cite the upstream tools it stands on:
**BindCraft** (github.com/martinpacesa/BindCraft and its publication),
**ColabDesign** (github.com/sokrypton/ColabDesign), **AlphaFold2** (Jumper et
al., Nature 2021), **ProteinMPNN** (Dauparas et al., Science 2022),
**PyRosetta** (RosettaCommons), target structure **6ARU** (RCSB PDB), and
sequence **UniProt P00533**. This repo itself is a challenge project
(Anthropic × Adaptyv Challenge 01, Track 3); its reports are internal working
documents, not publications.

## 47. Current project status

Stage 2 (cloud smoke test) — pipeline consolidated and pinned, tests green,
**awaiting the first full real smoke run on Colab**. Real observed so far:
one T4 GPU session, one successful (persisted) PDL1 control run with **zero
final accepted designs**, and **zero
EGFR trajectories** — per-trajectory timing and acceptance rates are not
known yet; those numbers come from the first real smoke run. Production
generation (larger batches) is gated on the smoke report being reviewed.
Status file of record: [STATE.md](STATE.md).

## 48. English → Chinese full translation

The complete Chinese guide follows below, in the same file — same structure,
written as a guide, not a machine translation.

## What this workflow can and cannot tell you

**What it can tell you** — with evidence you can open and re-check:

- whether the frozen target/config produces candidate structures that look
  foldable and form an interface (that is the entire purpose of Stage 2);
- geometry facts: which residues the binder contacts (in verified
  biological numbering), per-hotspot distances, envelope coverage,
  crop-edge and C-terminal flags, clashes against the full ECD.

**What it cannot tell you** — no matter how good the numbers look:

- that anything binds human EGFR, or mouse EGFR;
- that anything binds at pH 6.5 or *stops* binding at pH 7.4;
- KD, kon, koff — no computational number here is an affinity;
- expression, manufacturability, or wet-lab success.

Stage 2 answers one narrow question. Everything after it — human/mouse
structural compatibility, pH mechanism, PROPKA/protonation/mutational design,
full-ECD and glycan context, assay construct, final selection — is later
work, on later evidence. Keep the evidence grades straight:
`software_test_passed` → `model_run_completed` → `computational_filter_passed`
→ `experimentally_validated` (always `false` here). The third is not the
fourth.

## Problems you may hit

These all happened while building this workflow. The last column is the
reaction to resist.

| Symptom | Real cause | Correct fix | Wrong reaction |
|---|---|---|---|
| `jax.lib has no attribute xla_bridge` | Colab's rolling JAX too new for BindCraft | isolated Python 3.10 / JAX 0.6.0 env (cell D) | change EGFR target settings |
| `TypeError: 'set' object is not subscriptable` | preflight assumed `devices()` returns a list | iterate the device set | reinstall CUDA |
| 30-min weight download wait, zero files | fire-and-forget `Popen`, stderr lost | observable downloader + return code + resume | wait another 30 minutes |
| 15 `.npz` files but assertion fails | wrong expected count / stale logic | validate the exact official 15-file set | trust a `done.txt` flag |
| `unrecognized argument --out` | notebook/script CLI drift | integration contract test | loosen the test |
| `RUNROOT` NameError | notebook state vanished with the runtime | reconstruct config from disk | retype globals into cells |
| PDL1 file "missing" | looked in a guessed path | read `design_path` from the manifest | hunt by hand in `/content` |
| Cannot connect to GPU backend | Colab quota | keep Drive checkpoint, resume later | run BindCraft on CPU |
| manifest stuck on `RUNNING` forever | child process crashed before finalizer | `finally`-based manifest finalization | hand-edit the manifest to `COMPLETED` |
| `mpnn9_model2` relaxed PDB missing | single per-model PyRosetta relaxation failure | candidate-level failure containment (patch D-019) | throw away the previously accepted mpnn4 |
| hotspot 390 "not present" in output | BindCraft renumbers target to local 1–172 | explicit residue-map conversion | conclude the hotspot was ignored |
| `Accepted` but contacts look suspicious | filters score the model's own prediction, not biological context | post-generation scientific QC | trust it because filters passed |

## Worked example: why "Accepted" is not the end

A real candidate from the smoke work: `EGFR_D3_Bcons_l80_s313440_mpnn4`. It
passed BindCraft's default filters — by the filter definition, it is
`Accepted`. Then the post-generation checks found, in order: the output PDB
numbers the target 1–172, so the epitope cannot even be queried without the
residue map; once mapped correctly, epitope-migration still needed checking;
the candidate sits close to the crop's C-terminal edge; and the binder's own
C-terminus participates in the interface — an assay-format risk. Full-ECD and
assay-context QC are therefore required before this design can move anywhere.

This design passed BindCraft's default filters, but it is still on hold until
the full-target and assay-context checks are complete.

This is a normal candidate state, not a failure story. "On hold" is not
"failed", and a computational pass is not an experimental pass.

---

# 中文版完整攻略

这份仓库做一件事：在人 EGFR 上选一段科学上批准过的表位，用免费的
Google Colab GPU 生成小型 de novo minibinder 候选，然后审计产出——
几何、编号、裁剪伪影，以及计算结果到底能证明什么、不能证明什么。
目前没有 EGFR 轨迹，也没有最终 accepted 设计。

先说三句最重要的话：

1. **`Accepted` 不等于 validated。** 它只说明通过了 BindCraft 自己的过滤
   阈值，不代表结合、不代表 pH 切换、更不代表湿实验会成功。
2. **`/content` 会被清空，Drive 不会。** Colab 每次重置都会抹掉临时盘，
   所以所有贵重产物（权重、检查点、报告、结构）都写 Drive。
3. **没有 GPU 就不跑生成。** 配额被拒就等配额恢复，绝不降级 CPU。
   这不是固执，是结果可信度问题。

## 十分钟 orientation（中文）

- **这个仓库在干什么**：准备 EGFR Domain III（310–481，172 个残基）作为
  生成靶标，用 BindCraft 生成 80 aa 的 binder 候选，再用自写脚本审计：
  binder 真的接触批准的表位了吗？裁剪边缘有没有伪影？编号可信吗？
- **贵的是什么**：环境搭建（10–25 分钟）、AF2 权重下载（5.3 GB，Drive
  缓存后只下一次）、GPU 生成本身（PDL1 对照约 30 分钟）。其余都便宜。
- **不会自动替你证明什么**：结合、pH 开关、KD、鼠交叉反应——都证明不了。
  它产出的是结构和几何事实，解释权在你和你的老师。
- **一条铁律**：PDL1 对照先跑通，EGFR 才开始。如果 PDL1 这一步都跑不通，
  先别碰 EGFR 的 hotspot。这个时候优先怀疑环境，不是科学设计。

## 流程总览

```
靶标准备（UniProt P00533，PDB 6ARU）
      |
      v
残基编号映射（已验证）
      |
      v
表位选择（B 包络 390-403 + 421-431，已冻结）
      |
      v
裁剪小靶标 PDB（Domain III 310-481）
      |
      v
Colab 环境 + preflight（notebook A-E）
      |
      v
PDL1 对照（cell G 的门）
      |
      v
EGFR micro 生成（MPNN + AF2 + 过滤）
      |
      v
几何 + 编号 QC（analyze_bindcraft_run.py）
      |
      v
完整 ECD 上下文审计
      |
      v
人/鼠 + pH 机制检查
      |
      v
短名单 / 最终遴选
      |
      v
湿实验
```

本仓库覆盖靶标准备到完整 ECD 上下文审计。人/鼠结构检查、pH 机制、
最终遴选和湿实验是后续阶段。

## 从零到 smoke 的最短路线

1. **准备 token**：GitHub → Settings → Developer settings → Personal access
   tokens（classic），勾 `repo` 读权限，生成后复制。Colab 左栏钥匙图标 →
   Secrets → 添加名为 `GITHUB_TOKEN` 的 secret，粘贴 token。
   （没有 token 也可以：Cell C 支持手动上传仓库压缩包。）
2. **打开 notebook**：colab.research.google.com → 上传
   `cloud/stage2_bindcraft_smoke.ipynb`。
3. **选 GPU**：Runtime → Change runtime type → **T4 GPU**。选不了 GPU 就是
   配额问题，见下文"配额被拒"。
4. **从 A 顺序跑到 H，数字一个都不改**。A 查 GPU；B 挂 Drive；C 按 pin
   commit 拉本仓库；D 建 Python 3.10 / JAX 0.6.0 隔离环境（首次 10–25
   分钟）并打唯一授权补丁；E preflight 硬门；F 备齐 15 个 AF2 权重文件
   （首次下载 5.3 GB，之后 Drive 秒恢复）；G 跑 PDL1 对照（约 30 分钟）→
   通过后自动跑 EGFR micro（3 条轨迹）；H 读报告 + 3D 目检（CPU 即可）。
5. **中途挂了**：重连 GPU → 重跑 A→G。已完成的步骤（含 30 分钟的 PDL1）
   会从 Drive 检查点跳过，不会重付费。
6. **看结果**：Cell H 打印的 `stage2_smoke_report.json` 就是 smoke 的交付物；
   Drive `MyDrive/BindCraft/stage2_smoke/persistent/reports/` 里永久保留。

## 每一步的要点与常见错（速查）

| 步骤 | 干什么 | 常见错 | 正确处理 |
|---|---|---|---|
| A GPU 门 | 确认有 NVIDIA GPU，打印硬件元数据 | 不看输出直接跑下一格 | 无 GPU → `GPU_UNAVAILABLE`/`COMPUTE_QUOTA_BLOCKED`，退出码 2，停下等配额 |
| B 挂 Drive | 建立持久根目录 | 取消授权弹窗 | 必须授权；否则按设计失败 |
| C 拉 pin | 按精确 commit 取本仓库 | 私库无 token | 加 `GITHUB_TOKEN` secret 或手动传 tarball |
| D 环境 | 隔离 py3.10/jax0.6.0 + 补丁 | 手动升级 JAX"修复" | 别动。Colab 自带 JAX 太新，会弄崩 BindCraft |
| E preflight | 版本/GPU/矩阵乘法硬门 | 跳过它省时间 | 别跳。我们跳过一次，JAX 版本不匹配浪费了一整轮 |
| F 权重 | 15 个 .npz，本地→缓存→下载 | 旧 `done.txt` 当真 | 文件集本身才是权威；数量不对就拒收 |
| G 生成 | PDL1 门 → EGFR micro，可恢复 | 失败后乱改配置 | 读 manifest 和日志；PDL1 失败=环境问题 |
| H 报告 | 读 JSON + py3Dmol 看结构 | 直接相信 accepted | 表位高亮已经过编号映射换算，目检要自己看接触 |

## 可能会踩的坑（12 条速查）

| 症状 | 真实原因 | 正确修法 | 错误反应 |
|---|---|---|---|
| `jax.lib has no attribute xla_bridge` | Colab 滚动 JAX 太新 | 隔离 py3.10/JAX 0.6.0 环境 | 去"改好"EGFR 靶标设置 |
| `TypeError: 'set' object is not subscriptable` | preflight 假设 devices() 是列表 | 迭代设备集合 | 重装 CUDA |
| 权重下载等 30 分钟、零文件 | 发射后不管的 Popen，stderr 丢失 | 可观测下载器+返回码+续传 | 再等 30 分钟 |
| 15 个 .npz 但断言失败 | 期望数量写错/逻辑过期 | 校验精确官方 15 文件集 | 信 `done.txt` |
| `unrecognized argument --out` | notebook 与脚本 CLI 漂移 | 集成契约测试 | 放宽测试 |
| `RUNROOT` NameError | notebook 状态随 runtime 消失 | 从磁盘/配置重建 | 手敲全局变量 |
| PDL1 文件"不见了" | 在猜的路径里找 | 读 manifest 的 design_path | 在 /content 里手动翻 |
| 连不上 GPU 后端 | Colab 配额 | 保住 Drive 检查点，稍后恢复 | 用 CPU 跑 BindCraft |
| manifest 永远 RUNNING | 子进程在终结前崩溃 | finally 兜底终结 manifest | 手改 manifest 为 COMPLETED |
| `mpnn9_model2` 的 relaxed PDB 缺失 | 单个 per-model PyRosetta 松弛失败 | candidate 级故障隔离（D-019 补丁） | 把之前已 accepted 的 mpnn4 也扔了 |
| hotspot 390"不存在" | 输出把靶标重编号为 local 1–172 | 走显式残基映射 | 下结论"hotspot 被忽略了" |
| Accepted 但接触可疑 | 过滤器评的是模型自己的预测 | 生成后科学 QC | 因为过了过滤就信了 |

完整版（每个错误的确认命令、修复步骤、会丢什么）见
[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)。

## 案例：为什么 `Accepted` 不是终点

真实 smoke 候选 `EGFR_D3_Bcons_l80_s313440_mpnn4`：通过了 BindCraft 默认
过滤。随后的检查发现——输出 PDB 的靶标编号是 local 1–172，不映射就查不了
表位；正确映射后还要查表位迁移；候选贴近裁剪 C 端边缘；binder 自己的
C 端参与了界面（assay 风险）。所以它必须等完整 ECD 与 assay 上下文检查。

> This design passed BindCraft's default filters, but it is still on hold
> until the full-target and assay-context checks are complete.

"on hold" 不是 "failed"。计算通过不等于实验通过。

## 这个流程能告诉你什么 / 不能告诉你什么

**能（有据可查）**：冻结的靶标/配置能否产出看起来可折叠、可形成界面的
候选结构（这就是 Stage 2 的全部意义）；几何事实——接触了哪些残基（已验证
生物学编号）、每个 hotspot 的最小重原子距离、包络内接触占比、裁剪边缘与
C 端风险旗标、对完整 ECD 的冲突检查。

**不能（无论数字多好看）**：人 EGFR 结合？鼠 EGFR 结合？pH 6.5 结合、
pH 7.4 不结合？KD、kon/koff？表达量？湿实验成功率？——统统不能。
本仓库所有报告里 `experimentally_validated` 恒为 `false`。
后续才是：人/鼠结构相容性、pH 机制、PROPKA/质子化/突变设计、完整 ECD、
糖基化、assay 构建、最终遴选。

## 断点恢复与配额（中文速查）

- **runtime 被重置**：`/content` 全没，Drive 全在。重连 GPU，重跑 A→G。
  A–D 自动重建环境（10–25 分钟）；F 从缓存秒恢复权重；G 读 manifest，
  `CHECKPOINT_REUSED` 跳过已完成的 PDL1，EGFR 从断点继续。
  不要中途改格子、不要删 Drive 目录"清理"。
- **配额被拒**（"Cannot connect to the GPU backend due to usage limits"）：
  这是账号的免费 GPU 额度用完了，不是 bug。工作流会在建环境/下载之前
  以退出码 2 停止，绝不偷偷用 CPU。正确动作：停，Drive 进度都在，
  等额度恢复（通常一天内），重跑 A→G。

## 复现与版本（中文）

所有可动部分都被 pin：本仓库按 `PROJECT_PIN` 精确 commit 获取；BindCraft
`7713aa0d0d351e4117a8befeb8541f3a8ebd3368`；ColabDesign
`e31a56fe1d9b4de25c8697f3a28b75892941cc72`；Python 3.10 + JAX/jaxlib 0.6.0 +
numpy<2 + flax<0.10；唯一授权补丁见 [patches/PATCHES.md](patches/PATCHES.md)。
每次 run 都把环境版本记录进 `persistent/metadata/`。完整清单与复现步骤见
[docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md)。已知限制直说：
PyRosetta 走季度发布通道，不承诺逐位复现，按 run 记录观察版本。

## 许可与上游（中文）

PyRosetta 需要免费的学术（非商业）许可，确认你的用途符合；AlphaFold2
参数遵循 DeepMind 使用条款；BindCraft / ColabDesign 按 pin 的上游仓库使用。
本仓库是比赛项目（Anthropic × Adaptyv Challenge 01, Track 3），
引用请引上游工具：BindCraft、ColabDesign、AlphaFold2（Jumper et al. 2021）、
ProteinMPNN（Dauparas et al. 2022）、PyRosetta、6ARU、UniProt P00533。

## 当前状态（中文）

阶段 2（云端 smoke）：流水线已收口并 pin 死，测试全绿，
**等待第一次完整的真实 smoke run**。目前真实观测：一次 T4 会话、
一次成功且已持久化的 PDL1 对照 run（**零最终接受**）、**零条 EGFR 轨迹**；
单轨迹耗时与接受率要等真实 run 跑完才有数。
生产规模生成被"smoke 报告经人工复核"这道门挡住。状态以
[STATE.md](STATE.md) 为准。
