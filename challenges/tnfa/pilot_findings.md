# Pilot run findings (24 raw BoltzGen designs, `tnfa_e3_core`, protein-anything, T4)

Date 2026-10-09. Raw `intermediate_designs_inverse_folded` output, before BoltzGen's folding/filtering steps finished. Sequences are not committed (not submissions); numbers below are COMPUTED from the uploaded files.

## Speed (measured on the user's Colab T4)
- Step 1 design: 24 designs in 1 h 03 min = about 158 s per design (batch size 1, bf16-mixed, kernels off on this GPU). Step 2 inverse folding: 40 s for 24. Steps 3-6 timing: pending.
- At this rate 3 h of design time is about 68 designs. Pass rate after filtering: pending.

## File-format trap (fixed in `scripts/tnfa_analyze_designs.py`)
BoltzGen writes ungenerated atoms at (0, 0, 0): 403 of 3229 atoms in design 00. Any distance analysis must drop them; before the fix every design appeared to have its C-terminus 1-3 A from the target, which was an artifact. Side-chain coordinates in these intermediate files are incomplete, so interface histidine counts from them are unreliable. Use the refolded complexes for that.

## What the sequences look like (rough classification by sequence motifs, not ANARCI)
- 9 of 24 carry antibody-like framework motifs (heavy-chain FR4 `WGQGT`: 5; light-chain FR4 `FGxGTK`: 6, some overlap not counted twice in the table by hand): these would be read as nanobody/antibody-like designs, not de novo mini-proteins.
- 2 of 24 are 91% and 96% identical to human ubiquitin (identity against a reference typed from memory; confirm before relying on it). This is a natural protein, not a de novo design.
- 3 of 24 are low-complexity (poly-Ala/Gly-rich, Shannon entropy 1.3-2.8 bits).
- The remaining 10 include helical bundle-like and Ig/fibronectin-like sequences.
Competition rules (page FAQ 8): designs must be de novo and zero-shot, with adequate sequence and structural diversity from known proteins; nanobody/antibody status is judged by ANARCI and then CDR diversity matters. So many raw designs would not qualify or would need to be submitted under a different class. The filter step may remove some; this has to be re-checked on the final ranked set.

## Geometry (after dropping (0,0,0) atoms)
- 22 of 24 binders touch both protomers; design 07 and 11 touch only one.
- Hotspots touched out of 12 range from 2 to 12; 12 designs touch 10 or more (several of the low-complexity ones touch all 12).
- No design collides with the third protomer (0 atoms within 2.5 A). C-terminus to target distance: 2.4-21 A; 5 designs have it under 3 A (07 not, 11, 12, 16, 20) and would block the Twin-Strep tag position.
- Nothing here says a design binds or switches with pH.

## Options if the final filtered set stays dominated by antibody-like / ubiquitin-like / low-complexity sequences (not yet tried)
1. Constrain the binder secondary structure (`secondary_structure` in the yaml) toward helical bundles, the classic de novo minibinder fold; fixed length needed.
2. Use residue constraints to limit low-complexity (for example cap Gly/Ala).
3. Run the `nanobody-anything` protocol deliberately and submit as `nanobody` with CDR diversity, if the rules allow it for this challenge.
4. A second model (BindCraft path) for diversity.
