"""
EXACT 2026 — Retrieval Engine
Hybrid search + Reranking cho RAG pipeline.
Tu dong nap kien thuc vat ly vao Vector DB neu chua co.
"""
import json
from pathlib import Path

from src.core.config import settings
from src.utils.logger import logger
from src.retrieval.vector_db import VectorDBManager
from src.llm.embedding import EmbeddingFactory
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.core import Document

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Retriever:
    """Retriever chinh: Hybrid Search (BM25 + Vector) -> Rerank -> Top N.

    Tu dong nap du lieu vao Vector DB lan dau su dung.
    """

    _instance = None  # Singleton
    _initialized = False

    def __init__(self):
        embed_factory = EmbeddingFactory()
        self.embedding_model = embed_factory.get_embedding()
        self.vector_db = VectorDBManager(embedding_model=self.embedding_model)

        # Khoi tao Reranker
        rerank_model = settings.rag.reranker
        rerank_top_n = settings.retrieval.rerank_top_n
        logger.info(f"Loading reranker: {rerank_model} (top_n={rerank_top_n})")
        self.reranker = SentenceTransformerRerank(
            model=rerank_model,
            top_n=rerank_top_n,
            device="cpu",  # [TEST BRANCH] Ép Reranker chạy trên CPU để tránh OOM
        )

        # Tu dong nap du lieu neu Vector DB trong
        self._auto_ingest_if_empty()

        logger.info("[OK] Retriever initialized")

    def _auto_ingest_if_empty(self):
        """Kiem tra Vector DB, neu trong thi tu dong nap kien thuc."""
        collection_name = settings.storage.collection_name
        index = self.vector_db.get_index(collection_name)

        if index is not None:
            logger.info(f"Vector DB '{collection_name}' da co du lieu, khong can nap lai")
            return

        logger.info("Vector DB trong, tu dong nap kien thuc vat ly...")
        documents = self._load_all_knowledge()

        if not documents:
            logger.warning("[WARN] Khong co du lieu de nap vao Vector DB")
            return

        self.vector_db.add_documents(
            documents=documents,
            collection_name=collection_name,
        )
        logger.info(f"[OK] Da tu dong nap {len(documents)} documents vao Vector DB")

    def _load_all_knowledge(self):
        """Load toan bo kien thuc tu cac file co san."""
        docs = []

        # 2. Load bai tap training tu sft_dataset
        train_file = _PROJECT_ROOT / "data" / "sft_dataset" / "train.jsonl"
        if train_file.exists():
            count = 0
            with open(train_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    item = json.loads(line)
                    messages = item.get("conversations", [])
                    question = ""
                    answer = ""
                    for msg in messages:
                        if msg.get("role") == "user":
                            question = msg.get("content", "")
                        elif msg.get("role") == "assistant":
                            answer = msg.get("content", "")
                    if question and answer:
                        docs.append(Document(
                            text=f"Cau hoi: {question}\nLoi giai: {answer}",
                            metadata={"topic": question[:80], "source": "training_data"},
                        ))
                        count += 1
            logger.info(f"  Load {count} bai tap tu train.jsonl")

        return docs

    def retrieval(
        self,
        query: str,
        collection_name: str = None,
        k: int = None,
        mode: str = "hybrid",
    ):
        """Retrieve documents + rerank.

        Args:
            query: Truy van tim kiem.
            collection_name: Ten collection trong Qdrant.
            k: So candidates ban dau.
            mode: "hybrid" hoac "vector".

        Returns:
            List cac documents da rerank.
        """
        if collection_name is None:
            collection_name = settings.storage.collection_name
        if k is None:
            k = settings.retrieval.top_k

        # 1. Lay retriever
        if mode == "hybrid":
            logger.info(f"[Hybrid Search] Top {k} cho: {query[:80]}...")
            retriever = self.vector_db.get_hybrid_retriever(
                similarity_top_k=k,
                collection_name=collection_name,
            )
        else:
            logger.info(f"[Vector Search] Top {k} cho: {query[:80]}...")
            retriever = self.vector_db.get_retriever(
                similarity_top_k=k,
                collection_name=collection_name,
            )

        if retriever is None:
            logger.warning("[WARN] Khong co index, tra ve rong")
            return []

        try:
            # 2. Initial retrieval
            initial_nodes = retriever.retrieve(query)
            logger.info(f"Retrieved {len(initial_nodes)} initial candidates")

            if not initial_nodes:
                return []

            # 3. Reranking
            logger.info(f"Reranking voi {settings.rag.reranker}...")
            reranked_nodes = self.reranker.postprocess_nodes(
                initial_nodes,
                query_str=query,
            )

            logger.info(f"[OK] Reranked -> {len(reranked_nodes)} documents")
            return reranked_nodes

        except Exception as e:
            logger.error(f"[ERROR] Retrieval error: {e}")
            return []
