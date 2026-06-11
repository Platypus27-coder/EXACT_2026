"""
EXACT 2026 — Embedding Factory
Quản lý embedding model (BAAI/bge-m3) cho RAG pipeline.
"""
from src.core.config import settings
from src.utils.logger import logger
from llama_index.embeddings.huggingface import HuggingFaceEmbedding


class EmbeddingFactory:
    """Factory tạo embedding model từ HuggingFace."""

    def __init__(self):
        self.model_name = settings.embedding.model_name

    def get_embedding(self) -> HuggingFaceEmbedding:
        """Load và trả về embedding model.

        Returns:
            HuggingFaceEmbedding instance.
        """
        if not self.model_name:
            self.model_name = "BAAI/bge-m3"

        import torch
        device = "cuda:1" if torch.cuda.device_count() > 1 else ("cuda:0" if torch.cuda.is_available() else "cpu")

        logger.info(f"Loading embedding model: {self.model_name} on {device}")

        return HuggingFaceEmbedding(
            model_name=self.model_name,
            device=device,
        )
