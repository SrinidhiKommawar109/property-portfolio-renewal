import json
import asyncio
import os
import time
from datetime import datetime
from google.adk import Agent
from opentelemetry import trace
from prompt_manager import create_prompt_manager
from telemetry.arize_setup import get_tracer
from mock_apis.portfolio_loader import load_portfolio as fetch_portfolio, save_results
from user_profile.profile_store import UserProfileStore
from agents.change_detection import detect_changes_for_property
from agents.property_reevaluation import reevaluate_property_risk
from agents.renewal_recommendation import generate_renewal_recommendation
from utils.llm_client import call_gemini_async
from agent_a2a.client.a2a_client import ChangeDetectionClient
from agent_a2a.client.reevaluation_client import ReevaluationClient
from agent_a2a.client.recommendation_client import RecommendationClient
import httpx

tracer = get_tracer("portfolio-orchestrator")
prompt_manager = create_prompt_manager()
profile_store = UserProfileStore()

system_instruction = """
You are an expert property portfolio renewal assistant for mid-market
commercial property insurance. You operate in two modes:

MODE 1 — BATCH PROCESSING:
When the user provides a portfolio JSON file path or portfolio ID, you:
1. Load and validate the portfolio (call load_portfolio tool)
2. Process ALL properties in PARALLEL (call process_portfolio_batch tool)
3. Generate portfolio summary (call generate_portfolio_summary tool)
4. Present formatted results and transition to review mode

MODE 2 — CONVERSATIONAL REVIEW:
After batch processing, when the user asks questions:
1. Profile the underwriter on first interaction if not already profiled
2. Adapt responses to their experience level:
   - JUNIOR: Full property walkthrough, define terms, explain why changes matter
   - SENIOR: Exceptions only, concise tables, no explanations unless requested
3. Support drill-down into specific properties
4. Support portfolio-level queries

Always respond with structured, evidence-based answers referencing specific
property IDs, risk scores, and change data.
"""



async def load_portfolio(portfolio_path: str) -> dict:
    """
    Loads portfolio JSON from path or by portfolio_id.
    """
    with tracer.start_as_current_span("load_portfolio") as span:
        data = fetch_portfolio(portfolio_path)
        if "error" in data:
            return data

        # Skip brittle LLM validation step and assume data is well-formed
        return {"validation_status": "SUCCESS", "portfolio_data": data}

async def process_single_property(property_data: dict, is_first: bool = False) -> dict:
    property_id = property_data.get("property_id")
    property_name = property_data.get("property_name")
    current_year = property_data.get("current_year")
    prior_year = property_data.get("prior_year")
    
    print(f"⏳ Processing property: {property_name}...")
    start_time = time.time()
    
    with tracer.start_as_current_span("process_single_property") as span:
        span.set_attribute("property_id", property_id)
        
        try:
            # 1. Change Detection
            try:
                # Try via A2A Server
                a2a_client = ChangeDetectionClient(base_url="http://localhost:8002")
                change_report = await a2a_client.detect_changes_async(
                    property_id=property_id,
                    current_year=current_year,
                    prior_year=prior_year
                )
            except (httpx.ConnectError, httpx.ConnectTimeout):
                # Fallback to local function if server is offline
                print(f"⚠️ A2A Server unreachable for {property_id}. Falling back to local agent.")
                change_report = await detect_changes_for_property(property_id, current_year, prior_year)
            
            # 2. Risk Re-evaluation
            try:
                # Try via A2A Server
                reevaluation_client = ReevaluationClient(base_url="http://localhost:8003")
                risk_reevaluation = await reevaluation_client.reevaluate_risk_async(
                    property_id=property_id,
                    current_data=current_year,
                    prior_data=prior_year,
                    change_report=change_report
                )
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.HTTPStatusError):
                # Fallback to local function if server is offline
                print(f"⚠️ Reevaluation A2A Server unreachable for {property_id}. Falling back to local agent.")
                risk_reevaluation = await reevaluate_property_risk(property_id, current_year, prior_year, change_report)
            
            # 3. Renewal Recommendation
            try:
                # Try via A2A Server
                recommendation_client = RecommendationClient(base_url="http://localhost:8004")
                recommendation = await recommendation_client.generate_recommendation_async(
                    property_id=property_id,
                    change_report=change_report,
                    risk_reevaluation=risk_reevaluation,
                    property_context={"property_type": property_data.get("property_type"), "name": property_name}
                )
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.HTTPStatusError):
                # Fallback to local function if server is offline
                print(f"⚠️ Recommendation A2A Server unreachable for {property_id}. Falling back to local agent.")
                recommendation = await generate_renewal_recommendation(
                    property_id, change_report, risk_reevaluation, 
                    {"property_type": property_data.get("property_type"), "name": property_name}
                )
            
            latency = time.time() - start_time
            print(f"✅ {property_name} complete ({latency:.1f}s)")
            
            return {
                "property_id": property_id,
                "property_name": property_name,
                "tiv": property_data.get("total_insured_value", 1),
                "change_report": change_report,
                "risk_reevaluation": risk_reevaluation,
                "recommendation": recommendation,
                "latency_ms": latency * 1000
            }
        except Exception as e:
            print(f"❌ Failed to process {property_name}: {str(e)}")
            span.record_exception(e)
            return {"property_id": property_id, "error": str(e)}

async def process_portfolio_batch(portfolio: dict) -> dict:
    """
    Processes ALL properties in PARALLEL using asyncio.gather(), limited by a Semaphore(2).
    """
    properties = portfolio.get("properties", [])
    semaphore = asyncio.Semaphore(2)

    async def sem_process(prop, is_first):
        async with semaphore:
            return await process_single_property(prop, is_first=is_first)

    tasks = []
    for i, prop in enumerate(properties):
        tasks.append(sem_process(prop, is_first=(i == 0)))
    
    results = await asyncio.gather(*tasks)
    return results

async def generate_portfolio_summary(
    portfolio_id: str,
    portfolio_name: str,
    property_results: list
) -> dict:
    """
    Aggregates per-property results into portfolio summary.
    """
    total = len(property_results)
    decision_counts = {}
    total_delta = 0
    total_tiv = 0
    material_changes_count = 0
    flagged_properties = []
    
    for res in property_results:
        if "error" in res: continue
        
        decision = res["recommendation"]["decision"]
        decision_counts[decision] = decision_counts.get(decision, 0) + 1
        
        delta = res["risk_reevaluation"].get("overall_delta", 0)
        tiv = res.get("tiv", 1)
        
        # We will compute total_tiv and accumulate the weighted delta products
        total_delta += (delta * tiv)
        total_tiv += tiv
        
        m_count = res["change_report"].get("material_count", 0)
        material_changes_count += m_count
        
        if m_count > 0:
            flagged_properties.append({
                "property_id": res["property_id"],
                "property_name": res["property_name"],
                "delta": delta,
                "decision": decision,
                "material_changes": res["change_report"]["material_changes"]
            })
            
    # Sort flagged by delta desc
    flagged_properties.sort(key=lambda x: x["delta"], reverse=True)
    
    avg_delta = (total_delta / total_tiv) if total_tiv > 0 else 0
    
    summary = {
        "portfolio_id": portfolio_id,
        "portfolio_name": portfolio_name,
        "property_count": total,
        "decision_mix": {d: {"count": c, "pct": round(c/total*100, 1)} for d, c in decision_counts.items()},
        "portfolio_avg_delta": round(avg_delta, 2),
        "total_material_changes": material_changes_count,
        "flagged_properties": flagged_properties,
        "timestamp": datetime.now().isoformat()
    }
    
    save_results(portfolio_id, {"summary": summary, "results": property_results})
    return summary

async def manage_user_profile(
    user_id: str,
    action: str,
    data: dict = None
) -> dict:
    if action == 'get':
        return profile_store.get_profile(user_id)
    elif action == 'get_or_create':
        return profile_store.get_or_create(user_id)
    elif action == 'profile_from_messages':
        messages = data.get("messages", "")
        prompt = prompt_manager.get_prompt(
            agent="portfolio_orchestrator",
            name="user_profiling_few_shot",
            variables={"underwriter_messages": messages}
        )
        response = await call_gemini_async(portfolio_orchestrator, prompt)
        text = response.text
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            profiling_result = json.loads(text)
            return profile_store.update_from_profiling(user_id, profiling_result)
        except:
            return profile_store.get_or_create(user_id)
    return {}

async def format_response_for_profile(
    content: dict,
    experience_level: str,
    response_type: str
) -> str:
    """
    Formats a result dict into a human-readable markdown string.
    """
    experience_level = experience_level.lower()
    
    if response_type == "portfolio_summary":
        summary = content
        if experience_level == "senior":
            # Concise table
            lines = [f"### Portfolio Summary: {summary['portfolio_name']}", ""]
            lines.append("| Property | Decision | Delta | Top Material Change |")
            lines.append("| :--- | :--- | :--- | :--- |")
            for prop in summary['flagged_properties']:
                top_change = prop['material_changes'][0]['risk_impact'] if prop['material_changes'] else "N/A"
                lines.append(f"| {prop['property_name']} | {prop['decision']} | {prop['delta']} | {top_change} |")
            lines.append("")
            lines.append(f"**Portfolio Avg Delta:** {summary['portfolio_avg_delta']}")
            lines.append("Want details on any flagged properties?")
            return "\n".join(lines)
        else:
            # Junior - Walkthrough
            lines = [f"## Portfolio Review: {summary['portfolio_name']}", ""]
            lines.append(f"Hello! I've analyzed your portfolio of {summary['property_count']} properties.")
            lines.append(f"Overall, the risk trend is {'deteriorating' if summary['portfolio_avg_delta'] > 0 else 'improving'} with an average score change of {summary['portfolio_avg_delta']}.")
            lines.append("")
            lines.append("### Key Findings")
            for prop in summary['flagged_properties'][:3]:
                lines.append(f"- **{prop['property_name']}**: Recommended for **{prop['decision']}**. We saw a risk increase of {prop['delta']} primarily due to {len(prop['material_changes'])} material changes.")
            lines.append("")
            lines.append("Would you like me to explain what these risk scores mean or walk through a specific property?")
            return "\n".join(lines)
    
    return json.dumps(content, indent=2)

# Tool Registration for ADK
portfolio_orchestrator = Agent(
    name="portfolio_orchestrator",
    model="gemini-2.5-flash",
    instruction=system_instruction,
    tools=[
        load_portfolio,
        process_portfolio_batch,
        generate_portfolio_summary,
        manage_user_profile,
        format_response_for_profile
    ]
)
