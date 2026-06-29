"""Analysis 1: basic transcript accuracy (CER primary, WER secondary, length ratio).

CER and WER measure surface similarity to the reference. They are reported with the
explicit caveat (see the paper §5.1 and the README "Frozen metric definitions")
that AI_LectureNote is a paraphrasing post-processor, so a higher WER there does not
by itself mean "worse".
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import config
import textutils as tu


@dataclass
class AccuracyResult:
    lecture_id: str
    condition: str
    cer: float | None
    wer: float | None
    ref_chars: int
    out_chars: int
    length_ratio: float | None  # out_chars / ref_chars

    def as_row(self) -> dict:
        return asdict(self)


def score_condition(reference_text: str, output_text: str, lecture_id: str,
                    condition: str) -> AccuracyResult:
    ref_chars = tu.chars_for_cer(reference_text)
    out_chars = tu.chars_for_cer(output_text)
    ref_words = tu.words_for_wer(reference_text)
    out_words = tu.words_for_wer(output_text)

    if ref_chars:
        cer = tu.edit_distance(ref_chars, out_chars) / len(ref_chars)
    else:
        cer = None
    if ref_words:
        wer = tu.edit_distance(ref_words, out_words) / len(ref_words)
    else:
        wer = None
    length_ratio = (len(out_chars) / len(ref_chars)) if ref_chars else None

    return AccuracyResult(
        lecture_id=lecture_id,
        condition=condition,
        cer=round(cer, 4) if cer is not None else None,
        wer=round(wer, 4) if wer is not None else None,
        ref_chars=len(ref_chars),
        out_chars=len(out_chars),
        length_ratio=round(length_ratio, 3) if length_ratio is not None else None,
    )


def accuracy_for_lecture(lecture_id: str) -> list[AccuracyResult]:
    """CER/WER for every condition of a lecture (empty if no reference)."""
    if not config.has_reference(lecture_id):
        return []
    reference = config.read_text(config.reference_path(lecture_id))
    results = []
    for cond in config.CONDITION_ORDER:
        out_path = config.data_path(lecture_id, config.CONDITIONS[cond]["file"])
        output = config.read_text(out_path)
        if not output:
            continue
        results.append(score_condition(reference, output, lecture_id, cond))
    return results
