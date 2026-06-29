"""Frozen text-normalization and string-distance utilities.

The normalization policy here is deliberately fixed (see the paper §5.1 and the
README "Frozen metric definitions"). Changing it changes every CER/WER number, so edit
it consciously and re-run the whole pipeline.

Policy:
  * English: lowercased.
  * Punctuation: replaced with a single space (standardized away).
  * Whitespace: collapsed.
  * CER is computed on the whitespace-stripped normalized string, so Korean spacing
    differences do not inflate the character error rate (Korean spacing is treated
    as non-meaningful -> CER is the primary metric).
  * WER is computed on whitespace-delimited tokens of the normalized string
    (secondary metric; unstable under Korean spacing / paraphrase).
  * Polarity-bearing morphemes (hypo/hyper, acidosis/alkalosis, ...) are NEVER
    merged here. Normalization only touches case / punctuation / whitespace.
"""
from __future__ import annotations

import regex as re

# Characters we treat as punctuation to strip. We keep '+', '-' and '/' because
# they carry meaning in medical notation (K+, Na+, anti-androgenic, GI/CNS).
_PUNCT_RE = re.compile(r"[^\p{L}\p{N}\s+\-/]", re.UNICODE)
_WS_RE = re.compile(r"\s+", re.UNICODE)


def normalize(text: str) -> str:
    """Lowercase, standardize punctuation to spaces, collapse whitespace."""
    if not text:
        return ""
    text = text.lower()
    text = _PUNCT_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text)
    return text.strip()


def chars_for_cer(text: str) -> list[str]:
    """Normalized characters with all whitespace removed (CER unit)."""
    norm = normalize(text)
    return [c for c in norm if not c.isspace()]


def words_for_wer(text: str) -> list[str]:
    """Normalized whitespace-delimited tokens (WER unit)."""
    norm = normalize(text)
    return norm.split() if norm else []


def edit_distance(a: list, b: list) -> int:
    """Levenshtein distance between two sequences (two-row DP)."""
    if a == b:
        return 0
    n, m = len(a), len(b)
    if n == 0:
        return m
    if m == 0:
        return n
    prev = list(range(m + 1))
    cur = [0] * (m + 1)
    for i in range(1, n + 1):
        cur[0] = i
        ai = a[i - 1]
        for j in range(1, m + 1):
            cost = 0 if ai == b[j - 1] else 1
            cur[j] = min(
                prev[j] + 1,        # deletion
                cur[j - 1] + 1,     # insertion
                prev[j - 1] + cost,  # substitution
            )
        prev, cur = cur, prev
    return prev[m]


# ---------------------------------------------------------------------------
# Latin-script (English) term extraction
# ---------------------------------------------------------------------------
# A "latin run" is a maximal stretch of Latin-script tokens embedded in Korean
# discourse, e.g. "carbonic anhydrase inhibitor", "loop of Henle", "hypokalemia".
# Tokens may contain digits and the in-token symbols + - /.
_TOKEN = r"[A-Za-z][A-Za-z0-9+\-/]*"
_LATIN_RUN_RE = re.compile(_TOKEN + r"(?:[ \t]+" + _TOKEN + r")*")

# English function words that are almost never domain terms on their own; used to
# pre-mark candidate rows as keep=0 and to trim run edges.
STOPWORDS = {
    "of", "and", "or", "the", "a", "an", "to", "in", "on", "for", "with", "by",
    "is", "are", "be", "this", "that", "these", "those", "as", "at", "it",
    "vs", "via", "per",
}


def latin_runs(text: str) -> list[str]:
    """Return the surface latin runs occurring in ``text`` (with repetition)."""
    runs = []
    for m in _LATIN_RUN_RE.finditer(text):
        run = m.group(0).strip()
        # Trim leading/trailing stopwords so "of action" / "the nephron" tidy up.
        tokens = run.split()
        while tokens and tokens[0].lower() in STOPWORDS:
            tokens.pop(0)
        while tokens and tokens[-1].lower() in STOPWORDS:
            tokens.pop()
        if not tokens:
            continue
        # Require at least one token with >= 2 alphabetic characters.
        if not any(sum(ch.isalpha() for ch in t) >= 2 for t in tokens):
            continue
        runs.append(" ".join(tokens))
    return runs


def count_english_occurrences(text: str, surface_forms: list[str]) -> int:
    """Count case-insensitive occurrences of any surface form in ``text``.

    Matching is whitespace-flexible for multi-word forms and guarded by Latin
    letter look-arounds so a form is not matched inside a longer Latin word.
    """
    total = 0
    for form in surface_forms:
        form = form.strip()
        if not form:
            continue
        parts = [re.escape(tok) for tok in form.split()]
        body = r"[ \t]+".join(parts)
        pattern = r"(?<![A-Za-z])" + body + r"(?![A-Za-z])"
        total += len(re.findall(pattern, text, flags=re.IGNORECASE))
    return total


def count_substring_occurrences(text: str, surface_forms: list[str]) -> int:
    """Count occurrences of Korean (or arbitrary) substrings, no boundary guard."""
    total = 0
    for form in surface_forms:
        form = form.strip()
        if not form:
            continue
        total += text.count(form)
    return total


def split_sentences(text: str) -> list[str]:
    """Split Korean/English prose into sentence-ish units for semantic templates."""
    text = text.strip()
    if not text:
        return []
    # Split on sentence-final punctuation followed by whitespace, keeping it simple.
    pieces = re.split(r"(?<=[\.!?。])\s+", text.replace("\n", " "))
    return [p.strip() for p in pieces if p.strip()]
