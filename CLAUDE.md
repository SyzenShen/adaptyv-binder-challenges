# CLAUDE.md
Project: computational protein design for the Anthropic x Adaptyv challenges.
- Challenge 1 (EGFR) history lives in the repo root (STATE.md, DECISIONS.md, reports/, data/). Do not rename or reuse it as TNF output.
- Challenge 2 (TNF-alpha, neutral ON / acid OFF) lives in `challenges/tnfa/`. Branch: claude/funny-maxwell-mfws7z.
- Read HANDOVER_C2.md first for what is verified vs reported.
- Rules: no GPU/cloud/API spend, no account actions, no Proteinbase submission, no legal checkboxes without the user's approval.
  Unknown metrics = null with reason. `experimentally_validated` stays false. Never claim pH switching from distances/Rosetta/MPNN scores.
- Residue mapping must key on chain/protomer instance; never assume chain A = target or a fixed offset.
- Explanations to the user in Chinese; code, public methods and submission text in English.
- Each big step: run targeted tests, commit only task files, push (no force), verify with `git ls-remote`. Push fails -> report LOCAL_ONLY.
- Tests: `python3 -m pytest -q tests` (1 known path-dependent failure, see HANDOVER_C2.md).
