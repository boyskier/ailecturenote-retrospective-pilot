"""Generate paper figures from the result tables.

All figure text is kept in English (condition labels, lecture ids) so no Korean
font configuration is needed. Figures are written to outputs/figures/.

Data-driven figures (need real data):
  fig1_english_script_rate.png       - English-script rendering rate by condition
  fig2_cer_wer.png                   - CER / WER by condition
  fig3_chunk_<lecture>.png           - per-chunk GPT-4o script counts (key figure)
  fig6_readability_vs_faithfulness.png - headline trade-off (script gain vs drift cost)
Schematic figure (data-independent):
  fig0_evaluation_conditions.png     - audio -> raw STT -> (same historical
                                       post-processing) -> five outputs -> reference
"""
from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config

_COND_COLORS = {
    "whisper1": "#8c8c8c",
    "ai_lecturenote": "#1f77b4",
    "gpt4o": "#2ca02c",
    "gpt4o_prompted": "#ff7f0e",
    "gpt4o_ailn_post": "#9467bd",
}

_COND_HATCHES = {
    "gpt4o_ailn_post": "///",
}

# Short lecture ids for grouped figures where the full id collides on the x-axis.
_LECTURE_ABBREV = {
    "acuteinflammation_02": "acuteinfl_02",
    "anthrax_01": "anthrax_01",
    "diuretics_01": "diuretics_01",
    "anticancerdrugs_02": "anticancer_02",
}


def _abbrev_lecture(lecture_id: str) -> str:
    return _LECTURE_ABBREV.get(lecture_id, lecture_id)


# Compact condition tags for grouped (lecture x condition) figures where the full
# "short" label ("gpt-4o -> AILN post") is too wide to sit under a bar. Use the
# arrow notation consistently across figures (input STT -> post-processor).
_COND_TAG = {
    "ai_lecturenote": "whisper→AILN",
    "gpt4o_ailn_post": "gpt4o→AILN post",
}


def _cond_tag(cond: str) -> str:
    return _COND_TAG.get(cond, config.CONDITIONS.get(cond, {}).get("short", cond))


# Single-line compact labels for per-condition axes (used where every one of the
# five conditions is a separate tick, so the full config "short" labels are too wide
# and inconsistent with the grouped-figure tags above).
_COMPACT_COND = {
    "whisper1": "whisper-1",
    "ai_lecturenote": "whisper→AILN",
    "gpt4o": "gpt-4o raw",
    "gpt4o_prompted": "gpt-4o prompted",
    "gpt4o_ailn_post": "gpt4o→AILN post",
}


def _compact_cond(cond: str) -> str:
    return _COMPACT_COND.get(cond, config.CONDITIONS.get(cond, {}).get("short", cond))


def _save(fig, name: str) -> str:
    config.ensure_output_dirs()
    path = os.path.join(config.FIGURES_DIR, name)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def fig_english_script_rate(term_df) -> str | None:
    if term_df is None or term_df.empty:
        return None
    df = term_df[term_df.english_script_rate.notna()].copy()
    if df.empty:
        return None
    lectures = [l for l in df.lecture_id.unique() if l != "MACRO_AVG"] + ["MACRO_AVG"]
    conds = [c for c in config.CONDITION_ORDER if c in set(df.condition)]
    n = len(conds)
    width = 0.8 / max(n, 1)

    fig, ax = plt.subplots(figsize=(1.6 * len(lectures) + 2, 4.2))
    for i, cond in enumerate(conds):
        sub = df[df.condition == cond].set_index("lecture_id")
        vals = [float(sub.loc[l].english_script_rate) if l in sub.index else 0
                for l in lectures]
        xs = [j + i * width for j in range(len(lectures))]
        ax.bar(xs, vals, width=width, label=config.CONDITIONS[cond]["label"],
               color=_COND_COLORS.get(cond), hatch=_COND_HATCHES.get(cond))
    ax.set_xticks([j + (n - 1) * width / 2 for j in range(len(lectures))])
    ax.set_xticklabels([_abbrev_lecture(l) if l != "MACRO_AVG" else "macro avg"
                        for l in lectures], rotation=15, ha="right")
    ax.set_ylabel("English-script rendering rate")
    ax.set_ylim(0, 1.05)
    # Set the macro average apart from the per-lecture groups so it does not read
    # as just another lecture on the same axis.
    if "MACRO_AVG" in lectures:
        sep_x = len(lectures) - 1.5 + (n - 1) * width / 2
        right_x = len(lectures) - 1 + n * width
        ax.axvspan(sep_x, right_x, color="0.92", zorder=0)
        ax.axvline(sep_x, color="0.4", linestyle="--", linewidth=1)
        ax.text(len(lectures) - 1 + (n - 1) * width / 2, 1.03, "macro\naverage",
                ha="center", va="top", fontsize=7, color="0.3")
    ax.set_title("English medical-term script rendering by condition\n"
                 "(rendered in English script, not necessarily the correct term "
                 "— see §5.1 and §6.3)")
    # Legend outside (right) so it does not crowd the plot interior / top whitespace.
    ax.legend(fontsize=8, loc="center left", bbox_to_anchor=(1.005, 0.5),
              frameon=False)
    ax.grid(axis="y", alpha=0.3)
    return _save(fig, "fig1_english_script_rate.png")


def fig_cer_wer(acc_df) -> str | None:
    """Per-lecture CER (primary) and WER (secondary) grouped by condition.

    Per-lecture (not just macro) so the anthrax_01 counter-example is visible: there
    raw whisper-1 is very clean (low CER) while AI_LectureNote's CER spikes — a
    dispersion the macro average hides.
    """
    if acc_df is None or acc_df.empty:
        return None
    lectures = [l for l in acc_df.lecture_id.unique() if l != "MACRO_AVG"] + ["MACRO_AVG"]
    conds = [c for c in config.CONDITION_ORDER if c in set(acc_df.condition)]
    n = len(conds)
    width = 0.8 / max(n, 1)

    fig, axes = plt.subplots(2, 1, figsize=(1.7 * len(lectures) + 2, 7), sharex=True)
    panels = (
        (axes[0], "cer", "CER (primary; lower = closer to reference)",
         "CER   ↓ lower = closer to reference"),
        (axes[1], "wer", "WER (secondary only; unstable under paraphrase)",
         "WER   (secondary only)"),
    )
    for ax, metric, title, ylabel in panels:
        for i, cond in enumerate(conds):
            sub = acc_df[acc_df.condition == cond].set_index("lecture_id")
            vals = [float(sub.loc[l][metric]) if l in sub.index else 0 for l in lectures]
            xs = [j + i * width for j in range(len(lectures))]
            ax.bar(xs, vals, width=width, label=config.CONDITIONS[cond]["label"],
                   color=_COND_COLORS.get(cond), hatch=_COND_HATCHES.get(cond))
        ax.set_ylabel(ylabel)
        ax.set_title(title, fontsize=10)
        ax.grid(axis="y", alpha=0.3)
        # Set the macro average apart with a shaded band + dashed separator, matching
        # fig1 so the figure set is consistent (macro must not read as a lecture).
        if "MACRO_AVG" in lectures:
            sep_x = len(lectures) - 1.5 + (n - 1) * width / 2
            right_x = len(lectures) - 1 + n * width
            ax.axvspan(sep_x, right_x, color="0.92", zorder=0)
            ax.axvline(sep_x, color="0.4", linestyle="--", linewidth=1)
    # Legend outside (right) of the top panel; hide the redundant x labels on the top
    # panel (shared x — they belong on the bottom panel only).
    axes[0].legend(fontsize=8, loc="center left", bbox_to_anchor=(1.005, 0.5),
                   frameon=False)
    axes[0].tick_params(labelbottom=False)
    axes[1].set_xticks([j + (n - 1) * width / 2 for j in range(len(lectures))])
    axes[1].set_xticklabels([_abbrev_lecture(l) if l != "MACRO_AVG" else "macro avg"
                             for l in lectures], rotation=15, ha="right")
    fig.tight_layout()
    fig.text(0.5, -0.01,
             "CER/WER measure surface distance to the cleaned study-transcript reference, "
             "not pure ASR accuracy.", ha="center", fontsize=8, color="0.3")
    return _save(fig, "fig2_cer_wer.png")


def fig_chunk_consistency(chunk_df) -> list[str]:
    if chunk_df is None or chunk_df.empty:
        return []
    paths = []
    for lecture_id in chunk_df.lecture_id.unique():
        ldf = chunk_df[chunk_df.lecture_id == lecture_id]
        conds = [c for c in config.CHUNKED_CONDITIONS if c in set(ldf.condition)]
        if not conds:
            continue
        fig, axes = plt.subplots(len(conds), 1, figsize=(9, 2.6 * len(conds)),
                                 squeeze=False, sharex=True)
        for r, cond in enumerate(conds):
            ax = axes[r][0]
            cdf = ldf[ldf.condition == cond].sort_values("chunk_id")
            xs = [int(c) for c in cdf.chunk_id.tolist()]
            eng = cdf.english_count.tolist()
            kor = cdf.phonetic_count.tolist()
            has_phonetic = any(k > 0 for k in kor)
            # Sparse lectures (e.g. anticancerdrugs_02 has only 2 chunks) leave very
            # wide default bars; narrow them so the panel does not look empty.
            bar_w = 0.55 if len(xs) <= 2 else 0.8
            eng_bars = ax.bar(xs, eng, width=bar_w, label="English script",
                              color="#2ca02c")
            kor_bars = ax.bar(xs, kor, width=bar_w, bottom=eng, label="Korean phonetic",
                              color="#ff7f0e")
            totals = [e + k for e, k in zip(eng, kor)]
            for idx, (x, e, k) in enumerate(zip(xs, eng, kor)):
                total = e + k
                if total == 0:
                    # Rate is undefined when a chunk has no curated reference terms.
                    ax.text(x, 0.5, "no curated\nterms", ha="center", va="bottom",
                            fontsize=7, color="0.35", style="italic")
                    continue
                if total < 5:
                    # Few curated occurrences: the per-chunk rate is unstable. Hatch
                    # the bar and flag the small denominator.
                    eng_bars[idx].set_hatch("xx")
                    kor_bars[idx].set_hatch("xx")
                # Always show the denominator so 0% (0/1) is not read like 0% (0/40).
                if has_phonetic:
                    label = f"{e/total:.0%}\n({e}/{total})"
                else:
                    label = f"{e}/{total}"
                # A dagger marks the small-denominator (n<5) chunks: the hatch alone
                # is nearly invisible on short bars.
                if total < 5:
                    label += "†"
                ax.text(x, total + 0.4, label, ha="center", fontsize=6.5)
            ax.set_ylim(0, (max(totals) if totals else 1) * 1.32)
            ax.set_ylabel("curated domain-term\noccurrences")
            ax.set_title(f"{lecture_id} — {config.CONDITIONS[cond]['label']}",
                         fontsize=9)
            ax.legend(fontsize=7, loc="upper right")
            ax.grid(axis="y", alpha=0.3)
        # Integer chunk ticks only: chunk ids are discrete, never fractional.
        all_chunks = sorted(int(c) for c in ldf.chunk_id.unique())
        ticks = list(range(min(all_chunks), max(all_chunks) + 1))
        for ax in (a[0] for a in axes):
            ax.set_xticks(ticks)
            # Pad the x-limits so sparse lectures (few chunks) are not flush to the
            # axis edges with oversized empty margins between bars.
            ax.set_xlim(min(ticks) - 0.7, max(ticks) + 0.7)
        axes[-1][0].set_xticklabels([f"Chunk {t}" for t in ticks])
        any_phonetic = bool((ldf.phonetic_count > 0).any())
        if any_phonetic:
            xlabel = ("3-min chunks · green = English / orange = Korean phonetic · "
                      "% = English-script rate (n = curated domain-term occurrences)\n"
                      "Rates undefined where a chunk has no curated terms (marked); "
                      "† = n<5 (small denominator, unstable) · y-axis scaled per lecture")
        else:
            xlabel = ("3-min chunks · fill korean_phonetic in domain_terms.csv for the "
                      "phonetic-vs-English split\n"
                      "Chunks with no curated reference term are marked “no curated terms” "
                      "· † = n<5 · y-axis scaled per lecture")
        axes[-1][0].set_xlabel(xlabel, fontsize=7.5)
        fig.tight_layout()
        paths.append(_save(fig, f"fig3_chunk_{lecture_id}.png"))
    return paths


_DRIFT_TOKENS = ["Omission", "Substitution", "Polarity error", "Addition",
                 "Relation error"]
_DRIFT_COLORS = {
    "Omission": "#4c72b0",
    "Substitution": "#dd8452",
    "Polarity error": "#c44e52",
    "Addition": "#8172b3",
    "Relation error": "#937860",
}


def fig_drift_taxonomy(tax_df) -> str | None:
    """Stacked per-lecture AI_LectureNote drift, decomposed by category.

    Shows that the drift *profile* differs by lecture (e.g. omission-heavy under
    heavy compression vs substitution-heavy when upstream STT errors are carried
    forward) rather than a single uniform failure mode.
    """
    if tax_df is None or tax_df.empty:
        return None
    labels = [
        f"{_abbrev_lecture(row.lecture_id)}\n{_cond_tag(row.condition)}"
        if "condition" in tax_df.columns else _abbrev_lecture(row.lecture_id)
        for row in tax_df.itertuples(index=False)
    ]
    fig, ax = plt.subplots(figsize=(1.5 * len(labels) + 2, 4.8))
    bottom = [0] * len(labels)
    for tok in _DRIFT_TOKENS:
        if tok not in tax_df.columns:
            continue
        vals = [int(v) for v in tax_df[tok]]
        ax.bar(labels, vals, bottom=bottom, label=tok, color=_DRIFT_COLORS.get(tok))
        for x, (b, v) in enumerate(zip(bottom, vals)):
            # Tiny (==1) segments are too cramped to label legibly; the bar-top
            # rows/inc. summary carries the totals, so only label segments >= 2.
            if v >= 2:
                ax.text(x, b + v / 2, str(v), ha="center", va="center", fontsize=8,
                        color="white")
        bottom = [b + v for b, v in zip(bottom, vals)]
    # Annotate each bar with both the unique drifted-row count and the total label
    # incidences. Compound rows inflate incidences above the unique-row count, so
    # without this the bar heights would not reconcile with the unique drift totals
    # quoted in the text (e.g. 10 unique rows but 11 incidences).
    drift_rows = list(tax_df["drift_rows"]) if "drift_rows" in tax_df.columns else None
    for x, inc in enumerate(bottom):
        if drift_rows is not None:
            txt = f"{int(drift_rows[x])} rows\n{int(inc)} inc."
        else:
            txt = f"{int(inc)} inc."
        ax.text(x, inc + 0.15, txt, ha="center", va="bottom", fontsize=7)
    ax.set_ylim(0, (max(bottom) if len(bottom) else 1) * 1.25 + 1)
    ax.set_ylabel("drift-label incidences")
    # Bar heights are per-category label incidences; the unique drifted-claim totals
    # (one row counted once, regardless of how many categories it carries) are smaller
    # and are no longer the N=3 "33 vs 33" — at N=4 they are 34 vs 36. Compute from data.
    subtitle = ("\nrows = unique drifted rows · inc. = label incidences "
                "(compound rows count once per category)")
    if {"drift_rows", "condition"}.issubset(tax_df.columns):
        by_cond = tax_df.groupby("condition").drift_rows.sum()
        ai_u = int(by_cond.get("ai_lecturenote", 0))
        g5_u = int(by_cond.get("gpt4o_ailn_post", 0))
        subtitle += f"; unique drifted claims: whisper→AILN {ai_u} vs gpt4o→AILN {g5_u}"
    ax.set_title("Post-processing semantic-drift profile by lecture and STT front-end"
                 + subtitle,
                 fontsize=9)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=0, ha="center", fontsize=8)
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    return _save(fig, "fig4_drift_taxonomy.png")


def fig_polarity_postprocessing(pol_sum_df, trans_df) -> str | None:
    """Two panels on critical medical polarity.

    (a) polarity failures per condition split into wrong (flipped) vs omitted,
        POOLED over every lecture / all polarity-cue rows (a corpus-level count,
        not a per-lecture rate);
    (b) raw whisper-1 -> AI_LectureNote transition (fixed vs newly introduced),
        restricted to diuretics_01 — the only lecture carrying enough
        polarity-sensitive statements to be informative (acuteinflammation: 1
        error, anthrax: 0, anticancerdrugs: 0) — labeled as illustrative / N=1.
    """
    if pol_sum_df is None or pol_sum_df.empty:
        return None
    # Panel (b) has only 3 categories vs panel (a)'s 5 conditions; give (a) a little
    # more width so the two panels look balanced rather than (b) looking empty.
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.4),
                             gridspec_kw={"width_ratios": [1.15, 1]})

    # Panel (a): wrong vs omitted per condition, POOLED across all lectures.
    conds = [c for c in config.CONDITION_ORDER if c in set(pol_sum_df.condition)]
    labels = [_compact_cond(c) for c in conds]
    wrong = [int(pol_sum_df[pol_sum_df.condition == c].wrong.sum()) for c in conds]
    omit = [int(pol_sum_df[pol_sum_df.condition == c].omitted.sum()) for c in conds]
    # Cue rows are shared across conditions; sum the per-lecture totals for one.
    n_rows = (int(pol_sum_df[pol_sum_df.condition == conds[0]].total_labeled.sum())
              if conds else 0)
    n_lec = int(pol_sum_df.lecture_id.nunique())
    ax = axes[0]
    ax.bar(labels, wrong, color="#c44e52", label="wrong (flipped)")
    ax.bar(labels, omit, bottom=wrong, color="#dd8452", label="omitted (dropped)")
    for x, (w, o) in enumerate(zip(wrong, omit)):
        if w:
            ax.text(x, w / 2, str(w), ha="center", va="center", color="white", fontsize=9)
        if o:
            ax.text(x, w + o / 2, str(o), ha="center", va="center", color="white", fontsize=9)
        ax.text(x, w + o + 0.15, f"fail {w + o}", ha="center", fontsize=8)
    ax.set_ylabel("polarity failures")
    ax.set_ylim(0, max((w + o for w, o in zip(wrong, omit)), default=1) + 2)
    ax.set_title(f"(a) Polarity failures by condition — pooled over all {n_lec} "
                 f"lectures ({n_rows} cue rows)", fontsize=9)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)

    # Panel (b): whisper-1 -> AI transition, diuretics_01 only (illustrative, N=1).
    lec = "diuretics_01"
    ax = axes[1]
    if trans_df is not None and not trans_df.empty and (trans_df.lecture_id == lec).any():
        t = trans_df[trans_df.lecture_id == lec].iloc[0]
        cats = ["fixed\n(raw wrong→AI ok)", "introduced flip\n(raw ok→AI wrong)",
                "introduced omission\n(raw ok→AI dropped)"]
        vals = [int(t["fixed"]), -int(t["introduced_flip"]), -int(t["introduced_omission"])]
        colors = ["#55a868", "#c44e52", "#dd8452"]
        ax.bar(cats, vals, color=colors)
        # Number centered inside each bar (white) — consistent for + and - bars, so a
        # negative-bar count no longer straddles the zero baseline.
        for x, v in enumerate(vals):
            if v != 0:
                ax.text(x, v / 2, f"{abs(v)}", ha="center", va="center",
                        color="white", fontsize=10)
        ax.axhline(0, color="black", lw=0.8)
        net = int(t["net_failure_change"])
        fixed = int(t["fixed"])
        introduced = int(t["introduced_flip"]) + int(t["introduced_omission"])
        # Bars sit on an improvement axis (fixed = up/positive, introduced = down/
        # negative), so state the net the same way to avoid a +/- sign clash with
        # the "failures increased" reading.
        improvement_net = fixed - introduced  # negative => failures increased
        ax.set_title("(b) Post-processing effect on polarity — diuretics_01 only\n"
                     f"+{fixed} fixed vs −{introduced} introduced = net "
                     f"{improvement_net:+d}  (failures +{net})", fontsize=9)
        ax.set_ylabel("net change on improvement axis")
        ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return _save(fig, "fig5_polarity_postprocessing.png")


def fig_readability_vs_faithfulness(term_df, sem_sum_df) -> str | None:
    """Headline trade-off: English-script rendering gain vs semantic-drift cost.

    Pairs the readability axis (English-script rendering rate by condition, macro)
    with the faithfulness cost the script metric hides (AI_LectureNote semantic-drift
    rate by lecture). Read together they are the paper's thesis: domain-aware
    post-processing raises English-script readability but introduces/propagates
    semantic drift, and a high script rate can coexist with wrong-English
    substitutions (paper §6.3). This is meant as the headline figure — the script
    metric should never be shown alone.
    """
    if term_df is None or term_df.empty or sem_sum_df is None or sem_sum_df.empty:
        return None
    macro = term_df[term_df.lecture_id == "MACRO_AVG"]
    if macro.empty:
        return None
    fig, axes = plt.subplots(1, 2, figsize=(16, 5.0))

    # Panel (a): readability axis — English-script rendering rate by condition (macro).
    ax = axes[0]
    conds = [c for c in config.CONDITION_ORDER if c in set(macro.condition)]
    labels = [_compact_cond(c) for c in conds]
    vals = [float(macro[macro.condition == c].english_script_rate.iloc[0]) for c in conds]
    bars = ax.bar(range(len(conds)), vals, color=[_COND_COLORS.get(c) for c in conds])
    for bar, cond in zip(bars, conds):
        if cond in _COND_HATCHES:
            bar.set_hatch(_COND_HATCHES[cond])
    for x, v in enumerate(vals):
        ax.text(x, v + 0.02, f"{v:.2f}", ha="center", fontsize=9)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("English-script rendering rate (macro)")
    ax.set_title("(a) Readability axis: English-script rendering — macro rate\n"
                 "(script only — not medical correctness)", fontsize=9)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.grid(axis="y", alpha=0.3)

    # Panel (b): faithfulness cost — AI_LectureNote semantic-drift rate by lecture.
    ax = axes[1]
    sdf = sem_sum_df.copy()
    sdf["drift_rate"] = sdf.semantic_drift / sdf.claims_labeled * 100
    sort_cols = ["lecture_id"] + (["condition"] if "condition" in sdf.columns else [])
    sdf = sdf.sort_values(sort_cols)
    lecs = [
        f"{_abbrev_lecture(row.lecture_id)}\n{_cond_tag(row.condition)}"
        if "condition" in sdf.columns else _abbrev_lecture(row.lecture_id)
        for row in sdf.itertuples(index=False)
    ]
    rates = sdf.drift_rate.tolist()
    colors = [
        _COND_COLORS.get(row.condition, _COND_COLORS["ai_lecturenote"])
        if "condition" in sdf.columns else _COND_COLORS["ai_lecturenote"]
        for row in sdf.itertuples(index=False)
    ]
    ax.bar(range(len(lecs)), rates, color=colors)
    for x, (r, d, n) in enumerate(zip(rates, sdf.semantic_drift, sdf.claims_labeled)):
        ax.text(x, r + 0.3, f"{r:.0f}%\n({int(d)}/{int(n)})", ha="center", fontsize=8)
    ax.set_ylim(0, max(rates, default=1) + 5)
    ax.set_ylabel("semantic-drift rate (%)")
    ax.set_title("(b) Faithfulness axis: observed post-processing drift — per-lecture "
                 "rate\n(post-processed conditions only; single-author labeled, single "
                 "annotator)", fontsize=9)
    ax.set_xticks(range(len(lecs)))
    ax.set_xticklabels(lecs, rotation=35, ha="right", fontsize=8)
    ax.grid(axis="y", alpha=0.3)

    fig.suptitle("Readability gain is not faithfulness: English-script rendering vs "
                 "semantic drift (pilot study, N=4 lectures)", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    return _save(fig, "fig6_readability_vs_faithfulness.png")


def fig_evaluation_conditions() -> str:
    """Schematic: audio -> raw STT -> (same historical post-processing) -> outputs -> reference.

    Crucially, AI_LectureNote and gpt4o_ailn_post are NOT produced directly from
    audio: each is a raw STT transcript (whisper-1 / gpt-4o) passed through the
    *same* historical AI_LectureNote post-processing pipeline. Raw whisper-1, raw
    gpt-4o-transcribe and prompted gpt-4o-transcribe are evaluated directly. All
    five evaluated outputs are scored against the reference transcript.
    """
    fig, ax = plt.subplots(figsize=(11.5, 5.7))
    ax.axis("off")
    bw, bh = 0.155, 0.13

    def box(cx, cy, text, color, w=bw, h=bh, fontsize=8, lw=1.0, edgecolor="black"):
        ax.add_patch(plt.Rectangle((cx - w / 2, cy - h / 2), w, h, fill=True,
                                   facecolor=color, edgecolor=edgecolor, alpha=0.9,
                                   linewidth=lw))
        ax.text(cx, cy, text, ha="center", va="center", fontsize=fontsize, wrap=True)
        return (cx, cy, w, h)

    def arrow(a, b, color="black", lw=1.1, style="arc3,rad=0", linestyle="solid"):
        ax.annotate("", xy=(b[0] - b[2] / 2, b[1]), xytext=(a[0] + a[2] / 2, a[1]),
                    arrowprops=dict(arrowstyle="->", color=color, lw=lw,
                                    connectionstyle=style, linestyle=linestyle))

    x_audio, x_raw, x_post, x_out, x_ref = 0.06, 0.27, 0.49, 0.71, 0.93
    y_w, y_g, y_p = 0.84, 0.50, 0.16  # whisper / gpt-4o / prompted rows

    audio = box(x_audio, 0.50, "Lecture\naudio", "#dddddd", w=0.10)

    whisper = box(x_raw, y_w, "raw whisper-1", _COND_COLORS["whisper1"])
    gpt4o = box(x_raw, y_g, "raw gpt-4o-\ntranscribe\n(3-min chunks)", _COND_COLORS["gpt4o"])
    prompted = box(x_raw, y_p, "prompted gpt-4o-\ntranscribe\n(preliminary)",
                   _COND_COLORS["gpt4o_prompted"])

    post_w = box(x_post, y_w, "AI_LectureNote\npost-processing\n(historical, fixed)",
                 "#cfe2f3", h=0.16)
    post_g = box(x_post, y_g, "same AI_LectureNote\npost-processing\n(identical config)",
                 "#cfe2f3", h=0.16)

    # Post-processed outputs get a heavier border to set them apart from the raw STT
    # outputs (left column) and the reference (right column).
    ai = box(x_out, y_w, "AI_LectureNote", _COND_COLORS["ai_lecturenote"], lw=2.5)
    g5 = box(x_out, y_g, "gpt4o_ailn_post", _COND_COLORS["gpt4o_ailn_post"], lw=2.5)

    ref = box(x_ref, 0.50, "Reference\ntranscript\n(metrics:\nCER/WER, term,\n"
              "polarity, drift)", "#f0e0b0", w=0.12, h=0.74, fontsize=7)

    # Main pipeline flow (solid black): audio -> raw STT -> post -> post-processed output.
    for b in (whisper, gpt4o, prompted):
        arrow(audio, b)
    arrow(whisper, post_w); arrow(post_w, ai)
    arrow(gpt4o, post_g); arrow(post_g, g5)

    # All five evaluated outputs scored vs reference: dashed gray = evaluation, kept
    # visually distinct from the solid pipeline arrows so the reference does not read
    # as being generated from the outputs. The two raw conditions that also feed
    # post-processing arc around the post/output boxes to avoid crossing through them.
    arrow(ai, ref, color="gray", lw=0.8, linestyle="dashed")
    arrow(g5, ref, color="gray", lw=0.8, linestyle="dashed")
    arrow(prompted, ref, color="gray", lw=0.8, linestyle="dashed")
    # whisper-1 shares its row with post_w / ai; only a pronounced downward sweep clears
    # those boxes (a shallow bow grazes them), so route it well below the row. The boxed
    # note below stays legible regardless. gpt-4o bows down past its own row (post_g / g5).
    arrow(whisper, ref, color="gray", lw=0.8, style="arc3,rad=-0.5", linestyle="dashed")
    arrow(gpt4o, ref, color="gray", lw=0.8, style="arc3,rad=0.28", linestyle="dashed")

    # Drawn after the arrows so the white callout sits on top of any dashed line that
    # passes nearby (keeps it legible instead of being crossed out). Placed low enough
    # to clear the gpt-4o evaluation arc above it.
    ax.text(x_out, y_g - 0.13, "diagnostic control,\nnot an optimized production system",
            ha="center", va="top", fontsize=6.3, style="italic", color="#444444",
            bbox=dict(boxstyle="round,pad=0.45", facecolor="white", edgecolor="#999999",
                      linewidth=0.6))

    # Column headers clarify the raw -> post-processing -> post-processed-output ->
    # reference grouping (also distinguished by box colour and border weight).
    for hx, htext in ((x_raw, "raw ASR"), (x_post, "post-processing"),
                      (x_out, "post-processed output"), (x_ref, "reference")):
        ax.text(hx, 0.985, htext, ha="center", va="top", fontsize=7.5,
                color="#333333", fontweight="bold")

    ax.text(0.5, -0.005,
            "Arrows: solid = processing pipeline,   dashed = evaluation "
            "(each output scored against the reference).",
            ha="center", va="center", fontsize=7.5, color="#333333")
    ax.text(0.5, -0.05,
            "Annotation scope: semantic drift annotated only for the two post-processed "
            "conditions; polarity annotated for all five conditions.",
            ha="center", va="center", fontsize=7, color="#333333")

    ax.set_xlim(0, 1)
    ax.set_ylim(-0.08, 1.0)
    ax.set_title("Evaluation conditions: one audio, five evaluated outputs, one reference\n"
                 "(AI_LectureNote = raw whisper-1 + post-processing; gpt4o_ailn_post = raw "
                 "gpt-4o + the same post-processing — neither is direct-from-audio)",
                 fontsize=10)
    return _save(fig, "fig0_evaluation_conditions.png")


def build_all(tables: dict, verbose: bool = True) -> None:
    made = []
    made.append(fig_evaluation_conditions())
    made.append(fig_english_script_rate(tables.get("table2_term_preservation")))
    made.append(fig_cer_wer(tables.get("table1_accuracy_cer_wer")))
    made.extend(fig_chunk_consistency(tables.get("table3_chunk_consistency")))
    made.append(fig_drift_taxonomy(tables.get("table8_drift_taxonomy")))
    made.append(fig_polarity_postprocessing(tables.get("table5_polarity_summary"),
                                            tables.get("table9_polarity_transition")))
    made.append(fig_readability_vs_faithfulness(tables.get("table2_term_preservation"),
                                                tables.get("table6_semantic_summary")))
    made = [m for m in made if m]
    if verbose:
        if made:
            for p in made:
                print(f"  {os.path.basename(p)}")
        else:
            print("  (no figures yet — awaiting references / annotations)")
