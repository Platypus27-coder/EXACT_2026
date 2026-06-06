"""
EXACT 2026 — Nap du lieu vao Vector DB
Chay script nay 1 lan de nap kien thuc vat ly vao Qdrant.

Su dung:
    python scripts/ingest_knowledge.py

Tren Colab:
    %run scripts/ingest_knowledge.py
"""
import json
import sys
from pathlib import Path

# Dam bao import duoc src/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config import settings
from src.utils.logger import logger


def load_physics_knowledge():
    return []


def load_physics_training_data():
    """Doc du lieu training physics lam them ngu lieu cho RAG."""
    train_file = PROJECT_ROOT / "data" / "sft_dataset" / "train.jsonl"
    if not train_file.exists():
        logger.warning(f"Khong tim thay file training: {train_file}")
        return []

    docs = []
    with open(train_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            # Lay phan question + answer tu conversations
            messages = item.get("conversations", [])
            question = ""
            answer = ""
            for msg in messages:
                if msg.get("role") == "user":
                    question = msg.get("content", "")
                elif msg.get("role") == "assistant":
                    answer = msg.get("content", "")

            if question and answer:
                docs.append({
                    "topic": f"Bai tap: {question[:80]}",
                    "content": f"Cau hoi: {question}\nLoi giai: {answer}"
                })

    logger.info(f"Da doc {len(docs)} bai tap tu train.jsonl")
    return docs


def ingest_to_vector_db(documents: list):
    """Nap documents vao Qdrant Vector DB."""
    from llama_index.core import Document, VectorStoreIndex, Settings as LlamaSettings
    from src.llm.embedding import EmbeddingFactory
    from src.retrieval.vector_db import VectorDBManager

    # Setup embedding
    embed_model = EmbeddingFactory().get_embedding()
    LlamaSettings.embed_model = embed_model

    # Tao documents cho LlamaIndex
    llama_docs = []
    for doc in documents:
        llama_docs.append(Document(
            text=doc["content"],
            metadata={"topic": doc["topic"]},
        ))

    logger.info(f"Dang nap {len(llama_docs)} documents vao Vector DB...")

    # Khoi tao Vector DB
    db_manager = VectorDBManager(embed_model=embed_model)
    collection_name = settings.storage.collection_name

    # Tao index va nap du lieu
    db_manager.add_documents(
        collection_name=collection_name,
        documents=llama_docs,
    )

    logger.info(f"[OK] Da nap {len(llama_docs)} documents vao collection '{collection_name}'")
    return len(llama_docs)


def main():
    """Nap toan bo kien thuc vao Vector DB."""
    logger.info("=== BAT DAU NAP DU LIEU VAO VECTOR DB ===")

    # 1. Load kien thuc vat ly (cong thuc)
    knowledge = load_physics_knowledge()

    # 2. Load bai tap training (optional)
    training_data = load_physics_training_data()

    # 3. Gop lai
    all_docs = knowledge + training_data
    if not all_docs:
        logger.error("Khong co du lieu de nap!")
        return

    logger.info(f"Tong cong: {len(all_docs)} documents ({len(knowledge)} cong thuc + {len(training_data)} bai tap)")

    # 4. Nap vao Vector DB
    total = ingest_to_vector_db(all_docs)

    logger.info("=== HOAN TAT ===")
    logger.info(f"Da nap {total} documents. RAG san sang su dung!")


if __name__ == "__main__":
    main()
