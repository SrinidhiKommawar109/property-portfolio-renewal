def register_renewal_recommendation_templates(manager):
    classification_template = """Recommend a renewal decision based on property changes and risk re-evaluation.

Property Summary: {property_summary}
Change Summary: {change_summary}
Risk Delta Summary: {risk_delta_summary}
Overall Risk Trend: {overall_risk_trend}

HARD GUARDRAILS (PRIORITIZE THESE):
{guardrails}

Decision Categories:
1. RENEW_AS_IS: Guardrail is ELIGIBLE_FOR_STP AND Overall Risk Delta is <= 0.0.
2. RENEW_WITH_ADJUSTMENTS: Guardrail suggests adjustments OR Risk Delta is between 0.1 and 1.5.
3. REFER_TO_SENIOR: Guardrail is MANDATORY_REFERRAL OR Risk Delta > 1.5.
4. NON_RENEW: Guardrail is MANDATORY_REFERRAL AND Risk Delta > 3.0.

NEVER base your decision on the raw count of material changes. 10 minor changes can be safe, while 1 major change can require escalation. Rely entirely on the Guardrail and the Risk Delta.

Return JSON only:
{{
  "decision": "string",
  "confidence": "HIGH | MEDIUM | LOW",
  "primary_drivers": ["string"],
  "rationale": "string",
  "premium_adjustment_pct": float,
  "renewal_conditions": ["string"]
}}"""
    manager.register("renewal_recommendation_agent", "renewal_classification_fewshot", "v1", classification_template)

    adjustment_template = """Generate specific premium and coverage adjustment recommendations.
Decision: {decision}
Change Summary: {change_summary}
Risk Re-evaluation: {risk_reevaluation}

Return JSON only:
{{
  "premium_adjustment_pct": float,
  "coverage_modifications": ["string"],
  "sublimits_recommended": ["string"],
  "exclusions_recommended": ["string"],
  "conditions": ["string"]
}}"""
    manager.register("renewal_recommendation_agent", "adjustment_generation_zero_shot", "v1", adjustment_template)

    rationale_template = """Generate a one-paragraph broker-ready rationale for the renewal decision.
Decision: {decision}
Change Summary: {change_summary}
Risk Re-evaluation: {risk_reevaluation}
Adjustments: {adjustments}

RATIONALE RULES:
1. Professional, clear, and evidence-based.
2. DO NOT use markdown blocks like ```json or ```. Return ONLY raw text.
3. Explain the net risk trend if there are conflicting changes."""
    manager.register("renewal_recommendation_agent", "rationale_generation_zero_shot", "v1", rationale_template)
