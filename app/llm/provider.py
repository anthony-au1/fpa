import json
from collections.abc import Sequence
from typing import Any, Protocol, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

OutputT = TypeVar("OutputT", bound=BaseModel)


class ModelError(RuntimeError):
    retryable = False


class ModelUnavailable(ModelError):
    pass


class ModelTransientError(ModelError):
    retryable = True


class MalformedModelOutput(ModelError):
    retryable = True


class ModelProvider(Protocol):
    async def generate_structured(
        self, *, instructions: str, untrusted_content: str, output_type: type[OutputT]
    ) -> OutputT: ...


class DisabledModelProvider:
    async def generate_structured(
        self, *, instructions: str, untrusted_content: str, output_type: type[OutputT]
    ) -> OutputT:
        raise ModelUnavailable("LLM provider is disabled; configure a provider explicitly")


class OpenAICompatibleModelProvider:
    def __init__(self, *, model: str, api_key: str, base_url: str, timeout_seconds: float) -> None:
        if not model or not api_key or not base_url:
            raise ModelUnavailable(
                "openai_compatible requires LLM_MODEL, LLM_API_KEY, and LLM_BASE_URL"
            )
        self.model = model
        self.api_key = api_key
        self.endpoint = f"{base_url.rstrip('/')}/chat/completions"
        self.timeout_seconds = timeout_seconds

    async def generate_structured(
        self, *, instructions: str, untrusted_content: str, output_type: type[OutputT]
    ) -> OutputT:
        request = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": untrusted_content},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": output_type.__name__,
                    "strict": True,
                    "schema": output_type.model_json_schema(),
                },
            },
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    self.endpoint,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=request,
                )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise ModelTransientError(
                "Model provider request timed out or was unavailable"
            ) from exc
        if response.status_code in {408, 409, 429} or response.status_code >= 500:
            raise ModelTransientError(f"Model provider returned HTTP {response.status_code}")
        if response.is_error:
            raise ModelUnavailable(f"Model provider returned HTTP {response.status_code}")
        try:
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
            raw = json.loads(content) if isinstance(content, str) else content
            return output_type.model_validate(raw)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValidationError) as exc:
            raise MalformedModelOutput("Model response failed structured validation") from exc


class FakeModelProvider:
    """Deterministic test provider. Values may be valid payloads or exceptions."""

    def __init__(self, responses: Sequence[dict[str, Any] | BaseException]) -> None:
        if not responses:
            raise ValueError("FakeModelProvider requires at least one response")
        self._responses = list(responses)
        self.call_count = 0

    async def generate_structured(
        self, *, instructions: str, untrusted_content: str, output_type: type[OutputT]
    ) -> OutputT:
        del instructions, untrusted_content
        index = min(self.call_count, len(self._responses) - 1)
        self.call_count += 1
        response = self._responses[index]
        if isinstance(response, BaseException):
            raise response
        try:
            return output_type.model_validate(response)
        except ValidationError as exc:
            raise MalformedModelOutput("Fake model output failed validation") from exc


def create_model_provider(settings) -> ModelProvider:
    if settings.llm_provider == "disabled":
        return DisabledModelProvider()
    if settings.llm_provider == "openai_compatible":
        return OpenAICompatibleModelProvider(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout_seconds=settings.llm_timeout_seconds,
        )
    raise ModelUnavailable(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")
