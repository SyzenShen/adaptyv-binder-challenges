# TNF-alpha functional epitope from receptor and antibody complexes (P4)

Scripts: `scripts/tnfa_complex_epitopes.py`, `scripts/tnfa_receptor_site.py`. Structures downloaded from RCSB: 7KP7, 3WD5, 4G3Y (`data/`). Contact = heavy atom within 4.5 A. All values COMPUTED. Numbering = mature TNF numbering (1 = V77 of P01375).

## Structures used
| Entry | What | TNF species | Note |
|---|---|---|---|
| 7KP7 | TNF trimer + human TNFR1 (3 receptors, chains D-F) | **mouse** (81% identical to human) | the receptor site as it exists on mouse TNF |
| 3WD5 | TNF + adalimumab Fab | human | one TNF chain in the entry |
| 4G3Y | TNF + infliximab Fab | human | one TNF chain in the entry |

## Receptor-binding site (best receptor, 7KP7 chain E)
Two protomers contribute. Superposed on 1TNF the pair is chain B (main) + chain A (other), RMSD about 1.0 A; the symmetry-equivalent pairs (C,B) and (A,C) give 1.0-1.1 A, the wrong-handed pairs 9 A.
- main protomer (1TNF chain B): Q21, R32, A33, K65, G66, Q67, E110, P113, Y115, D143, F144, A145, E146, S147, Q149
- other protomer (1TNF chain A): V74, L75, T77, R82, S86, Y87, Q88, K90, V91, N92, Q125, E127, E135, N137
- **All 29 positions are identical in human and mouse** (checked against `data/conservation_interface.json`, which is aligned to P06804). So the functional site is naturally cross-reactive.

## Antibody sites (for orientation only)
- adalimumab: P20 Q21 E23 K65 G66 Q67 E110 A111 P113 Y115 D140 Y141 D143 F144 A145 E146 S147
- infliximab: E23 G24 Q67 G68 P70 S71 H73 V74 L75 T77 I97 T105-A111 N137-Y141
Both overlap the receptor site (Q21, K65-Q67, E110, P113, Y115, D143-S147 for adalimumab; Q67, V74, L75, T77, N137 for infliximab).

## Correction to P3
`epitope_selection.md` (SASA rule) chose E1 and E2 without a complex. Against the receptor site: E1 overlaps 5 of 8 positions (75, 92, 115, 125, 147; misses K112, E116, Y119), E2 overlaps 1 of 6 (A33). The SASA rule only picks residues partly buried by trimerization, so it misses surface residues of one protomer that the receptor touches (Q21, K65-Q67, D143-A145). **Use the receptor-defined site (E3) below; E1/E2 are superseded.**

## E3 hotspot proposal (design target)
- Core, both protomers, high contact density: Y87 and V91 and N92 (other), Y115 and F144 and E146 and S147 (main), L75 (other).
- Charged anchors on the main protomer: R32, E146, E110, D143, K65. These are candidates for pH-dependent interactions only as a hypothesis.
- Target both protomers at once: designs should span the A/B groove, not one subunit.

## pH switch: what is known and not known
- Not stated by the competition: any mechanism. Hypothesis only: His in the binder placed against a conserved acidic or aromatic site residue (E110, E146, D143, Y115) so that protonation near pH 6 breaks the contact.
- Receptor-site residues on TNF itself contain no His (native H15 and H73 are outside the site). So the switch has to come from the binder.
- Never claim pH switching from distances, Rosetta or MPNN scores (project rule). Only the assay can show it.

## Design tools in this environment (checked 2026-10-08)
- No GPU, no torch, no jax, no ColabDesign, no OpenMM, no PyRosetta, no Biopython/scipy. 4 CPU cores, 15 GB RAM.
- So structure prediction and sequence design cannot run here. P5 needs external compute (Colab T4 15 GiB was USER_REPORTED in STATE.md) and the user's approval, per project rules.
