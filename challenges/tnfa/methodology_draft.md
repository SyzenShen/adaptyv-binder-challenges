# Methodology (draft for the Proteinbase "Describe your methodology" field)

Status: DRAFT. Every `[TO FILL]` must be replaced with a measured value from a real run, or deleted. No metric below has been computed yet. Plain factual text only; no instructions addressed to a reviewer.

## Target and epitope
- Target: soluble trimeric human TNF-alpha (P01375 residues 77-233). Structure basis: PDB 1TNF chains A-C.
- Epitope: the receptor-binding site between two adjacent protomers, taken from the TNFR1 complex 7KP7 (mouse TNF + human TNFR1) and superposed onto 1TNF (RMSD about 1.0 A). Adalimumab (3WD5) and infliximab (4G3Y) contacts overlap this site.
- All 29 receptor-contact positions are identical in human and mouse TNF-alpha (alignment to P06804), so one epitope serves the human and the mouse objectives.
- Known difference: 1TNF has Leu143 where the wild-type construct has Asp143. Residue 143 was not used as a hotspot, and designs are re-checked against wild-type sequence.

## Design method
- Generative design with BoltzGen 0.3.2 (`protein-anything`) against two protomers (chains B and A, 314 tokens), binder length 70-130, 12 residue-level binding constraints (8 on one protomer, 4 on the other), cysteine excluded at inverse folding. Run on a single Colab T4 under a fixed GPU-hour cap. [TO FILL: number of designs generated, hours used]
- De novo and zero-shot: no existing binder, antibody or receptor sequence was used as a starting point. Known complexes were used only to define the epitope.

## Filtering (CPU, scripts in the repository)
1. BoltzGen's own filtering and diversity selection. [TO FILL: thresholds, counts]
2. No collision with the third protomer of the trimer; binder C-terminus free of the target (the assay places a C-terminal Twin-Strep tag).
3. Re-fold against the wild-type human sequence (Asp143) and against mouse TNF (P06804 80-235). [TO FILL: how many designs kept both]
4. Sequence diversity: submitted designs are chosen from different sequence clusters. [TO FILL: clustering rule, number of clusters]

## pH-selective binding: hypothesis
- No design tool used here predicts pH dependence. The hypothesis is that histidine residues in the binder, facing conserved acidic or aromatic residues of the epitope (Glu110, Glu146, Asp143, Tyr115), lose their contacts when protonated near pH 6.0. [TO FILL: for each submitted design, which histidines and which contacts]
- The assay immobilizes the binder and flows trimeric TNF, so avidity can hide a weak pH effect. Designs whose interface depends on several histidine contacts were preferred over those with one. [TO FILL: how this was applied]

## What was not validated
- No binding, affinity, pH selectivity or mouse cross-reactivity was measured. In silico scores are predictions only and were not used as evidence of a pH switch.
- Ranking of the submitted list: [TO FILL: stated rule, for example cluster representative first, then predicted interface quality, then number of interface histidines].
