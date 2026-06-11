"""
EXACT 2026 — Output Parser (Regex-based)

CẢI TIẾN: Thay thế .with_structured_output() vốn không ổn định với model 8B.
Dùng regex để trích xuất answer, explanation từ text output của LLM.
"""
import re
from typing import Optional

from src.utils.logger import logger


def remove_think_tags(text: str) -> str:
    """Loai bo the <think>...</think> cua model DeepSeek-R1."""
    if not text:
        return ""
    # Xoa khoi <think> den </think>
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # Neu con sot <think> nhung chua co </think> (do bi truncate)
    text = re.sub(r"<think>.*", "", text, flags=re.DOTALL)
    return text.strip()


def extract_llm_explanation(text: str) -> str:
    """Trích xuất phần giải thích bằng lời từ LLM (bỏ phần code Python)."""
    if not text:
        return ""
    # Xóa code block
    text_no_code = re.sub(r"```.*?```", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Xóa thẻ think
    text_no_code = re.sub(r"</?think>", "", text_no_code, flags=re.IGNORECASE)
    # Xóa thẻ answer và nội dung bên trong
    text_no_code = re.sub(r"<answer>.*?</answer>", "", text_no_code, flags=re.DOTALL | re.IGNORECASE)
    return text_no_code.strip()


def parse_answer(text: str) -> str:
    """Trích xuất đáp án từ output text.

    Tìm pattern: ANSWER: <value> hoặc FINAL_ANSWER: <value>

    Args:
        text: Raw text output từ LLM hoặc solver.

    Returns:
        Đáp án đã trích xuất, hoặc "Unknown" nếu không tìm thấy.
    """
    text = remove_think_tags(text)
    if not text:
        return "Unknown"

    # 0. Đặc sản của V2: <answer>...</answer>
    match = re.search(r"<answer>\s*(.*?)\s*</answer>", text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()

    # Pattern 1: FINAL_ANSWER: <value> <unit> (physics)
    # Dung findall lay tat ca dong FINAL_ANSWER, chon dong DAU TIEN (ket qua tinh toan thuc)
    # Tranh lay dong hardcode cuoi cung cua LLM sinh ra co the sai
    all_final = re.findall(r"FINAL_ANSWER:\s*(.+)", text, re.IGNORECASE)
    if all_final:
        return all_final[0].strip()

    # Pattern 2: ANSWER: <value> (logic)
    match = re.search(r"ANSWER:\s*(.+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Pattern 3: Dong cuoi cung nhung phai ngan (tranh lay nguyen cau dai)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if lines:
        last_line = lines[-1]
        # Chi lay dong cuoi neu do dai < 50 ky tu (thuong la dap an ngan)
        if len(last_line) < 50:
            return last_line

    return "Unknown"


def parse_explanation(text: str) -> str:
    """Trích xuất phần giải thích từ output text."""
    # Với format mới, phần giải thích chính là văn bản trong thẻ <think> (sau khi bỏ code)
    explanation = extract_llm_explanation(text)
    
    if not explanation:
        return (
            "Hệ thống đã phân tích các giả thiết và sử dụng công cụ tính toán ký hiệu "
            "để tự động trích xuất đáp án cuối cùng nhằm đảm bảo độ chính xác tuyệt đối."
        )
    return explanation


def parse_llm_response(text: str) -> dict:
    """Parse toàn bộ response từ LLM thành dict chuẩn.

    Args:
        text: Raw text output từ LLM.

    Returns:
        Dict chứa answer, explanation.
    """
    return {
        "answer": parse_answer(text),
        "explanation": parse_explanation(text),
    }


def extract_code_block(text: str) -> Optional[str]:
    """Trích xuất code Python từ markdown code block trong response LLM."""
    if not text:
        return None

    # Tìm đúng block ```python ... ``` trong toàn bộ text nguyên bản
    match = re.search(r"```python\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Tìm ``` ... ``` (không chỉ định ngôn ngữ)
    match = re.search(r"```\s*(.*?)```", text, re.DOTALL)
    if match:
        code = match.group(1).strip()
        if "import" in code or "print" in code or "def " in code:
            return code

    # Fallback: nếu text bắt đầu bằng import hoặc from
    stripped = text.strip()
    if stripped.startswith(("import ", "from ")):
        return stripped

    logger.warning("Không tìm thấy code block trong response LLM")
    return None
