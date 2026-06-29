"""End-to-end driver for the MedLect-KR STT evaluation.

Typical workflow:
    1.  python analysis/make_templates.py      # once, creates fill-in templates
    2.  (human) fill annotations/*/domain_terms.csv etc., drop in missing reference.txt
    3.  python analysis/run_all.py             # rebuild all tables + figures

run_all.py never overwrites annotations. Pass --make-templates to also create any
still-missing templates (existing ones are preserved) before building results.

Everything degrades gracefully by design: any lecture missing a reference or
annotations simply contributes fewer rows. All four pilot lectures
(diuretics_01, acuteinflammation_02, anthrax_01, anticancerdrugs_02) currently
have a reference and a complete human annotation pass, so the pipeline produces
every reference-dependent table/figure; the graceful-degradation path remains for
adding future lectures.
"""
from __future__ import annotations

import argparse

import config
import term_dictionary as td
import semantic_audit as sem
import polarity as pol
import tables
import figures
import make_templates


def print_status() -> None:
    print("=" * 70)
    print("DATA / ANNOTATION STATUS")
    print("=" * 70)
    lectures = config.discover_lectures()
    if not lectures:
        print("No lectures found under data/. Nothing to do.")
        return
    for lecture_id in lectures:
        ref = "yes" if config.has_reference(lecture_id) else "NO (pending)"
        n_terms = len(td.load_domain_terms(lecture_id, kept_only=True))
        terms = f"{n_terms} kept" if td.has_domain_terms(lecture_id) else "no file"
        sem_parts = []
        for condition in sem.SEMANTIC_REVIEW_CONDITIONS:
            sem_s = sem.summarize_semantic(lecture_id, condition)
            sem_parts.append(
                f"{condition}: {sem_s['claims_labeled']} labeled" if sem_s
                else f"{condition}: 0 labeled"
            )
        sem_txt = "; ".join(sem_parts)
        pol_n = len(pol.load_polarity_items(lecture_id))
        conds = [c for c in config.CONDITION_ORDER
                 if config.read_text(
                     config.data_path(lecture_id, config.CONDITIONS[c]["file"]))]
        print(f"\n[{lecture_id}]")
        print(f"  reference        : {ref}")
        print(f"  conditions found : {', '.join(conds) if conds else 'none'}")
        print(f"  domain_terms     : {terms}")
        print(f"  semantic_review  : {sem_txt}")
        print(f"  polarity_review  : {pol_n} rows")
    print()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--make-templates", action="store_true",
                        help="create any missing templates first (never overwrites)")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    if args.make_templates:
        print("Creating missing templates (existing ones preserved)...")
        make_templates.make_all(force=False)
        print()

    print_status()

    print("=" * 70)
    print("BUILDING TABLES  ->  outputs/tables/")
    print("=" * 70)
    built = tables.build_all(verbose=not args.quiet)

    print("\n" + "=" * 70)
    print("BUILDING FIGURES ->  outputs/figures/")
    print("=" * 70)
    figures.build_all(built, verbose=not args.quiet)

    print("\nDone. See evaluation_paper/outputs/ for tables and figures.")


if __name__ == "__main__":
    main()
