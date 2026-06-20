"""
OpenAI client wrapper.
- Rate limiting guard (don't blow the budget)
- Fallback to pre-written content when AI is unavailable
- Async-ready
"""

import json
import logging
import random
import time
from typing import Optional

import openai

import config

log = logging.getLogger(__name__)

openai.api_key = config.OPENAI_API_KEY

_last_call_time: float = 0.0
_MIN_CALL_INTERVAL = 2.0   # seconds between calls (avoid hammering)


def _chat(system: str, user: str, model: str = None, json_mode: bool = False) -> Optional[str]:
    """Synchronous OpenAI call with basic rate limiting."""
    global _last_call_time

    if not config.OPENAI_API_KEY:
        log.warning("OPENAI_API_KEY not set — skipping AI call")
        return None

    # Rate limit guard
    elapsed = time.time() - _last_call_time
    if elapsed < _MIN_CALL_INTERVAL:
        time.sleep(_MIN_CALL_INTERVAL - elapsed)

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

        resp = openai.chat.completions.create(**kwargs)
        _last_call_time = time.time()
        return resp.choices[0].message.content.strip()

    except openai.RateLimitError:
        log.warning("OpenAI rate limit hit")
        return None
    except Exception as e:
        log.error(f"OpenAI call failed: {e}")
        return None


def generate_roast(
    trigger: str,
    app_name: str,
    time_spent_min: int,
    pending_assignments: str,
    days_until_deadline: int,
) -> str:
    """Generate a roast. Falls back to pre-written if AI is slow or unavailable."""
    from modules.ai_layer.prompts import ROAST_SYSTEM, ROAST_USER
    import config as cfg

    if cfg.LIVE_ROAST_USE_AI and config.OPENAI_API_KEY:
        user_prompt = ROAST_USER.format(
            trigger             = trigger,
            app_name            = app_name,
            time_spent          = time_spent_min,
            pending_assignments = pending_assignments,
            days_until_deadline = days_until_deadline,
        )
        result = _chat(ROAST_SYSTEM, user_prompt, model=config.OPENAI_FAST_MODEL)
        if result:
            return result

    # Fallback to pre-written
    roasts = cfg.PREWRITTEN_ROASTS.get(trigger, cfg.PREWRITTEN_ROASTS["generic"])
    return random.choice(roasts)


def generate_eod_report(context: dict) -> Optional[dict]:
    """Generate end-of-day report. Returns parsed JSON dict or None."""
    from modules.ai_layer.prompts import EOD_SYSTEM, EOD_USER

    user_prompt = EOD_USER.format(**context)
    raw = _chat(EOD_SYSTEM, user_prompt, json_mode=True)

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


def generate_study_recommendations(context: dict) -> Optional[list]:
    """Returns list of recommendation dicts or None."""
    from modules.ai_layer.prompts import STUDY_ADVISOR_SYSTEM, STUDY_ADVISOR_USER

    user_prompt = STUDY_ADVISOR_USER.format(**context)
    raw = _chat(STUDY_ADVISOR_SYSTEM, user_prompt, json_mode=True)

    if not raw:
        return None

    try:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:-1])
        data = json.loads(raw)
        # handle both {"recommendations": [...]} and bare [...]
        if isinstance(data, list):
            return data
        return data.get("recommendations", [])
    except Exception as e:
        log.error(f"Study rec parse failed: {e}")
        return None
