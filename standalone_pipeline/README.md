# Standalone Historical Pipeline

This folder contains the server-free historical AI_LectureNote core pipeline. It is kept for transparency around the retrospective pilot paper, but it is separate from the reproducible paper workspace in `evaluation_paper/`.

The pipeline can transcribe audio, chunk raw Korean-English lecture text, apply the historical correction pass, rewrite embedded medical terms into English/Latin script, and optionally build a downstream knowledge graph. The optional KG step is archived experimental code and is not evaluated in the paper.

## Requirements

Install the historical pipeline dependencies from this folder:

```bash
pip install -r standalone_pipeline/requirements.txt
```

Audio transcription requires `ffmpeg` to be available on your system path.

The text and KG stages use legacy OpenAI SDK calls such as `openai.ChatCompletion`. The pinned requirements reflect that historical SDK style rather than a modernized OpenAI client implementation.

Create a repository-root `.env` file when running the pipeline locally:

```text
OPEN_API_KEY=sk-...
UMLS_API_KEY=...
```

`OPENAI_API_KEY` is also accepted for OpenAI credentials. The `.env` file must not be committed.

## Commands

Run transcript-only processing from audio. This is the recommended smoke-check path for the paper release:

```bash
python standalone_pipeline/run_pipeline.py --skip-kg lecture1.mp3
```

Run the full historical path, including optional KG generation:

```bash
python standalone_pipeline/run_pipeline.py lecture1.mp3
```

The KG path requires OpenAI credentials, `UMLS_API_KEY`, and a user-provided seed/term vocabulary at `standalone_pipeline/data/cleaned_text.csv` with a `Clean Text` column. It is best-effort historical code and may fail or produce empty graphs on very short or sparse inputs.

Do not commit third-party deck content or derived term lists. This public release does not include AnKing deck content, media, card text, extracted terms, or AnKing-derived KG outputs. Historical KG experiments used private legacy AnKing cloze-answer concept names only as seed terms for domain-guided pruning; users must supply their own authorized seed vocabulary if they run this optional stage.

Start from existing raw STT text:

```bash
python standalone_pipeline/run_pipeline.py lecture1.txt lecture2.txt
```

Build only the optional KG from an already Englished transcript:

```bash
python standalone_pipeline/run_pipeline.py --kg-only lecture1_englished.txt
```

Regenerate the historical STT comparison conditions used as evaluation inputs:

```bash
python standalone_pipeline/eval_stt_compare.py lecture1.m4a
```

Generated files are written under `standalone_pipeline/products/`. They are local run artifacts, not paper data, and are ignored by Git. The helper does not write directly into `evaluation_paper/data/<lecture_id>/`.

When preparing paper inputs for a new lecture, copy/rename the generated files manually:

| generated file | paper data file |
| --- | --- |
| `standalone_pipeline/products/raw_stt/<stem>_whisper1.txt` | `evaluation_paper/data/<lecture_id>/whisper1.txt` |
| `standalone_pipeline/products/englished/<stem>_whisper1_englished.txt` | `evaluation_paper/data/<lecture_id>/ai_lecturenote.txt` |
| `standalone_pipeline/products/raw_stt/<stem>_gpt4otranscribe.txt` | `evaluation_paper/data/<lecture_id>/gpt4o.txt` |
| `standalone_pipeline/products/raw_stt/<stem>_gpt4otranscribe_prompted.txt` | `evaluation_paper/data/<lecture_id>/gpt4o_prompted.txt` |

The `gpt4o_ailn_post.txt` paper condition is not produced automatically by `eval_stt_compare.py`. To regenerate it, run the AI_LectureNote post-processing path on the raw gpt-4o transcript:

```bash
python standalone_pipeline/run_pipeline.py --skip-kg standalone_pipeline/products/raw_stt/<stem>_gpt4otranscribe.txt
```

Then copy:

```text
standalone_pipeline/products/englished/<stem>_gpt4otranscribe_englished.txt
-> evaluation_paper/data/<lecture_id>/gpt4o_ailn_post.txt
```
