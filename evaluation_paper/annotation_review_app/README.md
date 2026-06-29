# Medical Lecture Annotation Review App

This is a local review tool designed to help reviewers inspect, edit, write notes, and verify annotations for Mixed Korean-English medical lecture transcription evaluation datasets.

## Why This App Exists
Reviewing long text cells (containing mixed English and Korean medical terminology) directly in raw CSV files or Excel spreadsheets is error-prone. The spreadsheet view truncates text, and edits can easily corrupt the Korean character encoding or lead to inadvertent row order changes.

This tool provides a dedicated, readable UI to view one row at a time, compare system outputs side-by-side (using tabs), edit annotation labels safely, and write review comments without altering the underlying data structure.

## Setup & Installation

### Install Dependencies
To install the required libraries:
```bash
pip install -r evaluation_paper/annotation_review_app/requirements.txt
```

## Running the App

Run the app from the repository root directory:

```bash
python evaluation_paper/annotation_review_app/run_app.py
```
Or directly using:
```bash
python -m streamlit run evaluation_paper/annotation_review_app/app.py
```

## Features

1. **Robust Navigation**: Move previous/next, jump directly to a row number, or search/filter by text queries.
2. **Review Queues**: Filter items dynamically (e.g. Blank labels, High risk sentences, Drift/Error labels, and Needs-followup items).
3. **Reproducible Sampling**:
   - Spot-check large subsets (like `Faithful` or `Correct` labels) by taking a 20% random sample (configurable percentage and seed, default `42`).
   - Active samples are saved in JSON format under `evaluation_paper/annotation_review_app/samples/` and can be reloaded at any time.
4. **Safe Saving & Backups**:
   - Every time changes are written back to the annotation CSV, a timestamped copy of the original file is preserved under `evaluation_paper/annotation_review_app/backups/`.
   - Data is stored strictly using `utf-8-sig` encoding, protecting Korean text from corruption when opened in Microsoft Excel.
5. **Annotation Summary Export**:
   - Generate a markdown summary at `evaluation_paper/annotation_review_app/ANNOTATION_REVIEW_SUMMARY.md` (internal app output; not a paper source-of-truth file). All labels are single-pass labels from a single author-annotator; the export does not represent a second pass, independent replication, or adjudication.

## Methodology
All semantic and polarity annotations used in the paper were performed by a single author-annotator in a single pass. Inter-annotator agreement was not measured. This app was used as a review and editing interface during that annotation work.

## Running Tests

Tests are located under `tests/` and use `pytest`. Execute them from the repository root:

```bash
pytest evaluation_paper/annotation_review_app/tests
```
