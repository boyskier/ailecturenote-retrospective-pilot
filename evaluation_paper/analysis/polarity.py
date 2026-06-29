"""Analysis 8: critical medical polarity accuracy.

Two layers:
  1. ``auto_polarity_counts`` - descriptive, automatic. For every polarity_group
     defined in the dictionary it reports how often each polarity *value* surfaces
     in the reference vs each condition output. A value distribution that shifts
     (e.g. reference has 'low' but the output produces 'high') flags a candidate
     polarity flip for human review. This is a screening signal, not a verdict.
  2. ``load_polarity_items`` - authoritative. The exhaustive human worksheet
     ``polarity_review.csv`` where each polarity-sensitive reference statement is
     marked correct/wrong/omitted per condition. This drives the paper's polarity
     table.
"""
from __future__ import annotations

import csv
import os
from collections import defaultdict

import config
import term_dictionary as td

POLARITY_REVIEW_FILE = "polarity_review.csv"


def _read_items(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f)]
    # Ignore example/comment rows whose item_id starts with '#'.
    return [r for r in rows if (r.get("item_id") or "").strip()
            and not (r.get("item_id") or "").strip().startswith("#")]


def load_polarity_items(lecture_id: str) -> list[dict]:
    """Authoritative polarity items: the exhaustive human worksheet
    ``polarity_review.csv`` (one row per polarity-sensitive reference sentence)."""
    return _read_items(config.annotation_path(lecture_id, POLARITY_REVIEW_FILE))


def _normalize_verdict(value: str) -> str:
    """Map a verdict cell to correct / wrong / omitted / unclear / '' (blank).

    Accepts inline reviewer notes, e.g. ``'wrong (하이포가 맞음)'`` or
    ``'correct (근데 오타가 많음)'``. Any non-empty cell that is not a recognized
    verdict (e.g. the Korean ``'애매함 ...'`` = ambiguous) is bucketed as
    ``unclear`` so per-condition counts always reconcile with the row total.
    """
    verdict = (value or "").strip().lower()
    if not verdict:
        return ""
    for label in ("correct", "wrong", "omitted", "unclear"):
        if verdict == label or verdict.startswith((label + "(", label + ":", label + " ")):
            return label
    if verdict.startswith(("애매", "ambiguous", "unsure")):
        return "unclear"
    return "unclear"


def auto_polarity_counts(lecture_id: str) -> list[dict]:
    """Reference-vs-condition polarity-value distribution per polarity group."""
    if not config.has_reference(lecture_id) or not td.has_domain_terms(lecture_id):
        return []
    terms = [t for t in td.load_domain_terms(lecture_id, kept_only=True)
             if t.polarity_group and t.polarity_value]
    if not terms:
        return []

    reference = config.read_text(config.reference_path(lecture_id))
    outputs = {
        cond: config.read_text(
            config.data_path(lecture_id, config.CONDITIONS[cond]["file"])
        )
        for cond in config.CONDITION_ORDER
    }

    # group -> value -> {"reference": n, cond: n, ...}
    table: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(int))
    )
    for t in terms:
        ref_n = t.count_english(reference)
        table[t.polarity_group][t.polarity_value]["reference"] += ref_n
        for cond, text in outputs.items():
            if text:
                table[t.polarity_group][t.polarity_value][cond] += t.count_english(text)

    rows = []
    for group in sorted(table):
        for value in sorted(table[group]):
            row = {"lecture_id": lecture_id, "polarity_group": group,
                   "polarity_value": value,
                   "reference": table[group][value]["reference"]}
            for cond in config.CONDITION_ORDER:
                row[cond] = table[group][value].get(cond, 0)
            rows.append(row)
    return rows


def summarize_polarity_items(lecture_id: str) -> list[dict]:
    """Count correct/wrong/omitted polarity judgements per condition."""
    items = load_polarity_items(lecture_id)
    if not items:
        return []
    summary = {cond: defaultdict(int) for cond in config.CONDITION_ORDER}
    for item in items:
        for cond in config.CONDITION_ORDER:
            verdict = _normalize_verdict(item.get(cond) or "")
            if verdict:
                summary[cond][verdict] += 1
    rows = []
    for cond in config.CONDITION_ORDER:
        counts = summary[cond]
        if not counts:
            continue
        wrong = counts.get("wrong", 0)
        omitted = counts.get("omitted", 0)
        rows.append({
            "lecture_id": lecture_id,
            "condition": cond,
            "correct": counts.get("correct", 0),
            "wrong": wrong,
            "omitted": omitted,
            # polarity *failure* = wrong (flipped) + omitted (dropped). Shown as a
            # derived column; wrong/omitted are kept separate per the agreed policy.
            "polarity_failure": wrong + omitted,
            "unclear": counts.get("unclear", 0),
            "total_labeled": sum(counts.values()),
        })
    return rows


def _is_failure(verdict: str) -> bool:
    """Polarity *failure* = wrong (flipped pole) or omitted (dropped)."""
    return verdict in ("wrong", "omitted")


def _agreement_row(scope: str, cond_a: str, cond_b: str, n: int, same: int,
                   both_correct: int, both_fail: int, disagree: int,
                   a_fail: set, b_fail: set, shared: set, union: set) -> dict:
    return {
        "scope": scope,
        "comparison": f"{cond_a} vs {cond_b}",
        "n_items": n,
        "same_verdict": same,
        "agreement_rate": round(same / n, 4) if n else 0.0,
        "both_correct": both_correct,
        "both_fail": both_fail,
        "disagree": disagree,
        "a_failures": len(a_fail),
        "b_failures": len(b_fail),
        "shared_failures": len(shared),
        "union_failures": len(union),
        "failure_jaccard": round(len(shared) / len(union), 4) if union else 0.0,
    }


def polarity_agreement(cond_a: str = "ai_lecturenote",
                       cond_b: str = "gpt4o_ailn_post") -> list[dict]:
    """Cross-input polarity-verdict agreement between two post-processing conditions.

    AI_LectureNote (whisper-1 + post-processing) and ``gpt4o_ailn_post`` (gpt-4o +
    the *same* post-processing) differ only in the raw STT input. This quantifies
    how often the same post-processing reaches the *same* polarity verdict despite
    that different input, plus the failure-set Jaccard. One row per lecture and an
    ``ALL`` aggregate row. A row counts only when BOTH conditions carry a verdict;
    agreement is at the correct/failure level (failure = wrong + omitted).
    """
    rows = []
    tot_n = tot_same = tot_bc = tot_bf = tot_dis = 0
    a_all, b_all, shared_all = set(), set(), set()
    for lecture_id in config.discover_lectures():
        n = same = both_c = both_f = dis = 0
        a_fail, b_fail, shared = set(), set(), set()
        for it in load_polarity_items(lecture_id):
            va = _normalize_verdict(it.get(cond_a) or "")
            vb = _normalize_verdict(it.get(cond_b) or "")
            if not va or not vb:
                continue
            n += 1
            fa, fb = _is_failure(va), _is_failure(vb)
            rid = f"{lecture_id}:{it.get('item_id')}"
            if fa:
                a_fail.add(rid)
            if fb:
                b_fail.add(rid)
            if fa == fb:
                same += 1
                if fa:
                    both_f += 1
                    shared.add(rid)
                else:
                    both_c += 1
            else:
                dis += 1
        if n == 0:
            continue
        rows.append(_agreement_row(lecture_id, cond_a, cond_b, n, same, both_c,
                                   both_f, dis, a_fail, b_fail, shared,
                                   a_fail | b_fail))
        tot_n += n; tot_same += same; tot_bc += both_c; tot_bf += both_f
        tot_dis += dis
        a_all |= a_fail; b_all |= b_fail; shared_all |= shared
    if rows:
        rows.append(_agreement_row("ALL", cond_a, cond_b, tot_n, tot_same, tot_bc,
                                   tot_bf, tot_dis, a_all, b_all, shared_all,
                                   a_all | b_all))
    return rows


def transition_whisper_to_ai(lecture_id: str) -> dict:
    """Per-row polarity verdict transition raw whisper-1 -> AI_LectureNote.

    Isolates the *post-processing effect*: of the polarity statements raw whisper-1
    got right/wrong, how many did the AI_LectureNote post-processing keep, fix,
    flip, or drop? Counts only rows where at least one of the two has a verdict.
    """
    items = load_polarity_items(lecture_id)
    t = defaultdict(int)
    for it in items:
        w = _normalize_verdict(it.get("whisper1") or "")
        a = _normalize_verdict(it.get("ai_lecturenote") or "")
        if not w and not a:
            continue
        t[(w or "blank", a or "blank")] += 1
    fixed = t[("wrong", "correct")] + t[("omitted", "correct")]
    introduced_flip = t[("correct", "wrong")]
    introduced_omit = t[("correct", "omitted")]
    return {
        "lecture_id": lecture_id,
        "kept_correct": t[("correct", "correct")],
        "fixed": fixed,                       # raw wrong -> AI correct
        "introduced_flip": introduced_flip,   # raw correct -> AI wrong (NEW error)
        "introduced_omission": introduced_omit,  # raw correct -> AI dropped
        "still_wrong": t[("wrong", "wrong")] + t[("omitted", "wrong")]
                       + t[("wrong", "omitted")],
        "net_failure_change": (introduced_flip + introduced_omit) - fixed,
        "transitions": {f"{w}->{a}": n for (w, a), n in sorted(t.items())},
    }
