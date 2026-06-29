"""Generate the human fill-in templates and the condition manifest.

This is the *only* part of the pipeline that creates files for the human to edit.
It NEVER overwrites an existing template unless ``--force`` is given, so re-running
the analysis cannot clobber annotations you have already filled in.

Generated artifacts:
  manifest/condition_manifest.csv                         (partly pre-filled)
  annotations/<lecture_id>/domain_terms.csv               (auto-extracted candidates)

The exhaustive semantic / polarity review worksheets are created separately by
``build_review_worksheets.py``.

Run:  python analysis/make_templates.py            # create missing templates
      python analysis/make_templates.py --force     # regenerate everything
"""
from __future__ import annotations

import argparse
import csv
import os

import config
import term_dictionary as td


def _write_csv(path: str, fieldnames: list[str], rows: list[dict], force: bool) -> str:
    existed = os.path.exists(path)
    if existed and not force:
        return "skip (exists, preserved)"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})
    return "overwrote (--force)" if existed else "written (new)"


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------
MANIFEST_FIELDNAMES = [
    "lecture_id", "topic", "duration", "speaker",
    "reference_file", "reference_status",
    "whisper1_file", "whisper1_api_date",
    "ai_lecturenote_file", "ai_pipeline_version",
    "gpt4o_file", "gpt4o_api_date", "gpt4o_chunk_policy",
    "gpt4o_prompted_file", "gpt4o_prompt",
    "term_list_file", "release_status",
]


def write_manifest(force: bool) -> str:
    rows = []
    for lecture_id in config.discover_lectures():
        meta = config.LECTURE_META.get(lecture_id, {})
        has_ref = config.has_reference(lecture_id)
        rows.append({
            "lecture_id": lecture_id,
            "topic": meta.get("topic", ""),
            "duration": "",  # fill: mm:ss
            "speaker": meta.get("speaker", ""),
            "reference_file": "reference.txt" if has_ref else "(MISSING)",
            "reference_status": "available" if has_ref else "pending",
            "whisper1_file": "whisper1.txt",
            "whisper1_api_date": meta.get("whisper1_api_date", ""),
            "ai_lecturenote_file": "ai_lecturenote.txt",
            "ai_pipeline_version": "",  # fill: pipeline version / git sha
            "gpt4o_file": "gpt4o.txt",
            "gpt4o_api_date": meta.get("gpt4o_api_date", ""),
            "gpt4o_chunk_policy": config.GPT4O_CHUNK_POLICY,
            "gpt4o_prompted_file": "gpt4o_prompted.txt",
            "gpt4o_prompt": config.GPT4O_PROMPT,
            "term_list_file": "annotations/%s/domain_terms.csv" % lecture_id,
            "release_status": meta.get("release_status", ""),
        })
    path = os.path.join(config.MANIFEST_DIR, "condition_manifest.csv")
    return _write_csv(path, MANIFEST_FIELDNAMES, rows, force)


# ---------------------------------------------------------------------------
# Domain terms
# ---------------------------------------------------------------------------
def write_domain_terms(lecture_id: str, force: bool) -> str:
    if config.has_reference(lecture_id):
        source_text = config.read_text(config.reference_path(lecture_id))
        note_src = ""
    else:
        # No reference yet: seed candidates from the AI_LectureNote output so the
        # human has a head start; flag that the source is provisional.
        source_text = config.read_text(
            config.data_path(lecture_id, config.CONDITIONS["ai_lecturenote"]["file"])
        )
        note_src = "auto from ai_lecturenote (no reference yet)"
    rows = td.extract_candidates(source_text)
    if note_src:
        for r in rows:
            r["notes"] = note_src
    path = td.domain_terms_path(lecture_id)
    return _write_csv(path, td.FIELDNAMES, rows, force)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def make_all(force: bool) -> None:
    print(f"manifest: {write_manifest(force)}")
    for lecture_id in config.discover_lectures():
        print(f"[{lecture_id}]")
        print(f"  domain_terms.csv   : {write_domain_terms(lecture_id, force)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true",
                        help="overwrite existing templates (DESTROYS hand-filled data)")
    args = parser.parse_args()
    make_all(args.force)


if __name__ == "__main__":
    main()
