from google.adk import Agent
from google.adk.tools import ToolContext
import json
import asyncio
import os
import sys

# Add project root to path to ensure relative imports work correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.portfolio_orchestrator import (
    process_portfolio_batch,
    generate_portfolio_summary,
    load_portfolio as load_pf
)
from telemetry.arize_setup import init_arize_tracing

async def underwriting_tool(context: ToolContext, user_input: str):
    """
    Primary tool for property portfolio analysis. 
    Detects changes, re-evaluates risk, and provides renewal recommendations.
    Supports file uploads (artifacts) or direct JSON input.
    """
    # Initialize tracing for the session
    init_arize_tracing()
    
    portfolio = None

    # 1. Attempt to load portfolio from uploaded artifacts (ADK Web UI context)
    try:
        artifact_keys = await context.list_artifacts()
        if artifact_keys:
            # Find the most likely portfolio JSON
            key_to_load = artifact_keys[0]
            for k in artifact_keys:
                lk = str(k).lower()
                if lk.endswith(".json") and ("port" in lk):
                    key_to_load = k
                    break
            
            part = await context.load_artifact(key_to_load)
            if part and hasattr(part, "text") and part.text:
                portfolio = json.loads(part.text)
    except Exception:
        portfolio = None

    # 2. Fallback to parsing user input directly as JSON
    if not portfolio and user_input:
        try:
            maybe = json.loads(user_input)
            if isinstance(maybe, dict) and "properties" in maybe:
                portfolio = maybe
        except Exception:
            pass

    if not portfolio:
        return "Please upload a portfolio JSON file or paste the portfolio data to begin the analysis."

    try:
        # 3. Execute the Batch Processing Pipeline
        # This calls Change Detection, Risk Re-evaluation, and Recommendation for each property
        results = await process_portfolio_batch(portfolio)
        
        # 4. Generate the Portfolio Summary
        # This aggregates results and saves them to the results/ directory
        summary = await generate_portfolio_summary(
            portfolio.get("portfolio_id", "UPLOADED"),
            portfolio.get("portfolio_name", "New Analysis"),
            results
        )
        
        # Return structured results for the LLM or UI to present
        return f"Analysis complete for {summary['portfolio_name']}.\n\nResults Summary:\n{json.dumps(summary, indent=2)}"
        
    except Exception as e:
        return f"An error occurred during portfolio analysis: {str(e)}"

# Define the Root Agent for ADK
root_agent = Agent(
    name="underwriting_agent",
    model="gemini-2.5-flash",
    instruction="""
    You are an expert commercial property underwriting assistant. 
    You help underwriters process renewal portfolios by analyzing risk changes.
    Use the underwriting_tool to process any provided portfolio data.
    """,
    tools=[underwriting_tool]
)

# Export as 'agent' for ADK convention
agent = root_agent