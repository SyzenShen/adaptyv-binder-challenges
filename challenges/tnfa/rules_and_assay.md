# Challenge 2 rules and assay (VERIFIED against official page, fetched 2026-10-08)

Source: https://proteinbase.com/competitions/anthropic-adaptyv-2026/challenges/tnf-alpha
Raw text snapshot: `data/proteinbase_c2_page_2026-10-08.txt`. The page text is the authority; this table is a summary.
Tags: VERIFIED = read from the page or a downloaded file; COMPUTED = derived here; NOT_STATED = the page does not say.

| Field | Value | Tag |
|---|---|---|
| Target | soluble, trimeric TNF-alpha (3 receptor-binding sites at protomer interfaces) | VERIFIED |
| Recommended epitope | receptor-binding site between two protomers (also the adalimumab / infliximab site) | VERIFIED |
| Human reference | UniProt P01375-1, residues 77-233 (157 aa), assay product TNA-H4211, tag-free | VERIFIED |
| Structure reference | PDB 1TNF chains A-C (apo trimer) | VERIFIED |
| Mouse construct | sequence NOT given on the page; carries a C-terminal polyhistidine tag. Page: 79% identical to human (124/156 aligned). Both constructs are trimers by SEC-MALS (human 45-62 kDa, mouse 50-65 kDa) | VERIFIED |
| Mouse reference used here | UniProt P06804 residues 80-235 (`data/P06804_mouse.fasta`, mature domain starts `LRSSSQNSS`); 124/156 identical with 1 gap, matching the page's 79% | COMPUTED (the exact assay construct is NOT_STATED) |
| Ranking (in order) | 1. binds human at pH 7.4 and NO detectable binding at pH 6.0; 2. also binds mouse (pH 7.4); 3. affinity to human | VERIFIED |
| Assay | binding/affinity, human at pH 7.4 and pH 6.0, mouse at pH 7.4. Method, immobilization, buffer, concentration range: NOT_STATED | VERIFIED / NOT_STATED |
| Winner logic (FAQ 3) | a weak but clearly pH-sensitive binder may beat a high-affinity binder that is not pH-sensitive; affinity thresholds apply | VERIFIED |
| Deadline | Sun 2026-10-11 23:59 AoE (UTC-12) = 2026-10-12 11:59 UTC = 2026-10-12 13:59 Europe/Berlin | VERIFIED date, COMPUTED conversion |
| Length | 10-250 aa, single chain | VERIFIED |
| Formats / molecule_class | `protein`, `nanobody`, `scfv`, `fab_kappa`, `fab_lambda`; Fab as `{VH}:{VL}`; nanobody/antibody judged by ANARCI | VERIFIED |
| Submission file | CSV ordered by preference (top = best); required columns `name` (unique), `sequence`, `molecule_class`; extra metrics/methods encouraged | VERIFIED |
| Designs per participant | Track 1: 20-40 (top 20 passing filters screened); Tracks 2 and 3: at most 20 | VERIFIED |
| Tracks 2/3 selection | all submissions plus submitted info go to Claude with an undisclosed prompt; embedded instructions / prompt injection can disqualify | VERIFIED |
| Hard filters | unique; de novo and zero-shot (no starting binder, no modifying an existing binder); sequence and structural diversity from known proteins. Known binders may be used to calibrate filters or train models | VERIFIED |
| Tools | any tool you may legally use; commercial tools (e.g. Rosetta) only with an owned license | VERIFIED |
| Data / IP | all submitted data and methods may be made public; sequences under ODC-BY | VERIFIED |
| Submit via | Proteinbase account (anonymous allowed) -> challenge page -> CSV + workflow form | VERIFIED |

Design consequences (COMPUTED, for P2):
- Objective 1 is the pH switch. The page gives no mechanism; the usual approach is histidine at the interface (pKa about 6-6.5), but this is a hypothesis to test, not a stated rule.
- Mouse cross-reactivity favors an epitope conserved between human and mouse, so the 124/156 conserved positions at the interface matter.
- The target is a trimer, so avidity may mask pH sensitivity; the assay format is NOT_STATED.

Do not carry over from Challenge 1: HEK293 glycosylation claims, MES/HEPES recipe, tag, orientation, KD-shift tolerance.
