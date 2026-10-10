# HANDOVER (Claude Code takeover, 2026-10-08)

Status tags: VERIFIED = checked in this session against files/commands; USER_REPORTED = from the handover prompt only;
NOT_AVAILABLE = not reachable from this environment; NEEDS_REVIEW = conflicting or unproven.

| Item | Tag | Evidence / note |
|---|---|---|
| Repo SyzenShen/egfr-binder-challenge (renamed 2026-10-08 to adaptyv-binder-challenges), main @ c4de97c, remote matches (`git ls-remote`) | VERIFIED | working tree clean at takeover |
| Work branch `claude/funny-maxwell-mfws7z` | VERIFIED | created for Challenge 2 |
| STATE/RUNBOOK/DECISIONS/HUMAN_ACTIONS/README exist; no CLAUDE.md before this commit | VERIFIED | |
| Existing tests: 166 passed, 1 skipped, 1 failed (Python 3.13, fresh pip deps) | VERIFIED | failure `test_generator_rebuild_matches_committed_artifact`: committed `data/processed/target_residue_map.json` embeds an absolute macOS path (`/Users/shenyz/...`), so the rebuild differs on any other machine. Environment artifact, not a science error. Not fixed yet (low priority). |
| BindCraft pin 7713aa0d..., patch `patches/bindcraft-7713aa0-relax-tolerance.patch` (per-model relax tolerance) | VERIFIED (files exist) | patch effect not re-run here |
| EGFR smoke run, mpnn4 accepted, Drive artifacts under /content/drive/... | USER_REPORTED / NOT_AVAILABLE | repo docs mention `EGFR_D3_Bcons_l80_s313440_mpnn4` as an "Accepted is not the end" case; PDB/CSV/logs themselves are not in this checkout |
| mpnn9 missing relaxed PDB; cause | NEEDS_REVIEW | not attributed to GPU quota without logs |
| Colab T4 15 GiB measured | USER_REPORTED (recorded in STATE.md) | |
| EGFR_H433_submission.zip, 120 reviewed / 20 selected, 225-residue crop | NOT_AVAILABLE | no zip in repo. This is the supervisor's package, not the user's own run. Submission success unconfirmed without a receipt. |
| Any wet-lab data | NOT_AVAILABLE | `experimentally_validated = false`; unknown metrics are null |
| Challenge 2 official pages | VERIFIED (2026-10-08, after network policy set to Full) | snapshot in `challenges/tnfa/data/`; summary in `challenges/tnfa/rules_and_assay.md` |
| UniProt P01375 / RCSB 1TNF download | VERIFIED | P01375 77-233 equals the page sequence; 1TNF has chains A, B, C (152 CA each, 157-residue SEQRES) |
| LinkedIn / X announcements | NOT_AVAILABLE | not attempted (login-gated, and egress restricted) |

## Time warning
Handover says the Challenge 2 page deadline is 2026-10-11 23:59 AoE. That is UTC-12, i.e. 2026-10-12 11:59 UTC
= 2026-10-12 13:59 Europe/Berlin (CEST, UTC+2). Today is 2026-10-08. Roughly 3.5 days remain; this is USER_REPORTED
and must be re-read from the official page.


## Update 2026-10-10
Deadline: a 2-day extension was agreed in Slack by Anthropic and Adaptyv staff on 2026-10-09 (not yet seen as an official announcement). See `rules_and_assay.md`, section "Confirmed by organizers in the Proteinbase Slack". Slack is connected read-only for this project; nothing was posted.
