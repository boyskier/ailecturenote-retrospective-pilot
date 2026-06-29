# AI_LectureNote — STT evaluation workspace

Reproducible analysis for the AI_LectureNote paper (a system retrospective plus a
four-lecture pilot study of a post-ASR, study-transcript workflow for Korean–English
medical lectures). This folder turns the raw STT outputs and the human annotations into
every table and figure in the paper.

> **The paper is published as an arXiv technical report** (link to be added) — cite that.
> The manuscript source is not included in this repository. This README is the
> reproduction/workflow note for the analysis pipeline; the numbers below are kept in
> sync with the regenerated `outputs/tables/`.

The dataset is **four lectures**, each with a `reference.txt` and a full single-annotator
human pass. Polarity worksheets cover all five conditions; semantic-drift worksheets cover
the two post-processed conditions (`ai_lecturenote` and the `gpt4o_ailn_post` cross-input
control). The pipeline runs end-to-end on all four lectures with no pending tables or
figures. Adding a further lecture needs no code changes — drop in its `reference.txt` and
annotations and re-run (§8).

---

## 1. The five evaluated conditions

| key               | label                                         | what it is                                                                                                  |
| ----------------- | --------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `whisper1`        | raw whisper-1                                 | historical raw ASR baseline (2026 rerun)                                                                    |
| `ai_lecturenote`  | AI_LectureNote                                | whisper-1 → domain-aware post-processing                                                                    |
| `gpt4o`           | raw gpt-4o-transcribe                         | modern raw ASR, 3-min non-overlapping chunks                                                                |
| `gpt4o_prompted`  | prompted gpt-4o-transcribe                    | preliminary prompt-sensitivity only                                                                         |
| `gpt4o_ailn_post` | raw gpt-4o-transcribe → AI_LectureNote post   | **cross-input control:** raw gpt-4o run through the *same* post-processing path as AI_LectureNote           |

The first four were produced by [`../standalone_pipeline/eval_stt_compare.py`](../standalone_pipeline/eval_stt_compare.py). The
fifth (`gpt4o_ailn_post`) is the raw gpt-4o output (condition 3) pushed through the
identical AI_LectureNote chunk/correction/Englishing post-processing — it isolates the
*post-processing stage* from the raw STT front-end, so a readability gain or a faithfulness
cost can be attributed to the post-processing rather than to whisper-1 vs gpt-4o. The
prompt for the prompted condition is recorded verbatim in the manifest.

## 2. Folder layout

```
evaluation_paper/
├─ README.md                         # this file
├─ ANNOTATION_GUIDE.md               # reference policy + annotation methodology (Korean)
├─ DATASET.md                        # data provenance + speaker-consent note
├─ data/<lecture_id>/                # cleaned inputs
│    reference.txt                   #   self-annotated study-transcript reference
│    whisper1.txt  ai_lecturenote.txt  gpt4o.txt  gpt4o_prompted.txt
│    gpt4o_ailn_post.txt             #   condition 5: gpt-4o → AI_LectureNote post
│    speaker_errata.md               #   (where present) noted speaker misstatements
├─ manifest/condition_manifest.csv   # Methods table: model names, API dates, prompt
├─ annotations/<lecture_id>/         # human labels (source of truth for every table)
│    domain_terms.csv
│    polarity_review.csv             #   exhaustive polarity worksheet (all 5 conditions)
│    semantic_review.csv             #   exhaustive AI_LectureNote drift worksheet
│    semantic_review_gpt4o_ailn_post.csv  #   condition-5 drift worksheet (same schema)
├─ analysis/                         # the Python pipeline
├─ annotation_review_app/            # optional Streamlit app used to fill the worksheets
└─ outputs/                          # GENERATED — tables/ and figures/
```

## 3. Reproducing the tables and figures

```bash
pip install -r analysis/requirements.txt
python analysis/run_all.py
```

`run_all.py` prints a status block (which references / annotations exist) and then writes
`outputs/tables/*.csv` and `outputs/figures/*.png`. It reads the human labels from the
`*_review.csv` worksheets and `domain_terms.csv` only, and **never** modifies any
annotation file. The two helper scripts that originally generated the empty worksheets —
`analysis/make_templates.py` and `analysis/build_review_worksheets.py` — are retained for
the extension workflow (§8) and never overwrite existing annotations.

## 4. The human annotation files

All four lectures are fully annotated; these CSVs are the **source of truth** for the
quantitative results. Each was completed by a single author-annotator in a single pass.
See [ANNOTATION_GUIDE.md](ANNOTATION_GUIDE.md) (Korean) for the reference policy, the
term-canonicalization scheme, and the per-category labeling definitions.

### (a) `domain_terms.csv`
Curated reference domain terms (auto-extracted from the reference, then human-corrected):
`keep` flags real domain terms, `canonical_english`/`english_variants` define the accepted
English renderings, `korean_phonetic` records the phonetic spellings the ASR produces, and
`polarity_group`/`polarity_value` tag hypo/hyper-type terms for the polarity screen.
The `korean_phonetic` field is machine-assisted and diagnostic; it is not an exhaustive
human-verified list of every possible Korean phonetic rendering.
`canonical_english` alone is enough for CER/WER and the **English-script rendering rate**
(the paper's headline readability metric — it measures whether a term is rendered in
English *script*, not whether it is the medically *correct* term; see §6).

### (b) `semantic_review.csv` and `semantic_review_gpt4o_ailn_post.csv`
One row per reference sentence, with the aligned post-processed span pre-located. `label`
is one of `Faithful, Minor rewrite, Omission, Addition, Substitution, Polarity error,
Relation error, Unclear`; drift rows carry `why_it_matters` and feed the drift table.
The condition-5 worksheet uses the same schema (span column `gpt4o_ailn_post_output`).

### (c) `polarity_review.csv`
One row per reference sentence carrying a polarity/direction cue, with each condition's
matching span pre-located (polarity terms searched by stem, so a **flipped pole** shows up
in the span). Each condition is marked `correct` / `wrong` / `omitted`. This exhaustive
human pass — not the lexical `table4_polarity_auto_counts.csv` screen — is authoritative.

### (d) `manifest/condition_manifest.csv`
Per-lecture model names, API execution dates, chunking policy, the verbatim prompted-
condition prompt, and release status.

## 5. Outputs → paper mapping

| file | content | paper item |
| ---- | ------- | ---------- |
| `table1_accuracy_cer_wer.csv` | CER (primary) / WER / length ratio, per lecture + macro | §6.1, Fig S1 |
| `table2_term_preservation.csv` | occurrence & unique English-term recall, **English-script rate** | §6.2, Fig 2 |
| `table2b_term_detail.csv` | per-term English vs phonetic counts across conditions (qualitative) | §6.2 |
| `table3_chunk_consistency.csv` | per-3-min-chunk gpt-4o script counts | §6.2, Fig S3 |
| `table4_polarity_auto_counts.csv` | automatic polarity-value distribution (lexical screen) | §5.1 |
| `table5_polarity_summary.csv` | polarity correct/wrong/omitted (from the human labels) | §6.3, Table 4 |
| `table6_semantic_summary.csv` | semantic-faithfulness label counts (AI_LectureNote + condition 5) | §6.3, Table 3 |
| `table7_semantic_drift_examples.csv` | drift examples (+ high-risk review queue) | Appendix B |
| `table8_drift_taxonomy.csv` | drift decomposed by category, per condition | §6.3, Fig 3 |
| `table9_polarity_transition.csv` | raw whisper-1 → AI_LectureNote polarity transition (fixed/introduced) | §6.3, Fig 4b |
| `table10_postprocessing_polarity_agreement.csv` | cross-input polarity agreement (AI vs condition 5): same-verdict rate + failure-set Jaccard | §6.4 |
| `table11_postprocessing_semantic_agreement.csv` | cross-input semantic-drift-set overlap (AI vs condition 5): Jaccard | §6.4 |
| `table_main_cross_condition_summary.csv` | final cross-condition summary | Table 2 |
| `fig0_evaluation_conditions.png` | evaluation-condition diagram | Figure 1 |
| `fig1_english_script_rate.png` | English-script rendering rate by condition | Figure S2 |
| `fig2_cer_wer.png` | surface accuracy (CER/WER) | Figure S1 |
| `fig3_chunk_<lecture>.png` | per-chunk gpt-4o script | Figures S3a–d |
| `fig4_drift_taxonomy.png` | drift taxonomy (AI_LectureNote vs condition 5) | Figure 3 |
| `fig5_polarity_postprocessing.png` | polarity post-processing effect | Figure 4 |
| `fig6_readability_vs_faithfulness.png` | headline trade-off — rendering gain vs drift cost | Figure 2 |

## 6. Frozen metric definitions

- **Normalization** ([`analysis/textutils.py`](analysis/textutils.py)): lowercase English,
  punctuation → space, whitespace collapsed. **CER** is on whitespace-stripped characters
  (so Korean spacing does not inflate it → CER is primary). **WER** is on normalized tokens
  (secondary; unstable under paraphrase). Polarity morphemes (hypo/hyper, acidosis/
  alkalosis) are **never** merged.
- **English-script rendering rate** = English-script domain-term occurrences in the output
  (capped per term at the reference count) ÷ reference domain-term occurrences. Range 0–1.
  It is a script-occurrence recall, not a semantic-preservation metric.
- **Chunk recovery**: gpt-4o outputs are split on blank lines (the pipeline joins 3-min
  segments with a blank line), so chunk boundaries are exact.

## 7. Current results (all four lectures)

Macro averages over `diuretics_01` + `acuteinflammation_02` + `anthrax_01` +
`anticancerdrugs_02` (reproduce with `python analysis/run_all.py`; full numbers in
`outputs/tables/`):

| condition | CER | WER | English-script rate |
| --------- | --: | --: | ------------------: |
| raw whisper-1 (2026 rerun) | 0.31 | 0.30 | 0.39 |
| AI_LectureNote | 0.39 | 0.58 | 0.71 |
| raw gpt-4o-transcribe | 0.40 | 0.31 | 0.26 |
| prompted gpt-4o-transcribe (sensitivity) | 0.43 | 0.33 | 0.22 |
| gpt-4o → AI_LectureNote post (condition 5) | 0.42 | 0.61 | 0.65 |

Human-label denominators (pooled across the four lectures, single author-annotator, single
pass): **282** semantic reference rows and **101** polarity-cue rows. Semantic drift is
**34** (AI_LectureNote) vs **36** (condition 5).

The direction matches the paper's thesis: raw ASR (whisper-1 and gpt-4o) renders most
English medical terms phonetically; the *post-processing stage* restores English script but
rewrites wording (highest WER → semantic-faithfulness audit needed). Condition 5 is the
control that isolates this: applying the **same** post-processing to raw gpt-4o lifts
English-script rendering from 0.26 to 0.65, so the rendering gain is attributable to the
post-processing, not to whisper-1 vs gpt-4o. The same stage also carries the cost:
condition 5 has the highest polarity-failure count and reproduces the drift. Macro CER
barely separates the conditions, so read **per-lecture** — `anthrax_01` is a counterexample
where raw whisper-1 is already clean and post-processing *raises* CER, and
`anticancerdrugs_02` is an unusually clean lecture (whisper-1 CER 0.08). The English-script
rate measures whether a term is rendered in English, not whether it is the *correct* term;
correctness is assessed separately by the drift/polarity audit (paper §6.3).

## 8. Adding a further lecture

All four pilot lectures are complete (`anticancerdrugs_02` was itself added this way); to
extend the study with a new lecture `<id>`:

1. Put the finished reference at `data/<id>/reference.txt` and the five condition outputs
   alongside it (`whisper1`, `ai_lecturenote`, `gpt4o`, `gpt4o_prompted`,
   `gpt4o_ailn_post`).

   If the condition outputs are regenerated with `../standalone_pipeline/eval_stt_compare.py`,
   copy/rename the local artifacts into this paper workspace:

   | generated file | `data/<id>/` file |
   | --- | --- |
   | `../standalone_pipeline/products/raw_stt/<stem>_whisper1.txt` | `whisper1.txt` |
   | `../standalone_pipeline/products/englished/<stem>_whisper1_englished.txt` | `ai_lecturenote.txt` |
   | `../standalone_pipeline/products/raw_stt/<stem>_gpt4otranscribe.txt` | `gpt4o.txt` |
   | `../standalone_pipeline/products/raw_stt/<stem>_gpt4otranscribe_prompted.txt` | `gpt4o_prompted.txt` |

   `gpt4o_ailn_post.txt` is a separate cross-input condition: first run the same
   AI_LectureNote post-processing path on the raw gpt-4o transcript, then copy the generated
   Englished file:

   ```bash
   python ../standalone_pipeline/run_pipeline.py --skip-kg ../standalone_pipeline/products/raw_stt/<stem>_gpt4otranscribe.txt
   ```

   ```text
   ../standalone_pipeline/products/englished/<stem>_gpt4otranscribe_englished.txt
   -> data/<id>/gpt4o_ailn_post.txt
   ```
2. `python analysis/make_templates.py` (regenerates only still-missing templates; existing
   ones are preserved). Re-extract its `domain_terms.csv` from the real reference with:
   `python -c "import sys; sys.path.insert(0,'analysis'); import make_templates as m; m.write_domain_terms('<id>', force=True)"`.
3. Prune `annotations/<id>/domain_terms.csv` and add labels as in §4.
4. `python analysis/run_all.py` — `<id>` now appears in every table and figure.
