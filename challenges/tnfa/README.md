# Challenge 2: TNF-alpha conditional binder

Goal of the challenge: a de novo binder of soluble trimeric TNF-alpha that binds at pH 7.4, shows no detectable binding at pH 6.0, and also binds mouse TNF-alpha (pH 7.4 only). Ranked in that order: pH selectivity, mouse cross-reactivity, then affinity.

**Status (2026-10-13).** Pipeline built and run once on a free Colab T4 with 24 designs. **No design shows credible predicted binding** (ipSAE 0.00 for all). No experiments were done. The learning goal is the point of this folder; no GPU was rented. Deadline per the organizers' Slack announcement: 2026-10-18 23:59 AoE (verify on the challenge page).

Start with [`REPORT.md`](REPORT.md).

## What is here
| File or folder | What it is |
|---|---|
| [`REPORT.md`](REPORT.md) | outcome, measured numbers, mistakes and lessons |
| [`pilot_findings.md`](pilot_findings.md) | pilot speed, filter pass counts, sequence classes, confidence metrics |
| [`rules_and_assay.md`](rules_and_assay.md) | rules and assay facts, each tagged by source (official page, organizer statement on Slack, user report) |
| [`target_prep.md`](target_prep.md), [`receptor_epitope.md`](receptor_epitope.md), [`epitope_selection.md`](epitope_selection.md) | target preparation, receptor-defined site, and a superseded first epitope attempt |
| [`design_plan.md`](design_plan.md), [`methodology_draft.md`](methodology_draft.md) | the plan and a draft methodology text with real numbers |
| `data/` | structures (1TNF, 7KP7, 3WD5, 4G3Y), sequences, derived tables (third-party data keeps its own terms) |
| `boltz/` | BoltzGen inputs: `tnfa_e3_core.yaml` (12 hotspots, used in the pilot), `_wide`, `_min` (4 hotspots), `_min_helical` (experimental, never run) |
| `scripts/` | target prep, conservation, SASA, receptor-site mapping, BoltzGen input builder, design analysis, run summary |
| `cloud/` | Colab notebook and a terminal runner for a rented GPU machine |
| [`HANDOVER_C2.md`](HANDOVER_C2.md) | what was verified versus reported at the start |

## Reproduce
CPU only, from this folder (needs `numpy`):
```bash
python3 -I scripts/tnfa_prep_target.py          # target chains and interface residues
python3 -I scripts/tnfa_conservation.py         # human/mouse conservation
python3 -I scripts/tnfa_epitope_sasa.py         # exposed groove (about 45 s)
python3 -I scripts/tnfa_complex_epitopes.py     # receptor and antibody contacts
python3 -I scripts/tnfa_receptor_site.py        # receptor site on 1TNF chains
python3 -I scripts/tnfa_make_boltzgen_inputs.py # BoltzGen yaml files
```
Design runs need a GPU:
- **Free Colab T4**: open [`cloud/tnfa_boltzgen_colab.ipynb`](cloud/tnfa_boltzgen_colab.ipynb), select a T4, run cells A to E, then the pilot. About 7 minutes per design on a T4 for the whole pipeline.
- **Rented Linux GPU box** (untested): `bash cloud/run_on_gpu_box.sh tnfa_e3_min.yaml 10`.
- Compare runs with `python3 -I scripts/tnfa_summarize_run.py LABEL=RUN_DIR`.

## Key facts and cautions
- The assay immobilizes the binder through a C-terminal Twin-Strep tag and flows the trimer, so avidity matters; the organizers fit 1:1 and multivalent models. The C-terminus of a design should stay away from the target.
- The wet-lab target has Asp143; 1TNF has Leu143. Designs made against 1TNF need re-checking.
- Buffer is HEPES-based at both pH values; the pH 6.0 assay was still being tested by the organizers when last reported.
- Metrics from BoltzGen and Boltz-2 are confidence scores. Only the assay can show binding or a pH switch.
- The organizers state that participants must not run their own wet-lab validation before submitting.
