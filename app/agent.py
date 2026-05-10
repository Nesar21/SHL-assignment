"""
Agent orchestrator: prompt → LLM → validate → response.

This is the core pipeline for each /chat request:
  1. Count assistant responses so far (turn budget)
  2. Build system prompt with catalog + turn state
  3. Single Gemini call (JSON mode, adaptive retry)
  4. Strict validation: entity_id → catalog lookup
  5. Construct schema-compliant ChatResponse
"""

import logging

from app import catalog, config, llm
from app.models import ChatRequest, ChatResponse, Recommendation
from app.prompts import build_system_prompt

logger = logging.getLogger(__name__)


async def process(request: ChatRequest) -> ChatResponse:
    """Process a chat request and return a schema-compliant response.
    
    Every recommendation is constructed via catalog.lookup() — 
    name, url, test_type are NEVER from LLM output directly.
    """
    messages = request.messages

    # --- Step 1: Count assistant responses so far ---
    assistant_count = sum(1 for m in messages if m.role == "assistant")
    response_number = assistant_count + 1

    logger.info(
        f"Processing request: {len(messages)} messages, "
        f"assistant response #{response_number}"
    )

    # --- Step 2: Build system prompt ---
    system_prompt = build_system_prompt(response_number=response_number)

    # --- Step 3: Single Gemini call ---
    raw = await llm.generate(system_prompt, messages)

    # --- Step 4: Strict validation ---
    recommendations: list[Recommendation] = []
    raw_ids = raw.get("entity_ids", [])

    # Defensive: ensure raw_ids is a list
    if not isinstance(raw_ids, list):
        logger.warning(f"entity_ids is not a list: {type(raw_ids)}, treating as empty")
        raw_ids = []

    dropped: list[str] = []
    for eid in raw_ids:
        rec = catalog.lookup(str(eid))
        if rec is not None:
            recommendations.append(rec)
        else:
            dropped.append(str(eid))

    if dropped:
        logger.warning(f"Dropped invalid entity_ids: {dropped}")

    # Enforce max 10 recommendations (PDF: "1 to 10 items")
    recommendations = recommendations[: config.MAX_RECOMMENDATIONS]

    # --- Step 5: Extract reply and end_of_conversation ---
    reply = raw.get("reply", "")
    if not reply or not isinstance(reply, str):
        reply = "Could you tell me more about what you're looking for?"

    eoc = raw.get("end_of_conversation", False)
    if not isinstance(eoc, bool):
        eoc = False

    logger.info(
        f"Response: {len(recommendations)} recommendations, "
        f"eoc={eoc}, dropped={len(dropped)}"
    )

    return ChatResponse(
        reply=reply,
        recommendations=recommendations,
        end_of_conversation=eoc,
    )
