"""
EXACT 2026 — Abstract Base Class cho LLM Providers.
Mọi provider (LlamaCpp, Ollama, Mock...) phải implement interface này.
"""
from abc import ABC, abstractmethod
from typing import Any, Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseLLM(ABC):
    """Abstract base class cho tất cả LLM provider clients."""

    @abstractmethod
    def get_llm(self, **kwargs) -> Any:
        """Trả về LLM instance cho plain chat completions.

        Returns:
            Chat model object sẵn sàng gọi .invoke()
        """
        ...

    @abstractmethod
    def get_structured_llm(self, output_schema: Type[T]) -> Any:
        """Trả về LLM đã bind với Pydantic schema cho structured output.

        Args:
            output_schema: Pydantic model class định nghĩa output format.

        Returns:
            Model instance tự động parse response theo schema.
        """
        ...
