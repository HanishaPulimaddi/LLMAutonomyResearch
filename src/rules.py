"""Deterministic eligibility rule engine (Architecture C).

Implements data/eligibility_rule.md. Takes only extracted applicant facts; never reads ground truth.

Limitation: interruptions carry durations but no dates, so general overlap between periods cannot be
detected. The only overlap handled is parental leave marked as within a primary-carer period.
"""
import calendar
from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

THRESHOLD = date(2021, 3, 1)
RELOCATION_CAP_MONTHS = 3
PRIMARY_CARER_MONTHS_PER_CHILD = 24


class InterruptionType(str, Enum):
    unemployment = "unemployment"
    medical_condition = "medical_condition"
    caring_responsibilities = "caring_responsibilities"
    parental_leave = "parental_leave"
    primary_carer = "primary_carer"
    non_research_position = "non_research_position"
    international_relocation = "international_relocation"
    limited_access_to_facilities = "limited_access_to_facilities"
    disaster_management_and_recovery = "disaster_management_and_recovery"
    other = "other"


class Interruption(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: InterruptionType
    duration_months: int | None = Field(default=None, ge=0)
    after_phd: bool | None = None
    concurrent_with_research_employment: bool | None = None
    dependent_children: int | None = Field(default=None, ge=0)
    within_primary_carer_period: bool | None = None


class ApplicantFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phd_award_date: date
    interruptions: list[Interruption] = []


@dataclass
class Assessment:
    eligible: bool | None
    effective_date: date | None
    claimable_months: int | None
    trace: list[str] = field(default_factory=list)


def add_months(d, months):
    y, m = divmod(d.month - 1 + months, 12)
    year, month = d.year + y, m + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def claimable(i):
    """Return (claimable months, reason). Months is None when the facts are insufficient to decide."""
    if i.after_phd is not True:
        return 0, "not established as after PhD award; not counted"
    if i.type is InterruptionType.other:
        return 0, "not an allowable interruption category; not counted"
    if i.type is InterruptionType.parental_leave and i.within_primary_carer_period:
        return 0, "parental leave within primary-carer period; not added"
    if i.type is InterruptionType.non_research_position:
        if i.concurrent_with_research_employment is None:
            return None, "concurrency with research employment not stated; cannot decide"
        if i.concurrent_with_research_employment:
            return 0, "concurrent with research employment; not counted"
    if i.duration_months is None:
        return None, "duration not stated; cannot decide"
    if i.type is InterruptionType.international_relocation:
        months = min(i.duration_months, RELOCATION_CAP_MONTHS)
        return months, f"capped at {RELOCATION_CAP_MONTHS} months per relocation" if months < i.duration_months else "within cap"
    if i.type is InterruptionType.primary_carer:
        if i.dependent_children is None:
            return None, "number of dependent children not stated; cannot decide"
        cap = PRIMARY_CARER_MONTHS_PER_CHILD * i.dependent_children
        months = min(i.duration_months, cap)
        return months, f"capped at {cap} months for {i.dependent_children} child(ren)" if months < i.duration_months else f"within {cap}-month allowance"
    return i.duration_months, "allowable; counted in full"


def assess(facts: ApplicantFacts) -> Assessment:
    total = 0
    trace = [f"PhD award date: {facts.phd_award_date.isoformat()}"]
    if not facts.interruptions:
        trace.append("No career interruptions extracted")
    for n, i in enumerate(facts.interruptions, 1):
        months, reason = claimable(i)
        trace.append(f"Interruption {n} ({i.type.value}, {i.duration_months} months stated): "
                     f"{reason} -> {months if months is not None else 'undetermined'} claimable")
        if months is None:
            trace.append("Result: undetermined (insufficient facts)")
            return Assessment(None, None, None, trace)
        total += months
    effective = add_months(facts.phd_award_date, total)
    eligible = effective >= THRESHOLD
    trace.append(f"Total claimable months: {total}")
    trace.append(f"Effective date: {facts.phd_award_date.isoformat()} + {total} months = {effective.isoformat()}")
    trace.append(f"{effective.isoformat()} {'>=' if eligible else '<'} threshold {THRESHOLD.isoformat()}: "
                 f"{'ELIGIBLE' if eligible else 'INELIGIBLE'}")
    return Assessment(eligible, effective, total, trace)
