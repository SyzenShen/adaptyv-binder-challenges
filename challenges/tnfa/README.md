# Challenge 2: TNF-alpha conditional binder (neutral ON / acid OFF)
Status: P0 done. P1 (rules, target data) DONE 2026-10-08: official page, UniProt P01375 and P06804, and PDB 1TNF downloaded to `data/`.
Run scripts as `python3 -I scripts/tnfa_prep_target.py` etc. from this directory.
Rules and assay: `rules_and_assay.md` (VERIFIED against the page snapshot in `data/`).
Status 2026-10-10: pipeline built and run once on a free T4 (24 designs): no design with credible predicted binding (ipSAE 0.00 for all). User chose to stop at learning level, no GPU rental. See `REPORT.md`, `pilot_findings.md`. Optional relaxed specs in `boltz/`.
