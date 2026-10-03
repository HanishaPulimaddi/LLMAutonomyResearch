"""Regenerate data/applicants.json and data/ground_truth.json from data/20_applicant_cases.md.

The Markdown file is the source dataset. Each case has the form:

    ## A01 — category_name

    <applicant profile paragraph>

    **Ground truth:** eligible | ineligible
    **Effective date:** YYYY-MM-DD
    **Reason:** ...

    **Interruptions:** `[{"type": ..., "stated_months": ..., "claimable_months": ..., ...}]`

applicants.json (LLM input) receives only `id` and `profile`.
ground_truth.json (evaluation only) receives everything else and must never enter a prompt.

Usage:
    python src/prepare_data.py

Exits with status 1 if any validation check fails.
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

# THRESHOLD is used only to check that each case's stated date and label agree with each other.
from rules import THRESHOLD, add_months

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SOURCE = DATA / "20_applicant_cases.md"
APPLICANTS = DATA / "applicants.json"
GROUND_TRUTH = DATA / "ground_truth.json"

EXPECTED_IDS = [f"A{i:02d}" for i in range(1, 21)]

# Strings that must not appear anywhere in applicants.json.
BANNED_STRINGS = ["ground_truth", "ground_truth_effective_date", "eligible", "eligibility date",
                  "category", "expected", "answer"]
# Answer or rule-explanation wording that must not appear in profile text.
LEAK_PATTERN = re.compile(
    r"therefore|eligib|effective|threshold|\bARC\b|\brule\b|allowance|claim|\bcap(ped)?\b|"
    r"up to|per (dependent )?child|double[- ]count|included within|rather than added|qualifying",
    re.I,
)

MONTHS = {m: i for i, m in enumerate(
    "January February March April May June July August September October November December".split(), 1)}


def parse_cases(md):
    cases = []
    for block in re.split(r"^## ", md, flags=re.M)[1:]:
        head, body = block.split("\n", 1)
        case_id, category = [s.strip() for s in head.split("—")]
        profile = body.split("**Ground truth:**")[0].strip()
        label = re.search(r"\*\*Ground truth:\*\*\s*(\w+)", body).group(1)
        effective = re.search(r"\*\*Effective date:\*\*\s*(\S+)", body).group(1)
        reason = re.search(r"\*\*Reason:\*\*\s*(.+)", body).group(1).strip()
        interruptions = json.loads(re.search(r"\*\*Interruptions:\*\*\s*`(.+)`", body).group(1))
        day, month, year = re.search(r"awarded (?:his|her) PhD.*? on (\d+) (\w+) (\d{4})", profile).groups()
        cases.append({
            "id": case_id,
            "category": category,
            "profile": profile,
            "phd_award_date": date(int(year), MONTHS[month], int(day)).isoformat(),
            "interruptions": interruptions,
            "ground_truth_effective_date": effective,
            "ground_truth": {"eligible": True, "ineligible": False}[label],
            "reason": reason,
        })
    return cases


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def validate(md):
    """Re-read the written files and check counts, IDs, traceability, leakage and arithmetic."""
    raw_applicants = APPLICANTS.read_text(encoding="utf-8")
    applicants = json.loads(raw_applicants)
    truth = json.loads(GROUND_TRUTH.read_text(encoding="utf-8"))
    a_ids = [a["id"] for a in applicants]
    g_ids = [g["id"] for g in truth]

    extra_keys = sorted({k for a in applicants for k in a} - {"id", "profile"})
    banned_hits = [s for s in BANNED_STRINGS if s in raw_applicants.lower()]
    leaks = {a["id"]: LEAK_PATTERN.findall(a["profile"]) for a in applicants}
    leaks = {k: v for k, v in leaks.items() if v}
    untraceable = [a["id"] for a in applicants if a["profile"] not in md]
    missing = len(set(EXPECTED_IDS) - set(a_ids)) + len(set(EXPECTED_IDS) - set(g_ids))
    duplicates = (len(a_ids) - len(set(a_ids))) + (len(g_ids) - len(set(g_ids)))
    inconsistent = []
    for g in truth:
        months = sum(i["claimable_months"] for i in g["interruptions"])
        computed = add_months(date.fromisoformat(g["phd_award_date"]), months)
        if computed.isoformat() != g["ground_truth_effective_date"] or (computed >= THRESHOLD) != g["ground_truth"]:
            inconsistent.append(g["id"])

    ids_ok = a_ids == EXPECTED_IDS and g_ids == EXPECTED_IDS
    print(f"Applicants: {len(applicants)}")
    print(f"Ground-truth records: {len(truth)}")
    print(f"IDs matched: {'A01–A20' if ids_ok else 'NO'}")
    print(f"Missing records: {missing}")
    print(f"Duplicate records: {duplicates}")
    print(f"applicants.json keys: {sorted({k for a in applicants for k in a})}")
    print(f"Profiles traceable verbatim to Markdown: {len(applicants) - len(untraceable)}/{len(applicants)}"
          + (f" {untraceable}" if untraceable else ""))
    print(f"Banned strings in applicants.json: {banned_hits or 'none'}")
    print(f"Answer/rule wording in profile text: {leaks or 'none'}")
    print(f"PhD date + claimable months vs stated date and label: "
          f"{'all consistent' if not inconsistent else inconsistent}")

    ok = ids_ok and not (extra_keys or banned_hits or leaks or untraceable or missing or duplicates or inconsistent)
    print(f"Ground truth exposed to LLM: {'NO' if ok else 'CHECK FAILED'}")
    return ok


def main():
    md = SOURCE.read_text(encoding="utf-8")
    cases = parse_cases(md)
    write_json(APPLICANTS, [{"id": c["id"], "profile": c["profile"]} for c in cases])
    write_json(GROUND_TRUTH, [{k: v for k, v in c.items() if k != "profile"} for c in cases])
    sys.exit(0 if validate(md) else 1)


if __name__ == "__main__":
    main()
