"""
Pydantic models matching the PDF's non-negotiable API schema exactly.

Request:  POST /chat  { "messages": [{"role": "user"|"assistant", "content": "..."}] }
Response: { "reply": str, "recommendations": [{name, url, test_type}], "end_of_conversation": bool }
"""

from typing import Literal
from pydantic import BaseModel


class Message(BaseModel):
    """A single message in the conversation history."""
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """POST /chat request body. Carries full conversation history (stateless)."""
    messages: list[Message]


class Recommendation(BaseModel):
    """A single assessment recommendation. All fields constructed from catalog lookup."""
    name: str
    url: str
    test_type: str  # "K", "A,S", "P,C" etc. — format controlled by config.TEST_TYPE_PRIMARY_ONLY


class ChatResponse(BaseModel):
    """POST /chat response body. Schema is non-negotiable per PDF."""
    reply: str
    recommendations: list[Recommendation]
    end_of_conversation: bool
