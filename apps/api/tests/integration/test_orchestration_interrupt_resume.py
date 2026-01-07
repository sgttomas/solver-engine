"""
LLM Integration Smoke Test.

Verifies that the LLM adapter can make real API calls and return valid content.
Gate behavior tests are in test_gate_c.py and test_gate_d.py using mocked LLM.

NOTE: Requires RUN_LLM_TESTS=1 and a valid API key.
"""

import os
import pytest

# Skip entire module unless RUN_LLM_TESTS=1 is set
pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LLM_TESTS", "0") != "1",
    reason="LLM tests require RUN_LLM_TESTS=1 and valid API key"
)

from infrastructure.llm import get_llm_adapter, LLMResponse


class TestLLMAdapterIntegration:
    """Smoke tests for real LLM API calls."""

    @pytest.mark.asyncio
    async def test_llm_adapter_returns_valid_response(self):
        """LLM adapter can make a real API call and return valid content.

        This is a smoke test to verify:
        1. API key is configured correctly
        2. Model name is valid
        3. Response parsing works with real API response
        """
        adapter = get_llm_adapter()

        messages = [
            {"role": "user", "content": "Reply with exactly: HELLO"}
        ]

        response = await adapter.generate(messages)

        # Verify response structure
        assert isinstance(response, LLMResponse)
        assert isinstance(response.content, str)
        assert len(response.content) > 0
        assert response.provider == "openai"
        assert response.model is not None

    @pytest.mark.asyncio
    async def test_llm_adapter_returns_json_when_requested(self):
        """LLM can return structured JSON content.

        Verifies that the model can produce JSON output that the
        workflow would need for step artifacts.
        """
        adapter = get_llm_adapter()

        messages = [
            {"role": "user", "content": 'Return a JSON object with keys "status" and "message". Example: {"status": "ok", "message": "test"}'}
        ]

        response = await adapter.generate(messages)

        # Verify we got a response
        assert isinstance(response.content, str)
        assert len(response.content) > 0

        # Try to parse as JSON (content may have markdown fences)
        import json
        content = response.content.strip()
        # Remove markdown code fences if present
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        data = json.loads(content)
        assert "status" in data or "message" in data  # At least one expected key

