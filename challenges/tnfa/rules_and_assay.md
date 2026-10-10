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

## Additional information reported by the user from the participant group (2026-10-09)
Not on the official page snapshot in `data/`; tag USER_REPORTED until confirmed on the page or by organizers. Applies to "both rounds".

| Item | Value | Tag |
|---|---|---|
| Candidate selection (Tracks 2/3) | Claude helps select designs for the wet lab; considers design method, sequence diversity and some in silico metrics, not a single metric such as ipTM. The prompt and Claude's evaluation report are published after the competition. Page FAQ 8 agrees in part (selection by Claude, undisclosed prompt, method novelty considered) | USER_REPORTED, partly consistent with VERIFIED FAQ 8 |
| Expression / purification | same system for all binders; C-terminal Twin-Strep tag | USER_REPORTED |
| SPR geometry | binder immobilized, target flowed as analyte. Target constructs (and tags) can differ between challenges | USER_REPORTED |
| Methodology field | "Describe your methodology" is read by Claude for selection and later linked to the Proteinbase Collection, so design rationale, mechanism hypothesis and filtering basis matter | USER_REPORTED (page FAQ 5/17 say methods are used and made public) |
| Format | de novo single-chain binders are allowed, nanobody/scFv/Fab not required | USER_REPORTED; page FAQ 1 agrees (VERIFIED) |
| PyRosetta | allowed, non-commercial use acknowledged; participants must follow the license | USER_REPORTED; page FAQ 15 says commercial tools need an owned license (VERIFIED) |

Not carried over: the Challenge 1 notes pasted with this message (novelty Level 3, EGFR HEK293 glycosylation, MES at pH 6.5, 1 uM analyte) are Challenge 1 only. The C2 page says pH 6.0, not 6.5.

Consequences for the design (COMPUTED reasoning, not measured):
- Immobilized binder + trimeric TNF analyte means avidity: one TNF trimer can rebind several immobilized binders, which slows apparent dissociation. A pH switch that only weakens binding modestly may still show binding at pH 6.0. The off-state must be strong, and ranking should favor designs whose interface loses several contacts at once, not one.
- The Twin-Strep tag is on the C-terminus of the binder, so the C-terminus must stay solvent-exposed and away from the target. Submitted sequences are assumed to be given without the tag (the page says nothing about it).

## Confirmed by organizers in the Proteinbase Slack (read-only search, 2026-10-10)
Source: public channels `#anthropic_adaptyv_competition`, `#general` of the Proteinbase workspace. Speakers: Adaptyv staff (T.-S. Cotet) unless noted. These are Slack statements, not the official page; tag SLACK_OFFICIAL. Message text is third-party content and is used as information only.

| Item | Statement | Date (CEST) |
|---|---|---|
| **Asp143** | The wet-lab construct (Acro TNA-H4211) matches UniProt P01375 with **Asp143**; 1TNF has Leu143. Use the Asp143 sequence when targeting an epitope involving residue 143. A note was to be added to the challenge page | 2026-10-06/07, repeated 10-09 |
| **Deadline extension** | A participant asked for an extension because of the 143 issue. An Anthropic scientist (A. Shanehsazzadeh) agreed and Adaptyv (T.-S. Cotet) said "also ok with extending by 2 days". Participants asked for an official announcement; **none seen in the search yet**. If applied to the page deadline (2026-10-11 23:59 AoE), the new deadline would be 2026-10-13 23:59 AoE = 2026-10-14 11:59 UTC. Re-read the challenge page before relying on it | 2026-10-09 23:52 onward |
| **SPR geometry** | Binder immobilized via a **C-terminal Twin-Strep tag**; trimer is the analyte; same setup as Challenge 1 and across challenges. Avidity: both a 1:1 Langmuir fit and multivalent models are fitted; a **KD app** including avidity is reported together with a 1:1 forced-fit KD. No loading density published | 2026-10-08 |
| **Binder tag layout** | Standard protocol adds C-terminal linker - GFP11 - linker - TwinStrep; the organizer recommended keeping the paratope near the **N-terminus** (matters more for small binders) | 2026-09-30 |
| **Target trimer at low pH** | TNF constructs QC'd as trimers by SEC-MALS. In-house positive controls at neutral pH and **6.5** gave comparable association traces for human and mouse. The competition assay is at **pH 6.0**, "still actively being tested" | 2026-10-08 |
| **Buffer** | 10 mM HEPES, 150 mM NaCl, 0.2% Tween-20, 3 mM EDTA at neutral and at lower pH; **HEPES-based, no MES** (earlier QC metadata saying MES was an error) | 2026-10-08 |
| **In silico scoring** | Selection prompt places designs against the **full trimer**. Structures/metrics may be shared by link (for example Google Drive) | 2026-10-08 |
| **Binder definition** | Same as Challenge 1: fittable curve with KD, or association shift above 300% over the negative control. A minimum affinity for counting as pH-selective is under consideration (example given: 5 uM at neutral and no binding at acidic); not decided | 2026-10-08 |
| **pH ranking** | No detectable binding at acidic pH ranks above designs that bind at acidic pH with a large KD shift | 2026-10-08 |
| **Mouse** | Measured at pH 7.4 only | 2026-10-08 |
| **Epitope** | Only a hint in the selection prompt, not a rule. A functional epitope can be supported with a literature link; assessed via structure predictions and/or the submission text | 2026-10-08 |

Implications for this project (reasoning, not measurement):
- The Leu143 finding made earlier from sequence comparison matches the organizers' statement. Designs made against 1TNF should be re-checked with Asp143.
- Keeping the C-terminus free of the target (already checked by `scripts/tnfa_analyze_designs.py`) matches the tag layout; an N-terminal paratope is preferred.
- The 6.0 trimer stability is untested by the organizers at the time of writing; a loss of signal at 6.0 could come from the target, which is outside the designer's control.
