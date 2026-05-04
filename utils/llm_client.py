import json
import re
import os
import asyncio
from dotenv import load_dotenv
from google import genai

load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    raise ValueError("❌ GOOGLE_API_KEY is missing in .env file")

client = genai.Client(api_key=API_KEY)


def clean_json(text: str):
    if not text:
        return None

    # remove markdown blocks
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)

    # safer JSON extraction (non-greedy)
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return match.group(0)

    return None


def call_gemini(prompt: str, expect_json: bool = False):
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt
        )

        raw = response.text or ""

        # ✅ normal text mode
        if not expect_json:
            return raw.strip()

        # ✅ JSON mode
        cleaned = clean_json(raw)

        if cleaned:
            return json.loads(cleaned)

        return {
            "error": "No JSON found",
            "raw": raw
        }

    except Exception as e:
        return {
            "error": str(e),
            "raw": None
        }

async def call_gemini_async(agent, prompt: str):
    max_retries = 3
    base_delay = 5
    for attempt in range(max_retries):
        try:
            response = await client.aio.models.generate_content(
                model=agent.model,
                contents=prompt,
                config={'system_instruction': agent.instruction}
            )
            class MockResponse:
                def __init__(self, text):
                    self.text = text if text is not None else ""
            return MockResponse(response.text)
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                if attempt < max_retries - 1:
                    wait_time = base_delay * (2 ** attempt)
                    print(f"⚠️ Rate limited for {agent.name}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
            print(f"❌ LLM Error for agent {agent.name}: {e}")
            raise e