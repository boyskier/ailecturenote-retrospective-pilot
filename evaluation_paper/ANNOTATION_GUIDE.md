# Annotation Protocol and Data Provenance

This document describes the annotation protocol used for the AI_LectureNote retrospective pilot study. It is intended as a public reproducibility note for the evaluation materials in this repository.

The paper is published as an arXiv technical report (link to be added); the manuscript source is not included in this repository. The analysis workspace and file layout are documented in [`README.md`](README.md). Quantitative results are regenerated from the annotation CSV files by running:

```bash
python analysis/run_all.py
```

## 1. Study scope

The evaluation set contains four author-recorded Korean-English medical lectures:

- `diuretics_01`
- `acuteinflammation_02`
- `anthrax_01`
- `anticancerdrugs_02`

Each lecture has a reference transcript, system outputs for the evaluated conditions, domain-term annotations, semantic-faithfulness annotations for the two post-processed conditions, and polarity annotations for all five conditions.

This is a retrospective, descriptive pilot study. The annotations were completed by a single author-annotator in a single pass. There was no independent second annotator, adjudication round, or inter-annotator agreement measurement. Rates should therefore be interpreted as descriptive summaries of this pilot dataset, not population estimates.

## 2. Reference transcript policy

The reference transcript is an author-created, lightly cleaned, content-preserving study transcript. It is not a strict verbatim conversational transcript and not an idealized lecture script.

The reference preserves:

- medical claims made in the recording;
- English medical terms as spoken or intended in the lecture context;
- polarity and direction cues, such as increase/decrease, hypo/hyper, and negation;
- medically imperfect speaker statements, when those statements were actually made in the recording.

The reference may lightly regularize non-content artifacts when doing so does not change the medical claim. Examples include fillers, coughs, abandoned fragments, and immediate stutter repetitions.

The guiding question for reference editing was: did the recording say this content? The reference was not edited to make the medicine more correct, more complete, or more polished than the recorded lecture.

Term canonicalization is handled in the annotation layer rather than by rewriting the reference. For example, abbreviations, full forms, and spelling variants may be grouped in `domain_terms.csv` through `canonical_english` and `english_variants`, while the reference remains a content-preserving study transcript.

## 3. Evaluated conditions

The study compares five output conditions for the same lecture recordings:

1. `whisper1` — raw whisper-1 output, re-run for this study.
2. `ai_lecturenote` — whisper-1 output passed through the historical AI_LectureNote post-processing workflow.
3. `gpt4o` — raw gpt-4o-transcribe output using 3-minute non-overlapping chunks.
4. `gpt4o_prompted` — the same gpt-4o chunking with a single minimal Korean prompt requesting English medical terms in English script.
5. `gpt4o_ailn_post` — raw gpt-4o-transcribe output passed through the same AI_LectureNote post-processing stage as condition 2.

The exact model names, execution dates, prompt text, chunking policy, and release status are recorded in `manifest/condition_manifest.csv`.

## 4. Source-of-truth annotation files

The quantitative tables and figures are derived from the following files:

```text
annotations/<lecture_id>/domain_terms.csv
annotations/<lecture_id>/polarity_review.csv
annotations/<lecture_id>/semantic_review.csv
annotations/<lecture_id>/semantic_review_gpt4o_ailn_post.csv
manifest/condition_manifest.csv
data/<lecture_id>/reference.txt
```

Machine-assisted draft hints, where present in internal working files, are not authoritative and do not define the paper results. The analysis scripts use the human-reviewed annotation fields described below.

## 5. Domain-term annotation

`domain_terms.csv` defines the curated domain-term dictionary for each lecture.

Schema:

```text
term_id, canonical_english, english_variants, korean_phonetic, category,
polarity_group, polarity_value, keep, ref_count_auto, notes
```

### 5.1 Candidate extraction

Candidate terms were initialized by automatically extracting Latin-script token runs from the reference transcript. The author then curated the term set by deciding which rows should be retained with `keep=1`, which terms should be excluded with `keep=0`, and which accepted English variants should be grouped under a canonical term.

The English-script rendering metric uses the kept `canonical_english` forms plus optional `english_variants`. It measures whether curated reference term occurrences appear in English/Latin script in the output. It does not directly measure whether an English term is medically correct in context, and it does not directly penalize hallucinated English terms except through missed reference terms.

### 5.2 Korean phonetic variants

The `korean_phonetic` field records observed Korean phonetic or transliterated forms for some curated English medical terms. These entries were machine-assisted from observed ASR/STT outputs and used for a descriptive phonetic-versus-omitted breakdown.

The phonetic variant lists were not exhaustively verified and should not be interpreted as a complete inventory of all possible Korean phonetic renderings. As a result, Korean-phonetic counts are diagnostic lower-bound counts. The headline English-script rendering rate does not depend on the completeness of the `korean_phonetic` field; it depends on the curated English canonical forms and accepted English variants.

### 5.3 Polarity tags in the term dictionary

For terms with explicit opposition pairs, such as hypo/hyper or acidosis/alkalosis, `polarity_group` and `polarity_value` identify the relevant contrast. These tags support automatic screening and descriptive counts, but they are not the final polarity verdict. The paper's polarity results come from the human-reviewed `polarity_review.csv` worksheet.

## 6. Polarity annotation

`polarity_review.csv` is the authoritative worksheet for critical polarity and direction cues.

Each row corresponds to a reference sentence or phrase containing a medically relevant polarity, direction, or assertion cue. Examples include:

- hypo versus hyper;
- increase versus decrease;
- presence versus absence;
- negation or omission of a directional cue;
- clinically or biologically important numeric or directional substitutions when represented in the polarity worksheet.

For each of the five evaluated conditions, the annotator assigned one of:

```text
correct
wrong
omitted
unclear
```

Definitions:

- `correct`: the condition preserves the relevant polarity or direction cue.
- `wrong`: the condition changes the polarity or direction cue, such as hypo to hyper or decrease to increase.
- `omitted`: the condition drops the relevant cue or fails to express the polarity-bearing claim.
- `unclear`: the output does not allow a confident judgement.

The paper reports polarity failure as:

```text
wrong + omitted
```

Wrong and omitted counts are also preserved separately in the output tables.

Automatic polarity screens are used only as candidate-finding or descriptive tools. They are not the source of the final polarity counts.

## 7. Semantic-faithfulness annotation

Semantic faithfulness was annotated for the two post-processed conditions:

- `ai_lecturenote`
- `gpt4o_ailn_post`

The relevant worksheets are:

```text
annotations/<lecture_id>/semantic_review.csv
annotations/<lecture_id>/semantic_review_gpt4o_ailn_post.csv
```

Each row corresponds to one reference sentence. The worksheet includes the aligned span from the post-processed output and a human-assigned label.

Allowed labels:

```text
Faithful
Minor rewrite
Omission
Addition
Substitution
Polarity error
Relation error
Unclear
```

Definitions:

- `Faithful`: the output preserves the medical meaning of the reference sentence, allowing wording changes.
- `Minor rewrite`: the output changes phrasing or minor detail but does not materially change the medical claim.
- `Omission`: the output drops a medically relevant claim or cue.
- `Addition`: the output adds medically relevant information not present in the reference.
- `Substitution`: the output replaces a term, entity, mechanism, number, or concept with a different one.
- `Polarity error`: the output flips or loses a critical polarity, direction, or negation cue.
- `Relation error`: the output changes the relation between entities or mechanisms, such as cause, sequence, mechanism, or association.
- `Unclear`: the output is too ambiguous to judge confidently.

Rows with `Omission`, `Addition`, `Substitution`, `Polarity error`, or `Relation error` are counted as semantic drift. Labels may contain compound drift categories in working data; the analysis decomposes these into drift-category incidences while also reporting unique drifted rows.

## 8. Introduced versus propagated errors

For qualitative interpretation, some examples are described as introduced or propagated:

- `introduced`: the raw ASR output preserved the relevant information, but post-processing lost or changed it.
- `propagated`: the raw ASR output already contained the relevant error, and post-processing carried it forward.

This distinction is used for diagnostic interpretation of the post-processing stage. It is not a separate independently adjudicated annotation task.

## 9. Annotation tool

The optional Streamlit review app in `annotation_review_app/` was used as a local interface for inspecting long mixed Korean-English rows, assigning labels, and reducing spreadsheet-editing errors. The app is not required to reproduce the paper results. The source-of-truth results are the annotation CSV files described above.

Generated app artifacts such as backups, samples, and local review summaries are internal workflow files and are not paper source-of-truth files.

## 10. Data provenance and consent note

The evaluation recordings were created for this retrospective pilot by author-speakers. The recordings are not third-party classroom recordings, patient recordings, textbook readings, website readings, or readings from pre-existing lecture scripts. Speakers used topic outlines only as loose speaking plans and delivered the lectures extemporaneously in their own Korean-English wording.

Where audio is released, it is released only with explicit author-speaker consent. Audio contains identifiable voices and should not be treated as anonymized. Speaker identifiers in the repository are coded, but coded speaker IDs do not make the audio de-identified.

Transcripts, references, system outputs, and annotation rows are derived from these author-recorded lectures and are released for research reproducibility according to the repository's data license and release notes.

## 11. Interpretation limits

The annotation protocol supports reproducibility of the reported pilot results, but it does not remove the study's core limitations:

- four lectures only;
- single author-annotator;
- single annotation pass;
- no independent replication or adjudication;
- no inter-annotator agreement;
- references are lightly cleaned study transcripts rather than verbatim ASR gold standards;
- semantic drift was exhaustively annotated only for the two post-processed conditions;
- Korean-phonetic variant lists are diagnostic and not exhaustively verified.

Accordingly, the reported rates should be read as exact counts for this pilot corpus and annotation protocol, not as general benchmark estimates.
