import json
import asyncio
from google.adk import Agent
from opentelemetry import trace
from prompt_manager import create_prompt_manager
from telemetry.arize_setup import get_tracer
from utils.llm_client import call_gemini_async

tracer = get_tracer("change-detection-agent")
prompt_manager = create_prompt_manager()

system_instruction = """
You are a property data change detection specialist for commercial property
insurance renewal underwriting. Your job is to compare a property's
current-year data against its prior-year data and identify EVERY change.

For each change found, classify severity:
- MATERIAL: Directly affects risk score or renewal terms.
  Examples: flood zone reclassification, sprinkler system removed,
  occupancy type changed from office to restaurant, new code violation.
- NOTABLE: Worth reviewing but may not change terms.
  Examples: TIV increase <10%, tenant name change (same occupancy type),
  roof age crossing threshold year.
- COSMETIC: No risk impact.
  Examples: contact info updated, address formatting changed.

Be exhaustive — compare EVERY nested field. A missed material change is
a serious underwriting error. Return results as structured JSON only.
"""

change_detection_agent = Agent(
    name="change_detection_agent",
    model="gemini-2.5-flash",
    instruction=system_instruction
)

async def compare_property_fields(
    property_id: str,
    current_data: dict,
    prior_data: dict
) -> dict:
    """
    Compares all nested fields between current and prior year data.
    """
    with tracer.start_as_current_span("compare_property_fields") as span:
        span.set_attribute("property_id", property_id)
        
        prompt = prompt_manager.get_prompt(
            agent="change_detection_agent",
            name="field_comparison_zero_shot",
            variables={
                "prior_year_json": json.dumps(prior_data, indent=2),
                "current_year_json": json.dumps(current_data, indent=2)
            }
        )
        
        response = await call_gemini_async(change_detection_agent, prompt)
        text = response.text
        
        # Extract JSON if necessary
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            changes = json.loads(text)
            span.set_attribute("total_changes_detected", len(changes))
            return changes
        except Exception as e:
            span.record_exception(e)
            return []

async def classify_change_severity(
    property_id: str,
    raw_changes: list,
    property_context: dict
) -> list:
    """
    Classifies each detected change as material/notable/cosmetic.
    """
    if not raw_changes:
        return []

    with tracer.start_as_current_span("classify_change_severity") as span:
        span.set_attribute("property_id", property_id)
        
        prompt = prompt_manager.get_prompt(
            agent="change_detection_agent",
            name="change_severity_few_shot",
            variables={
                "property_type": property_context.get("property_type", "commercial"),
                "raw_changes": json.dumps(raw_changes, indent=2)
            }
        )
        
        response = await call_gemini_async(change_detection_agent, prompt)
        text = response.text
        
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            classified = json.loads(text)
            material_count = sum(1 for c in classified if c.get('severity') == 'MATERIAL')
            span.set_attribute("material_changes_count", material_count)
            return classified
        except Exception as e:
            span.record_exception(e)
            return raw_changes

async def generate_change_summary(
    property_id: str,
    classified_changes: list
) -> dict:
    """
    Summarizes all changes for a property.
    """
    material_changes = [c for c in classified_changes if c.get('severity') == 'MATERIAL']
    notable_changes = [c for c in classified_changes if c.get('severity') == 'NOTABLE']
    cosmetic_changes = [c for c in classified_changes if c.get('severity') == 'COSMETIC']
    
    summary = {
        "property_id": property_id,
        "total_changes": len(classified_changes),
        "material_count": len(material_changes),
        "notable_count": len(notable_changes),
        "cosmetic_count": len(cosmetic_changes),
        "material_changes": material_changes,
        "overall_change_assessment": f"Detected {len(material_changes)} material, {len(notable_changes)} notable, and {len(cosmetic_changes)} cosmetic changes."
    }
    return summary

async def detect_changes_for_property(
    property_id: str,
    current_data: dict,
    prior_data: dict
) -> dict:
    """
    Runs full change detection pipeline for one property.
    """
    raw_changes = await compare_property_fields(property_id, current_data, prior_data)
    classified_changes = await classify_change_severity(property_id, raw_changes, {"property_type": current_data.get("property_type")})
    summary = await generate_change_summary(property_id, classified_changes)
    return summary
