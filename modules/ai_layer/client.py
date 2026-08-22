"""
Gemini client wrapper.
- Rate limiting guard (don't blow the budget)
- Uses user's personal API key if provided, falls back to server config
- Async-ready
"""

import json
import logging
import os
import random
import time
from typing import Optional

import config
from google import genai
from google.genai import types

log = logging.getLogger(__name__)

_last_call_time: float = 0.0
_MIN_CALL_INTERVAL = 2.0   # seconds between calls (avoid hammering)

def _chat(system: str, user: str, model: str = None, json_mode: bool = False, engine: str = "gemini", api_key: str = None) -> Optional[str]:
    """Synchronous AI call. STRICTLY uses Gemini."""
    global _last_call_time

    # Rate limit guard
    elapsed = time.time() - _last_call_time
    if elapsed < _MIN_CALL_INTERVAL:
        time.sleep(_MIN_CALL_INTERVAL - elapsed)
        
    _last_call_time = time.time()

    # Prioritize user's personal API key, fallback to server's GEMINI_API_KEY
    gemini_key = api_key or getattr(config, 'GEMINI_API_KEY', None)
    if not gemini_key:
        log.warning("No Gemini API key available (neither user nor server).")
        return None

    try:
        client = genai.Client(api_key=gemini_key)
        # Default to 2.5-flash since 3.6 might be a future reference, but 2.5-flash is stable 
        gemini_model = model if (model and "gemini" in model.lower()) else "gemini-3.0-flash"
        
        config_args = {
            "system_instruction": system,
            "temperature": 0.85,
        }
        if json_mode:
            config_args["response_mime_type"] = "application/json"
            
        response = client.models.generate_content(
            model=gemini_model,
            contents=user,
            config=types.GenerateContentConfig(**config_args),
        )
        if response and response.text:
            return response.text.strip()
    except Exception as e:
        log.error(f"Gemini call failed (limit reached or unresponsive): {e}")
        return None

def generate_roast(
    trigger: str,
    app_name: str,
    time_spent_min: int,
    pending_assignments: str,
    days_until_deadline: int,
    engine: str = "gemini",
    api_key: str = None,
) -> str:
    """Generate a roast. Falls back to pre-written if AI is slow or unavailable."""
    from modules.ai_layer.prompts import ROAST_SYSTEM, ROAST_USER
    import config as cfg

    if cfg.LIVE_ROAST_USE_AI:
        user_prompt = ROAST_USER.format(
            trigger             = trigger,
            app_name            = app_name,
            time_spent          = time_spent_min,
            pending_assignments = pending_assignments,
            days_until_deadline = days_until_deadline,
        )
        result = _chat(ROAST_SYSTEM, user_prompt, model="gemini-3.0-flash", engine=engine, api_key=api_key)
        if result:
            return result

    # Fallback to pre-written
    roasts = cfg.PREWRITTEN_ROASTS.get(trigger, cfg.PREWRITTEN_ROASTS["generic"])
    return random.choice(roasts)


def generate_eod_report(context: dict, engine: str = "gemini", api_key: str = None) -> Optional[dict]:
    """Generate end-of-day report. Returns parsed JSON dict or None."""
    from modules.ai_layer.prompts import EOD_SYSTEM, EOD_USER

    user_prompt = EOD_USER.format(**context)
    raw = _chat(EOD_SYSTEM, user_prompt, json_mode=True, engine=engine, api_key=api_key)

    if not raw:
        return None

    try:
        # Strip markdown code fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:-1])
        return json.loads(raw)
    except json.JSONDecodeError as e:
        log.error(f"EOD report JSON parse failed: {e}\nRaw: {raw[:200]}")
        return None


def generate_study_recommendations(context: dict, engine: str = "gemini", api_key: str = None) -> Optional[dict]:
    """Returns dict with recommendations and suggested_subjects or None."""
    from modules.ai_layer.prompts import STUDY_ADVISOR_SYSTEM, STUDY_ADVISOR_USER

    user_prompt = STUDY_ADVISOR_USER.format(**context)
    raw = _chat(STUDY_ADVISOR_SYSTEM, user_prompt, json_mode=True, engine=engine, api_key=api_key)

    if not raw:
        return None

    try:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:-1])
        data = json.loads(raw)
        
        # handle legacy array format just in case
        if isinstance(data, list):
            return {"recommendations": data, "suggested_subjects": []}
        return data
    except Exception as e:
        log.error(f"Study rec parse failed: {e}")
        return None

def generate_coach_response(
    question: str,
    context: dict,
    engine: str = "gemini",
    api_key: str = None
) -> str:
    """Generates a conversational response from the AI coach."""
    from modules.ai_layer.prompts import COACH_CHAT_SYSTEM, COACH_CHAT_USER

    user_prompt = COACH_CHAT_USER.format(
        question=question,
        pending_assignments=context.get("pending_assignments", "None"),
        focus_score=context.get("focus_score", 0),
        productive_min=context.get("productive_min", 0),
        distracting_min=context.get("distracting_min", 0)
    )

    result = _chat(COACH_CHAT_SYSTEM, user_prompt, model="gemini-3.0-flash", engine=engine, api_key=api_key)
    if result:
        return result
    return "I'm offline right now. Check your internet connection or API Key limits."
