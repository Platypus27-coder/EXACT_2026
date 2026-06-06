"""
EXACT 2026 — Agent State
Định nghĩa trạng thái chia sẻ giữa tất cả nodes trong LangGraph pipeline.

CẢI TIẾN so với code cũ:
- Thêm retry_count để theo dõi số lần retry
- Thêm time_started để quản lý budget 60 giây
- Tách rõ solver_answer vs direct_answer
"""
from typing import TypedDict, Literal, Optional


class SolverResult(TypedDict, total=False):
    """Kết quả từ nhánh Symbolic Solver (Z3/SymPy)."""
    generated_code: str          # Code Z3 hoặc SymPy do LLM sinh
    code_output: str             # stdout từ việc chạy code
    answer: str                  # Đáp án đã parse từ code output
    success: bool                # Solver chạy thành công?
    retry_count: int             # Số lần đã retry


class DirectResult(TypedDict, total=False):
    """Kết quả từ nhánh LLM Direct (fallback)."""
    answer: str                  # Đáp án từ LLM suy luận trực tiếp
    explanation: str             # Giải thích từ LLM
    raw_response: str            # Response gốc


class FinalAnswer(TypedDict, total=False):
    """Kết quả cuối cùng — format chuẩn EXACT 2026."""
    answer: str                  # Đáp án chính xác
    explanation: str             # Giải thích chi tiết
    fol: str                     # First-Order Logic (optional)
    cot: list[str]               # Chain-of-Thought steps (optional)
    premises: list[str]          # Danh sách premises đã dùng (optional)
    confidence: float            # Confidence score 0.0 - 1.0


class AgentState(TypedDict, total=False):
    """
    Trạng thái toàn cục của pipeline LangGraph.
    Single Source of Truth cho mỗi lượt xử lý.
    """
    # ── Input ──
    question: str                # Câu hỏi gốc
    premises: list[str]          # Giả thiết (Type 1 - Logic)
    collection_name: str         # Collection name cho RAG

    # ── Classification ──
    task_type: Literal["logic", "physics"]

    # ── RAG Context ──
    context: str                 # Ngữ cảnh từ RAG (chỉ physics)

    # ── Solver Branch Results ──
    solver_result: SolverResult  # Kết quả từ Z3/SymPy

    # ── Direct Branch Results ──
    direct_result: DirectResult  # Kết quả từ LLM direct

    # ── Final Output ──
    final_answer: FinalAnswer    # Đáp án cuối cùng

    # ── Control ──
    error: str                   # Lỗi nếu có
    time_started: float          # Timestamp bắt đầu (cho timeout control)
