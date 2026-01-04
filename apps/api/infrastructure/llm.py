"""
SOLVER API - LLM Infrastructure Adapter

OpenAI Responses API adapter per P5.1 specification.
Uses httpx for direct API calls to /v1/responses endpoint.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import httpx

from config import settings


# =============================================================================
# Exceptions
# =============================================================================


class LLMError(Exception):
    """Base exception for LLM adapter errors."""

    pass


class LLMConfigurationError(LLMError):
    """Error in LLM configuration (missing key, invalid model, etc.)."""

    pass


class LLMProviderError(LLMError):
    """Error from LLM provider (rate limit, API error, etc.)."""

    def __init__(self, message: str, status_code: int, response_body: str):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class LLMResponseError(LLMError):
    """Error parsing or validating LLM response."""

    def __init__(self, message: str, raw_response: dict):
        super().__init__(message)
        self.raw_response = raw_response


# =============================================================================
# Response Container
# =============================================================================


@dataclass
class LLMResponse:
    """Standardized response from LLM calls."""

    content: str
    provider: str
    model: str
    usage: dict | None = None
    raw: dict | None = None  # For debugging


# =============================================================================
# Abstract Base Class
# =============================================================================


class LLMAdapter(ABC):
    """Base adapter for LLM providers.

    Stateless adapter - receives all context via method parameters.
    Configuration is injected at construction time.
    """

    @abstractmethod
    async def generate(
        self,
        messages: list[dict],
        **kwargs,
    ) -> LLMResponse:
        """Generate completion from messages.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            **kwargs: Provider-specific options (temperature, max_tokens, etc.)

        Returns:
            LLMResponse with generated content.

        Raises:
            LLMProviderError: If API call fails.
            LLMResponseError: If response cannot be parsed.
        """
        pass


# =============================================================================
# OpenAI Responses API Adapter
# =============================================================================


class OpenAIResponsesAdapter(LLMAdapter):
    """OpenAI adapter using Responses API (/v1/responses).

    Note: This uses the Responses API, not the Chat Completions API.
    The payload uses 'input' instead of 'messages'.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1/responses",
    ):
        """Initialize OpenAI Responses adapter.

        Args:
            api_key: OpenAI API key (required).
            model: Model identifier (e.g., 'gpt-5.2').
            base_url: API endpoint URL.

        Raises:
            LLMConfigurationError: If api_key is missing.
        """
        if not api_key:
            raise LLMConfigurationError("OpenAI API key required")
        self._api_key = api_key
        self._model = model
        self._base_url = base_url

    async def generate(
        self,
        messages: list[dict],
        **kwargs,
    ) -> LLMResponse:
        """Generate completion using OpenAI Responses API.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            **kwargs: Optional parameters:
                - temperature: Sampling temperature (0-2).
                - max_output_tokens: Maximum tokens in response.
                - metadata: Additional metadata for the request.

        Returns:
            LLMResponse with generated content.

        Raises:
            LLMProviderError: If API returns non-200 status.
            LLMResponseError: If response cannot be parsed.
        """
        # Validate input
        if not isinstance(messages, list):
            raise LLMResponseError(
                "messages must be a list",
                raw_response={"input": messages},
            )

        # Build payload for Responses API
        # Note: Responses API uses 'input' not 'messages'
        payload: dict = {
            "model": self._model,
            "input": messages,
        }

        # Add optional parameters
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        if "max_output_tokens" in kwargs:
            payload["max_output_tokens"] = kwargs["max_output_tokens"]
        if "metadata" in kwargs:
            payload["metadata"] = kwargs["metadata"]

        # Make API request
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._base_url,
                json=payload,
                headers=headers,
                timeout=120.0,  # 2 minute timeout for long generations
            )

        # Handle non-200 responses
        if response.status_code != 200:
            raise LLMProviderError(
                f"OpenAI API error: {response.status_code}",
                status_code=response.status_code,
                response_body=response.text,
            )

        # Parse response
        resp_data = response.json()

        # Extract content from response
        # Responses API may return:
        # 1. output_text (string) - direct text output
        # 2. output (list) - list of content items
        content = self._extract_content(resp_data)

        return LLMResponse(
            content=content,
            provider="openai",
            model=resp_data.get("model", self._model),
            usage=resp_data.get("usage"),
            raw=resp_data,
        )

    def _extract_content(self, resp_data: dict) -> str:
        """Extract content from Responses API response.

        Tries multiple paths:
        1. output_text (if present and non-empty)
        2. output[0].content with type == 'output_text' or 'text'
        3. output[0].content[0].text (nested structure)

        Args:
            resp_data: Parsed JSON response from API.

        Returns:
            Extracted text content.

        Raises:
            LLMResponseError: If no content can be extracted.
        """
        # Path 1: Direct output_text field
        if "output_text" in resp_data and resp_data["output_text"]:
            return resp_data["output_text"]

        # Path 2: output array
        output = resp_data.get("output", [])
        if isinstance(output, list) and len(output) > 0:
            first_output = output[0]

            # Check for content field
            if isinstance(first_output, dict):
                # Direct text in content
                if "text" in first_output:
                    return first_output["text"]

                # Content array
                content = first_output.get("content", [])
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict):
                            # Look for output_text or text type
                            if item.get("type") in ("output_text", "text"):
                                if "text" in item:
                                    return item["text"]
                            # Direct text field
                            if "text" in item:
                                return item["text"]

        # No content found
        raise LLMResponseError(
            "Could not extract content from response",
            raw_response=resp_data,
        )


# =============================================================================
# Factory Functions
# =============================================================================


def get_llm_adapter(provider: str | None = None) -> LLMAdapter:
    """Factory function to get appropriate LLM adapter.

    Args:
        provider: Explicit provider name, or None to use default from settings.

    Returns:
        Configured LLMAdapter instance.

    Raises:
        NotImplementedError: If provider is not 'openai'.
        LLMConfigurationError: If API key is not configured.
    """
    provider = provider or settings.default_llm_provider

    if provider != "openai":
        raise NotImplementedError(
            f"Provider '{provider}' not yet supported. Only 'openai' is available."
        )

    if not settings.openai_api_key:
        raise LLMConfigurationError(
            "OPENAI_API_KEY not configured. Set the environment variable."
        )

    return OpenAIResponsesAdapter(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
    )


# Module-level singleton (lazy initialization)
_adapter: LLMAdapter | None = None


def get_default_adapter() -> LLMAdapter:
    """Get cached default adapter instance.

    Returns:
        Singleton LLMAdapter instance.

    Raises:
        NotImplementedError: If default provider is not 'openai'.
        LLMConfigurationError: If API key is not configured.
    """
    global _adapter
    if _adapter is None:
        _adapter = get_llm_adapter()
    return _adapter


def reset_adapter() -> None:
    """Reset the cached adapter instance.

    Useful for testing or reconfiguration.
    """
    global _adapter
    _adapter = None
