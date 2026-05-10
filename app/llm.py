"""
Gemini 3.1 Flash Lite client with adaptive retry.

Retry policy (from v4 plan):
  - 429 (rate limit): sleep 2s, retry with reduced timeout
  - 5xx (server error): sleep 1s, retry with reduced timeout
  - Timeout: retry once with remaining budget
  - All other errors: propagate immediately
  
Total wall clock never exceeds LLM_MAX_WALL_CLOCK (28s).
"""

import asyncio
import json
import logging
import time
from typing import Any

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from app import config
from app.models import Message

logger = logging.getLogger(__name__)


def initialize() -> None:
    """Initialize the Gemini client. Call once at startup."""
    if not config.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set — LLM calls will fail")
        return
    genai.configure(api_key=config.GEMINI_API_KEY)
    logger.info(f"Gemini client configured: model={config.MODEL_NAME}")


def _format_messages(messages: list[Message]) -> list[dict[str, Any]]:
    """Convert Message list to Gemini's content format.
    
    Gemini uses "user" and "model" roles (not "assistant").
    """
    contents = []
    for msg in messages:
        role = "model" if msg.role == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": msg.content}]})
    return contents


async def _call_gemini(
    system_prompt: str,
    messages: list[Message],
    timeout: float,
) -> dict[str, Any]:
    """Make a single Gemini API call with timeout."""
    model = genai.GenerativeModel(
        model_name=config.MODEL_NAME,
        system_instruction=system_prompt,
    )

    contents = _format_messages(messages)

    response = await asyncio.wait_for(
        model.generate_content_async(
            contents=contents,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
            ),
        ),
        timeout=timeout,
    )

    text = response.text
    if not text:
        raise ValueError("Empty response from Gemini")

    return json.loads(text)


async def generate(system_prompt: str, messages: list[Message]) -> dict[str, Any]:
    """Call Gemini with adaptive retry. Total wall clock <= LLM_MAX_WALL_CLOCK.
    
    Returns parsed JSON dict with keys: reply, entity_ids, end_of_conversation.
    """
    start = time.monotonic()
    max_wall = config.LLM_MAX_WALL_CLOCK
    last_error: Exception | None = None

    for attempt in range(2):  # Max 2 attempts
        elapsed = time.monotonic() - start
        remaining = max_wall - elapsed

        if remaining <= 2:
            break  # Not enough time for another attempt

        timeout = min(config.LLM_FIRST_ATTEMPT_TIMEOUT, remaining)

        try:
            result = await _call_gemini(system_prompt, messages, timeout)
            return result

        except google_exceptions.ResourceExhausted as e:
            # 429 — rate limited
            last_error = e
            if attempt == 0:
                logger.warning("Rate limited (429), retrying in 2s...")
                await asyncio.sleep(2)
                continue
            raise

        except (
            google_exceptions.InternalServerError,
            google_exceptions.ServiceUnavailable,
        ) as e:
            # 5xx — server error
            last_error = e
            if attempt == 0:
                logger.warning(f"Server error ({type(e).__name__}), retrying in 1s...")
                await asyncio.sleep(1)
                continue
            raise

        except asyncio.TimeoutError:
            last_error = TimeoutError(f"Gemini call timed out after {timeout:.1f}s")
            if attempt == 0:
                logger.warning(f"Timeout on attempt 1 ({timeout:.1f}s), retrying...")
                continue
            raise last_error

        except json.JSONDecodeError as e:
            # LLM returned non-JSON — do not retry, propagate
            logger.error(f"Gemini returned invalid JSON: {e}")
            raise

    # Exhausted retries or budget
    if last_error:
        raise last_error
    raise TimeoutError("LLM call exceeded time budget")
