# SHL Assessment Advisor API

A stateless, zero-RAG conversational AI agent that helps hiring managers select appropriate assessments from the SHL product catalog. Built using FastAPI and Gemini 3.1 Flash-Lite.

## 🚀 Performance
* **Behavioral Probes:** 6/6 (Passes strict constraints on prompt injection, vague queries, constraint refinement, and refusals).
* **Mean Recall@10:** 0.50 (Successfully mapping multi-turn conversational traces to precise catalog `entity_id` recommendations).

## 🛠 Tech Stack
* **Framework:** FastAPI
* **LLM:** Google Gemini 3.1 Flash-Lite
* **Testing:** Pytest & HTTPX
* **Deployment:** Render (Zero-downtime ASGI)

## 📦 Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Nesar21/SHL-assignment.git
   cd SHL-assignment
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   Create a `.env` file in the root directory:
   ```env
   GEMINI_API_KEY="your-gemini-api-key-here"
   MODEL_NAME="gemini-3.1-flash-lite"
   TEST_TYPE_PRIMARY_ONLY="true"
   ```

## 🏃‍♂️ Running the Server
Start the development server using Uvicorn:
```bash
uvicorn app.main:app --port 8000 --reload
```
The API will be available at `http://localhost:8000`. You can view the Swagger UI at `http://localhost:8000/docs`.

## 🧪 Running the Test Suite
The automated evaluation harness tests both behavioral constraints and semantic recall against provided markdown traces.

1. **Ensure the server is running on port 8000** in a separate terminal.
2. **Run Behavioral Probes:**
   ```bash
   pytest tests/test_behavior.py -s -v
   ```
3. **Run Trace Recall Evaluations:**
   ```bash
   pytest tests/test_traces.py -s -v
   ```

## 📄 Documentation
For detailed architectural decisions, prompt engineering strategies, and evaluation methodologies, please see the [Approach Document](approach_document.md).
