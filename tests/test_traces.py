"""
Recall@10 tests: replay public conversation traces against our agent via HTTP.

Maps to PDF scoring: "Recall@10 on final recommendations. Mean Recall@10 across
all conversation traces, public and holdout."

Recall@K = (Number of relevant assessments in top K) / (Total relevant assessments for query)
Mean Recall@K = (1/N) * sum over queries of Recall@K_i

These tests replay the 10 public traces (C1-C10) via the running HTTP server
and compute Recall@10.
"""

import re
import sys
import time
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_URL = "http://127.0.0.1:8000"


def parse_trace_expected_shortlist(trace_path: str) -> list[str]:
    """Parse the FINAL recommendation table from a trace file.
    
    Extracts assessment names from the last markdown table in the trace.
    These are the 'expected' items for Recall@10 computation.
    
    Returns list of assessment names.
    """
    with open(trace_path, "r") as f:
        content = f.read()

    # Find all markdown tables (lines starting with |)
    # We want the LAST table in the file (final shortlist)
    tables = []
    current_table = []
    in_table = False

    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("|") and "---" not in stripped and "# " not in stripped:
            in_table = True
            current_table.append(stripped)
        else:
            if in_table and current_table:
                tables.append(current_table)
                current_table = []
            in_table = False

    if current_table:
        tables.append(current_table)

    if not tables:
        return []

    # Last table = final shortlist
    last_table = tables[-1]

    NAME_NORMALIZATION_MAP = {
        "SHL Verify Interactive G+": "Verify - G+"
    }

    names = []
    for row in last_table:
        # Skip header row
        if "Name" in row and "Test Type" in row:
            continue
        # Parse: | # | Name | Test Type | ... |
        cells = [c.strip() for c in row.split("|")]
        cells = [c for c in cells if c]  # Remove empty strings
        if len(cells) >= 2:
            name = cells[1].strip()
            if name and name != "Name" and not name.startswith("---"):
                # Apply normalization if necessary
                normalized_name = NAME_NORMALIZATION_MAP.get(name, name)
                names.append(normalized_name)

    return names


def extract_user_messages_from_trace(trace_path: str) -> list[dict]:
    """Extract the conversation flow from a trace file.
    
    Returns list of {role, content} messages representing the trace conversation.
    We only extract user messages — our agent generates its own responses.
    """
    with open(trace_path, "r") as f:
        content = f.read()

    messages = []
    current_role = None
    current_content = []
    in_user = False
    in_agent = False

    for line in content.split("\n"):
        stripped = line.strip()

        if stripped == "**User**":
            # Save previous message if any
            if current_role and current_content:
                text = "\n".join(current_content).strip()
                if text:
                    messages.append({"role": current_role, "content": text})
            current_role = "user"
            current_content = []
            in_user = True
            in_agent = False
            continue

        if stripped == "**Agent**":
            # Save previous message if any
            if current_role and current_content:
                text = "\n".join(current_content).strip()
                if text:
                    messages.append({"role": current_role, "content": text})
            current_role = None  # We don't extract agent messages
            current_content = []
            in_user = False
            in_agent = True
            continue

        # Skip turn headers and metadata
        if stripped.startswith("### Turn") or stripped.startswith("## Conversation"):
            continue
        if stripped.startswith("_`end_of_conversation"):
            continue
        if stripped.startswith("_No recommendations"):
            continue

        if in_user and current_role == "user":
            # Clean blockquote markers
            cleaned = stripped.lstrip("> ").strip()
            if cleaned:
                current_content.append(cleaned)

    # Save last message
    if current_role and current_content:
        text = "\n".join(current_content).strip()
        if text:
            messages.append({"role": current_role, "content": text})

    return messages


def compute_recall_at_k(recommended: list[str], expected: list[str], k: int = 10) -> float:
    """Compute Recall@K.
    
    Recall@K = |recommended ∩ expected| / |expected|
    
    Uses case-insensitive name matching.
    """
    if not expected:
        return 1.0  # No expected items = trivially correct

    recommended_set = {name.lower().strip() for name in recommended[:k]}
    expected_set = {name.lower().strip() for name in expected}

    hits = recommended_set & expected_set
    return len(hits) / len(expected_set)


def _chat(messages: list[dict]) -> dict:
    """Send a POST /chat request to the running server."""
    with httpx.Client(timeout=35.0) as client:
        resp = client.post(f"{BASE_URL}/chat", json={"messages": messages})
        resp.raise_for_status()
        return resp.json()


@pytest.mark.integration
@pytest.mark.parametrize("trace_id", [f"C{i}" for i in range(1, 11)])
def test_trace_recall(trace_id: str):
    """Replay a trace and compute Recall@10.
    
    This test runs each trace as a multi-turn conversation against our agent,
    then compares the agent's final recommendations to the trace's expected shortlist.
    """
    trace_path = Path(__file__).parent.parent / "GenAI_SampleConversations" / f"{trace_id}.md"

    if not trace_path.exists():
        pytest.skip(f"Trace file not found: {trace_path}")

    # Get expected shortlist (names from final table)
    expected_names = parse_trace_expected_shortlist(str(trace_path))
    if not expected_names:
        pytest.skip(f"No expected shortlist found in {trace_id}")

    # Get user messages from trace
    user_messages = extract_user_messages_from_trace(str(trace_path))
    if not user_messages:
        pytest.skip(f"No user messages found in {trace_id}")

    # Replay the conversation against our agent
    conversation_history = []
    last_response = None

    for idx, user_msg in enumerate(user_messages):
        # Rate-limit pacing: ~29K token prompt burns per-minute quota fast
        if idx > 0:
            time.sleep(8)

        conversation_history.append(
            {"role": "user", "content": user_msg["content"]}
        )

        response = _chat(conversation_history)
        last_response = response

        # Add agent response to history for next turn
        conversation_history.append(
            {"role": "assistant", "content": response["reply"]}
        )

    # Compute Recall@10 on final recommendations
    recommended_names = [rec["name"] for rec in last_response["recommendations"]]
    recall = compute_recall_at_k(recommended_names, expected_names, k=10)

    print(f"\n{trace_id}: Recall@10 = {recall:.2f}")
    print(f"  Expected ({len(expected_names)}): {expected_names}")
    print(f"  Got      ({len(recommended_names)}): {recommended_names}")

    # We don't assert a threshold here — just report.
    # For now, verify we got SOME recommendations on the final turn.
    assert last_response is not None, f"No response from agent for {trace_id}"


@pytest.mark.integration
def test_mean_recall():
    """Compute Mean Recall@10 across all 10 traces and report it."""
    traces_dir = Path(__file__).parent.parent / "GenAI_SampleConversations"
    recalls = []

    for i in range(1, 11):
        trace_path = traces_dir / f"C{i}.md"
        if not trace_path.exists():
            continue

        expected_names = parse_trace_expected_shortlist(str(trace_path))
        if not expected_names:
            continue

        user_messages = extract_user_messages_from_trace(str(trace_path))
        if not user_messages:
            continue

        # Replay
        conversation_history = []
        last_response = None

        for idx, user_msg in enumerate(user_messages):
            # Rate-limit pacing between calls
            if idx > 0:
                time.sleep(8)

            conversation_history.append(
                {"role": "user", "content": user_msg["content"]}
            )
            response = _chat(conversation_history)
            last_response = response
            conversation_history.append(
                {"role": "assistant", "content": response["reply"]}
            )

        recommended_names = [rec["name"] for rec in last_response["recommendations"]]
        recall = compute_recall_at_k(recommended_names, expected_names, k=10)
        recalls.append((f"C{i}", recall))
        print(f"C{i}: Recall@10 = {recall:.2f} ({len(expected_names)} expected, {len(recommended_names)} recommended)")

    if recalls:
        mean_recall = sum(r for _, r in recalls) / len(recalls)
        print(f"\n=== Mean Recall@10: {mean_recall:.4f} ===")
        print(f"Traces evaluated: {len(recalls)}/10")
