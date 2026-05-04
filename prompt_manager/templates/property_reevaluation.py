FIRE_RISK_PROMPT = """
You are evaluating ONLY FIRE RISK.

STRICT INSTRUCTIONS:
- Use ONLY fire-related fields:
  sprinkler, alarm, electrical systems, fire code violations
- DO NOT use or reference:
  flood, windstorm, tenant type, vacancy, roof, hvac

Focus ONLY on the CHANGES provided.
If no fire-related change exists, keep scores unchanged.

OUTPUT FORMAT (STRICT JSON ONLY):
{
  "_scratchpad": "Put your step-by-step thinking and calculations here. This is hidden.",
  "prior_score": number,
  "current_score": number,
  "delta": number,
  "reasoning": "A clean, concise 1-2 sentence public rationale for the score without any 'Step 1' style logic."
}

Rules:
- Scores must be between 1 and 10
- delta = current_score - prior_score
- Do NOT mention unrelated factors

Data:
{data}

Return ONLY JSON.
"""
NATCAT_RISK_PROMPT = """
You are evaluating ONLY NATURAL CATASTROPHE (NatCat) risk.

STRICT INSTRUCTIONS:
- Use ONLY:
  flood risk, windstorm exposure, earthquake risk, geographic hazards
- DO NOT use or reference:
  sprinkler, alarm, electrical, tenant, vacancy, roof, hvac

Focus ONLY on the CHANGES provided.
If no NatCat-related change exists, keep scores unchanged.

OUTPUT FORMAT (STRICT JSON ONLY):
{
  "_scratchpad": "Put your step-by-step thinking and calculations here. This is hidden.",
  "prior_score": number,
  "current_score": number,
  "delta": number,
  "reasoning": "A clean, concise 1-2 sentence public rationale for the score without any 'Step 1' style logic."
}

Rules:
- Scores must be between 1 and 10
- delta = current_score - prior_score
- Do NOT mention unrelated factors

Data:
{data}

Return ONLY JSON.
"""
OCCUPANCY_RISK_PROMPT = """
You are evaluating ONLY OCCUPANCY RISK.

STRICT INSTRUCTIONS:
- Use ONLY:
  tenant type, vacancy rate, tenant stability
- DO NOT use or reference:
  sprinkler, alarm, electrical, flood, windstorm, roof, hvac

Focus ONLY on the CHANGES provided.
If no occupancy-related change exists, keep scores unchanged.

OUTPUT FORMAT (STRICT JSON ONLY):
{
  "_scratchpad": "Put your step-by-step thinking and calculations here. This is hidden.",
  "prior_score": number,
  "current_score": number,
  "delta": number,
  "reasoning": "A clean, concise 1-2 sentence public rationale for the score without any 'Step 1' style logic."
}

Rules:
- Scores must be between 1 and 10
- delta = current_score - prior_score
- Do NOT mention unrelated factors

Data:
{data}

Return ONLY JSON.
"""
BUILDING_RISK_PROMPT = """
You are evaluating ONLY BUILDING CONDITION risk.

STRICT INSTRUCTIONS:
- Use ONLY:
  roof condition, structural integrity, maintenance, HVAC condition
- DO NOT use or reference:
  sprinkler, alarm, electrical, flood, windstorm, tenant, vacancy

Focus ONLY on the CHANGES provided.
If no building-related change exists, keep scores unchanged.

OUTPUT FORMAT (STRICT JSON ONLY):
{
  "_scratchpad": "Put your step-by-step thinking and calculations here. This is hidden.",
  "prior_score": number,
  "current_score": number,
  "delta": number,
  "reasoning": "A clean, concise 1-2 sentence public rationale for the score without any 'Step 1' style logic."
}

Rules:
- Scores must be between 1 and 10
- delta = current_score - prior_score
- Do NOT mention unrelated factors

Data:
{data}

Return ONLY JSON.
"""