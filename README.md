# adaptyv-binder-challenges

A learning log of computational protein-binder design for the Anthropic x Adaptyv competition on Proteinbase: what was built, what the numbers say, and the mistakes along the way. Real data, including the negative results.

**Read this first.** Nothing in this repository shows that any designed protein binds its target, works at a given pH, or would succeed in a lab. No wet-lab data exists here. Scores such as ipTM, ipSAE or pLDDT are model confidence values, not affinity. Where a document sounds more confident than that, it is wrong.

| Challenge | Target | Folder | State |
|---|---|---|---|
| 1 | EGFR, pH-selective minibinder | [`challenges/egfr/`](challenges/egfr/) | closed; documented workflow and audits, no experimental result |
| 2 | TNF-alpha, binds at pH 7.4, no binding at pH 6.0, human and mouse | [`challenges/tnfa/`](challenges/tnfa/) | open until 2026-10-18 23:59 AoE (announced by the organizers on Slack, 2026-10-11; check the challenge page) |

## Result so far for TNF-alpha
One pilot of 24 designs with BoltzGen on a free Colab T4 gave **no design with credible predicted binding**: design-to-target ipTM 0.11-0.30, ipSAE 0.00 for all 24, and only 1 of 24 passed BoltzGen's default filters. Details, causes still untested, and the lessons are in [`challenges/tnfa/REPORT.md`](challenges/tnfa/REPORT.md).

What was useful along the way:
- the receptor-binding site was defined from a receptor complex (7KP7) and all 29 contact positions turned out identical in human and mouse;
- the crystal structure 1TNF differs from the assay protein at residue 143 (Leu instead of Asp), which the organizers later confirmed;
- several traps that cost time (cache on Google Drive, ungenerated atoms written at coordinates (0, 0, 0), files silently ignored by git) are written down with the fix.

## Where to start
1. [`challenges/tnfa/REPORT.md`](challenges/tnfa/REPORT.md): the short story with numbers and lessons.
2. [`challenges/tnfa/pilot_findings.md`](challenges/tnfa/pilot_findings.md): the raw pilot results.
3. [`challenges/tnfa/rules_and_assay.md`](challenges/tnfa/rules_and_assay.md): what is known about the assay, each item tagged by where it came from.
4. [`challenges/egfr/README.md`](challenges/egfr/README.md): a long beginner-oriented guide to a BindCraft workflow on Colab.

## Layout
```
challenges/
  egfr/   Challenge 1: scripts, tests, configs, reports, notebooks (own README)
  tnfa/   Challenge 2: data, scripts, BoltzGen inputs, notebooks, notes (own README)
CLAUDE.md  working rules for the AI assistant used in this project
LICENSE    MIT
```
The two challenges are self-contained and do not share conclusions.

## Reproducing
- TNF-alpha, CPU only (needs `numpy`): see [`challenges/tnfa/README.md`](challenges/tnfa/README.md#reproduce).
- EGFR tests (no third-party packages): `cd challenges/egfr && python3 -m unittest discover -s tests`. All 169 tests pass (1 is skipped by design).
- GPU runs (Colab or a rented machine) are described in the TNF-alpha README.

## How this was made
The work was done with an AI assistant (Claude Code) under the user's direction; commits carry a `Co-Authored-By` line. Information about the assay comes from the official challenge page and from statements by the organizers in the public Proteinbase Slack; each is labelled with its source. Participant discussions are used only as pointers, not as evidence.

## License and third-party material
Code and documents written for this project are under the MIT License (see [`LICENSE`](LICENSE)). Third-party files keep their own terms: PDB entries, UniProt sequences, the saved copy of the Proteinbase challenge page, BindCraft-related files, and any model weights downloaded at run time. Check the original source before reusing them.

The repository was named `egfr-binder-challenge` until 2026-10-08.
