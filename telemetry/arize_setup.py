"""
Arize OpenTelemetry setup (optional).

The rest of the codebase imports `get_tracer()` from here. This module is
deliberately resilient:
- If `arize_otel` isn't installed, we fall back to a local tracer.
- If credentials aren't present, we fall back to a local tracer.
"""

from __future__ import annotations

import os

from opentelemetry import trace


def init_arize_tracing(model_id: str = "property-portfolio-renewal"):
    """
    Initialize Arize OpenTelemetry tracing if possible, else return a local tracer.
    """
    space_id = os.getenv("ARIZE_SPACE_ID")
    api_key = os.getenv("ARIZE_API_KEY")

    # Missing credentials: keep things running with local tracer.
    if not space_id or not api_key:
        return trace.get_tracer(model_id)

    # Optional dependency: don't break local runs if not installed.
    try:
        from arize.otel import register
    except Exception as e:
        print(f"⚠️ Could not load arize.otel: {e}")
        return trace.get_tracer(model_id)

    try:
        register(
            space_id=space_id,
            api_key=api_key,
            project_name=model_id,
        )
        print(f"✅ Arize tracing registered for space_id: {space_id}")
    except Exception as e:
        print(f"⚠️ Failed to register Arize: {e}")

    return trace.get_tracer(model_id)


def get_tracer(name: str = "portfolio-renewal-agents"):
    """Return OpenTelemetry tracer (local if Arize not configured)."""
    return trace.get_tracer(name)
