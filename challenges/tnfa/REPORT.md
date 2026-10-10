# TNF-alpha conditional binder: what was done and what was learned

Written 2026-10-10. Purpose of the project for the user: learning. No GPU was rented. Everything below is either measured (from files in this repository or the user's Colab/Drive output) or labelled as a hypothesis.

## Outcome in one paragraph
Target data, rules, the receptor-defined epitope and a BoltzGen design pipeline were built and run end to end once on a free Colab T4 (24 designs). **No design showed credible predicted binding** (ipTM 0.11-0.30, ipSAE 0.00 for all 24; only 1 of 24 passed BoltzGen's default filters). Nothing was measured experimentally, so no claim about binding, affinity, mouse cross-reactivity or pH selectivity is made.

## What was built (all in `challenges/tnfa/`)
| Step | Result | Where |
|---|---|---|
| Official rules and assay | verified against the Proteinbase page; extra points from the group chat kept as USER_REPORTED | `rules_and_assay.md`, `data/proteinbase_c2_page_2026-10-08.txt` |
| Target data | 1TNF, UniProt P01375 and P06804 (mouse), complexes 7KP7 (TNFR1), 3WD5 (adalimumab), 4G3Y (infliximab) | `data/` |
| Receptor site | 29 contact residues across two protomers, all identical in human and mouse | `receptor_epitope.md`, `data/receptor_site.json` |
| Design inputs | BoltzGen specs with correct residue index mapping | `boltz/`, `scripts/tnfa_make_boltzgen_inputs.py` |
| Colab pipeline | pilot-then-scale notebook with a GPU-hour cap | `cloud/tnfa_boltzgen_colab.ipynb` |
| CPU checks | trimer clash, C-terminus (Twin-Strep) clearance, hotspot contacts | `scripts/tnfa_trimer_clash.py`, `scripts/tnfa_analyze_designs.py` |

## Measured numbers (T4, BoltzGen 0.3.2, 24 designs)
- 423 s per design in total: design 162 s, folding 222 s (the largest cost), design_folding 31 s, the rest under 10 s.
- Filters passed: refold RMSD 1, design RMSD 11, design-folding RMSD 15, Ala fraction 22, Gly fraction 22; all filters together: 1.
- Sequence classes among the 24 raw designs: at least 9 antibody-like frameworks, 2 close to human ubiquitin, 3 low-complexity, the rest helical bundles or Ig/fibronectin-like (see `pilot_findings.md`).

## Mistakes made along the way, and what they teach
1. **A first epitope choice based only on geometry was wrong.** The SASA rule (P3) overlapped the real receptor site by 5 of 8 and 1 of 6 residues. Comparing with a receptor complex (7KP7) exposed it. Lesson: check any epitope heuristic against a structure of the real binding partner.
2. **The crystal structure differs from the assay protein.** 1TNF has Leu143 where wild type has Asp143, and D143 is a receptor and adalimumab contact. The organizers later confirmed this in Slack (assay construct Acro TNA-H4211 = Asp143), and other teams reported having designed against Leu143 and needing rework. Lesson: always align the structure sequence to the reference sequence before designing.
3. **Index conventions.** BoltzGen counts resolved residues (1TNF lacks residues 1-5), so mature number n is position n-5. Lesson: write a self-check that compares amino acids at every constrained position.
4. **Model cache on Google Drive corrupted a zip** (`BadZipFile`). Hugging Face caches use symlinks that Drive does not support. Lesson: cache on local disk, keep results on Drive.
5. **The notebook hid errors.** Output of a subprocess did not appear in the cell, so a 9 s failure showed no reason. Lesson: stream and log subprocess output.
6. **A file-format trap in my analysis.** BoltzGen writes ungenerated atoms at (0, 0, 0); until filtered, every design looked like it clashed. Lesson: when a result looks too uniform to be physical, look at raw atoms before believing it.
7. **Files that git silently ignored.** `*.pdb` was in `.gitignore`, so the 1TNF files were never committed in the first pushes. Lesson: check a fresh clone, not the working directory.
8. **Commit authorship decides the GitHub contribution graph**, not the push. Commits authored as the assistant did not count for the user.

## What the numbers say about the method
- Confidence of the refolded complex is the only evidence available here, and it is near the floor. Reasons not tested: only 24 designs (BoltzGen's default is 10,000), a tight 12-hotspot specification over two protomers, bf16 on a T4, refolding without target MSA or templates.
- A T4 at 423 s per design cannot produce thousands of designs in the available time; a faster GPU was out of scope by choice.

## If this is continued (all free-tier options, none run)
- `boltz/tnfa_e3_min.yaml` (4 hotspots) and `boltz/tnfa_e3_min_helical.yaml` (experimental, fixed length 80, three helices). Run cell D (`boltzgen check`) first, then a pilot of 8-12 designs, and compare ipTM and ipSAE with the table above.
- Compare the refolded confidence of the wild-type target (Asp143) with the 1TNF version.
- Do not read any in silico score as evidence of a pH switch; only the assay can show that.
