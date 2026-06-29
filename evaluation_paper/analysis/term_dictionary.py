"""Domain-term dictionary: loading the human-curated CSV and counting term forms.

The dictionary is the single most important human deliverable. One CSV per lecture
lives at annotations/<lecture_id>/domain_terms.csv with columns:

    term_id, canonical_english, english_variants, korean_phonetic,
    category, polarity_group, polarity_value, keep, ref_count_auto, notes

Only ``canonical_english`` (plus optional ``english_variants``) is required to
compute the headline English-script-preservation metric. ``korean_phonetic`` is
optional and only refines the phonetic-vs-omitted breakdown. ``polarity_group`` /
``polarity_value`` enable the automatic polarity-substitution heuristic.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field

import config
import textutils as tu

DOMAIN_TERMS_FILE = "domain_terms.csv"

FIELDNAMES = [
    "term_id",
    "canonical_english",
    "english_variants",
    "korean_phonetic",
    "category",
    "polarity_group",
    "polarity_value",
    "keep",
    "ref_count_auto",
    "notes",
]


@dataclass
class TermEntry:
    term_id: str
    canonical_english: str
    english_variants: list[str] = field(default_factory=list)
    korean_phonetic: list[str] = field(default_factory=list)
    category: str = ""
    polarity_group: str = ""
    polarity_value: str = ""
    keep: bool = True
    notes: str = ""

    @property
    def english_surface_forms(self) -> list[str]:
        forms = [self.canonical_english] + self.english_variants
        return [f for f in forms if f.strip()]

    def count_english(self, text: str) -> int:
        return tu.count_english_occurrences(text, self.english_surface_forms)

    def count_korean_phonetic(self, text: str) -> int:
        return tu.count_substring_occurrences(text, self.korean_phonetic)


def _split_pipe(value: str) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split("|") if v.strip()]


def domain_terms_path(lecture_id: str) -> str:
    return config.annotation_path(lecture_id, DOMAIN_TERMS_FILE)


def has_domain_terms(lecture_id: str) -> bool:
    return os.path.exists(domain_terms_path(lecture_id))


def load_domain_terms(lecture_id: str, kept_only: bool = True) -> list[TermEntry]:
    """Load the curated domain-term dictionary for a lecture."""
    path = domain_terms_path(lecture_id)
    if not os.path.exists(path):
        return []
    entries: list[TermEntry] = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            keep_raw = (row.get("keep") or "1").strip().lower()
            keep = keep_raw not in ("0", "false", "no", "n", "")
            if kept_only and not keep:
                continue
            canonical = (row.get("canonical_english") or "").strip()
            if not canonical:
                continue
            entries.append(
                TermEntry(
                    term_id=(row.get("term_id") or canonical).strip(),
                    canonical_english=canonical,
                    english_variants=_split_pipe(row.get("english_variants") or ""),
                    korean_phonetic=_split_pipe(row.get("korean_phonetic") or ""),
                    category=(row.get("category") or "").strip(),
                    polarity_group=(row.get("polarity_group") or "").strip(),
                    polarity_value=(row.get("polarity_value") or "").strip(),
                    keep=keep,
                    notes=(row.get("notes") or "").strip(),
                )
            )
    return entries


# ---------------------------------------------------------------------------
# Candidate auto-extraction (used to pre-populate the human template)
# ---------------------------------------------------------------------------
def _term_id(canonical: str) -> str:
    slug = canonical.lower().strip()
    slug = slug.replace("/", "-").replace("+", "plus")
    slug = "_".join(slug.split())
    return slug


def extract_candidates(reference_text: str, min_count: int = 1) -> list[dict]:
    """Auto-extract candidate domain terms from a reference transcript.

    Returns rows ready to write to the domain_terms.csv template. Multi-word and
    single-word Latin runs are kept verbatim; obvious function-word-only runs are
    already trimmed by ``textutils.latin_runs``. The human prunes via ``keep``.
    """
    runs = tu.latin_runs(reference_text)

    # Count occurrences case-insensitively, but keep the most frequent surface
    # spelling as the canonical display form.
    counts: dict[str, int] = {}
    surface: dict[str, dict[str, int]] = {}
    for run in runs:
        key = run.lower()
        counts[key] = counts.get(key, 0) + 1
        surface.setdefault(key, {})
        surface[key][run] = surface[key].get(run, 0) + 1

    rows = []
    for key, count in counts.items():
        if count < min_count:
            continue
        canonical = max(surface[key].items(), key=lambda kv: kv[1])[0]
        is_stopwordy = all(tok.lower() in tu.STOPWORDS for tok in canonical.split())
        rows.append(
            {
                "term_id": _term_id(canonical),
                "canonical_english": canonical,
                "english_variants": "",
                "korean_phonetic": "",
                "category": "",
                "polarity_group": "",
                "polarity_value": "",
                "keep": "0" if is_stopwordy else "1",
                "ref_count_auto": str(count),
                "notes": "",
            }
        )
    # Sort by descending reference frequency, then alphabetically.
    rows.sort(key=lambda r: (-int(r["ref_count_auto"]), r["canonical_english"].lower()))
    return rows
