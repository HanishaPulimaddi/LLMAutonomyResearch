"""Pre-call leakage check for the smoke test.

This module reads ground_truth.json only to confirm that none of an applicant's answer values appear
in a built prompt. It returns findings; it never passes ground-truth data into a prompt or a client.
"""
import json
from datetime import date
from pathlib import Path

from prompts import ELIGIBILITY_RULE
from rules import InterruptionType

GROUND_TRUTH = Path(__file__).resolve().parent.parent / "data" / "ground_truth.json"
# Category names that are also legitimate interruption types in the Architecture C schema.
SCHEMA_TERMS = {t.value for t in InterruptionType}


def _prose(iso):
    d = date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%B')} {d.year}"


def find_leaks(applicant_id, prompt):
    record = next(r for r in json.loads(GROUND_TRUTH.read_text(encoding="utf-8")) if r["id"] == applicant_id)
    # The rule text is excluded: it legitimately contains the threshold date (1 March 2021), which is
    # also the expected effective date for several applicants.
    text = prompt.system + "\n" + prompt.user.replace(ELIGIBILITY_RULE, "")
    checks = {
        "ground-truth field name": "ground_truth" in text.lower(),
        "applicant ID": applicant_id in text,
        "category label": record["category"] not in SCHEMA_TERMS and record["category"] in text,
        "ground-truth reason": record["reason"] in text,
        "effective date (ISO)": record["ground_truth_effective_date"] in text,
    }
    # The prose effective date is a leak only when it differs from the PhD award date stated in the profile.
    if record["ground_truth_effective_date"] != record["phd_award_date"]:
        checks["effective date (prose)"] = _prose(record["ground_truth_effective_date"]) in text
    return [name for name, leaked in checks.items() if leaked]
