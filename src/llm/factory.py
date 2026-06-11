"""
EXACT 2026 — LLM Factory
Tao LLM client — mac dinh dung HuggingFace (tu dong tai model).
"""
import os
from typing import Literal

from src.core.config import settings
from src.utils.logger import logger


class LLMFactory:
    """Factory pattern — tao LLM client dua tren config."""

    _shared_client = None  # Cache de khong load model nhieu lan

    @staticmethod
    def create_client(
        purpose: Literal["reasoning", "code", "summary", "classifier"] = "reasoning",
        model_id: str = None,
    ):
        """Tao LLM client.

        Mac dinh dung HuggingFace (tu dong tai model tu Hub).
        Neu USE_MOCK_LLM=true, tra ve MockLLMClient de test offline.

        Args:
            purpose: Muc dich su dung (reasoning, code, summary, classifier).
            model_id: Model ID tren HuggingFace (neu None, dung tu config).

        Returns:
            LLM client instance.
        """
        # Check mock mode
        use_mock = os.getenv("USE_MOCK_LLM", "false").lower() == "true"
        if use_mock:
            from src.llm.provider.mock_client import MockLLMClient
            logger.warning("[MOCK] USING MOCK LLM CLIENT (Offline Mode)")
            return MockLLMClient()

        # Check GGUF mode
        use_gguf = os.getenv("USE_GGUF", "false").lower() == "true"
        if use_gguf:
            if LLMFactory._shared_client is None:
                from src.llm.provider.gguf_client import GGUFClient
                logger.info(f"Khoi tao GGUF client (Llama.cpp) cho {purpose.upper()}")
                LLMFactory._shared_client = GGUFClient()
            return LLMFactory._shared_client

        # Dung chung 1 client (singleton) de khong load model nhieu lan
        if LLMFactory._shared_client is None:
            from src.llm.provider.hf_client import HuggingFaceClient
            resolved_id = model_id or settings.llm.model_id
            logger.info(f"Khoi tao HuggingFace client cho {purpose.upper()} — model: {resolved_id}")
            LLMFactory._shared_client = HuggingFaceClient(model_id=resolved_id)

        return LLMFactory._shared_client
