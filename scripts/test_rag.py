import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from src.core.config import settings
from src.retrieval.engine import Retriever
from src.utils.logger import logger

def test_retrieval():
    question = (
        "An object with a height of 4 cm is placed perpendicularly on the principal axis of a converging lens, "
        "at a distance of 30 cm from the lens. The focal length of the lens is f = 20 cm. Calculate the distance "
        "from the image to the lens and determine the height of the resulting image."
    )
    
    print("Initializing Retriever...")
    retriever = Retriever()
    
    print("\nRunning Retrieval...")
    # Lấy tài liệu thô ban đầu (chưa lọc threshold trong engine để xem score thực tế)
    k = settings.retrieval.top_k
    collection_name = settings.storage.collection_name
    
    # Chạy tương tự logic trong engine.py
    hybrid_retriever = retriever.vector_db.get_hybrid_retriever(
        similarity_top_k=k,
        collection_name=collection_name,
    )
    
    if hybrid_retriever is None:
        print("Error: Retriever is None. Make sure Vector DB is initialized.")
        return
        
    initial_nodes = hybrid_retriever.retrieve(question)
    print(f"Retrieved {len(initial_nodes)} initial candidates.")
    
    print("\nReranking...")
    reranked_nodes = retriever.reranker.postprocess_nodes(
        initial_nodes,
        query_str=question,
    )
    
    print(f"\nTop {len(reranked_nodes)} Reranked Documents:")
    for i, node in enumerate(reranked_nodes):
        print(f"\n[{i+1}] Score: {node.score}")
        print(f"Content snippet: {node.node.get_content()[:200]}...")

if __name__ == "__main__":
    test_retrieval()
