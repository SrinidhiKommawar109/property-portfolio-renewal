import json
import asyncio
from google.adk import Agent
from opentelemetry import trace
from prompt_manager import create_prompt_manager
from telemetry.arize_setup import get_tracer
from utils.llm_client import call_gemini_async

tracer = get_tracer("renewal-recommendation-agent")
prompt_manager = create_prompt_manager()

system_instruction = """
You are a property renewal recommendation specialist for mid-market commercial
property insurance. Based on detected changes and risk re-evaluation results,
recommend one of 4 renewal decisions:

1. RENEW_AS_IS: 0 material changes + all categories stable/improved
2. RENEW_WITH_ADJUSTMENTS: 1-2 material changes, risk within appetite with premium/terms modification
3. REFER_TO_SENIOR: 3+ material changes OR mixed signals OR complex changes requiring human judgment
4. NON_RENEW: 2+ categories with SIGNIFICANT deterioration beyond carrier appetite

Return all results as structured JSON only. Include confidence (HIGH/MEDIUM/LOW),
top 3 evidence points, one-paragraph rationale, and specific adjustment suggestions
if applicable.
"""

renewal_recommendation_agent = Agent(
    name="renewal_recommendation_agent",
    model="gemini-2.5-flash",
    instruction=system_instruction
)

def determine_renewal_guardrails(property_data: dict, risk_delta: float) -> str:
    current_year = property_data.get("current_year", {})
    tiv = property_data.get("total_insured_value", 1)
    total_claims_cost = current_year.get("loss", {}).get("total_incurred_last_3yr", 0)
    vacancy_rate = current_year.get("occupancy", {}).get("vacancy_rate_pct", 0)

    if (total_claims_cost / tiv) > 0.05:
        return "MANDATORY_REFERRAL: Claims exceed 5% of TIV."
    if vacancy_rate > 30:
        return "MANDATORY_REFERRAL: Vacancy exceeds 30%."

    if risk_delta < 0:
        if total_claims_cost < 25000:
            return "ELIGIBLE_FOR_STP: Risk has improved and losses are minor. Prioritize auto-renewal or adjustment."
        else:
            return "RENEW_WITH_ADJUSTMENTS: Risk improved but notable losses present. Adjust premium."
            
    if risk_delta > 2.0:
        return "REFER_TO_SENIOR: Significant risk deterioration detected mathematically."

    return "NEUTRAL: Use standard underwriting judgment based on material changes."

async def classify_renewal_decision(
    property_id: str,
    change_summary: dict,
    risk_reevaluation: dict,
    property_context: dict
) -> dict:
    """
    Uses 'renewal_classification_fewshot' prompt from prompt_manager.
    """
    with tracer.start_as_current_span("classify_renewal_decision") as span:
        span.set_attribute("property_id", property_id)
        
        guardrails = determine_renewal_guardrails(property_context, risk_reevaluation.get("overall_delta", 0))

        prompt = prompt_manager.get_prompt(
            agent="renewal_recommendation_agent",
            name="renewal_classification_fewshot",
            variables={
                "property_summary": json.dumps(property_context),
                "change_summary": json.dumps(change_summary),
                "risk_delta_summary": json.dumps(risk_reevaluation.get("category_results")),
                "overall_risk_trend": risk_reevaluation.get("overall_trend"),
                "guardrails": guardrails
            }
        )
        
        response = await call_gemini_async(renewal_recommendation_agent, prompt)
        text = response.text
        
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(text)
            span.set_attribute("renewal_decision", result.get("decision", "UNKNOWN"))
            return result
        except Exception as e:
            span.record_exception(e)
            return {"decision": "REFER_TO_SENIOR", "error": str(e)}

async def generate_adjustments(
    property_id: str,
    decision: str,
    change_summary: dict,
    risk_reevaluation: dict
) -> dict:
    """
    Only called if decision == 'RENEW_WITH_ADJUSTMENTS'.
    """
    if decision != "RENEW_WITH_ADJUSTMENTS":
        return {}

    with tracer.start_as_current_span("generate_adjustments") as span:
        prompt = prompt_manager.get_prompt(
            agent="renewal_recommendation_agent",
            name="adjustment_generation_zero_shot",
            variables={
                "decision": decision,
                "change_summary": json.dumps(change_summary),
                "risk_reevaluation": json.dumps(risk_reevaluation)
            }
        )
        
        response = await call_gemini_async(renewal_recommendation_agent, prompt)
        text = response.text
        
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            return json.loads(text)
        except Exception as e:
            span.record_exception(e)
            return {"error": str(e)}

async def generate_rationale(
    property_id: str,
    decision: str,
    change_summary: dict,
    risk_reevaluation: dict,
    adjustments: dict
) -> str:
    """
    Uses 'rationale_generation_zero_shot' prompt.
    """
    with tracer.start_as_current_span("generate_rationale") as span:
        prompt = prompt_manager.get_prompt(
            agent="renewal_recommendation_agent",
            name="rationale_generation_zero_shot",
            variables={
                "decision": decision,
                "change_summary": json.dumps(change_summary),
                "risk_reevaluation": json.dumps(risk_reevaluation),
                "adjustments": json.dumps(adjustments)
            }
        )
        
        response = await call_gemini_async(renewal_recommendation_agent, prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text.split("```json")[1].split("```")[0].strip()
        elif text.startswith("```"):
            text = text.split("```")[1].split("```")[0].strip()
        return text

async def generate_renewal_recommendation(
    property_id: str,
    change_report: dict,
    risk_reevaluation: dict,
    property_context: dict
) -> dict:
    """
    Runs full recommendation pipeline.
    """
    decision_report = await classify_renewal_decision(
        property_id, change_report, risk_reevaluation, property_context
    )
    
    decision = decision_report.get("decision")
    
    adjustments = await generate_adjustments(
        property_id, decision, change_report, risk_reevaluation
    )
    
    rationale = await generate_rationale(
        property_id, decision, change_report, risk_reevaluation, adjustments
    )
    
    return {
        "property_id": property_id,
        "decision": decision,
        "confidence": decision_report.get("confidence"),
        "primary_drivers": decision_report.get("primary_drivers"),
        "adjustments": adjustments,
        "rationale": rationale,
        "recommendation_report": decision_report
    }
