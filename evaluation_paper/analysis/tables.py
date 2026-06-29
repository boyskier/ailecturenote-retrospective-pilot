"""Assemble every result table as a pandas DataFrame and write it to outputs/tables/.

Tables degrade gracefully: lectures without a reference or without curated
annotations simply contribute fewer rows. All four pilot lectures (diuretics_01,
acuteinflammation_02, anthrax_01, anticancerdrugs_02) currently have a reference
and curated annotations, so the reference-dependent tables are fully populated;
the degradation path remains for any future lecture added without complete inputs.
"""
from __future__ import annotations

import os

import pandas as pd

import config
import accuracy
import term_preservation as tp
import chunk_consistency as cc
import polarity as pol
import semantic_audit as sem


def _cond_label(cond: str) -> str:
    return config.CONDITIONS[cond]["label"]


# ---------------------------------------------------------------------------
# Per-analysis tables
# ---------------------------------------------------------------------------
def accuracy_table() -> pd.DataFrame:
    rows = []
    for lecture_id in config.discover_lectures():
        for res in accuracy.accuracy_for_lecture(lecture_id):
            row = res.as_row()
            row["condition_label"] = _cond_label(row["condition"])
            rows.append(row)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    # Macro average across lectures, per condition.
    macro = (df.groupby("condition", as_index=False)[["cer", "wer", "length_ratio"]]
               .mean(numeric_only=True))
    macro["lecture_id"] = "MACRO_AVG"
    macro["condition_label"] = macro["condition"].map(_cond_label)
    for col in ("cer", "wer", "length_ratio"):
        macro[col] = macro[col].round(4)
    df = pd.concat([df, macro], ignore_index=True)
    return _order_conditions(df)


def term_preservation_table() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    detail_rows = []
    for lecture_id in config.discover_lectures():
        results, details = tp.preservation_for_lecture(lecture_id)
        for res in results:
            row = res.as_row()
            row["condition_label"] = _cond_label(row["condition"])
            rows.append(row)
        for d in details:
            base = {
                "lecture_id": d.lecture_id,
                "term_id": d.term_id,
                "canonical_english": d.canonical_english,
                "category": d.category,
                "ref_count": d.ref_count,
            }
            for cond in config.CONDITION_ORDER:
                base[f"{cond}_english"] = d.per_condition_english.get(cond, "")
                base[f"{cond}_phonetic"] = d.per_condition_phonetic.get(cond, "")
            detail_rows.append(base)
    df = pd.DataFrame(rows)
    if not df.empty:
        macro = (df.groupby("condition", as_index=False)
                   [["english_script_rate", "unique_term_recall"]]
                   .mean(numeric_only=True))
        macro["lecture_id"] = "MACRO_AVG"
        macro["condition_label"] = macro["condition"].map(_cond_label)
        for col in ("english_script_rate", "unique_term_recall"):
            macro[col] = macro[col].round(4)
        df = pd.concat([df, macro], ignore_index=True)
        df = _order_conditions(df)
    return df, pd.DataFrame(detail_rows)


def chunk_table() -> pd.DataFrame:
    rows = []
    for lecture_id in config.discover_lectures():
        for row in cc.chunks_for_lecture(lecture_id):
            r = row.as_row()
            r["condition_label"] = _cond_label(r["condition"])
            rows.append(r)
    return pd.DataFrame(rows)


def polarity_auto_table() -> pd.DataFrame:
    rows = []
    for lecture_id in config.discover_lectures():
        rows.extend(pol.auto_polarity_counts(lecture_id))
    return pd.DataFrame(rows)


def polarity_summary_table() -> pd.DataFrame:
    rows = []
    for lecture_id in config.discover_lectures():
        for r in pol.summarize_polarity_items(lecture_id):
            r["condition_label"] = _cond_label(r["condition"])
            rows.append(r)
    return pd.DataFrame(rows)


def semantic_summary_table() -> pd.DataFrame:
    rows = []
    for lecture_id in config.discover_lectures():
        for condition in sem.SEMANTIC_REVIEW_CONDITIONS:
            s = sem.summarize_semantic(lecture_id, condition)
            if s:
                s.pop("counts", None)
                s["condition_label"] = _cond_label(condition)
                rows.append(s)
    return pd.DataFrame(rows)


def semantic_drift_table() -> pd.DataFrame:
    rows = []
    for lecture_id in config.discover_lectures():
        for condition in sem.SEMANTIC_REVIEW_CONDITIONS:
            rows.extend(sem.drift_examples(lecture_id, condition))
    return pd.DataFrame(rows)


def drift_taxonomy_table() -> pd.DataFrame:
    """Per-lecture AI_LectureNote drift decomposed by category (Analysis 9)."""
    rows = []
    for lecture_id in config.discover_lectures():
        for condition in sem.SEMANTIC_REVIEW_CONDITIONS:
            s = sem.summarize_semantic(lecture_id, condition)
            if s:
                row = sem.drift_taxonomy(lecture_id, condition)
                row["condition_label"] = _cond_label(condition)
                rows.append(row)
    return pd.DataFrame(rows)


def polarity_transition_table() -> pd.DataFrame:
    """Post-processing effect on polarity: raw whisper-1 -> AI_LectureNote.

    Quantifies how many polarity statements the AI kept / fixed / newly flipped /
    dropped relative to the raw ASR it post-processes (Analysis 6 + 8).
    """
    rows = []
    for lecture_id in config.discover_lectures():
        if not pol.load_polarity_items(lecture_id):
            continue
        t = pol.transition_whisper_to_ai(lecture_id)
        t.pop("transitions", None)
        rows.append(t)
    return pd.DataFrame(rows)


def polarity_agreement_table() -> pd.DataFrame:
    """Cross-input polarity agreement: AI_LectureNote vs gpt4o_ailn_post.

    Makes the body claim "the two post-processing conditions reach the same
    polarity verdict on 95/101 items (94%), failure-set Jaccard 0.60" reproducible
    from outputs/tables/ rather than living only in the paper text (paper §6.6/§6.7).
    """
    return pd.DataFrame(pol.polarity_agreement())


def semantic_agreement_table() -> pd.DataFrame:
    """Cross-input semantic-drift-set overlap: AI_LectureNote vs gpt4o_ailn_post.

    Makes the "similar drift total (34 vs 36) but Jaccard 0.23 -> drift re-routes to
    different sentences under a different STT" claim reproducible (paper §6.7).
    """
    return pd.DataFrame(sem.drift_agreement())


# ---------------------------------------------------------------------------
# Final cross-condition summary (paper Table M)
# ---------------------------------------------------------------------------
def cross_condition_summary(acc_df: pd.DataFrame, term_df: pd.DataFrame,
                            pol_sum_df: pd.DataFrame,
                            sem_sum_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cond in config.CONDITION_ORDER:
        meta = config.CONDITIONS[cond]
        row = {"condition": cond, "condition_label": meta["label"]}

        if not acc_df.empty:
            m = acc_df[(acc_df.lecture_id == "MACRO_AVG") & (acc_df.condition == cond)]
            row["CER_macro"] = float(m.cer.iloc[0]) if not m.empty else None
            row["WER_macro"] = float(m.wer.iloc[0]) if not m.empty else None
        if not term_df.empty:
            m = term_df[(term_df.lecture_id == "MACRO_AVG") & (term_df.condition == cond)]
            row["english_script_rate_macro"] = (
                float(m.english_script_rate.iloc[0]) if not m.empty else None)
            occ = term_df[(term_df.lecture_id != "MACRO_AVG") & (term_df.condition == cond)]
            row["korean_phonetic_count_total"] = (
                int(occ.korean_phonetic_count.sum()) if not occ.empty else None)
        if not pol_sum_df.empty:
            m = pol_sum_df[pol_sum_df.condition == cond]
            # Keep wrong (flipped) and omitted (dropped) separate, and report the
            # combined polarity-failure count used in interpretation.
            row["polarity_wrong_total"] = int(m.wrong.sum()) if not m.empty else None
            row["polarity_omitted_total"] = int(m.omitted.sum()) if not m.empty else None
            row["polarity_failure_total"] = (
                int(m.wrong.sum() + m.omitted.sum()) if not m.empty else None)
        else:
            row["polarity_wrong_total"] = None
            row["polarity_omitted_total"] = None
            row["polarity_failure_total"] = None
        # Semantic drift applies only to post-processing conditions with human labels.
        if cond not in sem.SEMANTIC_REVIEW_CONDITIONS:
            row["semantic_drift_total"] = "N/A"
        elif (not sem_sum_df.empty and "condition" in sem_sum_df.columns
              and cond in set(sem_sum_df.condition)):
            m = sem_sum_df[sem_sum_df.condition == cond]
            # A semantic-review condition is only "done" when every lecture that the
            # reference condition (ai_lecturenote) has labeled is also labeled here.
            ref_lectures = set(sem_sum_df[sem_sum_df.condition == "ai_lecturenote"].lecture_id)
            cond_lectures = set(m.lecture_id)
            if ref_lectures and not ref_lectures.issubset(cond_lectures):
                # Partially labeled -> a "0" here would falsely read as "no drift".
                row["semantic_drift_total"] = "pending"
            else:
                row["semantic_drift_total"] = int(m.semantic_drift.sum())
        else:
            # In SEMANTIC_REVIEW_CONDITIONS but nothing labeled yet.
            row["semantic_drift_total"] = "pending"
        row["notes"] = meta["role"]
        rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Helpers / driver
# ---------------------------------------------------------------------------
def _order_conditions(df: pd.DataFrame) -> pd.DataFrame:
    order = {c: i for i, c in enumerate(config.CONDITION_ORDER)}
    df = df.copy()
    df["_o"] = df["condition"].map(order).fillna(99)
    lec_order = {"MACRO_AVG": "zzz"}
    df["_l"] = df["lecture_id"].map(lambda x: lec_order.get(x, x))
    df = df.sort_values(["_l", "_o"]).drop(columns=["_o", "_l"]).reset_index(drop=True)
    return df


_TABLE_NOTES = """# Table aggregation notes

Auto-generated by `analysis/run_all.py` (do not edit by hand). Its purpose is to
keep two kinds of cross-lecture aggregate explicitly separated so a count is never
read as a mean.

## Two aggregation types

- **Macro mean** — the unweighted mean across the lectures (each lecture weighted
  equally, regardless of length). Used for *rates / error metrics*: CER, WER,
  length ratio, English-script rendering rate, unique-term recall. In
  `table1`/`table2` these are the values in the `lecture_id == MACRO_AVG` row; in
  `table_main_cross_condition_summary` they carry the **`_macro`** suffix.

- **Pooled count** — the sum over all lectures (a corpus-level total, NOT a
  per-lecture average). Used for *counts*: Korean phonetic occurrences, polarity
  failures (wrong / omitted), semantic-drift counts, domain-term occurrences. In
  `table_main_cross_condition_summary` these carry the **`_total`** suffix.

**Pooled counts are not macro means.** The `MACRO_AVG` rows of `table1`/`table2`
deliberately leave the count columns (e.g. `korean_phonetic_count`, `ref_chars`,
`english_preserved`) blank so a pooled total is never mislabeled as a macro value.

## Per-table column roles

- `table1_accuracy_cer_wer`: `cer`, `wer`, `length_ratio` are macro means in the
  `MACRO_AVG` row; `ref_chars`, `out_chars` are per-lecture only.
- `table2_term_preservation`: `english_script_rate`, `unique_term_recall` are macro
  means in the `MACRO_AVG` row; `ref_term_occurrences`, `english_preserved`,
  `korean_phonetic_count`, `unique_terms_*` are pooled counts, reported per-lecture
  only (blank in `MACRO_AVG`).
- `table_main_cross_condition_summary`: `CER_macro`, `WER_macro`,
  `english_script_rate_macro` are macro means; `korean_phonetic_count_total`,
  `polarity_wrong_total`, `polarity_omitted_total`, `polarity_failure_total`,
  `semantic_drift_total` are pooled counts. `semantic_drift_total` is `N/A` for the
  raw-ASR conditions (no human semantic labels) and is never silently 0.
- `table5_polarity_summary`, `table6_semantic_summary`, `table8_drift_taxonomy`:
  per-lecture rows; corpus figures are pooled sums of these rows (polarity cue rows
  and semantic claims pool to corpus totals; drift `drift_rows` pool to the unique
  drifted-claim totals, distinct from the per-category label incidences).
"""


def write_table_notes() -> str:
    """Write the macro-vs-pooled aggregation notes alongside the CSVs."""
    config.ensure_output_dirs()
    path = os.path.join(config.TABLES_DIR, "_TABLE_NOTES.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(_TABLE_NOTES)
    return path


def build_all(verbose: bool = True) -> dict:
    config.ensure_output_dirs()
    acc = accuracy_table()
    term_df, term_detail = term_preservation_table()
    chunks = chunk_table()
    pol_auto = polarity_auto_table()
    pol_sum = polarity_summary_table()
    pol_trans = polarity_transition_table()
    sem_sum = semantic_summary_table()
    sem_drift = semantic_drift_table()
    sem_tax = drift_taxonomy_table()
    pol_agree = polarity_agreement_table()
    sem_agree = semantic_agreement_table()
    summary = cross_condition_summary(acc, term_df, pol_sum, sem_sum)

    outputs = {
        "table1_accuracy_cer_wer": acc,
        "table2_term_preservation": term_df,
        "table2b_term_detail": term_detail,
        "table3_chunk_consistency": chunks,
        "table4_polarity_auto_counts": pol_auto,
        "table5_polarity_summary": pol_sum,
        "table6_semantic_summary": sem_sum,
        "table7_semantic_drift_examples": sem_drift,
        "table8_drift_taxonomy": sem_tax,
        "table9_polarity_transition": pol_trans,
        "table10_postprocessing_polarity_agreement": pol_agree,
        "table11_postprocessing_semantic_agreement": sem_agree,
        "table_main_cross_condition_summary": summary,
    }
    for name, df in outputs.items():
        path = os.path.join(config.TABLES_DIR, name + ".csv")
        df.to_csv(path, index=False, encoding="utf-8-sig")
        if verbose:
            status = "empty (awaiting data)" if df.empty else f"{len(df)} rows"
            print(f"  {name}.csv: {status}")
    write_table_notes()
    if verbose:
        print("  _TABLE_NOTES.md: macro-vs-pooled aggregation notes")
    return outputs


if __name__ == "__main__":
    build_all()
