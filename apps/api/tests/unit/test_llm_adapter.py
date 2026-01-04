"""
Unit tests for LLM adapter.

Tests the OpenAI Responses API adapter with mocked httpx.
No network calls are made.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from infrastructure.llm import (
    LLMAdapter,
    LLMResponse,
    LLMConfigurationError,
    LLMProviderError,
    LLMResponseError,
    OpenAIResponsesAdapter,
    get_llm_adapter,
    get_default_adapter,
    reset_adapter,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_settings():
    """Mock settings with OpenAI configuration."""
    with patch("infrastructure.llm.settings") as mock:
        mock.default_llm_provider = "openai"
        mock.openai_api_key = "test-api-key"
        mock.openai_model = "gpt-5.2"
        yield mock


@pytest.fixture
def adapter():
    """Create a test adapter instance."""
    return OpenAIResponsesAdapter(
        api_key="test-api-key",
        model="gpt-5.2",
    )


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset adapter singleton before each test."""
    reset_adapter()
    yield
    reset_adapter()


# =============================================================================
# OpenAIResponsesAdapter Tests
# =============================================================================


class TestOpenAIResponsesAdapterInit:
    """Tests for adapter initialization."""

    def test_init_with_valid_key(self):
        """Adapter initializes with valid API key."""
        adapter = OpenAIResponsesAdapter(
            api_key="test-key",
            model="gpt-5.2",
        )
        assert adapter._api_key == "test-key"
        assert adapter._model == "gpt-5.2"
        assert adapter._base_url == "https://api.openai.com/v1/responses"

    def test_init_with_custom_base_url(self):
        """Adapter accepts custom base URL."""
        adapter = OpenAIResponsesAdapter(
            api_key="test-key",
            model="gpt-5.2",
            base_url="https://custom.api.com/v1/responses",
        )
        assert adapter._base_url == "https://custom.api.com/v1/responses"

    def test_init_without_key_raises_error(self):
        """Adapter raises LLMConfigurationError without API key."""
        with pytest.raises(LLMConfigurationError, match="API key required"):
            OpenAIResponsesAdapter(api_key="", model="gpt-5.2")

    def test_init_with_none_key_raises_error(self):
        """Adapter raises LLMConfigurationError with None API key."""
        with pytest.raises(LLMConfigurationError, match="API key required"):
            OpenAIResponsesAdapter(api_key=None, model="gpt-5.2")


class TestOpenAIResponsesAdapterGenerate:
    """Tests for the generate method."""

    @pytest.mark.asyncio
    async def test_generate_uses_responses_endpoint(self, adapter):
        """Generate calls /v1/responses endpoint."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "output_text": "Test response",
            "model": "gpt-5.2",
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await adapter.generate([{"role": "user", "content": "Hello"}])

            # Verify endpoint
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "https://api.openai.com/v1/responses"

    @pytest.mark.asyncio
    async def test_generate_uses_input_key(self, adapter):
        """Generate sends messages as 'input' not 'messages'."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"output_text": "Response"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            messages = [{"role": "user", "content": "Hello"}]
            await adapter.generate(messages)

            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]

            # Verify 'input' key is used, not 'messages'
            assert "input" in payload
            assert payload["input"] == messages
            assert "messages" not in payload

    @pytest.mark.asyncio
    async def test_generate_uses_correct_model(self, adapter):
        """Generate includes model in payload."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"output_text": "Response"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await adapter.generate([{"role": "user", "content": "Hello"}])

            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]
            assert payload["model"] == "gpt-5.2"

    @pytest.mark.asyncio
    async def test_generate_returns_llm_response(self, adapter):
        """Generate returns properly structured LLMResponse."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "output_text": "Test response content",
            "model": "gpt-5.2",
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await adapter.generate([{"role": "user", "content": "Hello"}])

            assert isinstance(result, LLMResponse)
            assert result.content == "Test response content"
            assert result.provider == "openai"
            assert result.model == "gpt-5.2"
            assert result.usage == {"input_tokens": 10, "output_tokens": 20}

    @pytest.mark.asyncio
    async def test_generate_handles_api_error(self, adapter):
        """Generate raises LLMProviderError on non-200 response."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(LLMProviderError) as exc_info:
                await adapter.generate([{"role": "user", "content": "Hello"}])

            assert exc_info.value.status_code == 429
            assert "Rate limit exceeded" in exc_info.value.response_body

    @pytest.mark.asyncio
    async def test_generate_validates_messages_type(self, adapter):
        """Generate raises LLMResponseError if messages is not a list."""
        with pytest.raises(LLMResponseError, match="must be a list"):
            await adapter.generate("not a list")

    @pytest.mark.asyncio
    async def test_generate_includes_optional_params(self, adapter):
        """Generate includes optional parameters in payload."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"output_text": "Response"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await adapter.generate(
                [{"role": "user", "content": "Hello"}],
                temperature=0.7,
                max_output_tokens=1000,
            )

            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]
            assert payload["temperature"] == 0.7
            assert payload["max_output_tokens"] == 1000


class TestContentExtraction:
    """Tests for response content extraction."""

    @pytest.mark.asyncio
    async def test_extract_output_text(self, adapter):
        """Extracts content from output_text field."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "output_text": "Direct output text",
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await adapter.generate([{"role": "user", "content": "Hello"}])
            assert result.content == "Direct output text"

    @pytest.mark.asyncio
    async def test_extract_from_output_array(self, adapter):
        """Extracts content from output array with text field."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "output": [{"text": "Text from output array"}],
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await adapter.generate([{"role": "user", "content": "Hello"}])
            assert result.content == "Text from output array"

    @pytest.mark.asyncio
    async def test_extract_from_nested_content(self, adapter):
        """Extracts content from nested content array."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "output": [
                {
                    "content": [
                        {"type": "output_text", "text": "Nested text content"},
                    ]
                }
            ],
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await adapter.generate([{"role": "user", "content": "Hello"}])
            assert result.content == "Nested text content"

    @pytest.mark.asyncio
    async def test_extract_raises_on_empty_response(self, adapter):
        """Raises LLMResponseError when no content can be extracted."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"output": []}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(LLMResponseError, match="Could not extract content"):
                await adapter.generate([{"role": "user", "content": "Hello"}])


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestGetLLMAdapter:
    """Tests for factory function."""

    def test_returns_openai_adapter(self, mock_settings):
        """Factory returns OpenAI adapter when configured."""
        adapter = get_llm_adapter()
        assert isinstance(adapter, OpenAIResponsesAdapter)

    def test_raises_for_unsupported_provider(self, mock_settings):
        """Factory raises NotImplementedError for unsupported providers."""
        mock_settings.default_llm_provider = "anthropic"

        with pytest.raises(NotImplementedError, match="not yet supported"):
            get_llm_adapter()

    def test_raises_for_missing_api_key(self, mock_settings):
        """Factory raises LLMConfigurationError for missing API key."""
        mock_settings.openai_api_key = None

        with pytest.raises(LLMConfigurationError, match="OPENAI_API_KEY"):
            get_llm_adapter()

    def test_explicit_provider_override(self, mock_settings):
        """Factory accepts explicit provider override."""
        adapter = get_llm_adapter(provider="openai")
        assert isinstance(adapter, OpenAIResponsesAdapter)

    def test_explicit_unsupported_provider(self, mock_settings):
        """Factory raises NotImplementedError for explicit unsupported provider."""
        with pytest.raises(NotImplementedError, match="google"):
            get_llm_adapter(provider="google")


class TestGetDefaultAdapter:
    """Tests for singleton accessor."""

    def test_returns_singleton(self, mock_settings):
        """get_default_adapter returns same instance."""
        adapter1 = get_default_adapter()
        adapter2 = get_default_adapter()
        assert adapter1 is adapter2

    def test_reset_clears_singleton(self, mock_settings):
        """reset_adapter clears the cached instance."""
        adapter1 = get_default_adapter()
        reset_adapter()
        adapter2 = get_default_adapter()
        assert adapter1 is not adapter2
