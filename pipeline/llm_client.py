"""
Unified LLM client — wraps Gemini and Anthropic behind one interface.
Provider is set via config/settings.yaml (llm.provider).
"""

import logging
import os
import time
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

_config_cache: dict | None = None


def _config() -> dict:
    global _config_cache
    if _config_cache is None:
        with open(Path("config/settings.yaml")) as f:
            _config_cache = yaml.safe_load(f).get("llm", {})
    return _config_cache


def complete(system_prompt: str, user_message: str, max_tokens: int = 2000) -> str:
    """
    Send a system + user message to the configured LLM.
    Returns the response text, or raises on failure.
    """
    provider = _config().get("provider", "gemini").lower()

    if provider == "gemini":
        return _gemini(system_prompt, user_message, max_tokens)
    elif provider == "anthropic":
        return _anthropic(system_prompt, user_message, max_tokens)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}. Set llm.provider in settings.yaml.")


def _gemini(system_prompt: str, user_message: str, max_tokens: int) -> str:
    from google import genai
    from google.genai import types

    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not set in .env")

    client = genai.Client(api_key=api_key, http_options={"timeout": 60})
    model_name = _config().get("gemini_model", "gemini-2.0-flash")

    # 1K RPM paid tier → 2s between calls is plenty
    time.sleep(2)

    response = client.models.generate_content(
        model=model_name,
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=max_tokens,
            temperature=0.3,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )

    candidate = response.candidates[0]
    finish_reason = getattr(candidate, "finish_reason", None)
    finish_name = finish_reason.name if finish_reason else "UNKNOWN"

    if finish_name not in ("STOP", "MAX_TOKENS"):
        logger.warning(f"Gemini finish_reason={finish_name} — response may be incomplete")

    # Concatenate all text parts (handles multi-part responses)
    text = "".join(
        part.text for part in candidate.content.parts
        if getattr(part, "text", None)
    )
    if not text:
        raise RuntimeError(f"Gemini returned empty response (finish_reason={finish_name})")

    if finish_name == "MAX_TOKENS":
        logger.warning("Gemini hit MAX_TOKENS — output may be cut off. Consider raising max_tokens or using a model with higher output quota.")

    return text


def _anthropic(system_prompt: str, user_message: str, max_tokens: int) -> str:
    import anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in .env")

    client = anthropic.Anthropic(api_key=api_key)
    model_name = _config().get("anthropic_model", "claude-sonnet-4-6")

    # Free tier: 5 RPM
    time.sleep(13)

    response = client.messages.create(
        model=model_name,
        max_tokens=max_tokens,
        system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text
