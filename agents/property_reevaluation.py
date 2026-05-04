import json
import asyncio
from google.adk import Agent
from opentelemetry import trace
from prompt_manager import create_prompt_manager
from telemetry.arize_setup import get_tracer
from utils.llm_client import call_gemini_async

tracer = get_tracer("property-reevaluation-agent")
prompt_manager = create_prompt_manager()

system_instruction = """
You are an expert property risk re-evaluation specialist for mid-market
commercial property insurance. Your job is to compare a property's CURRENT
year data against its PRIOR year data and determine how risk has changed
across 4 categories: Fire, NatCat, Occupancy, and Building Condition.

For each category, provide:
1. Prior year score (1-10) — based on prior year data only
2. Current year score (1-10) — based on current year data only
3. Delta direction: IMPROVED, STABLE, or DETERIORATED
4. Delta magnitude: MINOR (<1), MODERATE (1-2), or SIGNIFICANT (>2)
5. Primary change drivers
6. Step-by-step CoT reasoning

Focus on CHANGES, not absolute risk. A high-risk stable property →
renew as-is. A moderate-risk deteriorating property → needs attention.
Return all results as structured JSON only.
"""

property_reevaluation_agent = Agent(
    name="property_reevaluation_agent",
    model="gemini-2.5-flash",
    instruction=system_instruction
)

async def _call_llm_for_category(category_name: str, prompt_name: str, variables: dict) -> dict:
    with tracer.start_as_current_span(f"assess_{category_name.lower().replace(' ', '_')}_risk_change") as span:
        span.set_attribute("category", category_name)
        
        prompt = prompt_manager.get_prompt(
            agent="property_reevaluation_agent",
            name=prompt_name,
            variables=variables
        )
        
        response = await call_gemini_async(property_reevaluation_agent, prompt)
        text = response.text
        
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(text)
            span.set_attribute("risk_delta", result.get("delta", 0))
            return result
        except Exception as e:
            span.record_exception(e)
            return {"category": category_name, "error": str(e)}

async def assess_fire_risk_change(property_id: str, current_data: dict, prior_data: dict, detected_changes: list) -> dict:
    return await _call_llm_for_category("Fire", "fire_risk_delta_cot", {
        "property_name": current_data.get("property_name"),
        "property_address": current_data.get("address"),
        "prior_construction_type": prior_data.get("construction", {}).get("construction_type"),
        "current_construction_type": current_data.get("construction", {}).get("construction_type"),
        "prior_sprinkler_status": prior_data.get("protection", {}).get("sprinkler_status"),
        "current_sprinkler_status": current_data.get("protection", {}).get("sprinkler_status"),
        "prior_alarm_status": prior_data.get("protection", {}).get("alarm_status"),
        "current_alarm_status": current_data.get("protection", {}).get("alarm_status"),
        "prior_protection_class": prior_data.get("protection", {}).get("fire_protection_class"),
        "current_protection_class": current_data.get("protection", {}).get("fire_protection_class"),
        "prior_cooking_operations": prior_data.get("occupancy", {}).get("cooking_operations"),
        "current_cooking_operations": current_data.get("occupancy", {}).get("cooking_operations"),
        "prior_electrical_age": 2026 - prior_data.get("construction", {}).get("year_built"), # Simplification
        "current_electrical_age": 2026 - current_data.get("construction", {}).get("year_built"),
        "prior_fire_station_distance": prior_data.get("protection", {}).get("distance_to_fire_station_miles"),
        "current_fire_station_distance": current_data.get("protection", {}).get("distance_to_fire_station_miles"),
        "detected_fire_changes": json.dumps([c for c in detected_changes if c.get('risk_category_affected') == 'Fire'], indent=2)
    })

async def assess_natcat_risk_change(property_id: str, current_data: dict, prior_data: dict, detected_changes: list) -> dict:
    return await _call_llm_for_category("NatCat", "natcat_risk_delta_cot", {
        "property_name": current_data.get("property_name"),
        "prior_flood_zone": prior_data.get("hazards", {}).get("flood_zone"),
        "current_flood_zone": current_data.get("hazards", {}).get("flood_zone"),
        "prior_earthquake_zone": prior_data.get("hazards", {}).get("earthquake_zone"),
        "current_earthquake_zone": current_data.get("hazards", {}).get("earthquake_zone"),
        "prior_windstorm_zone": prior_data.get("hazards", {}).get("windstorm_zone"),
        "current_windstorm_zone": current_data.get("hazards", {}).get("windstorm_zone"),
        "prior_brush_fire_exposure": prior_data.get("hazards", {}).get("brush_fire_exposure"),
        "current_brush_fire_exposure": current_data.get("hazards", {}).get("brush_fire_exposure"),
        "detected_natcat_changes": json.dumps([c for c in detected_changes if c.get('risk_category_affected') == 'NatCat'], indent=2)
    })

async def assess_occupancy_risk_change(property_id: str, current_data: dict, prior_data: dict, detected_changes: list) -> dict:
    return await _call_llm_for_category("Occupancy", "occupancy_risk_delta_cot", {
        "property_name": current_data.get("property_name"),
        "prior_occupancy_type": prior_data.get("occupancy", {}).get("occupancy_type"),
        "current_occupancy_type": current_data.get("occupancy", {}).get("occupancy_type"),
        "prior_primary_tenant": prior_data.get("occupancy", {}).get("primary_tenant"),
        "current_primary_tenant": current_data.get("occupancy", {}).get("primary_tenant"),
        "prior_vacancy_rate_pct": prior_data.get("occupancy", {}).get("vacancy_rate_pct"),
        "current_vacancy_rate_pct": current_data.get("occupancy", {}).get("vacancy_rate_pct"),
        "prior_cooking_operations": prior_data.get("occupancy", {}).get("cooking_operations"),
        "current_cooking_operations": current_data.get("occupancy", {}).get("cooking_operations"),
        "prior_public_assembly": prior_data.get("occupancy", {}).get("public_assembly"),
        "current_public_assembly": current_data.get("occupancy", {}).get("public_assembly"),
        "prior_hazardous_materials": prior_data.get("hazards", {}).get("hazardous_materials"),
        "current_hazardous_materials": current_data.get("hazards", {}).get("hazardous_materials"),
        "detected_occupancy_changes": json.dumps([c for c in detected_changes if c.get('risk_category_affected') == 'Occupancy'], indent=2)
    })

async def assess_building_condition_change(property_id: str, current_data: dict, prior_data: dict, detected_changes: list) -> dict:
    return await _call_llm_for_category("Building Condition", "building_condition_delta_cot", {
        "property_name": current_data.get("property_name"),
        "prior_construction_type": prior_data.get("construction", {}).get("construction_type"),
        "current_construction_type": current_data.get("construction", {}).get("construction_type"),
        "prior_year_built": prior_data.get("construction", {}).get("year_built"),
        "current_year_built": current_data.get("construction", {}).get("year_built"),
        "prior_roof_age_years": prior_data.get("construction", {}).get("roof_age_years"),
        "current_roof_age_years": current_data.get("construction", {}).get("roof_age_years"),
        "prior_last_renovation_year": prior_data.get("construction", {}).get("last_renovation_year"),
        "current_last_renovation_year": current_data.get("construction", {}).get("last_renovation_year"),
        "prior_code_violations": prior_data.get("compliance", {}).get("code_violations"),
        "current_code_violations": current_data.get("compliance", {}).get("code_violations"),
        "detected_building_changes": json.dumps([c for c in detected_changes if c.get('risk_category_affected') == 'Building'], indent=2)
    })

async def combine_risk_deltas(
    property_id: str,
    fire_result: dict,
    natcat_result: dict,
    occupancy_result: dict,
    building_result: dict
) -> dict:
    """
    Combines 4 category results into overall risk trend.
    """
    with tracer.start_as_current_span("combine_risk_deltas") as span:
        prompt = prompt_manager.get_prompt(
            agent="property_reevaluation_agent",
            name="overall_trend_synthesis_cot",
            variables={
                "fire_result_json": json.dumps(fire_result),
                "natcat_result_json": json.dumps(natcat_result),
                "occupancy_result_json": json.dumps(occupancy_result),
                "building_result_json": json.dumps(building_result)
            }
        )
        
        response = await call_gemini_async(property_reevaluation_agent, prompt)
        text = response.text
        
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            combined = json.loads(text)
            combined["category_results"] = {
                "Fire": fire_result,
                "NatCat": natcat_result,
                "Occupancy": occupancy_result,
                "Building": building_result
            }
            span.set_attribute("overall_delta", combined.get("overall_delta", 0))
            return combined
        except Exception as e:
            span.record_exception(e)
            return {"error": str(e)}

async def reevaluate_property_risk(
    property_id: str,
    current_data: dict,
    prior_data: dict,
    change_report: dict
) -> dict:
    """
    Runs ALL 4 category assessments in PARALLEL using asyncio.gather().
    Then combines results via combine_risk_deltas.
    """
    detected_changes = change_report.get("material_changes", [])
    
    tasks = [
        assess_fire_risk_change(property_id, current_data, prior_data, detected_changes),
        assess_natcat_risk_change(property_id, current_data, prior_data, detected_changes),
        assess_occupancy_risk_change(property_id, current_data, prior_data, detected_changes),
        assess_building_condition_change(property_id, current_data, prior_data, detected_changes)
    ]
    
    results = await asyncio.gather(*tasks)
    
    fire_res, natcat_res, occ_res, build_res = results
    
    combined_report = await combine_risk_deltas(
        property_id, fire_res, natcat_res, occ_res, build_res
    )
    
    return combined_report
