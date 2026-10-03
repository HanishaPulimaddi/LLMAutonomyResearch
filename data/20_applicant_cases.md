# DECRA Synthetic Applicant Cases

## A01 — clearly_eligible

Dr Maya Chen was awarded her PhD in Computational Biology on 15 July 2023. She has had no career interruptions since the PhD was awarded.

**Ground truth:** eligible  
**Effective date:** 2023-07-15  
**Reason:** PhD award date is after the 1 March 2021 threshold.

**Interruptions:** `[]`

---

## A02 — boundary_exact

Dr Liam Patel was awarded his PhD on 1 March 2021. He has had no career interruptions since the PhD was awarded.

**Ground truth:** eligible  
**Effective date:** 2021-03-01  
**Reason:** PhD award date falls exactly on the threshold.

**Interruptions:** `[]`

---

## A03 — boundary_before

Dr Sofia Nguyen was awarded her PhD on 28 February 2021. She has had no career interruptions since the PhD was awarded.

**Ground truth:** ineligible  
**Effective date:** 2021-02-28  
**Reason:** PhD award date is one day before the threshold and no extension applies.

**Interruptions:** `[]`

---

## A04 — single_interruption_boundary

Dr Noah Williams was awarded his PhD on 1 September 2020. After the PhD, he had a six-month period of unemployment that did not overlap with any other interruption.

**Ground truth:** eligible  
**Effective date:** 2021-03-01  
**Reason:** The six-month allowable interruption moves the effective date to the threshold.

**Interruptions:** `[{"type": "unemployment", "stated_months": 6, "claimable_months": 6}]`

---

## A05 — non_research_concurrent_condition

Dr Aisha Rahman was awarded her PhD on 1 September 2020. After conferral, she worked for five months in a non-research position, but continued her research employment concurrently throughout that period.

**Ground truth:** ineligible  
**Effective date:** 2020-09-01  
**Reason:** The non-research-position category applies only when the position is not concurrent with research employment, so this period is not claimable.

**Interruptions:** `[{"type": "non_research_position", "stated_months": 5, "claimable_months": 0, "concurrent_with_research": true}]`

---

## A06 — medical_condition

Dr Ethan Brooks was awarded his PhD on 15 January 2020. He subsequently had a 14-month period of recovery from a medical condition. The interruption occurred after PhD conferral and did not overlap with another interruption.

**Ground truth:** eligible  
**Effective date:** 2021-03-15  
**Reason:** A 14-month allowable medical interruption moves the effective date beyond the threshold.

**Interruptions:** `[{"type": "medical_condition", "stated_months": 14, "claimable_months": 14}]`

---

## A07 — caring_responsibilities_boundary

Dr Priya Nair was awarded her PhD on 1 May 2020. She subsequently had nine months of caring responsibilities for a dependent family member. The interruption was after PhD conferral and did not overlap with another interruption.

**Ground truth:** ineligible  
**Effective date:** 2021-02-01  
**Reason:** Nine months of interruption leaves the effective date before the threshold.

**Interruptions:** `[{"type": "caring_responsibilities", "stated_months": 9, "claimable_months": 9}]`

---

## A08 — caring_responsibilities_boundary_exact

Dr Daniel Kim was awarded his PhD on 1 May 2020. He subsequently had ten months of caring responsibilities. The interruption was after PhD conferral and did not overlap with another interruption.

**Ground truth:** eligible  
**Effective date:** 2021-03-01  
**Reason:** Ten months of allowable interruption moves the effective date exactly to the threshold.

**Interruptions:** `[{"type": "caring_responsibilities", "stated_months": 10, "claimable_months": 10}]`

---

## A09 — multiple_non_overlapping

Dr Olivia Smith was awarded her PhD on 15 August 2019. After conferral, she had six months of parental leave followed later by twelve months in a non-research position that was not concurrent with research employment. The periods did not overlap.

**Ground truth:** ineligible  
**Effective date:** 2021-02-15  
**Reason:** The combined 18 months of non-overlapping allowable interruptions still leaves the effective date before the threshold.

**Interruptions:** `[{"type": "parental_leave", "stated_months": 6, "claimable_months": 6}, {"type": "non_research_position", "stated_months": 12, "claimable_months": 12, "concurrent_with_research": false}]`

---

## A10 — multiple_non_overlapping_exact

Dr James Wilson was awarded his PhD on 15 August 2019. After conferral, he had seven months of parental leave followed later by twelve months in a non-research position that was not concurrent with research employment. The periods did not overlap.

**Ground truth:** eligible  
**Effective date:** 2021-03-15  
**Reason:** The combined 19 months of allowable interruptions moves the effective date beyond the threshold.

**Interruptions:** `[{"type": "parental_leave", "stated_months": 7, "claimable_months": 7}, {"type": "non_research_position", "stated_months": 12, "claimable_months": 12, "concurrent_with_research": false}]`

---

## A11 — international_relocation_cap

Dr Sara Ahmed was awarded her PhD on 1 August 2020. After being awarded her PhD, she relocated internationally for work for five months.

**Ground truth:** ineligible  
**Effective date:** 2020-11-01  
**Reason:** The five-month relocation is capped at three claimable months.

**Interruptions:** `[{"type": "international_relocation", "stated_months": 5, "claimable_months": 3}]`

---

## A12 — two_relocations

Dr Lucas Martin was awarded his PhD on 1 June 2020. He then had two separate international relocations, each lasting three months. The relocations did not overlap.

**Ground truth:** ineligible  
**Effective date:** 2020-12-01  
**Reason:** Two relocations permit up to six months in total, leaving the effective date before the threshold.

**Interruptions:** `[{"type": "international_relocation", "stated_months": 3, "claimable_months": 3}, {"type": "international_relocation", "stated_months": 3, "claimable_months": 3}]`

---

## A13 — primary_carer

Dr Emily Jones was awarded her PhD on 1 January 2020. She was subsequently the primary carer of one dependent child for 24 months. She took parental leave for that child during this period.

**Ground truth:** eligible  
**Effective date:** 2022-01-01  
**Reason:** One dependent child permits up to two years, inclusive of parental leave.

**Interruptions:** `[{"type": "primary_carer", "stated_months": 24, "claimable_months": 24, "dependent_children": 1, "includes_parental_leave_months": null}]`

---

## A14 — primary_carer_inclusive_parental_leave

Dr Grace Lee was awarded her PhD on 1 January 2020. She was subsequently the primary carer of one dependent child for 24 months and took 12 months of parental leave during that period.

**Ground truth:** eligible  
**Effective date:** 2022-01-01  
**Reason:** The total primary-carer allowance is two years; the 12 months of parental leave must not be double-counted.

**Interruptions:** `[{"type": "primary_carer", "stated_months": 24, "claimable_months": 24, "dependent_children": 1, "includes_parental_leave_months": 12}]`

---

## A15 — multiple_children

Dr Hannah Taylor was awarded her PhD on 1 March 2019. She was subsequently the primary carer of her first dependent child for 24 months, followed by a further 24 months as the primary carer of her second dependent child.

**Ground truth:** eligible  
**Effective date:** 2023-03-01  
**Reason:** Two dependent children permit up to four years in total under the primary-carer provision.

**Interruptions:** `[{"type": "primary_carer", "stated_months": 24, "claimable_months": 24, "dependent_children": 1}, {"type": "primary_carer", "stated_months": 24, "claimable_months": 24, "dependent_children": 1}]`

---

## A16 — primary_carer_exact_threshold

Dr Michael Chen was awarded his PhD on 1 March 2019. He was subsequently the primary carer of one dependent child for 24 months, and had no other career interruptions.

**Ground truth:** eligible  
**Effective date:** 2021-03-01  
**Reason:** One two-year primary-carer allowance moves the effective date exactly to the threshold.

**Interruptions:** `[{"type": "primary_carer", "stated_months": 24, "claimable_months": 24, "dependent_children": 1}]`

---

## A17 — overlap_should_not_double_count

Dr Isabella Rossi was awarded her PhD on 1 March 2019. She was subsequently the primary carer of one dependent child for 24 months and took 18 months of parental leave during that same period. The parental leave fell entirely within the primary-carer period.

**Ground truth:** eligible  
**Effective date:** 2021-03-01  
**Reason:** The 18 months of parental leave cannot be added to the two-year primary-carer allowance.

**Interruptions:** `[{"type": "primary_carer", "stated_months": 24, "claimable_months": 24, "dependent_children": 1, "includes_parental_leave_months": 18}]`

---

## A18 — non_research_position

Dr Noah Garcia was awarded his PhD on 1 March 2020. After conferral, he spent 12 months in a non-research position that was not concurrent with research employment.

**Ground truth:** eligible  
**Effective date:** 2021-03-01  
**Reason:** The 12-month allowable non-research period moves the effective date to the threshold.

**Interruptions:** `[{"type": "non_research_position", "stated_months": 12, "claimable_months": 12, "concurrent_with_research": false}]`

---

## A19 — limited_access_to_facilities

Dr Zoe Brown was awarded her PhD on 1 July 2020. After conferral, her research facility was inaccessible for eight months because of a workplace interruption, and she had limited or no access to the facilities and resources required for her research during that period.

**Ground truth:** eligible  
**Effective date:** 2021-03-01  
**Reason:** The eight-month post-PhD interruption is an eligible limited-access interruption and moves the effective date to the threshold.

**Interruptions:** `[{"type": "limited_access_to_facilities", "stated_months": 8, "claimable_months": 8}]`

---

## A20 — disaster_recovery

Dr Adam Wilson was awarded his PhD on 1 March 2020. Following a major disaster affecting his research location, he spent 11 months on disaster management and recovery activities. The interruption did not overlap with another interruption.

**Ground truth:** ineligible  
**Effective date:** 2021-02-01  
**Reason:** The 11-month allowable interruption leaves the effective date one month before the threshold.

**Interruptions:** `[{"type": "disaster_management_and_recovery", "stated_months": 11, "claimable_months": 11}]`

---

