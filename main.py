
import json
import argparse
import asyncio
import sys
import os

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.portfolio_orchestrator import (
    load_portfolio as load_pf,
    process_portfolio_batch,
    generate_portfolio_summary,
    portfolio_orchestrator
)

from telemetry.arize_setup import init_arize_tracing
from user_profile.profile_store import UserProfileStore
from mock_apis.portfolio_loader import load_results
from utils.llm_client import client


load_dotenv()

import subprocess
import httpx
import time

async def run_batch_only(portfolio_id):
    print(f"🚀 Starting batch processing for portfolio: {portfolio_id}")
    
    print("📡 Starting A2A Servers in background...")
    change_detection_process = subprocess.Popen(
        [sys.executable, "agent_a2a/server/a2a_server.py"]
    )
    reevaluation_process = subprocess.Popen(
        [sys.executable, "agent_a2a/server/reevaluation_a2a_server.py"]
    )
    recommendation_process = subprocess.Popen(
        [sys.executable, "agent_a2a/server/recommendation_a2a_server.py"]
    )
    
    servers_ready = False
    for _ in range(15):
        try:
            async with httpx.AsyncClient() as client:
                cd_resp = await client.get("http://127.0.0.1:8002/health")
                re_resp = await client.get("http://127.0.0.1:8003/health")
                rec_resp = await client.get("http://127.0.0.1:8004/health")
                if cd_resp.status_code == 200 and re_resp.status_code == 200 and rec_resp.status_code == 200:
                    servers_ready = True
                    break
        except httpx.ConnectError:
            pass
        await asyncio.sleep(1)
        
    if not servers_ready:
        print("⚠️ Could not start all A2A Servers in background. Proceeding with fallbacks.")
    
    try:
        # Init tracing
        init_arize_tracing()
        
        # 1. Load
        validation = await load_pf(portfolio_id)
        if validation.get("validation_status") == "FAILED":
            print(f"❌ Validation failed: {validation.get('errors')}")
            return
        
        portfolio_data = validation["portfolio_data"]
        
        # 2. Process
        results = await process_portfolio_batch(portfolio_data)
        
        # 3. Summarize
        summary = await generate_portfolio_summary(
            portfolio_data["portfolio_id"],
            portfolio_data["portfolio_name"],
            results
        )
        
        print("\n--- BATCH PROCESS COMPLETE ---")
        print(f"Portfolio: {summary['portfolio_name']}")
        print(f"Total Properties: {summary['property_count']}")
        print(f"Avg Risk Delta: {summary['portfolio_avg_delta']}")
        print(f"Decision Mix: {summary['decision_mix']}")
        print(f"Material Changes: {summary['total_material_changes']}")
        print(f"Results saved to results/{portfolio_id}.json")
        return portfolio_data["portfolio_id"]
    finally:
        change_detection_process.terminate()
        change_detection_process.wait()
        reevaluation_process.terminate()
        reevaluation_process.wait()
        recommendation_process.terminate()
        recommendation_process.wait()

async def run_interactive_chat(portfolio_id: str):
    print(f"\n💬 Entering Conversational Review Mode for portfolio: {portfolio_id}")
    print("Type 'exit' or 'quit' to end the session.\n")
    
    profile_store = UserProfileStore()
    user_id = "default_underwriter" # In a real app, this would come from session/auth
    profile = profile_store.get_or_create(user_id)
    
    # Initial context: Load the batch results so the agent knows what happened
    results = load_results(portfolio_id)
    if not results:
        print(f"⚠️ No results found for {portfolio_id}. Have you run the batch process yet?")
        return

    # Start a chat session with the agent's instructions and tools
    chat = client.aio.chats.create(
        model=portfolio_orchestrator.model,
        config={
            'system_instruction': portfolio_orchestrator.instruction,
            'tools': [t for t in portfolio_orchestrator.tools if t.__name__ in [
                'get_portfolio_results', 'manage_user_profile', 'format_response_for_profile', 'load_portfolio'
            ]],
            'automatic_function_calling': {'disable': False}
        },
        history=[
            {
                "role": "user", 
                "parts": [{"text": f"Context: Current user is '{user_id}'. Current portfolio is '{portfolio_id}'. Batch results summary: {json.dumps(results['summary'])}"}]
            },
            {
                "role": "model",
                "parts": [{"text": f"I've reviewed the results for {portfolio_id}. I'm ready to help you analyze the portfolio or walk through specific property changes. How would you like to start?"}]
            }
        ]
    )

    print(f"Assistant: I've reviewed the results for {portfolio_id}. I'm ready to help you analyze the portfolio or walk through specific property changes. How would you like to start?")

    while True:
        try:
            user_input = input("\nUnderwriter > ").strip()
            if user_input.lower() in ['exit', 'quit']:
                break
            
            if not user_input:
                continue

            # Automatic function calling will handle any tool calls requested by the agent
            response = await chat.send_message(user_input)
            print(f"\nAssistant: {response.text}")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ Error: {e}")

    print("\n👋 Review session ended.")

def main():
    parser = argparse.ArgumentParser(description="Property Portfolio Renewal System")
    parser.add_argument("--portfolio", type=str, help="Portfolio ID or path to process in batch mode")
    parser.add_argument("--a2a-server", action="store_true", help="Start the Change Detection A2A server")
    parser.add_argument("--interactive", action="store_true", help="Start interactive review after batch processing")
    parser.add_argument("--review", type=str, help="Start interactive review for a previously processed portfolio")
    
    args = parser.parse_args()

    if args.a2a_server:
        print("📡 Starting all A2A Servers...")
        import uvicorn
        # For simplicity, start them sequentially or in threads, but since async, perhaps run them in parallel.
        # But uvicorn.run blocks, so maybe need to run them in separate processes or use multiprocessing.
        # For now, since the user wants them started, perhaps modify to start each in a subprocess.
        # But the original was uvicorn.run for change detection.
        # To keep simple, change to start all three in subprocesses.
        subprocess.Popen([sys.executable, "agent_a2a/server/a2a_server.py"])
        subprocess.Popen([sys.executable, "agent_a2a/server/reevaluation_a2a_server.py"])
        subprocess.Popen([sys.executable, "agent_a2a/server/recommendation_a2a_server.py"])
        print("All A2A servers started.")
    elif args.portfolio:
        actual_id = asyncio.run(run_batch_only(args.portfolio))
        if args.interactive and actual_id:
            asyncio.run(run_interactive_chat(actual_id))
    elif args.review:
        asyncio.run(run_interactive_chat(args.review))
    else:
        # Default: Run ADK Web UI
        print("🖥️ Starting ADK Web UI for Portfolio Orchestrator...")
        # Note: In a real environment, the user would run 'adk web agents/portfolio_orchestrator.py'
        # We can simulate the command here if needed, but the prompt says 'run adk web'
        # We will use os.system for simplicity in this script context
        os.system("adk web agents/portfolio_orchestrator.py")

if __name__ == "__main__":
    main()
