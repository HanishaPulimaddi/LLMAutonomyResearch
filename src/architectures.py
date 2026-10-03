"""The three experimental architectures.

Each entry point receives one applicant ({"id", "profile"}) and an LLMClient. Only the profile text
is placed in the prompt. Nothing here reads ground_truth.json.

    A  run_architecture_a: profile -> LLM -> free-text decision
    B  run_architecture_b: profile -> LLM -> JSON -> schema validation -> decision
    C  run_architecture_c: profile -> LLM -> extracted facts (JSON) -> rules.assess -> decision
"""
import re
from dataclasses import dataclass
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, ValidationError

import prompts
from llm_client import LLMClient
from prompts import Prompt
from rules import ApplicantFacts, assess


@dataclass
class ArchitectureResult:
    architecture: str
    prompt: Prompt
    raw_response: str | None
    parsed_response: dict | None
    predicted_eligible: bool | None
    predicted_effective_date: str | None
    status: str  # "ok", "api_error", "parse_error" or "validation_error"
    error: str | None = None


class DecisionOutput(BaseModel):
    """Architecture B output schema."""
    model_config = ConfigDict(extra="forbid")
    eligible: bool
    effective_eligibility_date: date
    claimable_interruption_months: int = Field(ge=0)
    reasoning: str


BUILD_PROMPT = {"A": prompts.architecture_a, "B": prompts.architecture_b, "C": prompts.architecture_c}


def _call(architecture, prompt, client):
    try:
        return client.complete(prompt), None
    except Exception as e:  # recorded, not raised, so one failed call does not stop a run
        return None, ArchitectureResult(architecture, prompt, None, None, None, None, "api_error", repr(e))


def run_architecture_a(applicant, client: LLMClient, prompt=None):
    prompt = prompt or prompts.architecture_a(applicant["profile"])
    raw, failed = _call("A", prompt, client)
    if failed:
        return failed
    decisions = re.findall(r"DECISION:\s*(ELIGIBLE|INELIGIBLE)", raw, re.I)
    dates = re.findall(r"EFFECTIVE_DATE:\s*(\d{4}-\d{2}-\d{2})", raw, re.I)
    if not decisions:
        return ArchitectureResult("A", prompt, raw, None, None, None, "parse_error", "no DECISION line found")
    parsed = {"decision": decisions[-1].upper(), "effective_date": dates[-1] if dates else None}
    return ArchitectureResult("A", prompt, raw, parsed, parsed["decision"] == "ELIGIBLE", parsed["effective_date"], "ok")


def run_architecture_b(applicant, client: LLMClient, prompt=None):
    prompt = prompt or prompts.architecture_b(applicant["profile"])
    raw, failed = _call("B", prompt, client)
    if failed:
        return failed
    try:
        out = DecisionOutput.model_validate_json(raw)
    except ValidationError as e:
        return ArchitectureResult("B", prompt, raw, None, None, None, "validation_error", str(e))
    parsed = out.model_dump(mode="json")
    return ArchitectureResult("B", prompt, raw, parsed, out.eligible, parsed["effective_eligibility_date"], "ok")


def run_architecture_c(applicant, client: LLMClient, prompt=None):
    prompt = prompt or prompts.architecture_c(applicant["profile"])
    raw, failed = _call("C", prompt, client)
    if failed:
        return failed
    try:
        facts = ApplicantFacts.model_validate_json(raw)
    except ValidationError as e:
        return ArchitectureResult("C", prompt, raw, None, None, None, "validation_error", str(e))
    result = assess(facts)
    parsed = {
        "extracted_facts": facts.model_dump(mode="json"),
        "rule_engine": {
            "eligible": result.eligible,
            "effective_date": result.effective_date.isoformat() if result.effective_date else None,
            "claimable_months": result.claimable_months,
            "trace": result.trace,
        },
    }
    return ArchitectureResult("C", prompt, raw, parsed, result.eligible, parsed["rule_engine"]["effective_date"], "ok")


RUN = {"A": run_architecture_a, "B": run_architecture_b, "C": run_architecture_c}
