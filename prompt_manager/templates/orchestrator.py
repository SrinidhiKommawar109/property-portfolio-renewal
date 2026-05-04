def register_orchestrator_templates(manager):
    validation_template = """Validate the following portfolio JSON data.
Portfolio: {portfolio_json}

Check for:
- Required fields (portfolio_id, portfolio_name, properties)
- Each property has current_year and prior_year
- property_type is valid
- tiv > 0
- property_ids are unique

Return JSON only:
{{
  "validation_status": "SUCCESS | FAILED",
  "errors": ["string"],
  "warnings": ["string"],
  "property_count": int
}}"""
    manager.register("portfolio_orchestrator", "portfolio_validation_zero_shot", "v1", validation_template)

    profiling_template = """Classify the underwriter experience level from their messages.

Messages: {underwriter_messages}

Examples:
- "I just started doing renewals this quarter" -> JUNIOR
- "Pull up exceptions, sort by NatCat zone reclassification" -> SENIOR
- "I'm not sure which changes are important vs which I can ignore" -> JUNIOR
- "Show me delta summary, anything >+1.0 I'll review directly" -> SENIOR

Return JSON only:
{{
  "experience_level": "JUNIOR | SENIOR",
  "reasoning": "string",
  "preferred_mode": "string"
}}"""
    manager.register("portfolio_orchestrator", "user_profiling_few_shot", "v1", profiling_template)

    chat_template = """Respond to the underwriter's question about the portfolio.
Experience Level: {experience_level}
Portfolio: {portfolio_name}
Property Count: {property_count}
Question: {question}

Adapt verbosity:
- JUNIOR: Full narrative, define terms, explain why changes matter.
- SENIOR: Concise, exceptions only, data-driven.
"""
    manager.register("portfolio_orchestrator", "review_chat_general_zero_shot", "v1", chat_template)

    react_template = """You are a ReAct agent assisting an underwriter.
Portfolio: {portfolio_name}
Property Count: {property_count}
Experience Level: {experience_level}
User Query: {user_query}
Available Tools: {available_tools}

Follow Thought/Action/Observation scaffolding."""
    manager.register("portfolio_orchestrator", "review_chat_react", "v1", react_template)
