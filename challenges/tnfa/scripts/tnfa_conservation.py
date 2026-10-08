"""P2: human vs mouse TNF-alpha conservation on the 1TNF numbering, joined with the trimer interface.

Outputs data/conservation_interface.json and prints a summary.
Alignment: Needleman-Wunsch (identity +1, mismatch -1, gap -2), mouse = UniProt P06804 mature domain.
"""
import json
from pathlib import Path

D = Path(__file__).resolve().parents[1] / "data"


def fa(p):
    return "".join(l.strip() for l in open(p) if not l.startswith(">"))


def nw(a, b, g=-2):
    M, N = len(a), len(b)
    S = [[0] * (N + 1) for _ in range(M + 1)]
    for i in range(M + 1): S[i][0] = g * i
    for j in range(N + 1): S[0][j] = g * j
    sc = lambda x, y: 1 if x == y else -1
    for i in range(1, M + 1):
        for j in range(1, N + 1):
            S[i][j] = max(S[i-1][j-1] + sc(a[i-1], b[j-1]), S[i-1][j] + g, S[i][j-1] + g)
    i, j, pairs = M, N, {}
    while i and j:
        if S[i][j] == S[i-1][j-1] + sc(a[i-1], b[j-1]):
            pairs[i] = b[j-1]; i -= 1; j -= 1
        elif S[i][j] == S[i-1][j] + g:
            i -= 1
        else:
            j -= 1
    return pairs


def main():
    h = fa(D / "P01375.fasta")[76:233]
    m = fa(D / "P06804_mouse.fasta")
    m = m[m.find("RSSSQNSS") - 1:]
    pairs = nw(h, m)  # human mature index (1-based, 1 = V77) -> mouse aa
    iface = json.load(open(D / "interface_residues.json"))["chains"]
    contacts = {}
    for c, rows in iface.items():
        for r in rows:
            contacts.setdefault(r["res"], set()).add(c)
    rows = []
    for i in range(1, len(h) + 1):
        mo = pairs.get(i, "-")
        rows.append({"res": i, "uniprot": 76 + i, "human": h[i-1], "mouse": mo, "conserved": h[i-1] == mo,
                     "interface_chains": "".join(sorted(contacts.get(i, [])))})
    json.dump(rows, open(D / "conservation_interface.json", "w"), indent=1)
    cons = [r for r in rows if r["conserved"]]
    ic = [r for r in rows if r["interface_chains"]]
    icc = [r for r in ic if r["conserved"]]
    print(f"conserved {len(cons)}/{len(rows)}; interface residues (any chain) {len(ic)}, conserved among them {len(icc)}")
    print("interface non-conserved:", " ".join(f"{r['human']}{r['res']}{r['mouse']}" for r in ic if not r["conserved"]))


if __name__ == "__main__":
    main()
