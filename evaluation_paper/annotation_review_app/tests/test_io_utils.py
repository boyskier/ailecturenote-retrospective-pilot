import sys
import os
import json
from pathlib import Path
import pandas as pd
import pytest

# Add the app directory to sys.path to enable imports
app_dir = Path(__file__).resolve().parents[1]
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

from io_utils import (
    load_review_csv,
    save_review_csv,
    create_random_sample,
    calculate_audit_stats,
    export_audit_summary_markdown,
)

# Sample mixed Korean-English medical text
KOREAN_TEST_STR = "저칼륨혈증 hypokalemia와 고칼륨혈증 hyperkalemia를 구분해야 합니다."
CELL_WITH_COMMAS_AND_NEWLINES = "line 1, with comma\nline 2, with \"quotes\"\nedema factor, protective antigen, adenylate cyclase"

def test_load_and_save_korean_preservation(tmp_path):
    # Create a mock CSV with mixed Korean/English medical terms
    csv_file = tmp_path / "test_semantic.csv"
    
    data = {
        "claim_id": ["sr01", "sr02"],
        "reference_claim": [KOREAN_TEST_STR, "Normal phrase"],
        "ai_lecturenote_output": [CELL_WITH_COMMAS_AND_NEWLINES, "Normal output"],
        "label": ["Faithful", "Omission"],
    }
    
    df_orig = pd.DataFrame(data)
    # Save it using utf-8-sig
    df_orig.to_csv(csv_file, index=False, encoding="utf-8-sig")
    
    # 1. Load the CSV - should auto add review columns
    df_loaded = load_review_csv(csv_file)
    assert len(df_loaded) == 2
    assert "reviewer_status" in df_loaded.columns
    assert "needs_followup" in df_loaded.columns
    assert df_loaded.loc[0, "reference_claim"] == KOREAN_TEST_STR
    assert df_loaded.loc[0, "ai_lecturenote_output"] == CELL_WITH_COMMAS_AND_NEWLINES
    
    # 2. Modify label and review note
    df_loaded.at[0, "label"] = "Substitution"
    df_loaded.at[0, "reviewer_status"] = "revised"
    df_loaded.at[0, "review_note"] = "수정되었습니다."
    
    # Mocking get_backups_dir to place backups in tmp_path
    import io_utils
    orig_get_backups_dir = io_utils.get_backups_dir
    io_utils.get_backups_dir = lambda: tmp_path / "backups"
    
    try:
        # Save CSV (creates a backup in the backups folder under tmp_path)
        backup_path = save_review_csv(df_loaded, csv_file, "lecture_test", "semantic")
        
        # Verify backup exists
        assert backup_path.exists()
        assert "lecture_test" in backup_path.name
        
        # 3. Reload from the original path and check content
        df_reloaded = load_review_csv(csv_file)
        assert len(df_reloaded) == 2
        assert df_reloaded.loc[0, "label"] == "Substitution"
        assert df_reloaded.loc[0, "reviewer_status"] == "revised"
        assert df_reloaded.loc[0, "review_note"] == "수정되었습니다."
        assert df_reloaded.loc[0, "reference_claim"] == KOREAN_TEST_STR
        assert df_reloaded.loc[0, "ai_lecturenote_output"] == CELL_WITH_COMMAS_AND_NEWLINES
        
        # Verify row order is preserved
        assert list(df_reloaded["claim_id"]) == ["sr01", "sr02"]
        
    finally:
        io_utils.get_backups_dir = orig_get_backups_dir

def test_sampling_logic(tmp_path):
    # Mock samples directory
    import io_utils
    orig_get_samples_dir = io_utils.get_samples_dir
    io_utils.get_samples_dir = lambda: tmp_path / "samples"
    
    try:
        data = {
            "claim_id": [f"sr{i}" for i in range(10)],
            "label": ["Faithful"] * 5 + ["Omission"] * 3 + ["Addition"] * 2,
            "reviewer_status": ["unreviewed"] * 10
        }
        df = pd.DataFrame(data)
        
        # Sample Faithful rows: 5 rows exist, 40% sample = 2 rows
        indices, sample_path = create_random_sample(
            df, 
            filter_name="Faithful / Correct", 
            pct=40.0, 
            seed=42, 
            lecture_id="test_lect", 
            csv_type="semantic"
        )
        
        assert len(indices) == 2
        assert sample_path.exists()
        
        # Read the sample JSON to verify contents
        with open(sample_path, "r", encoding="utf-8") as f:
            sample_data = json.load(f)
            
        assert sample_data["lecture_id"] == "test_lect"
        assert sample_data["percentage"] == 40.0
        assert sample_data["seed"] == 42
        assert len(sample_data["indices"]) == 2
        
        # Verify seed reproducibility (same parameters should yield same indices)
        indices2, _ = create_random_sample(
            df, 
            filter_name="Faithful / Correct", 
            pct=40.0, 
            seed=42, 
            lecture_id="test_lect", 
            csv_type="semantic"
        )
        assert indices == indices2
        
        # Verify ValueError on empty filter (e.g. searching for High risk rows which don't exist in df)
        with pytest.raises(ValueError):
            create_random_sample(
                df,
                filter_name="High risk rows",
                pct=20.0,
                seed=42,
                lecture_id="test_lect",
                csv_type="semantic"
            )
        
    finally:
        io_utils.get_samples_dir = orig_get_samples_dir

def test_calculate_audit_stats():
    data = {
        "label": ["Faithful", "Omission", "", "Faithful", "Incorrect", "Correct"],
        "reviewer_status": ["unreviewed", "reviewed_ok", "needs_followup", "spot_checked_ok", "exclude", "revised"],
        "needs_followup": [True, False, True, False, False, False]
    }
    df = pd.DataFrame(data)
    
    stats = calculate_audit_stats(df)
    
    assert stats["total_rows"] == 6
    # Reviewed statuses are: reviewed_ok, spot_checked_ok, exclude, revised (total 4)
    assert stats["reviewed_rows"] == 4
    # Unreviewed statuses are: unreviewed, needs_followup (total 2)
    assert stats["unreviewed_rows"] == 2
    # Needs followup counts: needs_followup status + needs_followup boolean column (total 2 rows)
    assert stats["needs_followup_rows"] == 2
    # Blank label rows: the third one is empty (total 1)
    assert stats["blank_label_rows"] == 1
    # Check status counts
    assert stats["status_counts"]["unreviewed"] == 1
    assert stats["status_counts"]["reviewed_ok"] == 1

def test_nan_and_mixed_types_propagation(tmp_path):
    csv_file = tmp_path / "test_nan_propagation.csv"
    
    # Create mock CSV with float nan, string "nan", and mixed needs_followup values
    data = {
        "claim_id": ["sr01", "sr02", "sr03"],
        "reviewer_status": [float("nan"), "NaN", "reviewed_ok"],
        "needs_followup": [float("nan"), "True", 1],
        "review_note": [float("nan"), "Some note", None],
    }
    
    df = pd.DataFrame(data)
    df.to_csv(csv_file, index=False, encoding="utf-8-sig")
    
    # Load and verify
    df_loaded = load_review_csv(csv_file)
    assert len(df_loaded) == 3
    
    # Verify NaN/None is cleaned to empty strings
    assert df_loaded.loc[0, "reviewer_status"] == ""
    assert df_loaded.loc[1, "reviewer_status"] == ""
    assert df_loaded.loc[2, "reviewer_status"] == "reviewed_ok"
    
    assert df_loaded.loc[0, "review_note"] == ""
    assert df_loaded.loc[1, "review_note"] == "Some note"
    assert df_loaded.loc[2, "review_note"] == ""
    
    # Verify needs_followup is cast to booleans safely
    assert df_loaded.loc[0, "needs_followup"] == False
    assert df_loaded.loc[1, "needs_followup"] == True
    assert df_loaded.loc[2, "needs_followup"] == True

def test_empty_file_handling(tmp_path):
    # Create a 0-byte file
    empty_file = tmp_path / "empty.csv"
    empty_file.touch()
    
    # Loading should not crash, it should return an empty DataFrame with metadata columns
    df_loaded = load_review_csv(empty_file)
    assert len(df_loaded) == 0
    assert "reviewer_status" in df_loaded.columns
    assert "needs_followup" in df_loaded.columns

