"""Submission sequence validation helpers - standard library only.

Created in phase 0 and reused through phase 7 (final submission checks).
These functions validate FORMAT only. They do not assess binding, pH or
novelty; uncomputed scientific metrics stay null/NA at the caller side.
"""
from __future__ import annotations

# Canonical 20 canonical amino acids, one-letter IUPAC.
AA_ALPHABET = set("ACDEFGHIKLMNPQRSTVWY")


def validate_protein_sequence(seq):
    """Return None if sequence is valid, else a machine-readable error string."""
    if not isinstance(seq, str) or not seq:
        return "empty_sequence"
    illegal = sorted({c for c in seq if c not in AA_ALPHABET})
    if illegal:
        return "illegal_characters:" + "".join(illegal)
    return None


def _chains(seq, molecule_class):
    """Split Fab-style 'VH:VL' strings; single sequence otherwise."""
    if molecule_class in ("fab_kappa", "fab_lambda"):
        parts = seq.split(":")
        return parts if len(parts) == 2 else []
    return [seq]


def validate_row(name, sequence, molecule_class, cfg):
    """Validate one submission row against competition config.

    cfg: parsed configs/competition.json-like mapping.
    Returns a list of error strings (empty list = passed).
    """
    errors = []
    sub = cfg["submission"]

    if not isinstance(name, str) or not name.strip():
        errors.append("missing_name")

    if molecule_class not in sub["molecule_class_allowed"]:
        errors.append("bad_molecule_class")

    if not isinstance(sequence, str) or not sequence:
        errors.append("empty_sequence")
        return errors

    chains = _chains(sequence, molecule_class)
    if not chains:
        errors.append("bad_fab_separator")
        return errors

    for chain in chains:
        msg = validate_protein_sequence(chain)
        if msg:
            errors.append(msg)

    # Length rules apply to single-chain proteins (and minibinder category).
    if molecule_class == "protein" and all(validate_protein_sequence(c) is None for c in chains):
        length = len(sequence)
        if not (sub["single_chain_length_min"] <= length <= sub["single_chain_length_max"]):
            errors.append(
                f"length_out_of_range:{length}:"
                f"{sub['single_chain_length_min']}-{sub['single_chain_length_max']}"
            )
    return errors


def check_uniqueness(rows):
    """rows: iterable of (name, sequence). Return duplicate names/sequences lists."""
    names, seqs = [], []
    for name, seq in rows:
        names.append(name)
        seqs.append(seq)
    dup_names = sorted({n for n in names if names.count(n) > 1})
    dup_seqs = sorted({s for s in seqs if seqs.count(s) > 1})
    return dup_names, dup_seqs
