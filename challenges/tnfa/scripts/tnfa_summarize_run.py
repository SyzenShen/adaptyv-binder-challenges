"""Summarize one or more BoltzGen output folders (reads final_ranked_designs/all_designs_metrics.csv).

Usage: python3 -I scripts/tnfa_summarize_run.py LABEL=PATH_TO_RUN_DIR [LABEL=PATH ...]
Prints min / median / max of ipTM, ipSAE and min interface PAE and how many designs passed all BoltzGen filters.
Pilot reference (12 hotspots, 24 designs, T4): ipTM 0.11/0.15/0.30, ipSAE 0.00/0.00/0.00, min PAE 13.9/19.3/23.2 A, 1 passed.
"""
import csv
import statistics as st
import sys
from pathlib import Path

KEYS = ("design_to_target_iptm", "design_ipsae_min", "min_design_to_target_pae")


def num(r, k):
    try:
        return float(r[k])
    except (KeyError, ValueError):
        return float("nan")


def summarize(label, run_dir):
    path = Path(run_dir) / "final_ranked_designs" / "all_designs_metrics.csv"
    rows = list(csv.DictReader(open(path)))
    parts = [label, f"n={len(rows)}"]
    for k in KEYS:
        v = [num(r, k) for r in rows]
        parts.append(f"{k}: {min(v):.2f} / {st.median(v):.2f} / {max(v):.2f}")
    parts.append("passed all filters: %d" % sum(r.get("pass_filters") == "True" for r in rows))
    print(" | ".join(parts))


def main(argv):
    if not argv:
        sys.exit(__doc__)
    for a in argv:
        label, _, path = a.partition("=")
        try:
            summarize(label, path)
        except Exception as e:
            print(label, "failed:", repr(e))


if __name__ == "__main__":
    main(sys.argv[1:])
