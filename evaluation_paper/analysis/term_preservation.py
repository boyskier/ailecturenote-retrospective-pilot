"""Analyses 2 & 3: English medical-term preservation and English-script rate.

Headline metric of the paper:

    English-script preservation rate
        = English-script-preserved domain-term occurrences (in condition output)
          / domain-term occurrences in the reference

This needs only the reference + the curated ``canonical_english`` forms, so it is
computed fully automatically. ``korean_phonetic`` (if the human fills it) adds the
phonetic-rendering breakdown; otherwise that column is reported as 0 / "n/a".
"""
from __future__ import annotations

from dataclasses import dataclass, field

import config
import term_dictionary as td


@dataclass
class TermConditionResult:
    lecture_id: str
    condition: str
    ref_occurrences: int           # denominator (occurrence level)
    english_preserved: int         # numerator (capped per term at ref count)
    korean_phonetic: int           # informational (needs korean_phonetic filled)
    unique_terms_total: int
    unique_terms_preserved: int

    @property
    def english_script_rate(self):
        if self.ref_occurrences == 0:
            return None
        return round(self.english_preserved / self.ref_occurrences, 4)

    @property
    def unique_recall(self):
        if self.unique_terms_total == 0:
            return None
        return round(self.unique_terms_preserved / self.unique_terms_total, 4)

    def as_row(self) -> dict:
        return {
            "lecture_id": self.lecture_id,
            "condition": self.condition,
            "ref_term_occurrences": self.ref_occurrences,
            "english_preserved": self.english_preserved,
            "english_script_rate": self.english_script_rate,
            "korean_phonetic_count": self.korean_phonetic,
            "unique_terms_total": self.unique_terms_total,
            "unique_terms_preserved": self.unique_terms_preserved,
            "unique_term_recall": self.unique_recall,
        }


@dataclass
class TermDetail:
    """Per-term, per-lecture breakdown across all conditions (qualitative table)."""
    lecture_id: str
    term_id: str
    canonical_english: str
    category: str
    ref_count: int
    per_condition_english: dict = field(default_factory=dict)
    per_condition_phonetic: dict = field(default_factory=dict)


def preservation_for_lecture(lecture_id: str):
    """Return (per-condition results, per-term details) for a lecture.

    Empty if the lecture has no reference or no curated term dictionary yet.
    """
    if not config.has_reference(lecture_id) or not td.has_domain_terms(lecture_id):
        return [], []

    reference = config.read_text(config.reference_path(lecture_id))
    terms = td.load_domain_terms(lecture_id, kept_only=True)
    if not terms:
        return [], []

    # Reference English-script occurrences per term (the denominator basis).
    ref_counts = {t.term_id: t.count_english(reference) for t in terms}

    # Load each available condition's output text once.
    outputs = {}
    for cond in config.CONDITION_ORDER:
        text = config.read_text(
            config.data_path(lecture_id, config.CONDITIONS[cond]["file"])
        )
        if text:
            outputs[cond] = text

    details = []
    for t in terms:
        ref_n = ref_counts[t.term_id]
        d = TermDetail(
            lecture_id=lecture_id,
            term_id=t.term_id,
            canonical_english=t.canonical_english,
            category=t.category,
            ref_count=ref_n,
        )
        for cond, text in outputs.items():
            d.per_condition_english[cond] = t.count_english(text)
            d.per_condition_phonetic[cond] = t.count_korean_phonetic(text)
        details.append(d)

    results = []
    for cond, text in outputs.items():
        ref_total = 0
        preserved_total = 0
        phonetic_total = 0
        unique_total = 0
        unique_preserved = 0
        for t in terms:
            ref_n = ref_counts[t.term_id]
            if ref_n == 0:
                continue  # term never appears in the reference -> not in denominator
            out_eng = t.count_english(text)
            out_kor = t.count_korean_phonetic(text)
            ref_total += ref_n
            preserved = min(out_eng, ref_n)
            preserved_total += preserved
            phonetic_total += min(out_kor, max(ref_n - preserved, 0))
            unique_total += 1
            if out_eng >= 1:
                unique_preserved += 1
        results.append(
            TermConditionResult(
                lecture_id=lecture_id,
                condition=cond,
                ref_occurrences=ref_total,
                english_preserved=preserved_total,
                korean_phonetic=phonetic_total,
                unique_terms_total=unique_total,
                unique_terms_preserved=unique_preserved,
            )
        )
    return results, details
