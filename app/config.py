"""
Configuration for SHL Assessment Advisor.
All values from environment variables with sensible defaults.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- Gemini API ---
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
MODEL_NAME: str = os.getenv("MODEL_NAME", "gemini-3.1-flash-lite")

# --- Timeout Budget (seconds) ---
# First LLM attempt gets 22s. On retry, adaptive timeout = max(0, 28 - elapsed).
# Total wall clock never exceeds 28s, leaving 2s buffer for FastAPI overhead
# to stay within the PDF's hard 30s deadline.
LLM_FIRST_ATTEMPT_TIMEOUT: float = 22.0
LLM_MAX_WALL_CLOCK: float = 28.0

# --- Limits ---
MAX_RECOMMENDATIONS: int = 10
MAX_TURNS: int = 8  # PDF: "8 turns including user & assistant"
MAX_ASSISTANT_RESPONSES: int = MAX_TURNS // 2  # Derived: 4 assistant responses

# --- test_type format ---
# Default: comma-separated (trace-aligned, e.g. "A,S", "P,C").
# Set TEST_TYPE_PRIMARY_ONLY=true to use single primary code only (e.g. "A", "P").
TEST_TYPE_PRIMARY_ONLY: bool = os.getenv("TEST_TYPE_PRIMARY_ONLY", "false").lower() == "true"

# --- Catalog ---
CATALOG_PATH: str = os.getenv("CATALOG_PATH", "shl_product_catalog.json")

# --- Description truncation ---
DESCRIPTION_MAX_WORDS: int = int(os.getenv("DESCRIPTION_MAX_WORDS", "40"))
