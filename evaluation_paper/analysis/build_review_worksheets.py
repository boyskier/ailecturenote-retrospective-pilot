"""Build comprehensive human-review worksheets (exhaustive-review option).

For each lecture that has a reference, this emits two PRE-FILLED worksheets whose
only empty cells are the human's *judgements* — no hunting through transcripts:

  annotations/<id>/polarity_review.csv
      One row per reference sentence that carries a polarity / direction cue
      (hypo/hyper, -emia, acidosis/alkalosis, 증가/감소, 차단/억제/촉진, 1차/2차,
      배출/손실, negation …). For each of the 4 conditions the matching span is
      located for you (anchored on the sentence's domain terms; polarity terms are
      searched by stem so a FLIPPED pole, e.g. hyper- where the reference says hypo-,
      shows up in the span). You fill correct / wrong / omitted per condition.

  annotations/<id>/semantic_review.csv
      One row per reference sentence (exhaustive reference-vs-AI_LectureNote pass).
      The aligned AI_LectureNote span is pre-located into ai_lecturenote_output. You
      assign the label (Faithful / Omission / Substitution / Polarity error / ...).

These SUPERSET the Claude drafts. When a review file exists the pipeline prefers it
(see polarity.load_polarity_items / semantic_audit.load_semantic_claims). Claude's
draft insight is surfaced in a non-authoritative ``claude_hint`` column and is NOT
pre-filled as a verdict, so every row is judged by a human (keeps the annotation
'human', not LLM-as-judge). ``correct_value`` IS pre-filled when the sentence has a
single polarity-tagged term, because that is read mechanically off the reference,
not judged.

Safe to re-run: existing review files are preserved unless --force (so you never
lose verdicts you have already typed).

    python analysis/build_review_worksheets.py [--force]
"""
from __future__ import annotations

import csv
import os
import argparse
from collections import defaultdict

import regex as re

import config
import term_dictionary as td
import textutils as tu
import curate_annotations as ca

# A located span is expanded outward to the full sentence(s) containing the anchor
# (not a fixed character window) so a polarity/quantity clause is never cut
# mid-sentence — the reviewer must see whether e.g. "나트륨 그리고 bicarbonate 재흡수를
# 감소" was transcribed in full. SENT_PAD_MAX bounds the one-directional expansion so a
# run-on with no sentence-final period cannot dump a whole paragraph (longest real
# sentence in the corpus is ~320 chars, so 400 never clips a genuine sentence).
SENT_PAD_MAX = 400
_SENT_END_RE = re.compile(r"[.!?。]")
LOCALITY_RADIUS = SENT_PAD_MAX // 2
CURSOR_BACKTRACK = 120
KEY_RANK_PENALTY = 80
LONG_KEY_BONUS = 3
WEAK_WINDOW_BONUS = 220

# ---------------------------------------------------------------------------
# Cue detection
# ---------------------------------------------------------------------------
_POLARITY_EN = re.compile(
    r"hypo|hyper|[a-z]emia|acidosis|alkalosis|tension|vasodilat|vasoconstrict|"
    r"first[\- ]?line|second[\- ]?line|increas|decreas|elevat|reduc|inhibit|"
    r"stimulat|activat|suppress|secret",
    re.IGNORECASE,
)
_POLARITY_KR = [
    "증가", "감소", "상승", "저하", "높", "낮", "차단", "억제", "촉진", "자극",
    "활성", "방출", "분비", "배출", "손실", "보존", "재흡수", "예방", "악화",
    "완화", "1차", "2차", "일차", "이차", "아닌", "않", "없", "막아", "막는",
]

# polarity_group -> stem(s) to search for (so the opposite pole also surfaces).
_GROUP_STEM = {
    "potassium_serum": ["kalemia"],
    "calcium_serum": ["calcemia", "calcem"],
    "sodium_serum": ["natremia", "natre"],
    "magnesium_serum": ["magnes"],
    "acid_base": ["acidosis", "alkalosis"],
    "blood_pressure": ["tension"],
    "vessel_tone": ["vaso"],
}

_GROUP_KR_STEM = {
    "potassium_serum": ["칼리미아", "칼레미아", "칼리미야", "칼레미야"],
    "calcium_serum": ["칼세미아", "칼슘미아", "칼슘이야"],
    "sodium_serum": ["나트레미아", "나트리미아", "나트림이야"],
    "magnesium_serum": ["마그네시미아", "마그네심이야", "마그네티미아"],
    "acid_base": ["알칼로시스", "아시도시스", "에시도시스"],
}

_REFERENCE_KR_ENTITY_ANCHORS = [
    "나트륨", "칼륨", "칼슘", "마그네슘", "알도스테론", "프로톤",
]

_REFERENCE_KR_ACTION_ANCHORS = [
    "소변", "손실", "배출", "유입", "재흡수", "감소", "증가", "차단",
    "예방", "병용", "이뇨", "부작용", "효과",
]


def _has_polarity_cue(sentence: str) -> bool:
    if _POLARITY_EN.search(sentence):
        return True
    return any(k in sentence for k in _POLARITY_KR)


_SEMANTIC_KR_STOPWORDS = {
    "그리고", "그래서", "하지만", "그러면", "이렇게", "이것은", "이거는", "이제",
    "대한", "대해서", "경우", "때문", "때문에", "부분", "정도", "가지", "수업",
    "오늘", "여기", "우리", "먼저", "다음", "관련", "통해", "하게", "되는",
    "됩니다", "합니다", "있습니다", "없습니다", "입니다",
}
_SEMANTIC_EN_STOPWORDS = {
    "about", "after", "again", "also", "because", "before", "between", "class",
    "lecture", "these", "those", "there", "their", "which", "where", "while",
    "would",
}

_POLARITY_KR_CONTENT_STOPWORDS = {
    "\uc774\uc81c", "\uadf8\ub798\uc11c", "\uadf8\ub9ac\uace0", "\uadf8\ub7f0",
    "\uac83\uc744", "\uac83\uc774", "\uac83\uc740", "\uac83\ub3c4", "\uac83\ub4e4",
    "\uc5ec\ub7ec\uac00\uc9c0", "\ub300\ud574\uc11c", "\ub530\ub77c\uc11c",
    "\ub610\ub294", "\uc544\ub2c8\uba74", "\uac19\uc740", "\uacbd\uc6b0",
    "\uc774\ub7f0", "\uc774\ub807\uac8c", "\uc800\ud76c\uac00", "\uc774\uc57c\uae30",
    "\ud569\ub2c8\ub2e4", "\uc788\uc2b5\ub2c8\ub2e4", "\uc5c6\uc2b5\ub2c8\ub2e4",
    "\uc218", "\ub54c", "\ub4f1",
}


# ---------------------------------------------------------------------------
# Anchor extraction + span location
# ---------------------------------------------------------------------------
def _sentence_terms(sentence: str, terms: list[td.TermEntry]) -> list[td.TermEntry]:
    """Domain terms (kept) whose English surface form occurs in the sentence."""
    return [t for t in terms if t.count_english(sentence) > 0]


def _group_korean_forms(all_terms: list[td.TermEntry]) -> dict[str, list[str]]:
    """polarity_group -> korean phonetic forms of EVERY term in that group.

    The Hangul analogue of ``_GROUP_STEM``: a sentence tagged potassium_serum
    searches the phonetic spellings of BOTH hypo- and hyper-kalemia, so a pole the
    raw STT wrote in Korean syllables (e.g. 하이퍼칼리미아 where the reference says
    hypokalemia) still surfaces inside the snippet window.
    """
    m: dict[str, list[str]] = defaultdict(list)
    for t in all_terms:
        if t.polarity_group:
            m[t.polarity_group].extend(t.korean_phonetic)
    return m


def _search_keys(sentence: str, present: list[td.TermEntry],
                 group_kr: dict[str, list[str]] | None = None) -> list[str]:
    """Ordered substring keys used to locate the span in each output.

    Four tiers, most-diagnostic first so a polarity flip is never crowded out of
    the snippet-window cap on multi-term sentences:
      1. English polarity-group STEMS  - surface a FLIPPED pole in Latin script
         (searching 'magnes' finds hyper- where the reference says hypo-).
      2. Korean phonetic of every term in a present polarity group - the Hangul
         analogue of tier 1, for raw STT that wrote the pole phonetically.
      3. English surface forms of the sentence's domain terms (longest first).
      4. Korean phonetic of those terms (longest first) - catches raw STT that
         transliterates a term to Hangul (카르보닉 = carbonic, 다이렉스 = diuretics)
         rather than omitting it, instead of falsely reporting 'anchor not found'.

    Tiers 2 and 4 are skipped when ``group_kr`` is None (English-only callers such
    as the semantic worksheet, whose AI_LectureNote output is Latin-script).
    """
    korean_aware = group_kr is not None
    group_kr = group_kr or {}
    present_groups = {t.polarity_group for t in present if t.polarity_group}

    en_stems: list[str] = []
    for g in present_groups:
        en_stems.extend(_GROUP_STEM.get(g, []))
    kr_stems: list[str] = []
    if korean_aware:
        for g in present_groups:
            kr_stems.extend(_GROUP_KR_STEM.get(g, []))
    ref_kr_entities = [
        k for k in _REFERENCE_KR_ENTITY_ANCHORS if korean_aware and k in sentence
    ]
    ref_kr_actions = [
        k for k in _REFERENCE_KR_ACTION_ANCHORS if korean_aware and k in sentence
    ]
    kr_poles: list[str] = []
    for g in present_groups:
        kr_poles.extend(group_kr.get(g, []))

    en_forms: list[str] = []
    for t in present:
        en_forms.extend(t.english_surface_forms)
    en_forms.sort(key=len, reverse=True)

    kr_forms: list[str] = []
    if korean_aware:
        for t in present:
            kr_forms.extend(t.korean_phonetic)
        kr_forms.sort(key=len, reverse=True)

    seen = set()
    uniq: list[str] = []
    for k in (en_stems + ref_kr_entities + kr_stems + kr_poles +
              ref_kr_actions + en_forms + kr_forms):
        kl = k.lower()
        if kl and kl not in seen:
            seen.add(kl)
            uniq.append(k)
    return uniq


def _semantic_content_keys(sentence: str) -> list[str]:
    """Fallback anchors for semantic rows, especially Korean-only claims."""
    keys: list[str] = []
    for token in re.findall(r"\p{Hangul}{2,}", sentence):
        if token not in _SEMANTIC_KR_STOPWORDS:
            keys.append(token)
    for token in re.findall(r"[A-Za-z][A-Za-z0-9\-]{3,}", sentence):
        low = token.lower()
        if low not in _SEMANTIC_EN_STOPWORDS:
            keys.append(token)
    keys.sort(key=len, reverse=True)
    return keys


def _semantic_search_keys(sentence: str, present: list[td.TermEntry],
                          group_kr: dict[str, list[str]]) -> list[str]:
    """Richer anchors for AI_LectureNote semantic alignment."""
    keys = _search_keys(sentence, present, group_kr)
    keys.extend(_semantic_content_keys(sentence))
    seen = set()
    uniq: list[str] = []
    for key in keys:
        kl = key.lower()
        if kl and kl not in seen:
            seen.add(kl)
            uniq.append(key)
    return uniq


def _korean_anchor_variants(token: str) -> list[str]:
    """Useful substring variants for Korean-only polarity rows."""
    variants = [token]
    suffixes = [
        "\uc774", "\uac00", "\uc740", "\ub294", "\uc744", "\ub97c", "\uc5d0",
        "\uc5d0\uc11c", "\uc73c\ub85c", "\ub85c", "\uacfc", "\uc640", "\ub3c4",
        "\ub9cc", "\uc774\ub77c\ub358\uac00", "\ub77c\ub358\uac00", "\ud558\uac8c",
        "\ud558\uba74", "\ud558\ub294", "\ud569\ub2c8\ub2e4", "\uc2b5\ub2c8\ub2e4",
        "\uc785\ub2c8\ub2e4", "\uc774\uc5b4\uc9c0\uac8c", "\uc5b4\uc9c0\uac8c",
        "\uc9c4\ub2e4", "\ub41c\ub2e4", "\ub429\ub2c8\ub2e4", "\ub418\uad6c\uc694",
        "\uad6c\uc694", "\uc694",
    ]
    for suffix in suffixes:
        if token.endswith(suffix) and len(token) - len(suffix) >= 2:
            variants.append(token[:-len(suffix)])
    return variants


def _polarity_content_keys(sentence: str) -> list[str]:
    """Fallback anchors for polarity rows whose cue is Korean prose.

    Anthrax has many review rows like "treatment absent -> mortality high" where
    the polarity is carried by Korean words, not by a dictionary term such as
    hypokalemia. These anchors are appended after domain-term keys so specific
    medical terms still win when they exist.
    """
    keys: list[str] = []
    for token in re.findall(r"\p{Hangul}{2,}", sentence):
        if token in _POLARITY_KR_CONTENT_STOPWORDS:
            continue
        keys.extend(_korean_anchor_variants(token))
    for token in re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", sentence):
        low = token.lower()
        if low not in _SEMANTIC_EN_STOPWORDS:
            keys.append(token)
    keys.sort(key=len, reverse=True)
    seen = set()
    uniq: list[str] = []
    for key in keys:
        kl = key.lower()
        if kl and kl not in seen:
            seen.add(kl)
            uniq.append(key)
    return uniq


def _polarity_search_keys(sentence: str, present: list[td.TermEntry],
                          group_kr: dict[str, list[str]]) -> list[str]:
    keys = _search_keys(sentence, present, group_kr)
    keys.extend(_polarity_content_keys(sentence))
    seen = set()
    uniq: list[str] = []
    for key in keys:
        kl = key.lower()
        if kl and kl not in seen:
            seen.add(kl)
            uniq.append(key)
    return uniq


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _enclosing_sentence(text: str, idx: int, end_idx: int) -> tuple[int, int, bool, bool]:
    """Full-sentence bounds containing [idx, end_idx), clamped to SENT_PAD_MAX.

    Returns (start, end, left_clipped, right_clipped). ``*_clipped`` is True only
    when the clamp (not a real sentence boundary) cut the text — those are the only
    edges that warrant a '…' truncation marker.
    """
    start = 0
    for m in _SENT_END_RE.finditer(text, 0, idx):
        start = m.end()
    left_clipped = False
    if idx - start > SENT_PAD_MAX:
        start = idx - SENT_PAD_MAX
        left_clipped = True

    m = _SENT_END_RE.search(text, end_idx)
    end = m.end() if m else len(text)
    right_clipped = False
    if end - end_idx > SENT_PAD_MAX:
        end = end_idx + SENT_PAD_MAX
        right_clipped = True
    return start, end, left_clipped, right_clipped


def _locate(text: str, keys: list[str], max_spans: int = 3) -> str:
    """Return up to ``max_spans`` FULL-SENTENCE windows around the first key hits.

    Each anchor hit is expanded to its enclosing sentence (see _enclosing_sentence)
    so nothing is cut mid-sentence. Windows that overlap or are separated only by
    whitespace are merged; genuinely separated windows are joined by ' … ' (that
    gap denotes skipped sentences, not a truncated one).
    """
    if not text:
        return "(condition output empty)"
    low = text.lower()
    # window = [start, end, left_clipped, right_clipped]
    windows: list[list] = []
    for key in keys:
        idx = low.find(key.lower())
        if idx == -1:
            continue
        s, e, lc, rc = _enclosing_sentence(text, idx, idx + len(key))
        merged = False
        for w in windows:
            # overlapping, or adjacent with only whitespace between
            if s <= w[1] and e >= w[0] or \
               (w[1] <= s and not text[w[1]:s].strip()) or \
               (e <= w[0] and not text[e:w[0]].strip()):
                if s < w[0]:
                    w[0], w[2] = s, lc
                if e > w[1]:
                    w[1], w[3] = e, rc
                merged = True
                break
        if not merged:
            windows.append([s, e, lc, rc])
        if len(windows) >= max_spans:
            break
    if not windows:
        return "(anchor not found - likely omitted/paraphrased; check manually)"
    windows.sort()
    parts = []
    for s, e, lc, rc in windows:
        seg = _clean(text[s:e])
        if lc:
            seg = "…" + seg
        if rc:
            seg = seg + "…"
        parts.append(seg)
    return " … ".join(parts)


def _key_hits(text: str, keys: list[str]):
    """Yield every key occurrence as (rank, key, start, end)."""
    low = text.lower()
    for rank, key in enumerate(keys):
        needle = key.lower()
        if not needle:
            continue
        start = 0
        while True:
            idx = low.find(needle, start)
            if idx == -1:
                break
            yield rank, key, idx, idx + len(key)
            start = idx + max(len(needle), 1)


def _hit_score(rank: int, key: str, idx: int,
               expected_idx: int | None, cursor: int | None) -> float:
    """Lower is better: choose anchors near the reference-aligned location."""
    if expected_idx is not None:
        score = abs(idx - expected_idx)
    elif cursor is not None:
        score = abs(idx - cursor)
    else:
        score = idx

    if expected_idx is None and cursor is not None and idx < cursor - CURSOR_BACKTRACK:
        score += (cursor - idx) * 0.75
    elif expected_idx is not None and cursor is not None:
        score += min(abs(idx - cursor) * 0.20, 350)

    score += rank * KEY_RANK_PENALTY
    score -= min(len(key), 50) * LONG_KEY_BONUS
    return score


def _key_bonus(key: str, rank: int) -> float:
    """Weight a key when several anchors co-occur in the same sentence."""
    latin = bool(re.search(r"[A-Za-z]", key))
    base = 95 if latin else 45
    if len(key) <= 2 and not latin:
        base = 25
    return max(10, base - rank * 3) + min(len(key), 40)


def _window_key_bonus(text: str, start: int, end: int,
                      keys: list[str]) -> float:
    """Reward candidate windows that contain several row-specific anchors."""
    segment = text[start:end].lower()
    bonus = 0.0
    seen = set()
    for rank, key in enumerate(keys):
        kl = key.lower()
        if kl and kl not in seen and kl in segment:
            seen.add(kl)
            bonus += _key_bonus(key, rank)
    return bonus


def _merge_window(windows: list[list], text: str,
                  s: int, e: int, lc: bool, rc: bool) -> None:
    for w in windows:
        # overlapping, or adjacent with only whitespace between
        if s <= w[1] and e >= w[0] or \
           (w[1] <= s and not text[w[1]:s].strip()) or \
           (e <= w[0] and not text[e:w[0]].strip()):
            if s < w[0]:
                w[0], w[2] = s, lc
            if e > w[1]:
                w[1], w[3] = e, rc
            return
    windows.append([s, e, lc, rc])


def _expand_previous_sentence(text: str, start: int) -> tuple[int, bool]:
    """Return the previous sentence start, bounded to avoid huge paragraphs."""
    prev_start = 0
    prev_end = 0
    for m in _SENT_END_RE.finditer(text, 0, max(0, start - 1)):
        prev_start = prev_end
        prev_end = m.end()
    if prev_end <= 0:
        return start, False
    expanded = prev_start
    clipped = False
    if start - expanded > SENT_PAD_MAX:
        expanded = start - SENT_PAD_MAX
        clipped = True
    return expanded, clipped


def _format_windows(text: str, windows: list[list]) -> str:
    windows.sort()
    parts = []
    for s, e, lc, rc in windows:
        seg = _clean(text[s:e])
        if lc:
            seg = "…" + seg
        if rc:
            seg = seg + "…"
        parts.append(seg)
    return " … ".join(parts)


def _locate_span_ordered(text: str, keys: list[str], max_spans: int = 3,
                         expected_ratio: float | None = None,
                         cursor: int | None = None,
                         expand_weak_context: bool = True) -> tuple[str, int | None]:
    """Locate row-local span, avoiding the first-hit bias of repeated terms."""
    if not text:
        return "(condition output empty)", cursor
    if not keys:
        return "(anchor not found - likely omitted/paraphrased; check manually)", cursor

    expected_idx = None
    if expected_ratio is not None:
        expected_idx = max(0, min(len(text) - 1, round(expected_ratio * len(text))))

    candidates = []
    for rank, key, idx, end_idx in _key_hits(text, keys):
        s, e, _lc, _rc = _enclosing_sentence(text, idx, end_idx)
        score = _hit_score(rank, key, idx, expected_idx, cursor)
        score -= _window_key_bonus(text, s, e, keys)
        candidates.append((score, rank, idx, end_idx))
    if not candidates:
        return "(anchor not found - likely omitted/paraphrased; check manually)", cursor

    candidates.sort()
    best_idx = candidates[0][2]
    windows: list[list] = []
    for _score, _rank, idx, end_idx in candidates:
        if windows and abs(idx - best_idx) > LOCALITY_RADIUS:
            continue
        s, e, lc, rc = _enclosing_sentence(text, idx, end_idx)
        if expand_weak_context and _window_key_bonus(text, s, e, keys) < WEAK_WINDOW_BONUS:
            ps, plc = _expand_previous_sentence(text, s)
            if ps < s:
                s = ps
                lc = lc or plc
        _merge_window(windows, text, s, e, lc, rc)
        if len(windows) >= max_spans:
            break

    next_cursor = max(w[1] for w in windows) if windows else cursor
    return _format_windows(text, windows), next_cursor


def _sentence_spans(text: str) -> list[tuple[str, int, int]]:
    """Sentence-ish units with offsets in the flattened reference text."""
    flat = text.replace("\n", " ")
    cursor = 0
    spans = []
    for sent in tu.split_sentences(text):
        idx = flat.find(sent, cursor)
        if idx == -1:
            idx = flat.find(sent)
        if idx == -1:
            idx = cursor
        end = idx + len(sent)
        spans.append((sent, idx, end))
        cursor = max(cursor, end)
    return spans


# ---------------------------------------------------------------------------
# Claude-draft hint matching (best-effort guidance, not a verdict)
# ---------------------------------------------------------------------------
def _tokens(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[A-Za-z]{5,}", text)}



# ---------------------------------------------------------------------------
# Worksheet builders
# ---------------------------------------------------------------------------
def polarity_review_fields() -> list[str]:
    fields = ["item_id", "polarity_group", "reference_phrase", "correct_value"]
    for cond in config.CONDITION_ORDER:
        fields.extend([f"{cond}_span", cond])
    fields.extend(["why_it_matters"])
    fields.extend(REVIEW_METADATA_FIELDS)
    return fields


def semantic_review_file(condition: str) -> str:
    if condition == "ai_lecturenote":
        return "semantic_review.csv"
    return f"semantic_review_{condition}.csv"


def semantic_output_field(condition: str) -> str:
    return f"{condition}_output"


def semantic_review_fields(condition: str) -> list[str]:
    return [
        "claim_id", "reference_claim", semantic_output_field(condition),
        "label", "error_type", "why_it_matters",
    ] + REVIEW_METADATA_FIELDS


SEMANTIC_REVIEW_CONDITIONS = ["ai_lecturenote", "gpt4o_ailn_post"]
REVIEW_METADATA_FIELDS = [
    "reviewer_status",
    "review_note",
    "needs_followup",
    "final_note",
    "reviewed_by",
    "last_reviewed_at",
]

POLARITY_HUMAN_FIELDS = config.CONDITION_ORDER + ["why_it_matters"] + REVIEW_METADATA_FIELDS
SEMANTIC_HUMAN_FIELDS = ["label", "error_type", "why_it_matters"] + REVIEW_METADATA_FIELDS


def _existing_lookup(path: str, id_field: str,
                     text_field: str) -> tuple[dict[str, dict], dict[str, dict]]:
    by_id: dict[str, dict] = {}
    by_text: dict[str, dict] = {}
    if not os.path.exists(path):
        return by_id, by_text
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            row_id = (row.get(id_field) or "").strip()
            text = (row.get(text_field) or "").strip()
            if row_id:
                by_id[row_id] = row
            if text:
                by_text[text] = row
    return by_id, by_text


def _preserve_human_fields(row: dict, by_id: dict[str, dict],
                           by_text: dict[str, dict], id_field: str,
                           text_field: str, fields: list[str]) -> None:
    old = by_id.get((row.get(id_field) or "").strip())
    if old is None:
        old = by_text.get((row.get(text_field) or "").strip())
    if old is None:
        return
    for field in fields:
        old_value = old.get(field)
        if old_value is not None:
            row[field] = old_value


def _outputs(lecture_id: str) -> dict[str, str]:
    out = {}
    for cond in config.CONDITION_ORDER:
        out[cond] = config.read_text(
            config.data_path(lecture_id, config.CONDITIONS[cond]["file"])
        )
    return out


def build_polarity_review(lecture_id: str, force: bool) -> str:
    path = config.annotation_path(lecture_id, "polarity_review.csv")
    if os.path.exists(path) and not force:
        return f"skip (exists, preserved): {os.path.basename(path)}"

    reference = config.read_text(config.reference_path(lecture_id))
    terms = td.load_domain_terms(lecture_id, kept_only=True)
    outputs = _outputs(lecture_id)
    group_kr = _group_korean_forms(terms)
    sentences = _sentence_spans(reference)
    ref_len = max(1, len(reference.replace("\n", " ")))
    by_id, by_text = _existing_lookup(path, "item_id", "reference_phrase")
    cursors = {cond: 0 for cond in config.CONDITION_ORDER}

    rows = []
    n = 0
    for sent, start, end in sentences:
        if not _has_polarity_cue(sent):
            continue
        present = _sentence_terms(sent, terms)
        keys = _polarity_search_keys(sent, present, group_kr)
        expected_ratio = ((start + end) / 2) / ref_len
        pol_terms = [t for t in present if t.polarity_group and t.polarity_value]
        groups = sorted({t.polarity_group for t in pol_terms})
        if len(pol_terms) == 1:
            t = pol_terms[0]
            correct_value = f"{t.polarity_value} ({t.canonical_english})"
            group = t.polarity_group
        else:
            correct_value = ""
            group = "|".join(groups)
        n += 1
        spans = {}
        for cond in config.CONDITION_ORDER:
            span, next_cursor = _locate_span_ordered(
                outputs[cond], keys,
                expected_ratio=expected_ratio,
                cursor=cursors[cond],
            )
            spans[f"{cond}_span"] = span
            if next_cursor is not None:
                cursors[cond] = next_cursor

        row = {
            "item_id": f"{_abbr(lecture_id)}_pr{n:02d}",
            "polarity_group": group,
            "reference_phrase": _clean(sent),
            "correct_value": correct_value,
            "why_it_matters": "",
        }
        for cond in config.CONDITION_ORDER:
            row[f"{cond}_span"] = spans[f"{cond}_span"]
            row[cond] = ""
        _preserve_human_fields(
            row, by_id, by_text, "item_id", "reference_phrase",
            POLARITY_HUMAN_FIELDS,
        )
        rows.append(row)

    _write(path, polarity_review_fields(), rows)
    return f"{'overwrote' if force else 'written'} ({len(rows)} polarity rows): {os.path.basename(path)}"


def build_semantic_review(lecture_id: str, force: bool, condition: str = "ai_lecturenote") -> str:
    path = config.annotation_path(lecture_id, semantic_review_file(condition))
    if os.path.exists(path) and not force:
        return f"skip (exists, preserved): {os.path.basename(path)}"

    reference = config.read_text(config.reference_path(lecture_id))
    terms = td.load_domain_terms(lecture_id, kept_only=True)
    ai_text = config.read_text(
        config.data_path(lecture_id, config.CONDITIONS[condition]["file"])
    )
    if not ai_text:
        return f"skip (missing output): {config.CONDITIONS[condition]['file']}"
    group_kr = _group_korean_forms(terms)
    sentences = _sentence_spans(reference)
    ref_len = max(1, len(reference.replace("\n", " ")))
    by_id, by_text = _existing_lookup(path, "claim_id", "reference_claim")
    cursor = 0

    rows = []
    n = 0
    for sent, start, end in sentences:
        present = _sentence_terms(sent, terms)
        keys = _semantic_search_keys(sent, present, group_kr)
        expected_ratio = ((start + end) / 2) / ref_len
        if keys:
            ai_output, next_cursor = _locate_span_ordered(
                ai_text, keys, expected_ratio=expected_ratio, cursor=cursor,
                expand_weak_context=False,
            )
            if next_cursor is not None:
                cursor = next_cursor
        else:
            ai_output = "(no English anchor - read AI output for this claim manually)"
        n += 1
        row = {
            "claim_id": f"{_abbr(lecture_id)}_sr{n:02d}",
            "reference_claim": _clean(sent),
            semantic_output_field(condition): ai_output,
            "label": "",
            "error_type": "",
            "why_it_matters": "",
        }
        _preserve_human_fields(
            row, by_id, by_text, "claim_id", "reference_claim",
            SEMANTIC_HUMAN_FIELDS,
        )
        rows.append(row)

    _write(path, semantic_review_fields(condition), rows)
    return f"{'overwrote' if force else 'written'} ({len(rows)} claim rows): {os.path.basename(path)}"


def _abbr(lecture_id: str) -> str:
    return lecture_id.split("_")[0][:3]


def _write(path: str, fields: list[str], rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in fields})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--lecture-id",
        action="append",
        help="Build only the given lecture_id. May be passed more than once.",
    )
    parser.add_argument(
        "--polarity-only",
        action="store_true",
        help="Build only polarity_review.csv.",
    )
    parser.add_argument(
        "--semantic-only",
        action="store_true",
        help="Build only semantic_review.csv.",
    )
    args = parser.parse_args()
    if args.polarity_only and args.semantic_only:
        raise SystemExit("--polarity-only and --semantic-only cannot be combined")

    lecture_ids = args.lecture_id or config.discover_lectures()
    for lecture_id in lecture_ids:
        if not config.has_reference(lecture_id):
            print(f"[{lecture_id}] no reference - skipped")
            continue
        if not td.has_domain_terms(lecture_id):
            print(f"[{lecture_id}] no domain_terms - skipped")
            continue
        print(f"[{lecture_id}]")
        if not args.semantic_only:
            print("  " + build_polarity_review(lecture_id, args.force))
        if not args.polarity_only:
            for condition in SEMANTIC_REVIEW_CONDITIONS:
                print("  " + build_semantic_review(lecture_id, args.force, condition))
    print("\nFill the verdict columns in the *_review.csv files, then run_all.py.")
    print("(When a *_review.csv exists the pipeline uses it instead of the draft.)")


if __name__ == "__main__":
    main()
