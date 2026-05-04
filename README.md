# Property Portfolio Renewal & Risk Re-evaluation Agent System

A complete, production-ready multi-agent AI system for mid-market commercial property insurance renewal underwriting.

## Overview
This system automates the batch processing and conversational review of property insurance portfolios. It detects material changes between prior and current year data, re-evaluates risk across multiple categories (Fire, NatCat, Occupancy, Building Condition), and provides renewal recommendations (Renew As-Is, Adjustments, Senior Review, Non-Renew).

The system adapts its output based on the user's experience level (Junior vs. Senior), providing either full educational walkthroughs or concise exception-only reports.

## Architecture
```
[ Portfolio Orchestrator ] (Main Agent)
       |
       +---(Parallel Fan-out)---> [ Change Detection Agent ]
       |                                |
       +---(Parallel Fan-out)---> [ Risk Re-evaluation Agent ] (CoT)
       |                                |
       +---(Parallel Fan-out)---> [ Renewal Recommendation Agent ]
```

- **Portfolio Orchestrator**: Manages the end-to-end workflow and user interactions.
- **Change Detection Agent**: Identifies and classifies field-level changes.
- **Risk Re-evaluation Agent**: Performs factor-by-factor risk delta analysis using Chain-of-Thought.
- **Renewal Recommendation Agent**: Classifies the renewal decision and generates broker-ready rationales.

## Tech Stack
| Tool | Purpose |
| :--- | :--- |
| **Python 3.11+** | Primary language |
| **Google ADK** | Agent framework & UI |
| **Gemini 2.5 Flash** | Core LLM for all agents |
| **A2A SDK** | Inter-agent communication |
| **Arize OTel** | Observability & Tracing |
| **Pydantic** | Data validation |

## Setup Instructions
```bash
git clone <repo>
cd property-portfolio-renewal
python -m venv venv
source venv/bin/activate  # venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your GOOGLE_API_KEY and Arize keys
```

## Running the System
### Option A: Full UI (Batch + Chat)
```bash
adk web agents/portfolio_orchestrator.py
```

### Option B: Headless Batch
```bash
python main.py --portfolio PF-MIDWEST-001
```

### Option C: Start A2A Server
```bash
python main.py --a2a-server
```

## Demo Scenarios
- **Scenario 1 (Junior)**: Aisha reviewing Southeast Retail. Detailed explanations and term definitions provided.
- **Scenario 2 (Senior)**: Robert reviewing Northeast Mixed. Concise tables and exceptions-only reporting.

## Portfolio IDs
- `PF-MIDWEST-001`: Midwest Office Portfolio
- `PF-SOUTHEAST-001`: Southeast Retail Portfolio
- `PF-NORTHEAST-001`: Northeast Mixed-Use Portfolio

## Arize Tracing
The system is fully instrumented with OpenTelemetry. LLM calls, latencies, and risk deltas are sent to Arize for monitoring and debugging.
