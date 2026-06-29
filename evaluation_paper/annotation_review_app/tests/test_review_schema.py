import sys
import pandas as pd
from pathlib import Path

# Add the app directory to sys.path to enable imports
app_dir = Path(__file__).resolve().parents[1]
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

from review_schema import (
    detect_csv_type,
    get_suggested_labels,
    get_edit_target_cols,
    ensure_review_columns,
)

def test_detect_csv_type():
    assert detect_csv_type("semantic_review.csv") == "semantic"
    assert detect_csv_type("/path/to/semantic_review.csv") == "semantic"
    assert detect_csv_type("semantic_review_gpt4o_ailn_post.csv") == "semantic_gpt4o_ailn_post"
    assert detect_csv_type("polarity_review.csv") == "polarity"
    assert detect_csv_type("unknown_file.csv") == "unknown"

def test_get_suggested_labels():
    # Semantic suggestions should contain default semantic labels
    semantic_labels = get_suggested_labels("semantic")
    assert "Faithful" in semantic_labels
    assert "Omission" in semantic_labels
    
    # Polarity suggestions should contain default polarity labels
    polarity_labels = get_suggested_labels("polarity")
    assert "Correct" in polarity_labels
    assert "Flip" in polarity_labels
    
    # Merge existing labels
    merged = get_suggested_labels("semantic", ["CustomLabel", "Faithful"])
    assert "CustomLabel" in merged
    # Check that duplication is avoided
    assert merged.count("Faithful") == 1

def test_get_edit_target_cols():
    # Check that targets are extracted correctly
    df = pd.DataFrame(columns=["label", "error_type", "other_col"])
    targets = get_edit_target_cols(df, "semantic")
    assert "label" in targets
    assert "error_type" in targets
    assert "other_col" not in targets

    df_polarity = pd.DataFrame(columns=["whisper1", "gpt4o_ailn_post", "gpt4o_ailn_post_span"])
    polarity_targets = get_edit_target_cols(df_polarity, "polarity")
    assert "whisper1" in polarity_targets
    assert "gpt4o_ailn_post" in polarity_targets
    assert "gpt4o_ailn_post_span" not in polarity_targets

def test_ensure_review_columns():
    df = pd.DataFrame({
        "claim_id": ["id1"],
        "label": ["Faithful"],
    })
    
    df_new = ensure_review_columns(df)
    
    # Verify review columns are added
    for col in ["reviewer_status", "review_note", "needs_followup", "final_note", "reviewed_by", "last_reviewed_at"]:
        assert col in df_new.columns
        
    # Check default values
    assert df_new.loc[0, "reviewer_status"] == "unreviewed"
    assert df_new.loc[0, "needs_followup"] == False
    assert df_new.loc[0, "review_note"] == ""
    
    # Check that existing values are not overwritten
    df_existing = pd.DataFrame({
        "reviewer_status": ["reviewed_ok"],
        "needs_followup": [True]
    })
    df_existing_new = ensure_review_columns(df_existing)
    assert df_existing_new.loc[0, "reviewer_status"] == "reviewed_ok"
    assert df_existing_new.loc[0, "needs_followup"] == True
