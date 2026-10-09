# Pilot run findings (24 raw BoltzGen designs, `tnfa_e3_core`, protein-anything, T4)

Date 2026-10-09. Raw `intermediate_designs_inverse_folded` output, before BoltzGen's folding/filtering steps finished. Sequences are not committed (not submissions); numbers below are COMPUTED from the uploaded files.

## Speed (measured on the user's Colab T4)
- Step 1 design: 24 designs in 1 h 03 min = about 158 s per design (batch size 1, bf16-mixed, kernels off on this GPU). Step 2 inverse folding: 40 s for 24. Steps 3-6 timing: pending.
- At this rate 3 h of design time is about 68 designs. Pass rate after filtering: pending.

## File-format trap (fixed in `scripts/tnfa_analyze_designs.py`)
BoltzGen writes ungenerated atoms at (0, 0, 0): 403 of 3229 atoms in design 00. Any distance analysis must drop them; before the fix every design appeared to have its C-terminus 1-3 A from the target, which was an artifact. Side-chain coordinates in these intermediate files are incomplete, so interface histidine counts from them are unreliable. Use the refolded complexes for that.

## What the sequences look like (rough classification by sequence motifs, not ANARCI)
- 9 of 24 carry antibody-like framework motifs by regex: heavy-chain FR4 `WGQGT` in 5 (00, 03, 14, 15, 21) and light-chain FR4 `FGxGTK` in 4 (01, 02, 05, 07). By eye 18, 19 and 22 also look like light-chain variable domains, and 12 and 13 like heavy-chain ones, so the real count is higher (ANARCI not run). These would be read as nanobody/antibody-like designs, not de novo mini-proteins.
- 2 of 24 are 91% and 96% identical to human ubiquitin (identity against a reference typed from memory; confirm before relying on it). This is a natural protein, not a de novo design.
- 3 of 24 are low-complexity (poly-Ala/Gly-rich, Shannon entropy 1.3-2.8 bits).
- The remaining 10 include helical bundle-like and Ig/fibronectin-like sequences.
Competition rules (page FAQ 8): designs must be de novo and zero-shot, with adequate sequence and structural diversity from known proteins; nanobody/antibody status is judged by ANARCI and then CDR diversity matters. So many raw designs would not qualify or would need to be submitted under a different class. The filter step may remove some; this has to be re-checked on the final ranked set.

## Geometry (after dropping (0,0,0) atoms)
- 22 of 24 binders touch both protomers; design 07 and 11 touch only one.
- Hotspots touched out of 12 range from 2 to 12; 12 designs touch 10 or more (several of the low-complexity ones touch all 12).
- No design collides with the third protomer (0 atoms within 2.5 A). C-terminus to target distance: 2.4-21 A; 4 designs have it under 3 A (11, 12, 16, 20) and would block the Twin-Strep tag position.
- Nothing here says a design binds or switches with pH.

## Options if the final filtered set stays dominated by antibody-like / ubiquitin-like / low-complexity sequences (not yet tried)
1. Constrain the binder secondary structure (`secondary_structure` in the yaml) toward helical bundles, the classic de novo minibinder fold; fixed length needed.
2. Use residue constraints to limit low-complexity (for example cap Gly/Ala).
3. Run the `nanobody-anything` protocol deliberately and submit as `nanobody` with CDR diversity, if the rules allow it for this challenge.
4. A second model (BindCraft path) for diversity.

## Final pilot result (all 6 BoltzGen steps finished; read from Drive `all_designs_metrics.csv`, 24 rows)
Wall time 10150 s = 423 s per design on a T4: design 3881 s, inverse folding 66 s, **folding 5323 s (222 s per design, the largest cost)**, design_folding 747 s, analysis 99 s, filtering 27 s.

Filters (BoltzGen defaults): refold-vs-design RMSD under 2.5 A passed by 1 of 24; design RMSD 11; design-folding RMSD 15; Ala fraction 22, Gly fraction 22. **Only 1 design passed all filters** (id `04`, a 77-residue helical sequence). BoltzGen then ranked 8 final + 10 more designs by relaxing.

Binding confidence of the refolded complex (Boltz-2 inside BoltzGen), min / median / max over the 24:
- design-to-target ipTM: 0.11 / 0.15 / 0.30
- ipSAE (design_ipsae_min): 0.00 / 0.00 / 0.00
- min design-to-target PAE: 13.9 / 19.3 / 23.2 A
- Even the one design that passed all filters (rank 1, id 04) has ipTM 0.28, min PAE 14.5 A, ipSAE 0.00.
- The `designfolding-*` interface columns are placeholders (ipTM 0, PAE 100000) because that step folds the binder alone; only its RMSD columns mean something.
For comparison, the Anthropic technical report scores designs by ipSAE and reports target-averaged medians around 0.74-0.79 and best designs around 0.81-0.83 (single H200, 24 h).

Conclusion (COMPUTED from these numbers): none of the 24 designs has credible predicted binding to the target. Possible reasons, none tested: 24 designs is far below BoltzGen's default of 10,000; 12 forced contacts across two protomers is a hard specification; bf16 on a T4 (no native bf16); refolding without target MSA or templates may lower all confidences.
