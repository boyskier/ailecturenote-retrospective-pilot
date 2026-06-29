"""Publication-finalization pass for domain_terms.csv (cosmetic; changes no scores).

The domain_terms.csv files were auto-extracted from an EARLIER draft of each
reference and then hand-curated. That leaves three kinds of cruft that are fine for
analysis (the scorer ignores keep=0 rows and never reads ``ref_count_auto``) but
look messy in a published artifact:

  * tokenization junk  - fragments with a dangling '-' or '/', e.g. ``TNF-`` split
                         off ``TNF-alpha`` (the alpha was a non-ASCII glyph).
  * stale candidates   - keep=0 rows whose surface form no longer occurs in the
                         FINAL reference at all (left over from the pre-final draft).
  * stale counts       - ``ref_count_auto`` is the extraction-time count, computed
                         before the reference was finalized and before english_variants
                         merging, so it disagrees with the live scoring count.

This pass DROPS the first two and REFRESHES ``ref_count_auto`` to the live count
(canonical + english_variants) against the final reference, using the exact same
counting logic as scoring (textutils.count_english_occurrences). It deliberately
KEEPS deliberate exclusions and synonym-merge rows (with their notes): documenting
what was excluded/folded is a transparency asset, not noise.

Because the scorer ignores keep=0 and ref_count_auto, running this changes ZERO
numbers in any table/figure. It only tidies the CSV for release.

Usage:
    python analysis/clean_domain_terms.py            # dry-run report (no writes)
    python analysis/clean_domain_terms.py --apply     # rewrite the CSVs in place
"""
from __future__ import annotations

import csv
import sys

import config
import textutils as tu


def _split_pipe(value: str) -> list[str]:
    return [v.strip() for v in (value or "").split("|") if v.strip()]


def _is_dropped_keep(value: str) -> bool:
    return (value or "").strip().lower() in ("0", "false", "no", "n", "")


def _dangling(canonical: str) -> bool:
    """A canonical that begins/ends with a connector hyphen or slash is a
    tokenization fragment (e.g. ``TNF-``). ``K+`` / ``Na+`` are real, so '+' is
    intentionally not treated as dangling."""
    c = canonical.strip()
    if not c:
        return False
    return c[-1] in "-/" or c[0] in "-/"


def classify(reference: str, canonical: str, variants: list[str], keep_dropped: bool):
    """Return (action, live_count). action in KEEP / DROP_JUNK / DROP_STALE / FLAG."""
    live = tu.count_english_occurrences(reference, [canonical] + variants)
    if not canonical:
        return "KEEP", live  # leave odd/blank rows untouched
    if not keep_dropped:  # keep=1
        return ("FLAG" if live == 0 else "KEEP"), live
    # keep == 0
    if _dangling(canonical):
        return "DROP_JUNK", live
    if live == 0:
        return "DROP_STALE", live
    return "KEEP", live  # deliberate exclusion / merge row, still present in reference


def process_lecture(lecture_id: str, apply: bool) -> dict:
    path = config.annotation_path(lecture_id, "domain_terms.csv")
    reference = config.read_text(config.reference_path(lecture_id))
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        return {"lecture_id": lecture_id, "error": "empty file"}

    header = rows[0]
    idx = {name: header.index(name) for name in
           ("canonical_english", "english_variants", "keep", "ref_count_auto")
           if name in header}
    ic, iv = idx.get("canonical_english"), idx.get("english_variants")
    ik, icount = idx.get("keep"), idx.get("ref_count_auto")

    def cell(row, i):
        return row[i] if (i is not None and i < len(row)) else ""

    kept_rows, dropped, flagged = [header], [], []
    for row in rows[1:]:
        if not any((c or "").strip() for c in row):
            continue  # skip wholly blank lines
        canonical = cell(row, ic).strip()
        variants = _split_pipe(cell(row, iv))
        keep_dropped = _is_dropped_keep(cell(row, ik))
        action, live = classify(reference, canonical, variants, keep_dropped)

        if action.startswith("DROP"):
            dropped.append((action, canonical, cell(row, icount).strip(), live))
            continue
        if action == "FLAG":
            flagged.append((canonical, cell(row, icount).strip()))
        # refresh the count column on every surviving row
        if icount is not None:
            while len(row) <= icount:
                row.append("")
            row[icount] = str(live)
        kept_rows.append(row)

    if apply:
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            csv.writer(f).writerows(kept_rows)

    return {
        "lecture_id": lecture_id,
        "total": len(rows) - 1,
        "kept": len(kept_rows) - 1,
        "dropped": dropped,
        "flagged": flagged,
    }


def main(argv):
    apply = "--apply" in argv
    print("=== domain_terms cleanup ({}), scores unaffected ===".format(
        "APPLY" if apply else "DRY-RUN"))
    for lecture_id in config.discover_lectures():
        if not config.has_reference(lecture_id):
            print("\n[{}] no reference - skipped".format(lecture_id))
            continue
        r = process_lecture(lecture_id, apply)
        if r.get("error"):
            print("\n[{}] {}".format(lecture_id, r["error"]))
            continue
        print("\n[{}] {} rows -> {} kept, {} dropped".format(
            r["lecture_id"], r["total"], r["kept"], len(r["dropped"])))
        for action, canonical, old_count, live in r["dropped"]:
            print("   DROP  {:<10} {:<34} (was ref_count_auto={}, live={})".format(
                action.replace("DROP_", ""), canonical, old_count, live))
        for canonical, old_count in r["flagged"]:
            print("   FLAG  keep=1 but 0x in final reference: {} (was {})".format(
                canonical, old_count))
    if not apply:
        print("\n(dry-run only; re-run with --apply to rewrite the CSVs)")


if __name__ == "__main__":
    main(sys.argv[1:])
