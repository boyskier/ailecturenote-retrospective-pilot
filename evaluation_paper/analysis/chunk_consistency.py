"""Analysis 4: chunk-level GPT-4o script-selection (in)consistency.

The gpt-4o-transcribe outputs are produced in 3-minute chunks joined by blank
lines (audio_processing.py joins segments with "\\n\\n"), so chunk boundaries are
recovered by splitting on blank lines.

Per chunk we report, for the curated domain terms:
  * english_count    - domain-term tokens rendered in English script,
  * phonetic_count   - domain-term tokens rendered as Korean phonetic spellings,
  * english_rate     - english_count / (english_count + phonetic_count).

``english_rate`` needs the ``korean_phonetic`` column of the dictionary to be
filled to be meaningful; with it empty, phonetic_count is 0 and the rate collapses
to "100% whenever any English term appears". The raw english_count is always valid.
"""
from __future__ import annotations

from dataclasses import dataclass

import regex as re

import config
import term_dictionary as td

_BLANK_LINE_RE = re.compile(r"\n[ \t]*\n+")


def split_chunks(text: str) -> list[str]:
    """Split a chunked transcript on blank lines, dropping empty pieces."""
    if not text.strip():
        return []
    pieces = _BLANK_LINE_RE.split(text.strip())
    return [p.strip() for p in pieces if p.strip()]


def _time_range(chunk_index: int, minutes_per_chunk: int = 3) -> str:
    start = chunk_index * minutes_per_chunk
    end = start + minutes_per_chunk
    return f"{start:02d}:00-{end:02d}:00"


@dataclass
class ChunkRow:
    lecture_id: str
    condition: str
    chunk_id: int
    time_range: str
    english_count: int
    phonetic_count: int

    @property
    def english_rate(self):
        denom = self.english_count + self.phonetic_count
        if denom == 0:
            return None
        return round(self.english_count / denom, 4)

    @property
    def dominant_mode(self) -> str:
        rate = self.english_rate
        if rate is None:
            return "no-term"
        if rate >= 0.8:
            return "English-preserving"
        if rate <= 0.2:
            return "Korean-phonetic"
        return "mixed"

    def as_row(self) -> dict:
        return {
            "lecture_id": self.lecture_id,
            "condition": self.condition,
            "chunk_id": self.chunk_id,
            "time_range": self.time_range,
            "english_count": self.english_count,
            "phonetic_count": self.phonetic_count,
            "english_rate": self.english_rate,
            "dominant_mode": self.dominant_mode,
        }


def chunks_for_lecture(lecture_id: str) -> list[ChunkRow]:
    """Per-chunk script counts for each chunked condition of a lecture."""
    if not td.has_domain_terms(lecture_id):
        return []
    terms = td.load_domain_terms(lecture_id, kept_only=True)
    if not terms:
        return []

    rows: list[ChunkRow] = []
    for cond in config.CHUNKED_CONDITIONS:
        text = config.read_text(
            config.data_path(lecture_id, config.CONDITIONS[cond]["file"])
        )
        if not text:
            continue
        for idx, chunk in enumerate(split_chunks(text)):
            eng = sum(t.count_english(chunk) for t in terms)
            kor = sum(t.count_korean_phonetic(chunk) for t in terms)
            rows.append(
                ChunkRow(
                    lecture_id=lecture_id,
                    condition=cond,
                    chunk_id=idx,
                    time_range=_time_range(idx),
                    english_count=eng,
                    phonetic_count=kor,
                )
            )
    return rows
