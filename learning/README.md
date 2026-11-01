# Learning log

Goal of this folder: understand, line by line, the code this project uses, well enough to change it on purpose. The competition result is not the goal.

## How we work
- Predict before you run: write one sentence (output, shape) before executing anything.
- No code you cannot rewrite from memory. If a block is unclear, take it apart until it is.
- The assistant asks first, explains in small pieces, and asks you to predict the next step. It does not hand over finished code to copy.
- Bug checks: the assistant may quietly change 1-3 places in code you believe you understand (silent logic errors, not syntax errors). You find them.
- Every level ends with a check that can fail. Not passing is information, not a problem.

## Level 0: diagnosis
For each line of a file, mark: understood / roughly / no idea. The roughly/no-idea lines are the syllabus.
- [`00_diagnosis_tnfa_trimer_clash.md`](00_diagnosis_tnfa_trimer_clash.md): first worksheet (65 lines of numpy: broadcasting, centering, SVD, distances).

## Progress (estimated by checkpoints, not hours)
| Level | State |
|---|---|
| 0 diagnosis | worksheet created, not yet marked by the learner |
| 1 tensors, shapes, autograd | shapes, indexing, broadcasting done; `norm(axis=)` in progress; autograd and training loop not started |
| 2 attention | not started |
| 3 protein language model | not started |
| 4 fine-tuning | not started |
| 5 change a design repo | not started |

First file (`challenges/tnfa/scripts/tnfa_trimer_clash.py`): broadcasting for all-pairs differences understood; `norm(axis=2)` in progress; counting clashes, centering and the SVD superposition not yet covered.

## Log
| Date | What was done | What was predicted | What happened | What I learned |
|---|---|---|---|---|
| 2026-10-22 | numpy shapes: (3,) vs (1,3), indexing, broadcasting, `None` axes | A (3,3) right; B/C shapes wrong (thought (3,3) and (1,3), real (3,)); D guessed error, real: broadcast | Rule: right-align, each position equal or 1, size-1 stretches, both sides can stretch | `a[1]` drops a dimension, `a[1:2]` keeps it; `(N,1,3)-(1,M,3)` gives all pairs |
| 2026-11-01 | `norm(axis=)` and what `None` placement means | dist shape (3,3) right; axis=0/1 predicted as vectors, real shape (3,3) | A named axis disappears; broadcasting aligns positions, not meaning; the merged axis must be the xyz axis | A wrong-but-running `None` placement is a silent bug; xyz can sit in the middle if `norm` uses that axis |
| 2026-11-01 | indexing a 3-D array; what merging the wrong axis means | d3 shape right; `d3[0,:,1]` predicted as 3x3 with -1 in y, real (3,) = [-1,0,0]; axis=0 'has meaning' (wrong), but identified it merges i | Integer indices drop axes (two ints -> 1-D); axis=0 here mixes different atoms' x-differences, not a pair distance | Read subscripts position by position before computing |

