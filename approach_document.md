# SHL Assessment Advisor - Approach Document

## 1. Design Choices & Architecture
Our primary architectural decision was to build a **stateless, zero-RAG, full-context conversational agent** using FastAPI and Google's **Gemini 3.1 Flash-Lite**. 

Given the PDF's strict requirements to *never* recommend anything outside the SHL catalog and the fact that the catalog is relatively small (377 Individual Test Solutions), we explicitly chose **not to use vector stores or embeddings**. 
*   **Why zero-RAG?** Vector search often retrieves "semantically similar" but factually incorrect items, leading to hallucinations. By injecting the entire catalog into the LLM's context window, we provide the LLM with global visibility over all tests, allowing it to perform exact filtering (e.g., "language = French", "level = Mid-Professional") without relying on the lossy nature of embeddings.
*   **Strict Grounding via `entity_id`:** To enforce the API schema and guarantee grounding, the LLM is instructed to only output an array of `entity_id` strings (e.g., `["001", "042"]`). Our FastAPI backend (`agent.py`) intercepts these IDs and performs an $O(1)$ dictionary lookup against the `shl_product_catalog.json` file. The backend then constructs the final `name`, `url`, and `test_type` payload. If the LLM hallucinates an ID, the backend safely ignores it. This guarantees 100% compliance with the SHL catalog.

## 2. Retrieval & Context Setup
Instead of retrieving chunks, we compress the entire catalog at startup (`app/catalog.py`). 
*   We strip out unnecessary keys and truncate long descriptions to 40 words.
*   This creates a compact JSON string of ~117KB (roughly ~29,000 tokens), which fits comfortably within Gemini's 1-million token context window.
*   This approach completely eliminates retrieval latency during the conversation and prevents "missing chunk" errors when a user asks for complex cross-sections (e.g., "Compare OPQ to GSA").

## 3. Prompt Design & Conversation Management
Our system prompt (`app/prompts.py`) is structured as a state machine governing five strict behaviors: **Clarify, Recommend, Refine, Compare, and Refuse**.

*   **Turn-Budget Injection & Hard Constraints:** The PDF limits conversations to 8 turns (4 assistant responses). We dynamically inject the turn state into the prompt. When `remaining <= 1`, the prompt uses an absolute, unconditional override to force `end_of_conversation: true`, eliminating ambiguity.
*   **Coherence Rules & Anti-Leakage:** We noticed early LLMs would mention an assessment in the conversational `"reply"` string but forget to include its ID in the `"entity_ids"` array, or worse, leak internal bracket identifiers like `[3984]` into the prose. We added strict "Coherence Rules" to prevent identifier leakage and guarantee conversational flow matches the schema payload perfectly.
*   **Immediate Recommendation Constraint:** We strengthened the `RECOMMEND` instruction to force immediate recommendations on Turn 1 if the user provides enough context (e.g., Role + Skills), ensuring we don't annoy users with unnecessary clarifying questions.

## 4. Evaluation Approach & What Didn't Work
We built a rigorous automated evaluation harness using `pytest` and `httpx`.
*   **Behavioral Probes (`test_behavior.py`):** We test binary assertions, ensuring the agent refuses off-topic questions, handles prompt injections safely, and updates shortlists upon constraint refinement. All 6 behavioral probes strictly pass.
*   **Recall@10 Framework (`test_traces.py`):** We built a test suite that dynamically replays the 10 provided markdown traces via HTTP. The script parses the expected shortlists from the markdown and compares them against our API's JSON output. By implementing domain-specific prompt enhancements and name normalization, the system successfully achieved a Mean Recall@10 of **0.50** on the public dataset.

**What didn't work:**
Initially, we used `gemini-2.5-flash` due to its high reasoning, but we quickly hit API Rate Limit (429) errors because passing ~29K tokens per request rapidly exhausted the free-tier quota of 20 requests per day. 
*   *Solution:* We downgraded to the faster and vastly more generous `gemini-3.1-flash-lite` model (500 requests per day). We also implemented adaptive pacing (`time.sleep`) in our trace replay suite and robust fallback mechanics (`ChatResponse` defaults) so that temporary network errors during automated evaluation don't crash the simulation harness.

## 5. Deployment & Tools
*   **Frameworks:** `FastAPI` for the web server, `uvicorn` for ASGI hosting, `google-generativeai` for the LLM integration.
*   **Deployment:** Configured via `render.yaml` for zero-downtime deployment on Render.
*   **AI Tools Used:** Claude (Anthropic) used for plan design, architecture critique, gap analysis, and prompt iteration. Gemini (Google) used as the production LLM. All code written and verified by the author.
