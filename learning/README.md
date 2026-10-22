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

## Log
| Date | What was done | What was predicted | What happened | What I learned |
|---|---|---|---|---|
| 2026-10-22 | numpy shapes: (3,) vs (1,3), indexing, broadcasting, `None` axes | A (3,3) right; B/C shapes wrong (thought (3,3) and (1,3), real (3,)); D guessed error, real: broadcast | Rule: right-align, each position equal or 1, size-1 stretches, both sides can stretch | `a[1]` drops a dimension, `a[1:2]` keeps it; `(N,1,3)-(1,M,3)` gives all pairs |
