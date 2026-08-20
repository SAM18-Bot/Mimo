"""
OpenAI client wrapper.
- Rate limiting guard (don't blow the budget)
- Fallback to pre-written content when AI is unavailable
- Async-ready
"""

import json
import logging
import os
import random
import time
from typing import Optional

import openai

import config

log = logging.getLogger(__name__)

openai.api_key = config.OPENAI_API_KEY
from google import genai
from google.genai import types

_last_call_time: float = 0.0
_MIN_CALL_INTERVAL = 2.0   # seconds between calls (avoid hammering)


def _chat(system: str, user: str, model: str = None, json_mode: bool = False, engine: str = "openai", api_key: str = None) -> Optional[str]:
    """Synchronous AI call with basic rate limiting and multi-engine support."""
    global _last_call_time

    # Rate limit guard
    elapsed = time.time() - _last_call_time
    if elapsed < _MIN_CALL_INTERVAL:
        time.sleep(_MIN_CALL_INTERVAL - elapsed)
        
    _last_call_time = time.time()

    if engine == "gemini":
        key = api_key or config.GEMINI_API_KEY
        if not key:
            log.warning("GEMINI_API_KEY not set. Falling back to OpenAI.")
        else:
            try:
                client = genai.Client(api_key=key)
                gemini_model = model or "gemini-2.5-flash"
                
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
                return response.text.strip()
            except Exception as e:
                log.error(f"Gemini call failed: {e}. Falling back to OpenAI...")

    # Fallback to OpenAI
    key = api_key or config.OPENAI_API_KEY
    if not key:
        log.warning("OPENAI_API_KEY not set")
        return None
        
    model = model or config.OPENAI_MODEL
    try:
        kwargs = dict(
            model    = model,
            messages = [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            max_tokens = 500,
            temperature = 0.85,
        )
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        client = openai.OpenAI(api_key=key)
        resp = client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content.strip()

    except Exception as e:
        log.error(f"OpenAI call failed: {e}")
        return None


def generate_roast(
    trigger: str,
    app_name: str,
    time_spent_min: int,
    pending_assignments: str,
    days_until_deadline: int,
    engine: str = "openai",
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
        # Use a faster model if openai
        fast_model = config.OPENAI_FAST_MODEL if engine == "openai" else "gemini-2.5-flash"
        result = _chat(ROAST_SYSTEM, user_prompt, model=fast_model, engine=engine, api_key=api_key)
        if result:
            return result

    # Fallback to pre-written
    roasts = cfg.PREWRITTEN_ROASTS.get(trigger, cfg.PREWRITTEN_ROASTS["generic"])
    return random.choice(roasts)


def generate_eod_report(context: dict, engine: str = "openai", api_key: str = None) -> Optional[dict]:
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


def generate_study_recommendations(context: dict, engine: str = "openai", api_key: str = None) -> Optional[dict]:
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
