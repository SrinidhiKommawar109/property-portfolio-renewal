def register_re_evaluation_templates(manager):
    fire_template = """Assess how fire risk has changed for property '{property_name}' at '{property_address}'.

Prior Data:
Construction: {prior_construction_type}
Sprinkler: {prior_sprinkler_status}
Alarm: {prior_alarm_status}
Protection Class: {prior_protection_class}
Cooking: {prior_cooking_operations}
Electrical Age: {prior_electrical_age}
Fire Station Distance: {prior_fire_station_distance}

Current Data:
Construction: {current_construction_type}
Sprinkler: {current_sprinkler_status}
Alarm: {current_alarm_status}
Protection Class: {current_protection_class}
Cooking: {current_cooking_operations}
Electrical Age: {current_electrical_age}
Fire Station Distance: {current_fire_station_distance}

Detected Changes:
{detected_fire_changes}

Follow these 5 steps for analysis:
Step 1: Score PRIOR YEAR fire risk 1-10 with factor-by-factor analysis.
Step 2: Score CURRENT YEAR fire risk 1-10 with same criteria.
Step 3: Calculate delta = current - prior, classify direction (IMPROVED, STABLE, DETERIORATED).
Step 4: Assess magnitude (|delta| <1 minor, 1-2 moderate, >2 significant).
Step 5: Identify primary drivers of the change.

Return JSON only:
{{
  "category": "Fire",
  "prior_score": float,
  "current_score": float,
  "delta": float,
  "direction": "string",
  "magnitude": "string",
  "primary_drivers": ["string"],
  "reasoning": "string"
}}"""

    manager.register("property_reevaluation_agent", "fire_risk_delta_cot", "v1", fire_template)

    natcat_template = """Assess how Natural Catastrophe (NatCat) risk has changed for property '{property_name}'.

Prior Data:
Flood Zone: {prior_flood_zone}
Earthquake Zone: {prior_earthquake_zone}
Windstorm Zone: {prior_windstorm_zone}
Brush Fire Exposure: {prior_brush_fire_exposure}

Current Data:
Flood Zone: {current_flood_zone}
Earthquake Zone: {current_earthquake_zone}
Windstorm Zone: {current_windstorm_zone}
Brush Fire Exposure: {current_brush_fire_exposure}

Detected Changes:
{detected_natcat_changes}

Follow these 5 steps for analysis:
Step 1: Score PRIOR YEAR NatCat risk 1-10.
Step 2: Score CURRENT YEAR NatCat risk 1-10.
Step 3: Calculate delta = current - prior, classify direction.
Step 4: Assess magnitude.
Step 5: Identify primary drivers.

Return JSON only:
{{
  "category": "NatCat",
  "prior_score": float,
  "current_score": float,
  "delta": float,
  "direction": "string",
  "magnitude": "string",
  "primary_drivers": ["string"],
  "reasoning": "string"
}}"""
    manager.register("property_reevaluation_agent", "natcat_risk_delta_cot", "v1", natcat_template)

    occupancy_template = """Assess how occupancy risk has changed for property '{property_name}'.

Prior Data:
Type: {prior_occupancy_type}
Tenant: {prior_primary_tenant}
Vacancy: {prior_vacancy_rate_pct}%
Cooking: {prior_cooking_operations}
Public Assembly: {prior_public_assembly}
Hazmat: {prior_hazardous_materials}

Current Data:
Type: {current_occupancy_type}
Tenant: {current_primary_tenant}
Vacancy: {current_vacancy_rate_pct}%
Cooking: {current_cooking_operations}
Public Assembly: {current_public_assembly}
Hazmat: {current_hazardous_materials}

Detected Changes:
{detected_occupancy_changes}

Follow these 5 steps for analysis:
Step 1: Score PRIOR YEAR occupancy risk 1-10.
Step 2: Score CURRENT YEAR occupancy risk 1-10.
Step 3: Calculate delta = current - prior, classify direction.
Step 4: Assess magnitude.
Step 5: Identify primary drivers.

Return JSON only:
{{
  "category": "Occupancy",
  "prior_score": float,
  "current_score": float,
  "delta": float,
  "direction": "string",
  "magnitude": "string",
  "primary_drivers": ["string"],
  "reasoning": "string"
}}"""
    manager.register("property_reevaluation_agent", "occupancy_risk_delta_cot", "v1", occupancy_template)

    building_template = """Assess how building condition risk has changed for property '{property_name}'.

Prior Data:
Type: {prior_construction_type}
Year Built: {prior_year_built}
Roof Age: {prior_roof_age_years}
Renovation: {prior_last_renovation_year}
Violations: {prior_code_violations}

Current Data:
Type: {current_construction_type}
Year Built: {current_year_built}
Roof Age: {current_roof_age_years}
Renovation: {current_last_renovation_year}
Violations: {current_code_violations}

Detected Changes:
{detected_building_changes}

Follow these 5 steps for analysis:
Step 1: Score PRIOR YEAR building risk 1-10.
Step 2: Score CURRENT YEAR building risk 1-10.
Step 3: Calculate delta = current - prior, classify direction.
Step 4: Assess magnitude.
Step 5: Identify primary drivers.

Return JSON only:
{{
  "category": "Building Condition",
  "prior_score": float,
  "current_score": float,
  "delta": float,
  "direction": "string",
  "magnitude": "string",
  "primary_drivers": ["string"],
  "reasoning": "string"
}}"""
    manager.register("property_reevaluation_agent", "building_condition_delta_cot", "v1", building_template)

    synthesis_template = """Synthesize the overall risk trend for the property based on the 4 category assessments.

Assessments:
Fire: {fire_result_json}
NatCat: {natcat_result_json}
Occupancy: {occupancy_result_json}
Building: {building_result_json}

Follow these steps:
1. Aggregate the scores and deltas.
2. Identify the dominant category driving the change.
3. Provide an overall synthesis of the risk movement.

Return JSON only:
{{
  "overall_trend": "IMPROVED | STABLE | DETERIORATED",
  "prior_overall_score": float,
  "current_overall_score": float,
  "overall_delta": float,
  "dominant_category": "string",
  "synthesis_reasoning": "string"
}}"""
    manager.register("property_reevaluation_agent", "overall_trend_synthesis_cot", "v1", synthesis_template)
