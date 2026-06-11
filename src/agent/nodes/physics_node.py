"""
EXACT 2026 — Physics Node (RAG + SymPy Solver)

Pipeline: RAG tìm công thức → LLM sinh SymPy code → Chạy → Retry nếu lỗi

CẢI TIẾN so với code cũ:
- Iterative Refinement cho SymPy (giống logic node)
- RAG context được truyền cho cả solver lẫn direct
- Dùng sandbox executor + output parser
"""
import time

from src.agent.state import AgentState
from src.core.config import settings
from src.sandbox.executor import execute_code
from src.utils.logger import logger
from src.utils.output_parser import extract_code_block, parse_llm_response, extract_llm_explanation
from src.prompt import (
    COMPETITION_SYSTEM_PROMPT,
    PHYSICS_REPAIR_PROMPT,
)


def physics_rag_node(state: AgentState) -> dict:
    """Node RAG: Tìm kiếm công thức vật lý liên quan từ Vector DB.

    Hybrid search: BM25 + Vector → Rerank → Top 2 để tránh làm dài prompt.
    """
    try:
        from src.retrieval.engine import Retriever
        retriever = Retriever()
        docs = retriever.retrieval(
            query=state["question"],
            collection_name=state.get("collection_name") or settings.storage.collection_name,
            mode="hybrid",
        )
        if docs:
            context = "\n\n".join([d.node.get_content() for d in docs[:2]])
            logger.info(f"[Physics RAG] Tim thay {len(docs)} tai lieu, chot lay top {len(docs[:2])} lam context")
        else:
            context = ""
            logger.info("[Physics RAG] Khong tim thay tai lieu nao, chay zero-shot")
    except Exception as e:
        logger.warning(f"[WARN] [Physics RAG] Loi RAG: {e}")
        context = ""

    return {"context": context}


def physics_solver_branch(state: AgentState) -> dict:
    """Nhánh Solver: LLM sinh SymPy code → chạy → retry nếu lỗi.

    Args:
        state: Trạng thái chứa question + context từ RAG.

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

        context = state.get("context", "")
        context_block = f"\n\nPhysics Formulas & Guidelines:\n{context}\n" if context else ""
        dynamic_print_note = "\nImportant: Print ONLY ONE FINAL_ANSWER line using the computed SymPy variables. Do not add a second hardcoded FINAL_ANSWER line.\n"

        user_prompt = f"{context_block}{dynamic_print_note}[PHYSICS PROBLEM]\n{state['question']}"

        # ── Attempt 1 ──
        logger.info("[Physics Solver] Attempt 1: Sinh SymPy code...")
        response = llm.invoke([
            SystemMessage(content=COMPETITION_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ])
        generated_code = extract_code_block(response.content) or response.content.strip()
        llm_explanation = extract_llm_explanation(response.content)

        result = execute_code(generated_code)
        retry_count = 0

        # ── Retry Loop ──
        while not result.success and retry_count < max_retry:
            retry_count += 1
            last_error = result.error_message or "Unknown error"
            logger.info(f"[Physics Solver] Retry {retry_count}/{max_retry}: Sửa code...")

            # Kiểm tra budget thời gian
            elapsed = time.time() - state.get("time_started", time.time())
            if elapsed > settings.pipeline.global_timeout - 10:
                logger.warning("[TIMEOUT] Hết thời gian, dừng retry")
                break

            repair_prompt = PHYSICS_REPAIR_PROMPT.format(
                code=generated_code,
                error=last_error,
            )
            repair_response = llm.invoke([
                HumanMessage(content=repair_prompt),
            ])
            generated_code = extract_code_block(repair_response.content) or repair_response.content.strip()

            result = execute_code(generated_code)

        if result.success:
            logger.info(f"[OK] [Physics Solver] Thành công sau {retry_count} retry(s)")
        else:
            logger.warning(f"[WARN] [Physics Solver] Thất bại sau {retry_count} retry(s)")

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
        logger.error(f"[ERROR] [Physics Solver] Exception: {e}")
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


def physics_direct(state: AgentState) -> dict:
    """Nhánh Direct: LLM giải vật lý trực tiếp (fallback).

    Args:
        state: Trạng thái chứa question + RAG context.

    Returns:
        Dict cập nhật direct_result.
    """
    try:
        from src.llm.factory import LLMFactory
        llm = LLMFactory.create_client(purpose="reasoning").get_llm()
        from langchain_core.messages import HumanMessage, SystemMessage

        elapsed = time.time() - state.get("time_started", time.time())
        if elapsed > settings.pipeline.global_timeout - 5:
            logger.warning("[TIMEOUT] Quá thời gian, bỏ qua Physics Direct")
            return {
                "direct_result": {
                    "answer": "Unknown",
                    "explanation": "Hệ thống dừng sớm để đảm bảo giới hạn 120 giây.",
                    "raw_response": "",
                }
            }

        context = state.get("context", "")
        context_block = f"\n\nKnowledge Context:\n{context}\n" if context else ""

        user_prompt = f"{context_block}[PHYSICS PROBLEM]\n{state['question']}"

        response = llm.invoke([
            SystemMessage(content=COMPETITION_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt)
        ])
        parsed = parse_llm_response(response.content)

        logger.info(f"[OK] [Physics Direct] Answer: {parsed['answer']}")

        return {
            "direct_result": {
                "answer": parsed["answer"],
                "explanation": parsed["explanation"],
                "raw_response": response.content,
            }
        }

    except Exception as e:
        logger.error(f"[ERROR] [Physics Direct] Exception: {e}")
        return {
            "direct_result": {
                "answer": "Unknown",
                "explanation": f"Lỗi suy luận trực tiếp: {e}",
                "raw_response": "",
            }
        }
