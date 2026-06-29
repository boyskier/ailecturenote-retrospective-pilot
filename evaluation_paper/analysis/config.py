"""Central configuration for the MedLect-KR STT evaluation analysis.

All paths are derived from the location of this file so the package is portable.
Directory layout (under ``evaluation_paper/``)::

    data/<lecture_id>/{reference,whisper1,ai_lecturenote,gpt4o,gpt4o_prompted}.txt
    annotations/<lecture_id>/{domain_terms,semantic_review,polarity_review}.csv
    manifest/condition_manifest.csv
    analysis/*.py        <- this package
    outputs/tables/*.csv
    outputs/figures/*.png
"""
from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ANALYSIS_DIR = os.path.dirname(os.path.abspath(__file__))
PAPER_ROOT = os.path.dirname(ANALYSIS_DIR)            # evaluation_paper/

DATA_DIR = os.path.join(PAPER_ROOT, "data")
ANNOTATIONS_DIR = os.path.join(PAPER_ROOT, "annotations")
MANIFEST_DIR = os.path.join(PAPER_ROOT, "manifest")
OUTPUTS_DIR = os.path.join(PAPER_ROOT, "outputs")
TABLES_DIR = os.path.join(OUTPUTS_DIR, "tables")
FIGURES_DIR = os.path.join(OUTPUTS_DIR, "figures")

# ---------------------------------------------------------------------------
# Conditions (the four comparison columns of the paper)
# ---------------------------------------------------------------------------
# key -> (filename stem, display label, short label, role)
CONDITIONS = {
    "whisper1": {
        "file": "whisper1.txt",
        "label": "raw whisper-1",
        "short": "whisper-1",
        "role": "historical raw ASR baseline",
        "needs_reference_side": True,
    },
    "ai_lecturenote": {
        "file": "ai_lecturenote.txt",
        "label": "AI_LectureNote",
        "short": "AI_LectureNote",
        "role": "post-processing pipeline (not raw ASR)",
        "needs_reference_side": True,
    },
    "gpt4o": {
        "file": "gpt4o.txt",
        "label": "raw gpt-4o-transcribe",
        "short": "gpt-4o",
        "role": "modern raw ASR, 3-min chunks",
        "needs_reference_side": True,
    },
    "gpt4o_prompted": {
        "file": "gpt4o_prompted.txt",
        "label": "prompted gpt-4o-transcribe",
        "short": "gpt-4o (prompted)",
        "role": "preliminary prompt-sensitivity only",
        "needs_reference_side": True,
    },
    "gpt4o_ailn_post": {
        "file": "gpt4o_ailn_post.txt",
        "label": "raw gpt-4o-transcribe -> AI_LectureNote post-processing",
        "short": "gpt-4o -> AILN post",
        "role": "diagnostic cross-input control; same post-processing applied to raw gpt-4o output",
        "needs_reference_side": True,
    },
}

# Condition order used in every table / figure.
CONDITION_ORDER = ["whisper1", "ai_lecturenote", "gpt4o", "gpt4o_prompted", "gpt4o_ailn_post"]

REFERENCE_FILE = "reference.txt"

# Conditions that are produced with the 3-minute chunking policy and therefore
# can be split into chunks for the chunk-consistency analysis.
CHUNKED_CONDITIONS = ["gpt4o", "gpt4o_prompted"]

# The exact prompt used for the prompted gpt-4o-transcribe condition
# (kept here so it appears verbatim in the manifest / Methods section).
GPT4O_PROMPT = "의학 강의 녹음입니다. 영어 의학 용어는 영어로 표기합니다."

# Chunking policy facts (from audio_processing.py), for the manifest.
WHISPER1_CHUNK_POLICY = "10-min chunks, no overlap"
GPT4O_CHUNK_POLICY = "3-min non-overlapping chunks"

# Known per-lecture metadata. Fields left blank ("") are intended to be filled
# by the human in manifest/condition_manifest.csv after it is generated.
LECTURE_META = {
    "diuretics_01": {
        "topic": "Diuretics",
        "speaker": "lke",
        "whisper1_api_date": "2026-06-25",
        "gpt4o_api_date": "2026-06-25",
        "release_status": "transcript only",
    },
    "acuteinflammation_02": {
        "topic": "Acute inflammation",
        "speaker": "lke",
        "whisper1_api_date": "2026-06-25",
        "gpt4o_api_date": "2026-06-25",
        "release_status": "transcript only",
    },
    "anthrax_01": {
        "topic": "Anthrax (Bacillus anthracis)",
        "speaker": "cdh",
        "whisper1_api_date": "2026-06",
        "gpt4o_api_date": "2026-06",
        "release_status": "transcript only",
    },
    # Fourth lecture (N=4 extension), added 2026-06-28. A shorter, matched-speaker
    # (cdh) lecture on anticancer drugs. Exact duration is not recorded in the
    # manifest; its two 3-minute gpt-4o chunks bound it at <= 6 min. API dates are
    # left at month granularity (the 2026-06 study window) to avoid inventing a
    # precise transcription date that is not separately documented.
    "anticancerdrugs_02": {
        "topic": "Anticancer drugs",
        "speaker": "cdh",
        "whisper1_api_date": "2026-06",
        "gpt4o_api_date": "2026-06",
        "release_status": "transcript only",
    },
}


def discover_lectures():
    """Return sorted lecture ids that have a data/<lecture_id>/ directory."""
    if not os.path.isdir(DATA_DIR):
        return []
    lectures = [
        name
        for name in os.listdir(DATA_DIR)
        if os.path.isdir(os.path.join(DATA_DIR, name))
    ]
    return sorted(lectures)


def data_path(lecture_id, filename):
    return os.path.join(DATA_DIR, lecture_id, filename)


def reference_path(lecture_id):
    return data_path(lecture_id, REFERENCE_FILE)


def has_reference(lecture_id):
    return os.path.exists(reference_path(lecture_id))


def annotation_path(lecture_id, filename):
    return os.path.join(ANNOTATIONS_DIR, lecture_id, filename)


def ensure_output_dirs():
    for d in (OUTPUTS_DIR, TABLES_DIR, FIGURES_DIR):
        os.makedirs(d, exist_ok=True)


def read_text(path):
    """Read a transcript file, returning '' if it does not exist."""
    if not path or not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
