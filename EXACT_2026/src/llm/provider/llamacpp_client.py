"""
EXACT 2026 — LlamaCpp Client
Chạy model GGUF trực tiếp trên máy local (serverless, không cần Ollama).
"""
from typing import Any, Type

from langchain_community.chat_models import ChatLlamaCpp
from pydantic import BaseModel

from src.core.config import settings
from src.llm.base import BaseLLM
from src.utils.logger import logger


class LlamaCppClient(BaseLLM):
    """Client cho model GGUF chạy local qua llama-cpp-python.

    Hỗ trợ cả plain chat và structured output (qua with_structured_output).
    """

    def __init__(
        self,
        model_path: str = None,
        temperature: float = 0.0,
        n_ctx: int = None,
        n_gpu_layers: int = None,
    ):
        self.model_path = model_path or settings.llm.model_path
        self.temperature = temperature
        self.n_ctx = n_ctx or settings.llm.n_ctx
        self.n_gpu_layers = n_gpu_layers if n_gpu_layers is not None else settings.llm.n_gpu_layers

        logger.debug(
            f"LlamaCppClient initialized — model: {self.model_path}, "
            f"temp: {self.temperature}, n_ctx: {self.n_ctx}, gpu_layers: {self.n_gpu_layers}"
        )

    def get_llm(self, **kwargs) -> ChatLlamaCpp:
        """Build và trả về ChatLlamaCpp instance.

        Returns:
            Configured ChatLlamaCpp model.
        """
        logger.debug(f"Building ChatLlamaCpp (path: {self.model_path})")

        return ChatLlamaCpp(
            model_path=self.model_path,
            temperature=self.temperature,
            n_ctx=self.n_ctx,
            n_gpu_layers=self.n_gpu_layers,
            verbose=False,
            **kwargs,
        )

    def get_structured_llm(self, output_schema: Type[BaseModel]) -> Any:
        """Trả về LLM đã bind với Pydantic schema.

        Note: Với model 8B, structured output có thể không ổn định.
              Nên dùng output_parser.py (regex) thay thế khi cần.

        Args:
            output_schema: Pydantic model class.

        Returns:
            Model instance enforcing output schema.
        """
        logger.debug(f"Building structured LLM for schema: {output_schema.__name__}")
        model = self.get_llm()
        return model.with_structured_output(output_schema)
