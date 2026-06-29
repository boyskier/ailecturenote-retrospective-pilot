"""
Data I/O, backup, sampling, and audit summary logic.
"""

import os
import csv
import json
import datetime
import random
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
from review_schema import (
    ensure_review_columns,
    detect_csv_type,
    DRIFT_ERROR_LABELS,
    FAITHFUL_CORRECT_LABELS,
    safe_str,
)


def get_repo_root() -> Path:
    """
    Get the repository root path.
    """
    return Path(__file__).resolve().parents[2]


def get_annotations_root() -> Path:
    """
    Get the annotations directory path.
    """
    return get_repo_root() / "evaluation_paper" / "annotations"


def get_data_root() -> Path:
    """
    Get the data directory path.
    """
    return get_repo_root() / "evaluation_paper" / "data"


def get_backups_dir() -> Path:
    """
    Get the backups directory path.
    """
    d = get_repo_root() / "evaluation_paper" / "annotation_review_app" / "backups"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_samples_dir() -> Path:
    """
    Get the samples directory path.
    """
    d = get_repo_root() / "evaluation_paper" / "annotation_review_app" / "samples"
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_available_lectures() -> List[str]:
    """
    Scan annotations and data directories to list unique lecture_id folders.
    """
    roots = [get_annotations_root(), get_data_root()]
    lectures = set()
    for root in roots:
        if root.exists() and root.is_dir():
            for child in root.iterdir():
                if child.is_dir() and not child.name.startswith("."):
                    # We check if it has target CSV files or txt files
                    lectures.add(child.name)
    return sorted(list(lectures))


def get_csv_path(lecture_id: str, csv_name: str) -> Path:
    """
    Look for the CSV file in annotations, falling back to data directory.
    """
    # Prefer annotations
    path = get_annotations_root() / lecture_id / csv_name
    if path.exists():
        return path
    
    # Fall back to data
    path_data = get_data_root() / lecture_id / csv_name
    return path_data


def load_review_csv_tolerant(file_path: Path) -> pd.DataFrame:
    """
    Load a review CSV even if an unquoted comma split a text cell.
    Overlong rows are repaired by merging extra cells into the first text column.
    """
    text_merge_candidates = [
        "reference_claim",
        "reference_phrase",
        "ai_lecturenote_output",
        "gpt4o_ailn_post_output",
    ]

    repaired_rows = []
    repaired_line_numbers = []
    with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            df = pd.DataFrame()
            df.attrs["load_warnings"] = []
            return df

        expected_len = len(header)
        merge_col = next((c for c in text_merge_candidates if c in header), header[0])
        merge_idx = header.index(merge_col)

        for line_number, row in enumerate(reader, start=2):
            if len(row) > expected_len:
                extra = len(row) - expected_len
                row = (
                    row[:merge_idx]
                    + [",".join(row[merge_idx : merge_idx + extra + 1])]
                    + row[merge_idx + extra + 1 :]
                )
                repaired_line_numbers.append(line_number)
            elif len(row) < expected_len:
                row = row + [""] * (expected_len - len(row))
                repaired_line_numbers.append(line_number)
            repaired_rows.append(row)

    df = pd.DataFrame(repaired_rows, columns=header)
    df.attrs["load_warnings"] = repaired_line_numbers
    return df


def load_review_csv(file_path: Path) -> pd.DataFrame:
    """
    Load an annotation CSV file using utf-8-sig encoding.
    Ensures that the review metadata columns are initialized.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
        
    try:
        df = pd.read_csv(file_path, encoding="utf-8-sig")
    except pd.errors.EmptyDataError:
        df = pd.DataFrame()
    except pd.errors.ParserError:
        df = load_review_csv_tolerant(file_path)
        
    load_warnings = df.attrs.get("load_warnings", [])
    df = ensure_review_columns(df)
    df.attrs["load_warnings"] = load_warnings
    return df


def save_review_csv(df: pd.DataFrame, file_path: Path, lecture_id: str, csv_type: str) -> Path:
    """
    Save the DataFrame back to its CSV file, creating a backup first.
    All saving uses utf-8-sig encoding to preserve Korean and Excel support.
    """
    # 1. Create a backup if the original file exists
    if file_path.exists():
        backups_dir = get_backups_dir()
        backups_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{lecture_id}_{csv_type}_{timestamp}.csv"
        backup_path = backups_dir / backup_name
        
        # Read the existing raw content and write to backup to be completely safe
        with open(file_path, "r", encoding="utf-8-sig") as f:
            content = f.read()
        with open(backup_path, "w", encoding="utf-8-sig", newline="") as f:
            f.write(content)
    else:
        # If writing to a new file, ensure the directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path = Path("")

    # 2. Save the edited DataFrame to the original location
    # Use index=False, utf-8-sig, and ensure newlines in cells are preserved correctly
    df.to_csv(file_path, encoding="utf-8-sig", index=False, lineterminator="\n")
    return backup_path


def create_random_sample(
    df: pd.DataFrame,
    filter_name: str,
    pct: float,
    seed: int,
    lecture_id: str,
    csv_type: str
) -> Tuple[List[int], Path]:
    """
    Filter the DataFrame based on filter_name, take a random sample,
    and save the sampled indices to a JSON file in samples/.
    """
    # Identify matching indices
    matching_indices = []
    
    label_col = "label" if "label" in df.columns else ("polarity_label" if "polarity_label" in df.columns else None)
    
    for idx, row in df.iterrows():
        # Get label and status
        lbl = safe_str(row.get(label_col, "")) if label_col else ""
        status = safe_str(row.get("reviewer_status", "unreviewed"))
        match = False
        if filter_name == "All rows":
            match = True
        elif filter_name == "Faithful / Correct":
            match = any(lbl.lower() == f.lower() for f in FAITHFUL_CORRECT_LABELS)
        elif filter_name == "Drift / Error rows":
            match = any(lbl.lower() == d.lower() for d in DRIFT_ERROR_LABELS)
        elif filter_name == "Blank label rows":
            match = pd.isna(row.get(label_col)) or lbl == ""
        elif filter_name == "Unreviewed rows":
            match = (status == "unreviewed")
        elif filter_name == "Needs-followup rows":
            match = (status == "needs_followup" or row.get("needs_followup") is True)
            
        if match:
            matching_indices.append(idx)
            
    if not matching_indices:
        raise ValueError(f"No rows match the filter: '{filter_name}'")
        
    # Sample
    sample_size = max(1, int(len(matching_indices) * (pct / 100.0)))
    sample_size = min(sample_size, len(matching_indices))
    
    # Set seed
    random.seed(seed)
    sampled_indices = random.sample(matching_indices, sample_size)
    sampled_indices.sort()  # Keep indices in sorted order
    
    # Save active sample info to file
    samples_dir = get_samples_dir()
    samples_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    sanitized_filter = filter_name.replace("/", "_").replace(" ", "_")
    sample_filename = f"{lecture_id}_{csv_type}_{sanitized_filter}_pct{int(pct)}_seed{seed}_{timestamp}.json"
    sample_path = samples_dir / sample_filename
    
    sample_data = {
        "lecture_id": lecture_id,
        "csv_type": csv_type,
        "filter_name": filter_name,
        "percentage": pct,
        "seed": seed,
        "timestamp": timestamp,
        "indices": sampled_indices
    }
    
    with open(sample_path, "w", encoding="utf-8") as f:
        json.dump(sample_data, f, indent=2, ensure_ascii=False)
        
    return sampled_indices, sample_path


def load_saved_sample(sample_path: Path) -> Dict[str, Any]:
    """
    Load a saved sample file.
    """
    with open(sample_path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_saved_samples(lecture_id: str, csv_type: str) -> List[Path]:
    """
    List saved sample files for the given lecture and CSV type.
    """
    samples_dir = get_samples_dir()
    results = []
    if samples_dir.exists():
        for child in samples_dir.glob("*.json"):
            # Check prefix
            if child.name.startswith(f"{lecture_id}_{csv_type}_"):
                results.append(child)
    # Sort by modification time (newest first)
    results.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return results


def calculate_audit_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate stats for the audit summary.
    """
    total_rows = len(df)
    
    # Find label column
    label_col = "label" if "label" in df.columns else ("polarity_label" if "polarity_label" in df.columns else None)
    
    reviewed_rows = 0
    unreviewed_rows = 0
    needs_followup_rows = 0
    blank_label_rows = 0
    drift_error_reviewed = 0
    faithful_correct_spotchecked = 0
    faithful_correct_unreviewed = 0
    
    label_counts = {}
    status_counts = {}
    
    for idx, row in df.iterrows():
        status = safe_str(row.get("reviewer_status", "unreviewed")).lower()
        if status == "":
            status = "unreviewed"
        status_counts[status] = status_counts.get(status, 0) + 1
        
        is_reviewed = status in ["reviewed_ok", "revised", "spot_checked_ok", "exclude"]
        if is_reviewed:
            reviewed_rows += 1
        else:
            unreviewed_rows += 1
            
        lbl = safe_str(row.get(label_col, "")) if label_col else ""
        if pd.isna(row.get(label_col)) or lbl == "":
            blank_label_rows += 1
        else:
            label_counts[lbl] = label_counts.get(lbl, 0) + 1
            
        if row.get("needs_followup") is True or status == "needs_followup":
            needs_followup_rows += 1
            
        # Sampling metrics
        is_drift_error = any(lbl.lower() == d.lower() for d in DRIFT_ERROR_LABELS)
        is_faithful_correct = any(lbl.lower() == f.lower() for f in FAITHFUL_CORRECT_LABELS)

        if is_reviewed:
            if is_drift_error:
                drift_error_reviewed += 1
            if is_faithful_correct and status == "spot_checked_ok":
                faithful_correct_spotchecked += 1
        else:
            if is_faithful_correct:
                faithful_correct_unreviewed += 1
                
    return {
        "total_rows": total_rows,
        "reviewed_rows": reviewed_rows,
        "unreviewed_rows": unreviewed_rows,
        "blank_label_rows": blank_label_rows,
        "needs_followup_rows": needs_followup_rows,
        "drift_error_reviewed": drift_error_reviewed,
        "faithful_correct_spotchecked": faithful_correct_spotchecked,
        "faithful_correct_unreviewed": faithful_correct_unreviewed,
        "label_counts": label_counts,
        "status_counts": status_counts,
    }


def export_audit_summary_markdown(
    stats_dict: Dict[str, Dict[str, Any]],
    sampling_info_dict: Dict[str, Dict[str, Any]]
) -> str:
    """
    Generate markdown content for ANNOTATION_REVIEW_SUMMARY.md.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = []
    lines.append("# Annotation Review Summary")
    lines.append(f"\nGenerated on: `{timestamp}`")
    lines.append("\n> [!NOTE]")
    lines.append("> This is an internal review summary document generated by the annotation-review app.")
    lines.append("> All semantic and polarity labels used in the paper are single-pass labels from a single author-annotator.")
    lines.append("> This document does not represent a second pass, independent replication, or adjudication.")
    lines.append("> Inter-annotator agreement was not measured.")

    lines.append("\n## Review Sampling Details")
    lines.append("Rows were reviewed using the annotation-review app. Sampling details per lecture are shown below.")
    
    lines.append("\n## Summary Table")
    lines.append("| Lecture ID | File Type | Total Rows | Reviewed (Full + Spot) | Unreviewed | Blank Labels | Needs Followup |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    
    for key, stats in stats_dict.items():
        lecture_id, csv_type = key.split("|")
        lines.append(
            f"| `{lecture_id}` | `{csv_type}` | {stats['total_rows']} | {stats['reviewed_rows']} | {stats['unreviewed_rows']} | {stats['blank_label_rows']} | {stats['needs_followup_rows']} |"
        )
        
    lines.append("\n## Sampling Details")
    for key, s_info in sampling_info_dict.items():
        lecture_id, csv_type = key.split("|")
        stats = stats_dict[key]
        lines.append(f"### `{lecture_id}` - `{csv_type}`")
        if s_info.get("sampled", False):
            lines.append(f"- **Sampling Used**: Yes (Filter: `{s_info['filter_name']}`, Percentage: `{s_info['percentage']}%`, Seed: `{s_info['seed']}`)")
            lines.append(f"- **Sample File**: `{s_info['sample_file_path']}`")
        else:
            lines.append("- **Sampling Used**: No (Full Review)")
        
        lines.append(f"- **Drift/Error Rows Reviewed**: {stats['drift_error_reviewed']}")
        lines.append(f"- **Faithful/Correct Spot-Checked**: {stats['faithful_correct_spotchecked']}")
        lines.append(f"- **Remaining Unreviewed Faithful/Correct**: {stats['faithful_correct_unreviewed']}")
        lines.append("")
        
    lines.append("\n## Label and Status Breakdown")
    for key, stats in stats_dict.items():
        lecture_id, csv_type = key.split("|")
        lines.append(f"### `{lecture_id}` - `{csv_type}` Breakdown")
        
        lines.append("#### Reviewer Status counts:")
        for status, count in sorted(stats["status_counts"].items()):
            lines.append(f"- `{status}`: {count}")
            
        lines.append("#### Label counts:")
        for lbl, count in sorted(stats["label_counts"].items()):
            lines.append(f"- `{lbl}`: {count}")
        lines.append("")

    content = "\n".join(lines)
    
    summary_path = get_repo_root() / "evaluation_paper" / "annotation_review_app" / "ANNOTATION_REVIEW_SUMMARY.md"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    return content
