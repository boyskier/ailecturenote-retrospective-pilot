"""Analysis 7: AI_LectureNote semantic faithfulness / medical-meaning preservation.

This analysis is inherently human-judged: it compares the AI_LectureNote
(post-processed) output against the reference at the level of medical claims.
The pipeline does not auto-label meaning; it loads the exhaustive human worksheet
``semantic_review.csv`` (one row per reference sentence, built by
``build_review_worksheets.py`` and labeled by the annotator) and summarizes it,
plus extracts the confirmed drift rows for the qualitative table.

CSV schema (annotations/<lecture_id>/semantic_review*.csv):
    claim_id, reference_claim, <condition>_output, label, error_type, why_it_matters

``label`` is one of: Faithful, Minor rewrite, Omission, Addition, Substitution,
Polarity error, Relation error, Unclear (see the paper §5.2).
"""
from __future__ import annotations

import csv
import os
from collections import defaultdict

import config

SEMANTIC_BASE_FIELDNAMES = [
    "claim_id",
    "reference_claim",
    "label",
    "error_type",
    "why_it_matters",
]

# Canonical labels (used for ordering / sanity checking).
LABELS = [
    "Faithful",
    "Minor rewrite",
    "Omission",
    "Addition",
    "Substitution",
    "Polarity error",
    "Relation error",
    "Unclear",
]

DRIFT_LABELS = {"Omission", "Addition", "Substitution", "Polarity error",
                "Relation error"}

# Ordered drift token list (used for taxonomy decomposition of compound labels).
DRIFT_TOKENS = ["Omission", "Addition", "Substitution", "Polarity error",
                "Relation error"]


def drift_tokens_in(label: str) -> list[str]:
    """Drift categories present in a (possibly compound) label, case-insensitive.

    Handles real annotation noise: trailing spaces (``'Omission  '``), lowercase
    (``'omission'``), and compound labels (``'Polarity error, Omission'`` or
    ``'Omission / Addition / Substitution / Polarity error'``). Returns [] for
    Faithful / Minor rewrite / Unclear / blank.
    """
    low = (label or "").strip().lower()
    return [tok for tok in DRIFT_TOKENS if tok.lower() in low]


def classify_label(label: str) -> str:
    """Bucket a raw label into faithful / minor / drift / unclear / '' (blank)."""
    low = (label or "").strip().lower()
    if not low:
        return ""
    if low == "faithful":
        return "faithful"
    if low == "minor rewrite":
        return "minor"
    if drift_tokens_in(label):
        return "drift"
    if "unclear" in low:
        return "unclear"
    return "unclear"  # any other non-empty label is treated as unclear, not dropped


SEMANTIC_REVIEW_CONDITIONS = ["ai_lecturenote", "gpt4o_ailn_post"]


def semantic_review_file(condition: str) -> str:
    if condition == "ai_lecturenote":
        return "semantic_review.csv"
    return f"semantic_review_{condition}.csv"


def semantic_output_field(condition: str) -> str:
    return f"{condition}_output"


def semantic_fieldnames(condition: str) -> list[str]:
    return [
        "claim_id",
        "reference_claim",
        semantic_output_field(condition),
        "label",
        "error_type",
        "why_it_matters",
    ]


def _read_claims(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f)]
    return [r for r in rows if (r.get("claim_id") or "").strip()
            and not (r.get("claim_id") or "").strip().startswith("#")]


def load_semantic_claims(lecture_id: str, condition: str = "ai_lecturenote") -> list[dict]:
    """Authoritative semantic claims: the exhaustive human worksheet
    for the requested condition (one row per reference sentence)."""
    return _read_claims(config.annotation_path(lecture_id, semantic_review_file(condition)))


def summarize_semantic(lecture_id: str, condition: str = "ai_lecturenote") -> dict | None:
    """Count labels for a lecture; None if nothing labeled yet."""
    claims = load_semantic_claims(lecture_id, condition)
    labeled = [c for c in claims if (c.get("label") or "").strip()]
    if not labeled:
        return None
    buckets = defaultdict(int)
    for c in labeled:
        buckets[classify_label(c.get("label"))] += 1
    return {
        "lecture_id": lecture_id,
        "condition": condition,
        "claims_labeled": len(labeled),
        "faithful": buckets.get("faithful", 0),
        "minor_rewrite": buckets.get("minor", 0),
        "semantic_drift": buckets.get("drift", 0),
        "unclear": buckets.get("unclear", 0),
        "counts": dict(buckets),
    }


def drift_examples(lecture_id: str, condition: str = "ai_lecturenote") -> list[dict]:
    """Qualitative drift table rows — confirmed_drift only."""
    claims = load_semantic_claims(lecture_id, condition)
    out = []
    for c in claims:
        label = (c.get("label") or "").strip()
        if classify_label(label) != "drift":
            continue
        row = {"lecture_id": lecture_id, "condition": condition, "status": "confirmed_drift"}
        row.update({k: (c.get(k) or "").strip() for k in semantic_fieldnames(condition)})
        out.append(row)
    return out


def _drift_claim_ids(lecture_id: str, condition: str) -> set[str]:
    """Set of claim_ids that received a drift label for a condition in a lecture."""
    return {
        cid
        for c in load_semantic_claims(lecture_id, condition)
        if classify_label(c.get("label")) == "drift"
        and (cid := (c.get("claim_id") or "").strip())
    }


def drift_agreement(cond_a: str = "ai_lecturenote",
                    cond_b: str = "gpt4o_ailn_post") -> list[dict]:
    """Cross-input semantic-drift-set overlap between two post-processing conditions.

    Same idea as ``polarity.polarity_agreement`` but for the semantic-drift set:
    which reference claims drift under AI_LectureNote (whisper-1 + post) vs under
    ``gpt4o_ailn_post`` (gpt-4o + the *same* post). A low Jaccard with equal set
    sizes means the post-processing produces a *similar amount* of drift but on
    *different* sentences depending on the raw STT (propagated, STT-dependent
    drift), in contrast to the high-overlap polarity failures (intrinsic to the
    post-processing). One row per lecture plus an ``ALL`` aggregate row.
    """
    rows = []
    a_all, b_all = set(), set()
    for lecture_id in config.discover_lectures():
        a = {f"{lecture_id}:{x}" for x in _drift_claim_ids(lecture_id, cond_a)}
        b = {f"{lecture_id}:{x}" for x in _drift_claim_ids(lecture_id, cond_b)}
        if not a and not b:
            continue
        shared, union = a & b, a | b
        rows.append({
            "scope": lecture_id,
            "comparison": f"{cond_a} vs {cond_b}",
            "a_drift": len(a),
            "b_drift": len(b),
            "shared_drift": len(shared),
            "union_drift": len(union),
            "drift_jaccard": round(len(shared) / len(union), 4) if union else 0.0,
        })
        a_all |= a; b_all |= b
    if rows:
        shared, union = a_all & b_all, a_all | b_all
        rows.append({
            "scope": "ALL",
            "comparison": f"{cond_a} vs {cond_b}",
            "a_drift": len(a_all),
            "b_drift": len(b_all),
            "shared_drift": len(shared),
            "union_drift": len(union),
            "drift_jaccard": round(len(shared) / len(union), 4) if union else 0.0,
        })
    return rows


def drift_taxonomy(lecture_id: str, condition: str = "ai_lecturenote") -> dict:
    """Per-lecture drift-token incidence counts (compound labels add to >1 token).

    Returns ``{lecture_id, drift_rows, <token>: count, ...}``; the per-token counts
    sum to >= drift_rows because a compound label contributes to several tokens.
    """
    claims = load_semantic_claims(lecture_id, condition)
    rows = 0
    tok = defaultdict(int)
    for c in claims:
        toks = drift_tokens_in(c.get("label"))
        if toks:
            rows += 1
            for t in toks:
                tok[t] += 1
    out = {"lecture_id": lecture_id, "condition": condition, "drift_rows": rows}
    for t in DRIFT_TOKENS:
        out[t] = tok.get(t, 0)
    return out
