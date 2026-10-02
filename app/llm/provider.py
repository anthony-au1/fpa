from typing import Protocol, TypeVar

from pydantic import BaseModel

OutputT = TypeVar("OutputT", bound=BaseModel)


class ModelUnavailable(RuntimeError):
    pass


class ModelProvider(Protocol):
    async def generate_structured(
        self, *, instructions: str, untrusted_content: str, output_type: type[OutputT]
    ) -> OutputT: ...


class DisabledModelProvider:
    async def generate_structured(
        self, *, instructions: str, untrusted_content: str, output_type: type[OutputT]
    ) -> OutputT:
        raise ModelUnavailable(
            "LLM provider is disabled; configure an approved provider explicitly"
        )
