"""
Schema definitions and helpers for the annotation review application.
"""

from typing import List, Dict, Any, Optional
import pandas as pd

def safe_str(val: Any, default: str = "") -> str:
    """
    Safely convert a pandas cell value to a clean string, avoiding "nan" string propagation.
    """
    if pd.isna(val) or val is None:
        return default
    s = str(val).strip()
    if s.lower() == "nan":
        return default
    return s

# Core review metadata columns that we support and can add if missing
REVIEW_METADATA_COLS = {
    "reviewer_status": "unreviewed",
    "review_note": "",
    "needs_followup": False,
    "final_note": "",
    "reviewed_by": "",
    "last_reviewed_at": "",
}

# Review CSV files supported by the app.
REVIEW_CSV_OPTIONS = [
    "semantic_review.csv",
    "semantic_review_gpt4o_ailn_post.csv",
    "polarity_review.csv",
]

# Default labels for semantic reviews
SEMANTIC_SUGGESTED_LABELS = [
    "Faithful",
    "Minor rewrite",
    "Omission",
    "Substitution",
    "Polarity error",
    "Relation error",
    "Addition",
    "Unclear",
    "Not applicable",
]

# Default labels for polarity reviews
POLARITY_SUGGESTED_LABELS = [
    "Correct",
    "Incorrect",
    "Omitted",
    "Flip",
    "Unclear",
    "Not applicable",
]

# Per-condition polarity verdict columns.
CONDITION_VERDICT_COLS = [
    "whisper1",
    "ai_lecturenote",
    "gpt4o",
    "gpt4o_prompted",
    "gpt4o_ailn_post",
]

POLARITY_VERDICT_OPTIONS = [
    "correct",
    "wrong",
    "omitted",
    "unclear",
]

# Reviewer status options
REVIEWER_STATUS_OPTIONS = [
    "unreviewed",
    "reviewed_ok",
    "revised",
    "needs_followup",
    "exclude",
    "spot_checked_ok",
]

# Drift/Error values indicating annotation discrepancy or error
DRIFT_ERROR_LABELS = [
    "Omission",
    "Substitution",
    "Polarity error",
    "Relation error",
    "Addition",
    "Incorrect",
    "Omitted",
    "Flip",
    "Unclear",
]

# Faithful / Correct labels
FAITHFUL_CORRECT_LABELS = [
    "Faithful",
    "Correct",
]

# Common text and output columns to highlight in the UI
SOURCE_TEXT_COLS = [
    "reference_claim",
    "reference_phrase",
    "reference",
    "ref_text",
    "source",
    "context",
    "correct_value",
]

HYPOTHESIS_TEXT_COLS = [
    "ai_lecturenote_output",
    "gpt4o_ailn_post_output",
    "whisper1_span",
    "ai_lecturenote_span",
    "gpt4o_ailn_post_span",
    "gpt4o_span",
    "gpt4o_prompted_span",
    "output",
    "hypothesis",
    "ai_output",
    "whisper_output",
    "gpt4o_output",
    "target",
    "term",
    "claim",
]

INFO_COLS = [
    "why_it_matters",
    "polarity_group",
    "error_type",
]


def detect_csv_type(filename: str) -> str:
    """
    Detect the type of CSV based on filename.
    Returns a stable review kind such as 'semantic', 'semantic_gpt4o_ailn_post',
    'polarity', or 'unknown'.
    """
    fn = filename.lower()
    if "semantic_review_gpt4o_ailn_post" in fn:
        return "semantic_gpt4o_ailn_post"
    elif "semantic" in fn:
        return "semantic"
    elif "polarity" in fn:
        return "polarity"
    return "unknown"


def get_suggested_labels(csv_type: str, existing_labels: Optional[List[str]] = None) -> List[str]:
    """
    Get recommended label list based on CSV type, merged with unique existing values.
    """
    if csv_type.startswith("semantic"):
        defaults = list(SEMANTIC_SUGGESTED_LABELS)
    elif csv_type == "polarity":
        defaults = list(POLARITY_SUGGESTED_LABELS)
    else:
        defaults = []

    if existing_labels:
        # Merge existing unique labels, cleaning whitespace and filtering nan
        cleaned_existing = []
        for l in existing_labels:
            lbl = safe_str(l)
            if not lbl:
                continue
            if lbl not in cleaned_existing:
                cleaned_existing.append(lbl)
        
        # Combine
        for val in cleaned_existing:
            if val not in defaults:
                defaults.append(val)
                
    return defaults


def get_edit_target_cols(df: pd.DataFrame, csv_type: str) -> List[str]:
    """
    Determine columns that the user can edit as labels or annotations.
    """
    targets = []
    # Primary label fields
    for col in ["label", "semantic_label", "polarity_label"]:
        if col in df.columns:
            targets.append(col)

    if csv_type == "polarity":
        for col in CONDITION_VERDICT_COLS:
            if col in df.columns and col not in targets:
                targets.append(col)
            
    # Add generic 'error_type' if present and not already added
    if "error_type" in df.columns and "error_type" not in targets:
        targets.append("error_type")

    return targets


def ensure_review_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Check if review metadata columns exist in the DataFrame, and add them if missing.
    Preserves existing columns and order. New columns are appended to the end.
    """
    df_copy = df.copy()
    
    for col, default_val in REVIEW_METADATA_COLS.items():
        if col not in df_copy.columns:
            if col == "needs_followup":
                df_copy[col] = False
            else:
                df_copy[col] = default_val
            
    # Cast types properly for review columns to avoid mixed-type issues during editing
    if "needs_followup" in df_copy.columns:
        df_copy["needs_followup"] = df_copy["needs_followup"].fillna(False).astype(bool)
    
    for col in ["reviewer_status", "review_note", "final_note", "reviewed_by", "last_reviewed_at"]:
        if col in df_copy.columns:
            df_copy[col] = df_copy[col].apply(lambda x: safe_str(x))

    editable_text_cols = [
        "label",
        "semantic_label",
        "polarity_label",
        "error_type",
        *CONDITION_VERDICT_COLS,
    ]
    for col in editable_text_cols:
        if col in df_copy.columns:
            df_copy[col] = df_copy[col].astype("object")
            
    return df_copy
