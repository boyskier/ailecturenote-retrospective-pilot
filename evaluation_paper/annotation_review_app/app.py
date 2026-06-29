import streamlit as st
import pandas as pd
from pathlib import Path
import datetime
from io_utils import (
    list_available_lectures,
    get_csv_path,
    load_review_csv,
    save_review_csv,
    calculate_audit_stats,
    create_random_sample,
    list_saved_samples,
    load_saved_sample,
    export_audit_summary_markdown,
)
from review_schema import (
    detect_csv_type,
    get_suggested_labels,
    get_edit_target_cols,
    REVIEWER_STATUS_OPTIONS,
    DRIFT_ERROR_LABELS,
    FAITHFUL_CORRECT_LABELS,
    REVIEW_CSV_OPTIONS,
    CONDITION_VERDICT_COLS,
    POLARITY_VERDICT_OPTIONS,
    SOURCE_TEXT_COLS,
    HYPOTHESIS_TEXT_COLS,
    INFO_COLS,
    safe_str,
)


def truthy_cell(value) -> bool:
    """Interpret CSV checkbox-like cells without treating string '0' as true."""
    if pd.isna(value) or value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value == 1
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def get_display_hypothesis_cols(df: pd.DataFrame, csv_type: str) -> list[str]:
    """Keep polarity output tabs in the same order as the verdict controls."""
    available = [c for c in HYPOTHESIS_TEXT_COLS if c in df.columns]
    if csv_type != "polarity":
        return available

    ordered = []
    for verdict_col in CONDITION_VERDICT_COLS:
        span_col = f"{verdict_col}_span"
        if span_col in df.columns:
            ordered.append(span_col)

    return ordered + [c for c in available if c not in ordered]


# Page configuration
st.set_page_config(
    page_title="Medical Lecture Annotation Auditor",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom premium styling for Streamlit
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 3.5rem;
        padding-bottom: 0.5rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 100%;
    }
    h1 {
        font-size: 1.45rem !important;
        line-height: 1.15 !important;
        margin-bottom: 0.05rem !important;
    }
    h2, h3 {
        margin-top: 0.25rem !important;
        margin-bottom: 0.35rem !important;
    }
    div[data-testid="stVerticalBlock"] {
        gap: 0.45rem;
    }
    div[data-testid="stHorizontalBlock"] {
        gap: 0.7rem;
        width: 100%;
        min-width: 0;
        overflow: visible;
    }
    div[data-testid="column"] {
        min-width: 0 !important;
        flex-shrink: 1 !important;
    }
    .stTextInput, .stSelectbox, .stNumberInput, .stTextArea {
        min-width: 0 !important;
        width: 100% !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.3rem;
    }
    label, .stTextInput label, .stSelectbox label, .stNumberInput label {
        font-size: 0.78rem !important;
        margin-bottom: 0.15rem !important;
    }
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        min-height: 2rem;
        min-width: 0 !important;
        width: 100% !important;
    }
    div[data-testid="stNumberInput"] {
        min-width: 8.75rem;
    }
    div[data-testid="stNumberInput"] label p,
    .stTextInput label p,
    .stSelectbox label p {
        line-height: 1.2 !important;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .stButton button, .stFormSubmitButton button {
        min-height: 2rem;
        padding: 0.25rem 0.65rem;
        white-space: nowrap;
    }
    textarea {
        min-height: 4.8rem !important;
    }
    .reportview-container {
        background: #0e1117;
    }
    .metric-box {
        background-color: #1e222b;
        border-radius: 8px;
        padding: 15px;
        border: 1px solid #2e333d;
        text-align: center;
    }
    .text-box {
        background-color: #1a1c23;
        border-left: 5px solid #4B9CD3;
        padding: 8px 10px;
        border-radius: 4px;
        margin-top: 0.25rem;
        margin-bottom: 6px;
        font-family: inherit;
        white-space: pre-wrap;
        font-size: 13px;
        line-height: 1.42;
        max-height: 8.5rem;
        overflow-y: auto;
    }
    .text-box.output-box {
        max-height: 16rem;
    }
    .text-box-title {
        font-weight: bold;
        color: #8892b0;
        margin-bottom: 2px;
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.4px;
    }
    .compact-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        flex-wrap: wrap;
        gap: 1rem;
        margin-bottom: 0.65rem;
    }
    .compact-title {
        font-size: 1.35rem;
        font-weight: 750;
        line-height: 1.25;
    }
    .compact-subtitle {
        color: #8f95a3;
        font-size: 0.82rem;
    }
    .compact-section-label {
        display: block;
        color: #a8b3cf;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.45px;
        line-height: 1.25;
        margin-top: 0.65rem;
        margin-bottom: 0.65rem;
        clear: both;
        position: relative;
        z-index: 1;
    }
    .nav-spacer {
        height: 0.65rem;
        clear: both;
    }
    .save-note {
        color: #9ca3af;
        font-size: 0.78rem;
        line-height: 1.35;
    }
    .badge-high-risk {
        background-color: #ff4b4b;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 12px;
    }
    .badge-drift {
        background-color: #fca311;
        color: black;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 12px;
    }
    .badge-ok {
        background-color: #00c853;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Title
st.markdown(
    """
    <div class="compact-header">
      <div>
        <div class="compact-title">Medical Lecture Annotation Reviewer</div>
        <div class="compact-subtitle">Compact CSV-backed annotation workspace</div>
      </div>
      <div class="save-note">Save writes the current row directly to CSV. Export is only for audit summaries.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Initialize Session State
if "df" not in st.session_state:
    st.session_state.df = None
if "file_path" not in st.session_state:
    st.session_state.file_path = None
if "lecture_id" not in st.session_state:
    st.session_state.lecture_id = None
if "csv_type" not in st.session_state:
    st.session_state.csv_type = None
if "csv_name" not in st.session_state:
    st.session_state.csv_name = None
if "active_sample_info" not in st.session_state:
    st.session_state.active_sample_info = None
if "active_queue_indices" not in st.session_state:
    st.session_state.active_queue_indices = []
if "active_queue_ptr" not in st.session_state:
    st.session_state.active_queue_ptr = 0
if "reviewer_name" not in st.session_state:
    st.session_state.reviewer_name = "Auditor"
if "last_save_status" not in st.session_state:
    st.session_state.last_save_status = None

# --- SIDEBAR: Configuration & Navigation ---
st.sidebar.header("📁 Load Dataset")

# Reviewer Name
st.session_state.reviewer_name = st.sidebar.text_input(
    "Reviewer Name", value=st.session_state.reviewer_name
)

# Lecture list
lectures = list_available_lectures()
selected_lecture = st.sidebar.selectbox(
    "Select Lecture ID",
    options=lectures,
    index=lectures.index(st.session_state.lecture_id) if st.session_state.lecture_id in lectures else 0,
)

# CSV Type
selected_csv_type = st.sidebar.selectbox(
    "Select CSV Type",
    options=REVIEW_CSV_OPTIONS,
    index=REVIEW_CSV_OPTIONS.index(st.session_state.csv_name) if st.session_state.csv_name in REVIEW_CSV_OPTIONS else 0,
)

csv_type_key = detect_csv_type(selected_csv_type)
target_path = get_csv_path(selected_lecture, selected_csv_type)

# Trigger reload if lecture or file type changed, or if not loaded
load_triggered = False
if (st.session_state.lecture_id != selected_lecture or 
    st.session_state.csv_type != csv_type_key or 
    st.session_state.csv_name != selected_csv_type or
    st.session_state.df is None):
    
    st.session_state.lecture_id = selected_lecture
    st.session_state.csv_type = csv_type_key
    st.session_state.csv_name = selected_csv_type
    st.session_state.active_sample_info = None  # Reset active sample
    load_triggered = True

# Load button / auto load
if target_path.exists():
    loaded_ok = st.session_state.file_path == target_path and st.session_state.df is not None
    if load_triggered:
        try:
            st.session_state.df = load_review_csv(target_path)
            st.session_state.file_path = target_path
            st.session_state.active_queue_ptr = 0
            st.session_state.last_save_status = None
            loaded_ok = True
        except Exception as e:
            st.session_state.df = None
            st.session_state.file_path = None
            st.session_state.active_queue_ptr = 0
            st.session_state.last_save_status = None
            loaded_ok = False
            st.sidebar.error(f"Error loading file: {e}")
    if loaded_ok:
        st.sidebar.success(f"Loaded: `{target_path.name}`")
        load_warnings = st.session_state.df.attrs.get("load_warnings", [])
        if load_warnings:
            shown_lines = ", ".join(str(n) for n in load_warnings[:5])
            suffix = "..." if len(load_warnings) > 5 else ""
            st.sidebar.warning(
                f"Repaired {len(load_warnings)} malformed CSV row(s) while loading. "
                f"Line(s): {shown_lines}{suffix}"
            )
        st.sidebar.info(f"Path: `{target_path.relative_to(target_path.parents[3]) if len(target_path.parts) > 3 else target_path}`")
else:
    st.sidebar.warning(f"File does not exist: `{target_path.name}`")
    st.session_state.df = None
    st.session_state.file_path = None

# Stats Display
stats = {}
if st.session_state.df is not None:
    stats = calculate_audit_stats(st.session_state.df)
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Live Audit Statistics")
    
    col1, col2 = st.sidebar.columns(2)
    col1.metric("Total Rows", stats["total_rows"])
    col2.metric("Reviewed", stats["reviewed_rows"])
    
    col3, col4 = st.sidebar.columns(2)
    col3.metric("Unreviewed", stats["unreviewed_rows"])
    col4.metric("Followup", stats["needs_followup_rows"])
    
    # Detail expander
    with st.sidebar.expander("Show Status/Label Counts"):
        st.write("**Reviewer Status Counts:**")
        for status, val in sorted(stats["status_counts"].items()):
            st.write(f"- `{status}`: {val}")
        st.write("**Label Counts:**")
        for lbl, val in sorted(stats["label_counts"].items()):
            st.write(f"- `{lbl}`: {val}")

# --- SAMPLING PANEL ---
if st.session_state.df is not None:
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎯 Random Sampling")
    
    if st.session_state.active_sample_info:
        s_info = st.session_state.active_sample_info
        st.sidebar.warning(
            f"Active Sample: {s_info['filter_name']} ({int(s_info['percentage'])}%)\nSeed: {s_info['seed']}"
        )
        if st.sidebar.button("Clear Active Sample"):
            st.session_state.active_sample_info = None
            st.session_state.active_queue_ptr = 0
            st.rerun()
    else:
        # Create sample form
        sample_filter = st.sidebar.selectbox(
            "Sample Target",
            ["Faithful / Correct", "Drift / Error rows", "All rows"]
        )
        sample_pct = st.sidebar.slider("Sample Size (%)", 5, 100, 20, step=5)
        sample_seed = st.sidebar.number_input("Random Seed", value=42, step=1)
        
        if st.sidebar.button("Generate & Load Sample"):
            try:
                indices, s_path = create_random_sample(
                    st.session_state.df,
                    sample_filter,
                    sample_pct,
                    sample_seed,
                    st.session_state.lecture_id,
                    st.session_state.csv_type
                )
                st.session_state.active_sample_info = {
                    "filter_name": sample_filter,
                    "percentage": sample_pct,
                    "seed": sample_seed,
                    "indices": indices,
                    "sample_file_path": str(s_path),
                    "sampled": True
                }
                st.session_state.active_queue_ptr = 0
                st.sidebar.success(f"Sample generated! {len(indices)} rows loaded.")
                st.rerun()
            except ValueError as ve:
                st.sidebar.error(f"⚠️ {str(ve)}")
            
    # Load past samples
    past_samples = list_saved_samples(st.session_state.lecture_id, st.session_state.csv_type)
    if past_samples:
        selected_sample_file = st.sidebar.selectbox(
            "Reload Saved Sample",
            options=past_samples,
            format_func=lambda p: p.name.split("_pct")[0].split(f"{st.session_state.lecture_id}_{st.session_state.csv_type}_")[-1] + f" ({p.name.split('_pct')[-1].split('.json')[0]})"
        )
        if st.sidebar.button("Reload Sample"):
            s_data = load_saved_sample(selected_sample_file)
            st.session_state.active_sample_info = {
                "filter_name": s_data["filter_name"],
                "percentage": s_data["percentage"],
                "seed": s_data["seed"],
                "indices": s_data["indices"],
                "sample_file_path": str(selected_sample_file),
                "sampled": True
            }
            st.session_state.active_queue_ptr = 0
            st.sidebar.success(f"Sample reloaded! {len(s_data['indices'])} rows loaded.")
            st.rerun()

# --- MAIN CONTENT PANEL ---
if st.session_state.df is None:
    st.info("👈 Please select or configure a valid annotation CSV in the sidebar.")
else:
    df = st.session_state.df
    csv_type = st.session_state.csv_type
    
    # 1. Active Review Queue / Filters
    st.markdown("<div class='compact-section-label'>Queue & filters</div>", unsafe_allow_html=True)
    q_col1, q_col2, q_col3 = st.columns([1, 1, 1.25])
    
    # Define primary queues
    queue_options = [
        "All rows",
        "Rows needing review",
        "Blank label rows",
        "Drift / Error rows",
        "Faithful / Correct rows",
        "Unreviewed rows",
        "Needs-followup rows",
    ]
    
    if st.session_state.active_sample_info:
        # If sampling is active, add "Sampled Rows" and "Remaining (Not In Sample)" options
        queue_options.insert(0, "Sampled Rows")
        queue_options.append("Remaining Rows (Not In Sample)")
        default_queue = "Sampled Rows"
    else:
        default_queue = "All rows"
        
    active_queue = q_col1.selectbox(
        "Select Review Queue",
        options=queue_options,
        index=queue_options.index(default_queue) if default_queue in queue_options else 0,
        key="selected_active_queue"
    )
    
    # Status filter (optional secondary filter)
    status_filter = q_col2.selectbox(
        "Filter by Review Status",
        options=["Any"] + REVIEWER_STATUS_OPTIONS,
        index=0
    )
    
    # Text search
    text_search = q_col3.text_input("Text Search (any text column)", value="")
    
    # Build list of active indices matching all filters
    active_indices = []
    label_col = "label" if "label" in df.columns else ("polarity_label" if "polarity_label" in df.columns else None)
    
    for idx, row in df.iterrows():
        # Queue check
        in_queue = False
        lbl = safe_str(row.get(label_col, "")) if label_col else ""
        status = safe_str(row.get("reviewer_status", "unreviewed")).lower()
        sample_indices = st.session_state.active_sample_info["indices"] if st.session_state.active_sample_info else []
        
        if active_queue == "Sampled Rows":
            in_queue = idx in sample_indices
        elif active_queue == "Remaining Rows (Not In Sample)":
            in_queue = idx not in sample_indices
        elif active_queue == "All rows":
            in_queue = True
        elif active_queue == "Rows needing review":
            in_queue = (status == "unreviewed" or status == "needs_followup" or truthy_cell(row.get("needs_followup", False)))
        elif active_queue == "Blank label rows":
            in_queue = pd.isna(row.get(label_col)) or lbl == ""
        elif active_queue == "Drift / Error rows":
            in_queue = any(lbl.lower() == d.lower() for d in DRIFT_ERROR_LABELS)
        elif active_queue == "Faithful / Correct rows":
            in_queue = any(lbl.lower() == f.lower() for f in FAITHFUL_CORRECT_LABELS)
        elif active_queue == "Unreviewed rows":
            in_queue = (status == "unreviewed")
        elif active_queue == "Needs-followup rows":
            in_queue = (status == "needs_followup" or truthy_cell(row.get("needs_followup", False)))
            
        # Secondary status check
        if in_queue and status_filter != "Any":
            if status != status_filter.lower():
                in_queue = False
                
        # Secondary text search check
        if in_queue and text_search.strip():
            search_query = text_search.lower()
            found_text = False
            for col in df.columns:
                if col in SOURCE_TEXT_COLS or col in HYPOTHESIS_TEXT_COLS or col == "review_note" or col == "final_note":
                    val = safe_str(row.get(col, "")).lower()
                    if search_query in val:
                        found_text = True
                        break
            if not found_text:
                in_queue = False
                
        if in_queue:
            active_indices.append(idx)
            
    # Update active queue indices in session state
    st.session_state.active_queue_indices = active_indices
    
    # Adjust ptr bounds
    total_in_queue = len(active_indices)
    if total_in_queue == 0:
        st.warning("⚠️ No rows match the current queue and filters.")
    else:
        if st.session_state.active_queue_ptr >= total_in_queue:
            st.session_state.active_queue_ptr = total_in_queue - 1
        if st.session_state.active_queue_ptr < 0:
            st.session_state.active_queue_ptr = 0
            
        current_df_idx = active_indices[st.session_state.active_queue_ptr]
        st.session_state.current_index = current_df_idx
        row = df.loc[current_df_idx]
        try:
            current_row_number = int(df.index.get_loc(current_df_idx)) + 1
        except (TypeError, ValueError):
            current_row_number = st.session_state.active_queue_ptr + 1

        # Compact one-screen workbench. The legacy vertical layout remains below
        # this block as a fallback, but normal review stops after this UI renders.
        src_cols = [c for c in SOURCE_TEXT_COLS if c in df.columns]
        hyp_cols = get_display_hypothesis_cols(df, csv_type)
        other_info_cols = [c for c in INFO_COLS if c in df.columns]
        edit_cols = get_edit_target_cols(df, csv_type)

        badge_html = ""
        curr_lbl = safe_str(row.get(label_col, "")) if label_col else ""
        if any(curr_lbl.lower() == d.lower() for d in DRIFT_ERROR_LABELS):
            badge_html += '<span class="badge-drift">DRIFT/ERROR</span> '
        elif any(curr_lbl.lower() == f.lower() for f in FAITHFUL_CORRECT_LABELS):
            badge_html += '<span class="badge-ok">FAITHFUL</span> '

        work_left, work_right = st.columns([1.18, 1.0])

        with work_left:
            nav_col1, nav_col2, nav_col3, nav_col4 = st.columns([1.35, 0.85, 0.85, 1.35])
            jump_key = (
                f"jump_{st.session_state.lecture_id}_{st.session_state.csv_name}_"
                f"{active_queue}_{total_in_queue}_{st.session_state.active_queue_ptr}"
            )

            jump_ptr = nav_col1.number_input(
                f"Row {st.session_state.active_queue_ptr + 1}/{total_in_queue}",
                min_value=1,
                max_value=total_in_queue,
                value=st.session_state.active_queue_ptr + 1,
                step=1,
                key=jump_key,
            ) - 1

            if jump_ptr != st.session_state.active_queue_ptr:
                st.session_state.active_queue_ptr = jump_ptr
                st.rerun()

            prev_btn = nav_col2.button(
                "Prev",
                use_container_width=True,
                disabled=st.session_state.active_queue_ptr == 0,
            )
            next_btn = nav_col3.button(
                "Next",
                use_container_width=True,
                disabled=st.session_state.active_queue_ptr == total_in_queue - 1,
            )

            if prev_btn and st.session_state.active_queue_ptr > 0:
                st.session_state.active_queue_ptr -= 1
                st.rerun()
            if next_btn and st.session_state.active_queue_ptr < total_in_queue - 1:
                st.session_state.active_queue_ptr += 1
                st.rerun()

            nav_col4.markdown(
                f"<div class='compact-section-label'>CSV row #{current_row_number}</div>{badge_html}",
                unsafe_allow_html=True,
            )

            st.markdown("<div class='nav-spacer'></div>", unsafe_allow_html=True)
            st.markdown("<div class='compact-section-label'>Reference</div>", unsafe_allow_html=True)
            ref_text = ""
            for c in src_cols:
                val = row[c]
                if pd.notna(val) and str(val).strip():
                    ref_text += f"**{c}**: {val}\n\n"
            if not ref_text:
                ref_text = "*No reference phrase specified*"
            st.markdown(f"<div class='text-box'>{ref_text}</div>", unsafe_allow_html=True)

            if hyp_cols:
                st.markdown("<div class='compact-section-label'>Outputs</div>", unsafe_allow_html=True)
                tabs = st.tabs(hyp_cols)
                for idx_t, col_t in enumerate(hyp_cols):
                    with tabs[idx_t]:
                        output_val = row[col_t]
                        if pd.isna(output_val) or not str(output_val).strip():
                            st.info(f"*{col_t} is blank or omitted*")
                        else:
                            st.markdown(
                                f"<div class='text-box output-box'>{output_val}</div>",
                                unsafe_allow_html=True,
                            )
            else:
                st.dataframe(pd.DataFrame(row).T, height=240, use_container_width=True)

            if other_info_cols:
                with st.expander("Hints / row context", expanded=False):
                    for col_i in other_info_cols:
                        st.markdown(f"**{col_i}**")
                        st.write(row[col_i] if pd.notna(row[col_i]) else "")

        with work_right:
            st.markdown("<div class='compact-section-label'>Annotation</div>", unsafe_allow_html=True)

            with st.form("edit_form", clear_on_submit=False):
                save_col, save_next_col = st.columns(2)
                submit_save = save_col.form_submit_button("Save", use_container_width=True)
                submit_save_next = save_next_col.form_submit_button("Save & Next", use_container_width=True)

                if st.session_state.last_save_status:
                    status_info = st.session_state.last_save_status
                    if status_info.get("success"):
                        st.success(
                            f"Saved row #{current_row_number} at {status_info['time']} "
                            f"(backup: {status_info['backup']})"
                        )
                    else:
                        st.error(f"Save failed: {status_info.get('error')}")

                updated_vals = {}
                for col_e in edit_cols:
                    curr_val = safe_str(row[col_e])

                    if col_e == "error_type":
                        updated_vals[col_e] = st.text_input(
                            col_e,
                            value=curr_val,
                            key=f"{col_e}_{current_df_idx}",
                        )
                        continue

                    unique_vals = df[col_e].dropna().unique().tolist()
                    if col_e in CONDITION_VERDICT_COLS:
                        suggested = list(POLARITY_VERDICT_OPTIONS)
                        for val in unique_vals:
                            cleaned_val = safe_str(val)
                            if cleaned_val and cleaned_val not in suggested:
                                suggested.append(cleaned_val)
                    else:
                        suggested = get_suggested_labels(csv_type, unique_vals)

                    if not curr_val and "" not in suggested:
                        suggested.insert(0, "")
                    elif curr_val and curr_val not in suggested:
                        suggested.append(curr_val)
                    label_idx = suggested.index(curr_val) if curr_val in suggested else 0

                    updated_vals[col_e] = st.selectbox(
                        col_e,
                        options=suggested,
                        index=label_idx,
                        key=f"{col_e}_{current_df_idx}",
                    )

                status_left, followup_right = st.columns([1.5, 1])
                curr_status = safe_str(row.get("reviewer_status", "unreviewed")).lower()
                if not curr_status:
                    curr_status = "unreviewed"
                status_idx = REVIEWER_STATUS_OPTIONS.index(curr_status) if curr_status in REVIEWER_STATUS_OPTIONS else 0

                new_status = status_left.selectbox(
                    "Status",
                    options=REVIEWER_STATUS_OPTIONS,
                    index=status_idx,
                    key=f"status_{current_df_idx}",
                )

                new_needs_followup = followup_right.checkbox(
                    "Follow-up",
                    value=truthy_cell(row.get("needs_followup", False)),
                    key=f"followup_{current_df_idx}",
                )

                new_review_note = st.text_area(
                    "Review Note",
                    value=safe_str(row.get("review_note", "")),
                    height=82,
                    key=f"review_note_{current_df_idx}",
                )

                new_final_note = st.text_area(
                    "Final Note",
                    value=safe_str(row.get("final_note", "")),
                    height=70,
                    key=f"final_note_{current_df_idx}",
                )

                if submit_save or submit_save_next:
                    for col_e in edit_cols:
                        if col_e in df.columns:
                            df[col_e] = df[col_e].astype("object")

                    for col_e, val_e in updated_vals.items():
                        df.at[current_df_idx, col_e] = val_e

                    df.at[current_df_idx, "reviewer_status"] = new_status
                    df.at[current_df_idx, "needs_followup"] = new_needs_followup
                    df.at[current_df_idx, "review_note"] = new_review_note
                    df.at[current_df_idx, "final_note"] = new_final_note
                    df.at[current_df_idx, "reviewed_by"] = st.session_state.reviewer_name
                    df.at[current_df_idx, "last_reviewed_at"] = datetime.datetime.now().isoformat()

                    try:
                        backup_path = save_review_csv(df, st.session_state.file_path, st.session_state.lecture_id, csv_type)
                        st.session_state.df = df
                        st.session_state.last_save_status = {
                            "success": True,
                            "time": datetime.datetime.now().strftime("%H:%M:%S"),
                            "backup": backup_path.name if backup_path else "None",
                        }
                        if submit_save_next and st.session_state.active_queue_ptr < total_in_queue - 1:
                            st.session_state.active_queue_ptr += 1
                    except Exception as ex:
                        st.session_state.last_save_status = {
                            "success": False,
                            "error": str(ex),
                        }
                    st.rerun()

            with st.expander("Review summary export", expanded=False):
                st.write("This only writes `ANNOTATION_REVIEW_SUMMARY.md`; row annotations are already saved by Save.")
                if st.button("Export summary markdown", use_container_width=True):
                    all_stats = {}
                    all_samples = {}
                    for l_id in list_available_lectures():
                        for csv_name in REVIEW_CSV_OPTIONS:
                            path_csv = get_csv_path(l_id, csv_name)
                            if path_csv.exists():
                                temp_df = load_review_csv(path_csv)
                                key = f"{l_id}|{detect_csv_type(csv_name)}"
                                all_stats[key] = calculate_audit_stats(temp_df)
                                all_samples[key] = {"sampled": False}
                    if all_stats:
                        export_audit_summary_markdown(all_stats, all_samples)
                        st.success("Exported ANNOTATION_REVIEW_SUMMARY.md")
                    else:
                        st.error("No CSV data found to summarize.")

        st.stop()
        
        # 2. Navigation controls
        st.markdown("---")
        nav_col1, nav_col2, nav_col3, nav_col4 = st.columns([1.5, 3, 2, 2.5])
        legacy_jump_key = (
            f"legacy_jump_{st.session_state.lecture_id}_{st.session_state.csv_name}_"
            f"{active_queue}_{total_in_queue}_{st.session_state.active_queue_ptr}"
        )
        
        # Jump to row input
        jump_ptr = nav_col1.number_input(
            f"Row {st.session_state.active_queue_ptr + 1} of {total_in_queue}",
            min_value=1,
            max_value=total_in_queue,
            value=st.session_state.active_queue_ptr + 1,
            step=1,
            key=legacy_jump_key,
        ) - 1
        
        if jump_ptr != st.session_state.active_queue_ptr:
            st.session_state.active_queue_ptr = jump_ptr
            st.rerun()
            
        # Prev / Next
        prev_btn = nav_col2.button("⬅️ Previous Row", use_container_width=True, disabled=st.session_state.active_queue_ptr == 0)
        next_btn = nav_col2.button("Next Row ➡️", use_container_width=True, disabled=st.session_state.active_queue_ptr == total_in_queue - 1)
        
        if prev_btn and st.session_state.active_queue_ptr > 0:
            st.session_state.active_queue_ptr -= 1
            st.rerun()
        if next_btn and st.session_state.active_queue_ptr < total_in_queue - 1:
            st.session_state.active_queue_ptr += 1
            st.rerun()
            
        # Original Row Reference Index
        nav_col3.metric("Original CSV Index", f"Row #{current_row_number}")
        
        # Drift Badges
        badge_html = ""
        curr_lbl = safe_str(row.get(label_col, "")) if label_col else ""
        if any(curr_lbl.lower() == d.lower() for d in DRIFT_ERROR_LABELS):
            badge_html += '<span class="badge-drift">⚡ DRIFT/ERROR</span> '
        elif any(curr_lbl.lower() == f.lower() for f in FAITHFUL_CORRECT_LABELS):
            badge_html += '<span class="badge-ok">✅ FAITHFUL</span> '
            
        nav_col4.markdown("<div style='padding-top: 10px;'></div>" + badge_html, unsafe_allow_html=True)
        
        # 3. Readability layout
        st.markdown("### 📝 Transcription Content")
        
        # Identify reference/source columns
        src_cols = [c for c in SOURCE_TEXT_COLS if c in df.columns]
        hyp_cols = get_display_hypothesis_cols(df, csv_type)
        other_info_cols = [c for c in INFO_COLS if c in df.columns]
        
        # Source/Reference Text display
        st.markdown("<div class='text-box-title'>Reference / Gold Source Text</div>", unsafe_allow_html=True)
        ref_text = ""
        for c in src_cols:
            val = row[c]
            if pd.notna(val) and str(val).strip():
                ref_text += f"**{c}**: {val}\n\n"
        if not ref_text:
            ref_text = "*No reference phrase specified*"
        st.markdown(f"<div class='text-box'>{ref_text}</div>", unsafe_allow_html=True)
        
        # Comparison columns
        if hyp_cols:
            st.markdown("<div class='text-box-title'>System Outputs & Hypotheses</div>", unsafe_allow_html=True)
            tabs = st.tabs(hyp_cols)
            for idx_t, col_t in enumerate(hyp_cols):
                with tabs[idx_t]:
                    output_val = row[col_t]
                    if pd.isna(output_val) or not str(output_val).strip():
                        st.info(f"*{col_t} is blank or omitted*")
                    else:
                        st.markdown(f"<div class='text-box'>{output_val}</div>", unsafe_allow_html=True)
        else:
            # Fallback if no specific source/hypothesis columns detected
            st.markdown("#### All Row Details")
            st.dataframe(pd.DataFrame(row).T)
            
        # Helpful context hints / other info columns
        if other_info_cols:
            hint_cols = st.columns(len(other_info_cols))
            for i, col_i in enumerate(other_info_cols):
                with hint_cols[i]:
                    st.markdown(f"**{col_i}**")
                    st.write(row[col_i] if pd.notna(row[col_i]) else "")
                    
        # 4. Editing Panel
        st.markdown("### ✏️ Audit Decision")
        edit_cols = get_edit_target_cols(df, csv_type)
        
        with st.form("edit_form", clear_on_submit=False):
            form_col1, form_col2 = st.columns(2)
            
            # Label edits (supports multiple if multiple target columns present)
            updated_vals = {}
            for col_e in edit_cols:
                curr_val = safe_str(row[col_e])

                if col_e == "error_type":
                    updated_vals[col_e] = form_col1.text_input(
                        col_e,
                        value=curr_val,
                    )
                    continue

                # Retrieve unique values present in the column for suggestions
                unique_vals = df[col_e].dropna().unique().tolist()
                if col_e in CONDITION_VERDICT_COLS:
                    suggested = list(POLARITY_VERDICT_OPTIONS)
                    for val in unique_vals:
                        cleaned_val = safe_str(val)
                        if cleaned_val and cleaned_val not in suggested:
                            suggested.append(cleaned_val)
                else:
                    suggested = get_suggested_labels(csv_type, unique_vals)

                # Check if current label is in suggested
                if not curr_val and "" not in suggested:
                    suggested.insert(0, "")
                elif curr_val and curr_val not in suggested:
                    suggested.append(curr_val)
                    
                label_idx = suggested.index(curr_val) if curr_val in suggested else 0
                
                updated_vals[col_e] = form_col1.selectbox(
                    f"Choose {col_e}",
                    options=suggested,
                    index=label_idx
                )
                
            # Status and metadata
            curr_status = safe_str(row.get("reviewer_status", "unreviewed")).lower()
            if not curr_status:
                curr_status = "unreviewed"
            status_idx = REVIEWER_STATUS_OPTIONS.index(curr_status) if curr_status in REVIEWER_STATUS_OPTIONS else 0
            
            new_status = form_col2.selectbox(
                "Reviewer Status",
                options=REVIEWER_STATUS_OPTIONS,
                index=status_idx
            )

            new_needs_followup = form_col2.checkbox(
                "Needs Follow-up?",
                value=truthy_cell(row.get("needs_followup", False))
            )
            
            # Notes
            new_review_note = st.text_area(
                "Review Note",
                value=safe_str(row.get("review_note", ""))
            )
            
            new_final_note = st.text_area(
                "Final Note (optional)",
                value=safe_str(row.get("final_note", ""))
            )
            
            # Submit button
            submit_save = st.form_submit_button("💾 Save Changes for Current Row")
            
            if submit_save:
                # Update DataFrame in session state
                for col_e in edit_cols:
                    if col_e in df.columns:
                        df[col_e] = df[col_e].astype("object")

                for col_e, val_e in updated_vals.items():
                    df.at[current_df_idx, col_e] = val_e
                    
                df.at[current_df_idx, "reviewer_status"] = new_status
                df.at[current_df_idx, "needs_followup"] = new_needs_followup
                df.at[current_df_idx, "review_note"] = new_review_note
                df.at[current_df_idx, "final_note"] = new_final_note
                df.at[current_df_idx, "reviewed_by"] = st.session_state.reviewer_name
                df.at[current_df_idx, "last_reviewed_at"] = datetime.datetime.now().isoformat()
                
                # Write back to disk
                try:
                    backup_path = save_review_csv(df, st.session_state.file_path, st.session_state.lecture_id, csv_type)
                    st.session_state.df = df
                    st.session_state.last_save_status = {
                        "success": True,
                        "time": datetime.datetime.now().strftime("%H:%M:%S"),
                        "backup": backup_path.name if backup_path else "None"
                    }
                except Exception as ex:
                    st.session_state.last_save_status = {
                        "success": False,
                        "error": str(ex)
                    }
                st.rerun()

        # Save status alert
        if st.session_state.last_save_status:
            status_info = st.session_state.last_save_status
            if status_info.get("success"):
                st.success(
                    f"✅ Row #{current_row_number} saved successfully at {status_info['time']}! "
                    f"Backup created: `{status_info['backup']}`"
                )
            else:
                st.error(f"❌ Failed to save row: {status_info.get('error')}")
                
    # 5. Export Summary action
    st.markdown("---")
    st.markdown("### 📊 Generate Review Summary Document")
    st.write(
        "This will compile reviewed and unreviewed metrics across the active lecture CSVs, "
        "and export them to `evaluation_paper/annotation_review_app/ANNOTATION_REVIEW_SUMMARY.md`."
        " All labels are single-pass labels from a single author-annotator; this document does not represent a second pass or adjudication."
    )

    if st.button("📤 Export & Save ANNOTATION_REVIEW_SUMMARY.md"):
        # We want to scan the directories for all reviews to build a global audit summary
        all_stats = {}
        all_samples = {}
        
        # Scan through all available lectures and CSV types
        for l_id in list_available_lectures():
            for csv_name in REVIEW_CSV_OPTIONS:
                path_csv = get_csv_path(l_id, csv_name)
                if path_csv.exists():
                    try:
                        temp_df = load_review_csv(path_csv)
                        key = f"{l_id}|{detect_csv_type(csv_name)}"
                        all_stats[key] = calculate_audit_stats(temp_df)
                        
                        # Check active sample file (if matches session state, or check recent)
                        if (st.session_state.active_sample_info and 
                            st.session_state.lecture_id == l_id and 
                            st.session_state.csv_type == detect_csv_type(csv_name)):
                            s_info = st.session_state.active_sample_info
                            all_samples[key] = {
                                "sampled": True,
                                "filter_name": s_info["filter_name"],
                                "percentage": s_info["percentage"],
                                "seed": s_info["seed"],
                                "sample_file_path": s_info["sample_file_path"]
                            }
                        else:
                            # Search for any recent saved sample for this lecture/type
                            recent_samples = list_saved_samples(l_id, detect_csv_type(csv_name))
                            if recent_samples:
                                try:
                                    s_data = load_saved_sample(recent_samples[0])
                                    all_samples[key] = {
                                        "sampled": True,
                                        "filter_name": s_data["filter_name"],
                                        "percentage": s_data["percentage"],
                                        "seed": s_data["seed"],
                                        "sample_file_path": str(recent_samples[0])
                                    }
                                except:
                                    all_samples[key] = {"sampled": False}
                            else:
                                all_samples[key] = {"sampled": False}
                    except Exception as e:
                        st.error(f"Error reading stats for {l_id}/{csv_name}: {e}")
                        
        if all_stats:
            md_content = export_audit_summary_markdown(all_stats, all_samples)
            st.success("🎉 Successfully exported `ANNOTATION_REVIEW_SUMMARY.md`!")
            with st.expander("Preview exported document"):
                st.markdown(md_content)
        else:
            st.error("No CSV data found to summarize.")
