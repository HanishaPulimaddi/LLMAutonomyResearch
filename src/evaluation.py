"""Evaluate logged predictions against ground_truth.json.

Runs only after predictions exist. Imports no LLM code and makes no API calls; it reads
results/raw_results.csv and data/ground_truth.json, and never modifies either.

Usage:
    python src/evaluation.py              # latest Groq run in results/raw_results.csv
    python src/evaluation.py --run-id ID

Writes:
    results/evaluation_summary.csv   one row per architecture
    results/evaluation_details.csv   one row per prediction (60)
    results/error_analysis.csv       predictions that disagree with ground truth
    results/error_pattern_matrix.csv one row per applicant; pass/fail of each pipeline stage per architecture

Metric definitions:
    eligibility_accuracy      predicted eligible == ground truth; failed calls count as wrong (denominator 20)
    effective_date_accuracy   predicted effective date == ground-truth effective date (same denominator)
    format_validity           A: DECISION line parsed; B: JSON passed schema validation; C: facts passed schema validation
    internal_consistency      A/B: stated decision agrees with the model's own effective date vs the threshold
    B month_consistency       PhD award date + model's claimable months == model's effective date
    C phd_date_accuracy       extracted PhD date == ground-truth PhD date
    C interruption_accuracy   extracted (type, months) multiset == ground truth, with primary-carer periods summed
                              and parental leave within a primary-carer period expected as its own entry
    C attribute_accuracy      after_phd, concurrency and within-primary-carer flags all correct
    C fact_extraction_accuracy  all three of the above
    C replayable              re-running the rule engine on the logged facts reproduces the logged decision
"""
import argparse
import csv
import json
from collections import Counter
from datetime import date
from pathlib import Path

from rules import THRESHOLD, ApplicantFacts, add_months, assess

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "results" / "raw_results.csv"
GROUND_TRUTH = ROOT / "data" / "ground_truth.json"
SUMMARY = ROOT / "results" / "evaluation_summary.csv"
DETAILS = ROOT / "results" / "evaluation_details.csv"
ERRORS = ROOT / "results" / "error_analysis.csv"
MATRIX = ROOT / "results" / "error_pattern_matrix.csv"

TRACE_TYPE = {
    "A": "free-text explanation only",
    "B": "JSON with reasoning field and claimable months",
    "C": "extracted facts + deterministic step-by-step rule trace",
}


def months_between(a, b):
    return (b.year - a.year) * 12 + (b.month - a.month) + (0 if b.day >= a.day else -1)


def to_bool(s):
    return {"True": True, "False": False}.get(s)


def to_date(s):
    try:
        return date.fromisoformat(s) if s else None
    except ValueError:
        return None


def normalise(entries):
    """(type, months) multiset; primary-carer periods summed into one entry."""
    carer = [m for t, m in entries if t == "primary_carer"]
    rest = [(t, m) for t, m in entries if t != "primary_carer"]
    if carer:
        rest.append(("primary_carer", None if None in carer else sum(carer)))
    return Counter(rest)


def expected_facts(gt):
    entries, flags = [], []
    for i in gt["interruptions"]:
        entries.append((i["type"], i["stated_months"]))
        if "concurrent_with_research" in i:
            flags.append(("non_research_position", "concurrent_with_research_employment", i["concurrent_with_research"]))
        if "includes_parental_leave_months" in i:
            entries.append(("parental_leave", i["includes_parental_leave_months"]))
            flags.append(("parental_leave", "within_primary_carer_period", True))
    return entries, flags


def check_facts(facts, gt):
    entries, flags = expected_facts(gt)
    got = [(i["type"], i["duration_months"]) for i in facts["interruptions"]]
    phd_ok = facts["phd_award_date"] == gt["phd_award_date"]
    ints_ok = normalise(got) == normalise(entries)
    attrs_ok = all(i["after_phd"] is True for i in facts["interruptions"])  # every ground-truth interruption is post-PhD
    for t, attr, want in flags:
        attrs_ok &= any(i["type"] == t and i[attr] == want for i in facts["interruptions"])
    # Spurious flags also count as errors, e.g. parental leave marked as within a primary-carer period
    # when the profile describes no primary-carer period.
    carer_expected = any(t == "parental_leave" for t, _, _ in flags)
    for i in facts["interruptions"]:
        if i["type"] == "parental_leave":
            attrs_ok &= bool(i["within_primary_carer_period"]) == carer_expected
    return phd_ok, ints_ok, attrs_ok


def evaluate_row(row, gt):
    arch = row["architecture"]
    parsed = json.loads(row["parsed_response"]) if row["parsed_response"] else None
    pred_elig = to_bool(row["predicted_eligible"])
    pred_date = to_date(row["predicted_effective_date"])
    gt_date = date.fromisoformat(gt["ground_truth_effective_date"])
    d = {
        "applicant_id": row["applicant_id"], "architecture": arch, "case_category": gt["category"],
        "status": row["status"],
        "gt_eligible": gt["ground_truth"], "pred_eligible": pred_elig,
        "gt_effective_date": gt["ground_truth_effective_date"], "pred_effective_date": row["predicted_effective_date"] or None,
        "eligibility_correct": pred_elig == gt["ground_truth"],
        "date_correct": pred_date == gt_date,
        "date_error_months": months_between(gt_date, pred_date) if pred_date else None,
        "internally_consistent": None, "month_consistent": None,
        "phd_date_correct": None, "interruptions_correct": None, "attributes_correct": None,
        "facts_correct": None, "replayable": None,
    }
    if row["status"] == "ok" and arch in "AB" and pred_date and pred_elig is not None:
        d["internally_consistent"] = (pred_date >= THRESHOLD) == pred_elig
    if row["status"] == "ok" and arch == "B":
        phd = date.fromisoformat(gt["phd_award_date"])
        d["month_consistent"] = add_months(phd, parsed["claimable_interruption_months"]) == pred_date
    if row["status"] == "ok" and arch == "C":
        facts = parsed["extracted_facts"]
        d["phd_date_correct"], d["interruptions_correct"], d["attributes_correct"] = check_facts(facts, gt)
        d["facts_correct"] = d["phd_date_correct"] and d["interruptions_correct"] and d["attributes_correct"]
        replay = assess(ApplicantFacts.model_validate(facts))
        d["replayable"] = (replay.eligible == pred_elig
                           and (replay.effective_date.isoformat() if replay.effective_date else None) == d["pred_effective_date"]
                           and replay.trace == parsed["rule_engine"]["trace"])
    d["error_category"] = categorise(d, parsed)
    return d


def categorise(d, parsed):
    if d["eligibility_correct"] and d["date_correct"]:
        return None
    if d["status"] != "ok":
        return f"{d['status']}"
    if d["architecture"] == "C":
        if d["pred_eligible"] is None:
            return "C: insufficient facts extracted (engine undetermined)"
        if not d["phd_date_correct"]:
            return "C: PhD date extraction error"
        if not d["interruptions_correct"]:
            return "C: interruption type/duration extraction error"
        if not d["attributes_correct"]:
            return "C: interruption attribute extraction error"
        return "C: rule engine error (facts correct, outcome wrong)"
    if d["pred_effective_date"] is None:
        return "no effective date given"
    if not d["date_correct"]:
        direction = "over" if d["date_error_months"] > 0 else "under"
        cat = f"effective date {direction}-extended ({d['date_error_months']:+d} months)"
        if d["internally_consistent"] is False:
            cat += "; decision inconsistent with own date"
        return cat
    if d["internally_consistent"] is False:
        return "correct date, decision inconsistent with own date"
    return "threshold comparison error"


def rate(values):
    vals = [v for v in values if v is not None]
    return round(sum(vals) / len(vals), 3) if vals else None


def summarise(details):
    rows = []
    for arch in "ABC":
        ds = [d for d in details if d["architecture"] == arch]
        n = len(ds)
        rows.append({
            "architecture": arch,
            "n": n,
            "calls_ok": sum(d["status"] == "ok" for d in ds),
            "api_errors": sum(d["status"] == "api_error" for d in ds),
            "format_validity": round(sum(d["status"] == "ok" for d in ds) / n, 3),
            "eligibility_correct": sum(d["eligibility_correct"] for d in ds),
            "eligibility_accuracy": round(sum(d["eligibility_correct"] for d in ds) / n, 3),
            "effective_date_correct": sum(d["date_correct"] for d in ds),
            "effective_date_accuracy": round(sum(d["date_correct"] for d in ds) / n, 3),
            "internal_consistency": rate(d["internally_consistent"] for d in ds),
            "month_consistency": rate(d["month_consistent"] for d in ds),
            "phd_date_accuracy": rate(d["phd_date_correct"] for d in ds),
            "interruption_accuracy": rate(d["interruptions_correct"] for d in ds),
            "attribute_accuracy": rate(d["attributes_correct"] for d in ds),
            "fact_extraction_accuracy": rate(d["facts_correct"] for d in ds),
            "replayable_rate": rate(d["replayable"] for d in ds),
            "trace_type": TRACE_TYPE[arch],
            "disagreements": sum(d["error_category"] is not None for d in ds),
        })
    return rows


def error_pattern(details, rows, gt):
    """One row per applicant: pass/fail of every checkable stage in each architecture's pipeline."""
    by_key = {(d["applicant_id"], d["architecture"]): d for d in details}
    raw_b = {r["applicant_id"]: r for r in rows if r["architecture"] == "B"}
    matrix = []
    for cid in sorted(gt):
        a, b, c = by_key[(cid, "A")], by_key[(cid, "B")], by_key[(cid, "C")]
        b_parsed = json.loads(raw_b[cid]["parsed_response"]) if raw_b[cid]["parsed_response"] else None
        b_months = b_parsed["claimable_interruption_months"] if b_parsed else None
        matrix.append({
            "applicant_id": cid, "case_category": gt[cid]["category"],
            "A_eligibility": a["eligibility_correct"], "A_date": a["date_correct"],
            "B_schema_valid": b["status"] == "ok",
            "B_claimable_months": b_months == sum(i["claimable_months"] for i in gt[cid]["interruptions"]),
            "B_eligibility": b["eligibility_correct"], "B_date": b["date_correct"],
            "C_schema_valid": c["status"] == "ok", "C_facts_extracted": c["facts_correct"] is True,
            "C_rule_application": c["replayable"] is True,
            "C_eligibility": c["eligibility_correct"], "C_date": c["date_correct"],
        })
    return matrix


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id")
    args = parser.parse_args()

    raw = list(csv.DictReader(RAW.open(encoding="utf-8")))
    run_id = args.run_id or [r for r in raw if r["provider"] == "groq"][-1]["run_id"]
    rows = [r for r in raw if r["run_id"] == run_id]
    keys = Counter((r["applicant_id"], r["architecture"]) for r in rows)
    if len(rows) != 60 or len(keys) != 60:
        raise SystemExit(f"Run {run_id} has {len(rows)} rows ({len(keys)} unique); expected 60.")

    gt = {g["id"]: g for g in json.loads(GROUND_TRUTH.read_text(encoding="utf-8"))}
    details = [evaluate_row(r, gt[r["applicant_id"]]) for r in rows]
    summary = summarise(details)
    for s in summary:
        s["run_id"], s["model"] = run_id, rows[0]["model"]

    write_csv(DETAILS, details)
    write_csv(SUMMARY, summary)
    errors = [{k: d[k] for k in ("architecture", "applicant_id", "case_category", "gt_eligible", "pred_eligible",
                                 "gt_effective_date", "pred_effective_date", "date_error_months", "error_category")}
              for d in sorted(details, key=lambda d: (d["architecture"], d["applicant_id"])) if d["error_category"]]
    if errors:
        write_csv(ERRORS, errors)
    else:
        ERRORS.write_text("no disagreements\n", encoding="utf-8")
    write_csv(MATRIX, error_pattern(details, rows, gt))

    print(f"Run {run_id} ({rows[0]['model']}), {len(rows)} predictions")
    for s in summary:
        print(f"  {s['architecture']}: eligibility {s['eligibility_correct']}/{s['n']}, "
              f"date {s['effective_date_correct']}/{s['n']}, format valid {s['calls_ok']}/{s['n']}")
    print(f"Disagreements: {len(errors)} -> {ERRORS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
