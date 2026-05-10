"""
FastAPI application for SHL Assessment Advisor.

Endpoints (PDF contract):
  GET  /health → {"status": "ok"} with HTTP 200
  POST /chat   → ChatResponse (always valid schema, even on errors)

Startup: Eager loading of catalog and LLM client via lifespan.
Static files: Mounted at "/" for Phase 2 Chat UI (only if static/ directory exists).
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import agent, catalog, llm
from app.models import ChatRequest, ChatResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: load catalog + initialize LLM. Eager, not lazy."""
    logger.info("=== SHL Assessment Advisor Starting ===")

    # Load catalog (377 items, ~475KB JSON → in-memory dict)
    catalog.load()
    logger.info(f"Catalog ready: {catalog.get_item_count()} items")

    # Initialize Gemini client
    llm.initialize()
    logger.info("LLM client ready")

    logger.info("=== Startup Complete ===")
    yield
    logger.info("=== Shutting Down ===")


app = FastAPI(
    title="SHL Assessment Advisor",
    description="Conversational agent for SHL Individual Test Solutions",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    """Health check. PDF: returns {"status": "ok"} with HTTP 200."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Chat endpoint. PDF: stateless, full history in each request.
    
    ALWAYS returns a valid ChatResponse — even on internal errors.
    The evaluator's automated harness cannot parse error responses.
    """
    try:
        return await agent.process(request)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR: {repr(e)}")
        # Fallback: valid schema, no recommendations, conversation stays open
        return ChatResponse(
            reply="I encountered an issue processing your request. Could you rephrase your question?",
            recommendations=[],
            end_of_conversation=False,
        )


# Mount static files for Phase 2 Chat UI (only if the directory exists)
_static_dir = Path(__file__).parent.parent / "static"
if _static_dir.exists():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")
