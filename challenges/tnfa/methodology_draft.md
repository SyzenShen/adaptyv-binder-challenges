# Methodology (draft for the Proteinbase "Describe your methodology" field)

Status: DRAFT with real numbers from one pilot run. Factual text only; no instructions addressed to a reviewer. Submission itself is the user's decision (see REPORT.md); this text must be adjusted to whatever is actually submitted.

## Target and epitope
- Target: soluble trimeric human TNF-alpha (P01375 residues 77-233). Structure basis: PDB 1TNF chains A-C.
- Epitope: the receptor-binding site between two adjacent protomers, taken from the TNFR1 complex 7KP7 (mouse TNF + human TNFR1) and superposed onto 1TNF (RMSD about 1.0 A). The adalimumab (3WD5) and infliximab (4G3Y) contacts overlap this site.
- All 29 receptor-contact positions are identical in human and mouse TNF-alpha (alignment to P06804), so one epitope serves the human and mouse objectives.
- Known difference: 1TNF has Leu143 where the wild-type construct has Asp143. Residue 143 was not used as a hotspot. Designs were not re-checked against the wild-type sequence.

## Design method
- BoltzGen 0.3.2, protocol `protein-anything`, against two protomers (1TNF chains B and A, 314 tokens), binder length 70-130, 12 residue-level binding constraints (8 on one protomer, 4 on the other), cysteine excluded at inverse folding. One free Colab T4 GPU.
- 24 designs were generated (design step 1 h 03 min, whole pipeline 2 h 49 min), then inverse folding, refolding of the complex with Boltz-2, analysis and filtering with BoltzGen's default thresholds.
- De novo and zero-shot by construction: no existing binder, antibody or receptor sequence was used as a starting point. Known complexes defined the epitope only. Several raw designs nevertheless resemble antibody frameworks or ubiquitin (see below).

## Results of the pilot (no experiments were done)
- 1 of 24 designs passed all default filters; 8 final and 10 further designs were ranked after relaxing.
- Refolded complex confidence over all 24 designs: design-to-target ipTM 0.11-0.30 (median 0.15), ipSAE 0.00 for every design, minimum interface PAE 13.9-23.2 A. Even the design that passed all filters (77 residues, 86% helix) has ipTM 0.28 and ipSAE 0.00.
- Sequence classes among the 24 raw designs: at least 9 antibody-like frameworks, 2 close to human ubiquitin, 3 low-complexity, the rest helical bundles or Ig/fibronectin-like.

## Not done
- No re-folding against the wild-type target or against mouse TNF.
- No sequence clustering for diversity, no interface-histidine analysis of refolded complexes.
- No design has evidence of binding. The pH-switch hypothesis (histidines in the binder facing conserved acidic or aromatic epitope residues Glu110, Glu146, Asp143, Tyr115) was not applied or tested; no tool used here predicts pH dependence.
- The assay immobilizes the binder and flows trimeric TNF, so avidity could mask a weak pH effect; this was not modelled.
