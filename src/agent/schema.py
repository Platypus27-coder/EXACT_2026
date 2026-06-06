"""
EXACT 2026 — Response Schema
Pydantic model cho API response chuẩn cuộc thi.
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class SolveRequest(BaseModel):
    """Request body cho API endpoint POST /solve."""
    question: str = Field(..., description="Câu hỏi cần giải")
    premises: Optional[List[str]] = Field(None, description="Danh sách giả thiết (cho bài logic)")
    type: Optional[str] = Field(None, description="Gợi ý loại bài: 'logic' hoặc 'physics'")


class SolveResponse(BaseModel):
    """Response body — format chuẩn EXACT 2026."""
    answer: str = Field(..., description="Đáp án chính xác")
    explanation: str = Field(..., description="Giải thích chi tiết")

    # Các trường bổ sung (khuyến khích để tăng điểm)
    fol: Optional[str] = Field(None, description="First-Order Logic representation")
    cot: Optional[List[str]] = Field(None, description="Chain-of-Thought steps")
    premises: Optional[List[str]] = Field(None, description="Premises đã sử dụng")
    confidence: Optional[float] = Field(None, description="Confidence score (0.0 - 1.0)")

    # Metadata
    task_type: Optional[str] = Field(None, description="Loại bài: logic/physics")
    solver_used: Optional[str] = Field(None, description="Solver đã dùng: z3/sympy/direct")
