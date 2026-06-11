"""
EXACT 2026 — GGUF Client (Llama.cpp)
Tai model GGUF truc tiep tu HuggingFace, chay tren GPU qua Llama.cpp.
Chong OOM tuyet doi.
"""
import os
from typing import Any, Type

from pydantic import BaseModel
from langchain_community.llms.llama_cpp import LlamaCpp
from langchain_core.language_models.chat_models import BaseChatModel
from huggingface_hub import hf_hub_download

from src.core.config import settings
from src.llm.base import BaseLLM
from src.utils.logger import logger

class GGUFClient(BaseLLM):
    """Client cho model GGUF thong qua llama-cpp-python."""

    _instance = None  # Singleton

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(GGUFClient, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        repo_id: str = "Qwen/Qwen2.5-7B-Instruct-GGUF",
        filename: str = "*q4_k_m*.gguf",
        temperature: float = 0.0,
        max_new_tokens: int = None,
    ):
        if getattr(self, "_initialized", False):
            return
            
        self.repo_id = repo_id
        self.filename = filename
        self.temperature = temperature
        self.max_new_tokens = max_new_tokens or settings.llm.max_new_tokens

        self._llm = None
        self._initialized = True

    def _load_model(self):
        """Tai file GGUF va khoi tao LlamaCpp (chi chay 1 lan)."""
        if self._llm is not None:
            return

        logger.info(f"Dang tai model GGUF: {self.repo_id} ({self.filename}) ...")
        logger.info("Neu chua co san, he thong se tu dong tai tu HuggingFace Hub.")

        # Tu dong tai file .gguf tu repo
        try:
            model_path = hf_hub_download(
                repo_id=self.repo_id,
                filename=self.filename,
            )
        except Exception as e:
            # Thu tai kieu cu the hon neu wildcard fail
            logger.warning(f"Wildcard tai GGUF that bai, thu tai ten cu the. Chi tiet: {e}")
            model_path = hf_hub_download(
                repo_id=self.repo_id,
                filename="qwen2.5-7b-instruct-q4_k_m.gguf",
            )

        logger.info(f"File GGUF da san sang tai: {model_path}")
        logger.info("Dang load vao LlamaCpp (n_gpu_layers=-1 -> FULL GPU) ...")

        # Khoi tao LlamaCpp
        self._llm = LlamaCpp(
            model_path=model_path,
            n_gpu_layers=-1,      # Ep toan bo model vao GPU
            n_ctx=4096,           # Context window du dung
            max_tokens=self.max_new_tokens,
            temperature=self.temperature,
            echo=False,
            # Neu chay tren local bi OOM, ban co the doi n_gpu_layers=20 de day bot sang CPU
        )

        logger.info(f"[OK] Model GGUF da san sang hoat dong!")

    def get_llm(self, **kwargs) -> Any:
        """Tra ve LlamaCpp instance (tu dong load neu chua co)."""
        self._load_model()
        return self._llm

    def get_structured_llm(self, output_schema: Type[BaseModel]) -> Any:
        self._load_model()
        raise NotImplementedError("GGUF Client khong ho tro with_structured_output truc tiep. Dung output_parser.py thay the.")
