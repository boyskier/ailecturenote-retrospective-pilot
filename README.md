# AI_LectureNote Paper Release

This repository is the public release for the AI_LectureNote retrospective pilot paper and the historical standalone pipeline code that produced part of the evaluated material.

The manuscript itself is published separately as an arXiv technical report and is **not** included in this repository. This repository provides the code, source data, human annotations, and generated tables/figures needed to reproduce and inspect the evaluation.

> arXiv technical report: link to be added.

The repository has two intentionally separate areas:

- `evaluation_paper/`: reproducible evaluation workspace with the annotation protocol, source data, human annotation CSVs, analysis scripts, and generated tables/figures.
- `standalone_pipeline/`: historical server-free AI_LectureNote core pipeline code. It is retained for transparency and local experimentation, not as the paper reproduction workspace.

The paper evaluates transcript-level outputs only. The optional downstream knowledge-graph code is preserved in `standalone_pipeline/`, but KG outputs are out of scope for the paper and are not included as paper artifacts.

## Reproduce the Paper Tables and Figures

From the repository root:

```bash
cd evaluation_paper
pip install -r analysis/requirements.txt
python analysis/run_all.py
```

This regenerates `evaluation_paper/outputs/tables/` and `evaluation_paper/outputs/figures/` from the source-of-truth annotation CSV files and manifest. The generated paper outputs are tracked for convenience.

Evaluation entry points:

- Paper: published as an arXiv technical report (link to be added); not included in this repository.
- Evaluation README: `evaluation_paper/README.md`
- Annotation guide: `evaluation_paper/ANNOTATION_GUIDE.md`
- Condition manifest: `evaluation_paper/manifest/condition_manifest.csv`

## Historical Standalone Pipeline

The historical pipeline can run STT, chunking, correction, English-script rendering, and optionally KG generation. For paper-release smoke checks and transcript-only use, run it with `--skip-kg`:

```bash
pip install -r standalone_pipeline/requirements.txt
python standalone_pipeline/run_pipeline.py --skip-kg lecture1.mp3
```

The optional KG path is archived experimental code and is not part of paper reproduction. Running it requires OpenAI credentials, a UMLS API key, and a user-provided seed/term vocabulary at `standalone_pipeline/data/cleaned_text.csv` with a `Clean Text` column. It may fail or produce empty graphs on very short or sparse inputs.

No AnKing deck content, media, card text, extracted term list, or AnKing-derived KG output is included in this repository. Historical KG experiments used a private seed vocabulary derived from legacy AnKing cloze-answer concept names only as an internal pruning aid; users who experiment with KG generation must provide their own authorized seed vocabulary and should not commit third-party deck-derived term lists.

To experiment with the optional KG stage:

```bash
python standalone_pipeline/run_pipeline.py lecture1.mp3
```

See `standalone_pipeline/README.md` for setup details, API key notes, ffmpeg requirements, and additional commands.

Generated local pipeline outputs are written under `standalone_pipeline/products/`. Historical root `products/` outputs, if present locally, are also generated artifacts. These directories are ignored by Git and are not paper data.

The helper that originally generated the evaluated STT comparison conditions now lives at:

```bash
python standalone_pipeline/eval_stt_compare.py lecture1.m4a
```

This helper writes local generated files under `standalone_pipeline/products/`; it does not
write directly into `evaluation_paper/data/<lecture_id>/`. The checked-in paper data are
already normalized there. If you regenerate inputs for a new lecture, copy/rename the local
outputs using the mapping in `standalone_pipeline/README.md` and `evaluation_paper/README.md`;
the `gpt4o_ailn_post` condition requires a separate post-processing step.

## Repository Layout

```text
.
|-- README.md
|-- evaluation_paper/
|   |-- README.md
|   |-- ANNOTATION_GUIDE.md
|   |-- DATASET.md
|   |-- analysis/
|   |-- data/
|   |-- annotations/
|   |-- manifest/
|   `-- outputs/
|-- standalone_pipeline/
|   |-- README.md
|   |-- run_pipeline.py
|   |-- eval_stt_compare.py
|   |-- audio_processing.py
|   |-- text_processing.py
|   |-- knowledge_graph.py
|   |-- config.py
|   `-- requirements.txt
`-- inputs/                    # optional released audio, when included
```

Audio, if released in `inputs/` or elsewhere, contains identifiable author-speaker voices and should not be treated as anonymized. Speaker identifiers may be coded, but coded IDs do not de-identify voice recordings.

## Out of Scope

- `standalone_pipeline/products/` and root `products/` are local generated artifacts.
- Knowledge-graph construction, UMLS synonym integration, graph pruning, and HTML graph visualization are not scored or interpreted in the paper.
- The paper results should be reproduced from `evaluation_paper/`, not from generated local pipeline outputs.

License and data-use terms should be read from the repository license files and any data-specific release notes. Code, data, and audio may have different release terms.
