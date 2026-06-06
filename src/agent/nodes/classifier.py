"""
EXACT 2026 — Classifier Node
Phân loại câu hỏi thành logic (Type 1) hoặc physics (Type 2).
"""
import time

from src.agent.state import AgentState
from src.utils.logger import logger


def classify_node(state: AgentState) -> dict:
    """Phân loại câu hỏi dựa trên cấu trúc input.

    Logic phân loại:
    - Có premises (danh sách giả thiết) → Type 1 (Logic)
    - Không có premises → Type 2 (Physics)
    - Nếu có type hint từ API request → dùng luôn

    Args:
        state: Trạng thái hiện tại.

    Returns:
        Dict cập nhật task_type và time_started.
    """
    premises = state.get("premises", [])

    # Ghi nhận thời gian bắt đầu để quản lý budget 60 giây
    time_started = time.time()

    if premises:
        task_type = "logic"
        logger.info(f"Phân loại: LOGIC (phát hiện {len(premises)} premises)")
    else:
        task_type = "physics"
        logger.info("Phân loại: PHYSICS (không có premises)")

    return {
        "task_type": task_type,
        "time_started": time_started,
    }


def route_after_classify(state: AgentState) -> str:
    """Router — quyet dinh nhanh nao chay sau phan loai.

    Logic: -> solver truoc (direct chi khi solver fail)
    Physics: -> RAG truoc -> solver -> direct (neu can)

    Returns:
        Node name can chay tiep.
    """
    task_type = state.get("task_type", "logic")

    if task_type == "physics":
        return "physics_rag"
    else:
        return "logic_solver_branch"
