def register_change_detection_templates(manager):
    manager.register(
        agent="change_detection_agent",
        name="field_comparison_zero_shot",
        version="v2",
        template="""You are a strict QA underwriting data parser. Your sole job is to compare two JSON objects representing property data across two years and detect EVERY single change, no matter how small.

Prior Year JSON:
{prior_year_json}

Current Year JSON:
{current_year_json}

RULES:
1. Traverse EVERY nested dictionary recursively (e.g., `construction`, `hazards`, `occupancy`, `protection`, `loss`, `compliance`).
2. If a value has changed, add it to your output.
3. If a key exists in one year but is missing in the other, treat it as a change.
4. Output MUST be a valid JSON array of objects. Do not include markdown blocks or any other text.
5. If there are NO changes, output `[]`.

Format each change exactly like this:
[
  {{
    "field_path": "occupancy.vacancy_rate_pct",
    "prior_value": 40,
    "current_value": 100
  }},
  {{
    "field_path": "protection.sprinkler_status",
    "prior_value": "partial",
    "current_value": "none"
  }}
]
"""
    )

    manager.register(
        agent="change_detection_agent",
        name="change_severity_few_shot",
        version="v1",
        template="""Classify the severity of the following property data changes.
Property Type: {property_type}
Changes:
{raw_changes}

Severity Levels:
- MATERIAL: Directly affects risk score or renewal terms.
- NOTABLE: Worth reviewing but may not change terms.
- COSMETIC: No risk impact.

Examples:
- Material: flood_zone change AE->VE, risk_category_affected: NatCat, risk_impact: Significant increase in flood risk.
- Material: sprinkler_status full_wet->none, risk_category_affected: Fire, risk_impact: Significant increase in fire hazard.
- Notable: tiv_change +8%, risk_category_affected: General, risk_impact: Moderate increase in total value.
- Notable: roof_age_years crossing 15 years, risk_category_affected: Building, risk_impact: Increased probability of roof failure.
- Cosmetic: contact_email change, risk_category_affected: Admin, risk_impact: None.
- Cosmetic: address_format change, risk_category_affected: Admin, risk_impact: None.

Return a JSON list of objects with fields: `field_path`, `prior_value`, `current_value`, `severity`, `risk_category_affected`, `risk_impact`, `reasoning`."""
    )
