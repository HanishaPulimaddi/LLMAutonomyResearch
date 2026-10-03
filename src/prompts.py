"""Prompt templates for the three architectures.

A prompt may contain only: the eligibility rule, one applicant profile, architecture-specific
instructions, and the required output format. It never receives an applicant ID, category,
or anything from ground_truth.json.
"""
from dataclasses import dataclass
from pathlib import Path

PROMPT_VERSION = "v1"
RULE_PATH = Path(__file__).resolve().parent.parent / "data" / "eligibility_rule.md"
ELIGIBILITY_RULE = RULE_PATH.read_text(encoding="utf-8").strip()

# Static guard: these strings must never reach a model.
FORBIDDEN_IN_PROMPT = ["ground_truth", "ground truth"]


@dataclass(frozen=True)
class Prompt:
    name: str
    version: str
    system: str
    user: str
    json_mode: bool = False


def _check(prompt):
    text = (prompt.system + "\n" + prompt.user).lower()
    hits = [s for s in FORBIDDEN_IN_PROMPT if s in text]
    if hits:
        raise ValueError(f"Prompt {prompt.name} contains forbidden content: {hits}")
    return prompt


ASSESSOR_SYSTEM = "You are an assessor of research-funding eligibility. Apply the eligibility rule exactly as written."

ARCH_A_INSTRUCTIONS = """Decide whether the applicant is eligible and determine their effective PhD award date.
Explain your reasoning briefly, then finish your answer with exactly these two lines:
DECISION: ELIGIBLE or INELIGIBLE
EFFECTIVE_DATE: YYYY-MM-DD"""

ARCH_B_INSTRUCTIONS = """Decide whether the applicant is eligible and determine their effective PhD award date.
Respond with a single JSON object only, with exactly these fields:
{
  "eligible": true or false,
  "effective_eligibility_date": "YYYY-MM-DD",
  "claimable_interruption_months": integer,
  "reasoning": "short explanation"
}"""

ARCH_C_SYSTEM = ("You are an information extraction component. Do not determine eligibility. "
                 "Do not calculate the effective eligibility date. Do not decide whether the applicant is eligible.")

ARCH_C_INSTRUCTIONS = """Extract the applicant's facts from the profile. Report only facts stated in the profile; use null when a fact is not stated.
Respond with a single JSON object only, with exactly these fields:
{
  "phd_award_date": "YYYY-MM-DD",
  "interruptions": [
    {
      "type": one of "unemployment", "medical_condition", "caring_responsibilities", "parental_leave", "primary_carer", "non_research_position", "international_relocation", "limited_access_to_facilities", "disaster_management_and_recovery", "other",
      "duration_months": integer or null,
      "after_phd": true, false or null (did the period occur after the PhD was awarded?),
      "concurrent_with_research_employment": true, false or null (for non-research positions: was research employment continued at the same time?),
      "dependent_children": integer or null (for primary-carer periods: number of dependent children the period covers),
      "within_primary_carer_period": true, false or null (for parental leave: did it fall within a period in which the applicant was a primary carer?)
    }
  ]
}
List each separate period as its own entry. Use an empty list if the profile states there were no career interruptions."""


def _user(profile, instructions, include_rule=True):
    parts = [f"Eligibility rule:\n{ELIGIBILITY_RULE}"] if include_rule else []
    parts += [f"Applicant profile:\n{profile}", instructions]
    return "\n\n".join(parts)


def architecture_a(profile):
    return _check(Prompt("arch_a_llm_only", PROMPT_VERSION, ASSESSOR_SYSTEM,
                         _user(profile, ARCH_A_INSTRUCTIONS)))


def architecture_b(profile):
    return _check(Prompt("arch_b_llm_validation", PROMPT_VERSION, ASSESSOR_SYSTEM,
                         _user(profile, ARCH_B_INSTRUCTIONS), json_mode=True))


def architecture_c(profile):
    # The rule is deliberately withheld: the extractor must not apply it.
    return _check(Prompt("arch_c_extraction", PROMPT_VERSION, ARCH_C_SYSTEM,
                         _user(profile, ARCH_C_INSTRUCTIONS, include_rule=False), json_mode=True))
