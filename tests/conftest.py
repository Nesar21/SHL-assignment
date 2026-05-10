"""
Pytest configuration for SHL Assessment Advisor tests.

Configures:
  - Custom marker registration for 'integration' tests
  - Shared catalog/LLM setup for integration tests
"""

import pytest
from app import catalog, llm


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: marks tests requiring live LLM (GEMINI_API_KEY)")


_setup_done = False


@pytest.fixture(autouse=True)
def ensure_setup():
    """Ensure catalog and LLM are initialized before any test.
    
    Uses module-level flag to avoid repeated initialization.
    """
    global _setup_done
    if not _setup_done:
        catalog.load()
        llm.initialize()
        _setup_done = True
