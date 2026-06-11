"""
EXACT 2026 — Logic Node (Neurosymbolic Hybrid)

Pipeline: LLM sinh Z3 code → Chạy Z3 → Retry nếu lỗi → Fallback LLM direct

CẢI TIẾN so với code cũ:
- Tối đa 2 lần retry (đảm bảo trong budget 60 giây)
- Dùng sandbox executor thay vì subprocess trực tiếp
- Dùng output_parser thay vì structured output
"""
import time

from src.agent.state import AgentState
from src.core.config import settings
from src.sandbox.executor import execute_code
from src.utils.logger import logger
from src.utils.output_parser import extract_code_block, parse_llm_response, extract_llm_explanation
from src.prompt import (
    COMPETITION_SYSTEM_PROMPT,
    Z3_REPAIR_PROMPT,
)


def logic_solver_branch(state: AgentState) -> dict:
    """Nhánh Solver: LLM sinh Z3 code → chạy → retry nếu lỗi.

    Đây là nhánh chính (Neurosymbolic Hybrid):
    1. LLM dịch bài toán sang Z3 Python code
    2. Chạy code trong sandbox
    3. Nếu lỗi → feed error cho LLM sửa code → chạy lại (max 2 retry)

    Args:
        state: Trạng thái chứa question + premises.

    Returns:
        Dict cập nhật solver_result.
    """
    max_retry = settings.pipeline.max_retry
    generated_code = ""
    last_error = ""
    llm_explanation = ""

    try:
        from src.llm.factory import LLMFactory
        llm = LLMFactory.create_client(purpose="code").get_llm()
        from langchain_core.messages import SystemMessage, HumanMessage

        premises_text = "\n".join([f"{i+1}. {p}" for i, p in enumerate(state.get("premises", []))])
        user_prompt = f"[LOGIC PROBLEM]\nPremises:\n{premises_text}\n\nQuestion:\n{state['question']}"

        # ── Attempt 1: Sinh code lần đầu ──
        logger.info("[Logic Solver] Attempt 1: Sinh Z3 code...")
        response = llm.invoke([
            SystemMessage(content=COMPETITION_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ])
        generated_code = extract_code_block(response.content) or response.content.strip()
        llm_explanation = extract_llm_explanation(response.content)

        # Chạy code
        result = execute_code(generated_code)
        retry_count = 0

        # ── Retry Loop (Iterative Refinement) ──
        while not result.success and retry_count < max_retry:
            retry_count += 1
            last_error = result.error_message or "Unknown error"
            logger.info(f"[Logic Solver] Retry {retry_count}/{max_retry}: Sửa code...")

            # Kiểm tra còn thời gian không
            elapsed = time.time() - state.get("time_started", time.time())
            if elapsed > settings.pipeline.global_timeout - 10:
                logger.warning("[TIMEOUT] Hết thời gian, dừng retry")
                break

            # Feed error cho LLM sửa code
            repair_prompt = Z3_REPAIR_PROMPT.format(
                code=generated_code,
                error=last_error,
            )
            repair_response = llm.invoke([
                HumanMessage(content=repair_prompt),
            ])
            generated_code = extract_code_block(repair_response.content) or repair_response.content.strip()

            # Chạy lại code đã sửa
            result = execute_code(generated_code)

        if result.success:
            logger.info(f"[OK] [Logic Solver] Thành công sau {retry_count} retry(s)")
        else:
            logger.warning(f"[WARN] [Logic Solver] Thất bại sau {retry_count} retry(s)")

        return {
            "solver_result": {
                "generated_code": generated_code,
                "code_output": result.stdout or result.stderr,
                "answer": result.answer if result.success else "",
                "success": result.success,
                "retry_count": retry_count,
                "llm_explanation": llm_explanation,
            }
        }

    except Exception as e:
        logger.error(f"[ERROR] [Logic Solver] Exception: {e}")
        return {
            "solver_result": {
                "generated_code": generated_code,
                "code_output": "",
                "answer": "",
                "success": False,
                "retry_count": 0,
                "llm_explanation": llm_explanation,
            },
            "error": str(e),
        }


def logic_direct(state: AgentState) -> dict:
    """Nhánh Direct: LLM suy luận trực tiếp (chạy song song với solver).

    Đây là phương án fallback — không dùng Z3, chỉ dùng Chain-of-Thought.

    Args:
        state: Trạng thái chứa question + premises.

    Returns:
        Dict cập nhật direct_result.
    """
    try:
        from src.llm.factory import LLMFactory
        llm = LLMFactory.create_client(purpose="reasoning").get_llm()
        from langchain_core.messages import HumanMessage, SystemMessage

        elapsed = time.time() - state.get("time_started", time.time())
        if elapsed > settings.pipeline.global_timeout - 5:
            logger.warning("[TIMEOUT] Quá thời gian, bỏ qua Logic Direct")
            return {
                "direct_result": {
                    "answer": "Unknown",
                    "explanation": "Hệ thống dừng sớm để đảm bảo giới hạn 120 giây.",
                    "raw_response": "",
                }
            }

        premises_text = "\n".join([f"{i+1}. {p}" for i, p in enumerate(state.get("premises", []))])
        user_prompt = f"[LOGIC PROBLEM]\nPremises:\n{premises_text}\n\nQuestion:\n{state['question']}"

        response = llm.invoke([
            SystemMessage(content=COMPETITION_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt)
        ])
        parsed = parse_llm_response(response.content)

        logger.info(f"[OK] [Logic Direct] Answer: {parsed['answer']}")

        return {
            "direct_result": {
                "answer": parsed["answer"],
                "explanation": parsed["explanation"],
                "raw_response": response.content,
            }
        }

    except Exception as e:
        logger.error(f"[ERROR] [Logic Direct] Exception: {e}")
        return {
            "direct_result": {
                "answer": "Unknown",
                "explanation": f"Lỗi suy luận trực tiếp: {e}",
                "raw_response": "",
            }
        }
