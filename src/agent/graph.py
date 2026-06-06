"""
EXACT 2026 — Main LangGraph Pipeline

Graph flow (TOI UU CHO 60 GIAY):
    input -> classify -> {logic, physics}

    logic:
        classify -> logic_solver -> route:
            solver OK    -> answer_selector -> END
            solver FAIL  -> logic_direct -> answer_selector -> END

    physics:
        classify -> physics_rag -> physics_solver -> route:
            solver OK    -> answer_selector -> END
            solver FAIL  -> physics_direct -> answer_selector -> END

THAY DOI SO VOI PHIEN BAN CU:
- Bo song song (solver + direct) vi chung 1 GPU -> chay tuan tu
- Solver truoc, chi goi Direct khi solver that bai -> tiet kiem 30-60 giay
- Dam bao tong thoi gian <= 60 giay
"""
from langgraph.graph import StateGraph, END

from src.agent.state import AgentState
from src.agent.nodes.classifier import classify_node, route_after_classify
from src.agent.nodes.logic_node import logic_solver_branch, logic_direct
from src.agent.nodes.physics_node import (
    physics_rag_node,
    physics_solver_branch,
    physics_direct,
)
from src.agent.nodes.answer_selector import answer_selector_node
from src.utils.logger import logger


def _route_after_solver(state: AgentState) -> str:
    """Quyet dinh sau khi solver chay xong.

    Neu solver thanh cong -> di thang toi answer_selector.
    Neu solver that bai -> goi direct LLM lam fallback.
    """
    solver = state.get("solver_result", {})
    if solver.get("success", False) and solver.get("answer", ""):
        logger.info("[Router] Solver thanh cong, bo qua direct")
        return "answer_selector"
    else:
        logger.info("[Router] Solver that bai, goi direct fallback")
        task_type = state.get("task_type", "logic")
        return "logic_direct" if task_type == "logic" else "physics_direct"


def build_graph() -> StateGraph:
    """Xay dung va bien dich LangGraph pipeline.

    Returns:
        Compiled LangGraph workflow.
    """
    workflow = StateGraph(AgentState)

    # -- Dang ky Nodes --
    workflow.add_node("classify", classify_node)

    # Nhanh Logic
    workflow.add_node("logic_solver_branch", logic_solver_branch)
    workflow.add_node("logic_direct", logic_direct)

    # Nhanh Physics
    workflow.add_node("physics_rag", physics_rag_node)
    workflow.add_node("physics_solver_branch", physics_solver_branch)
    workflow.add_node("physics_direct", physics_direct)

    # Shared
    workflow.add_node("answer_selector", answer_selector_node)

    # -- Entry Point --
    workflow.set_entry_point("classify")

    # -- Routing sau Classify --
    workflow.add_conditional_edges(
        "classify",
        route_after_classify,
        ["logic_solver_branch", "physics_rag"],
    )

    # -- Logic Branch (tuan tu) --
    # Solver truoc -> neu fail thi goi direct
    workflow.add_conditional_edges(
        "logic_solver_branch",
        _route_after_solver,
        ["answer_selector", "logic_direct"],
    )
    workflow.add_edge("logic_direct", "answer_selector")

    # -- Physics Branch (tuan tu) --
    workflow.add_edge("physics_rag", "physics_solver_branch")
    workflow.add_conditional_edges(
        "physics_solver_branch",
        _route_after_solver,
        ["answer_selector", "physics_direct"],
    )
    workflow.add_edge("physics_direct", "answer_selector")

    # -- Answer Selector -> END --
    workflow.add_edge("answer_selector", END)

    return workflow.compile()


# -- Singleton Pattern --
_graph = None


def get_graph():
    """Lay hoac khoi tao instance cua graph (singleton)."""
    global _graph
    if _graph is None:
        logger.info("Dang bien dich LangGraph pipeline...")
        _graph = build_graph()
        logger.info("[OK] LangGraph pipeline san sang")
    return _graph


def run_pipeline(
    question: str,
    premises: list[str] = None,
    collection_name: str = None,
) -> dict:
    """Diem dau vao chinh de chay toan bo pipeline.

    Args:
        question: Cau hoi tu nguoi dung.
        premises: Danh sach gia thiet (neu co — cho bai logic).
        collection_name: Ten collection trong Vector DB.

    Returns:
        Dict chua dap an, giai thich, confidence, va metadata.
    """
    import time
    from src.core.config import settings

    graph = get_graph()

    if collection_name is None:
        collection_name = settings.storage.collection_name

    # Khoi tao trang thai ban dau
    initial_state: AgentState = {
        "question": question,
        "premises": premises or [],
        "task_type": "logic",
        "collection_name": collection_name,
        "context": "",
        "solver_result": {
            "generated_code": "",
            "code_output": "",
            "answer": "",
            "success": False,
            "retry_count": 0,
        },
        "direct_result": {
            "answer": "",
            "explanation": "",
            "raw_response": "",
        },
        "final_answer": {
            "answer": "",
            "explanation": "",
            "fol": "",
            "cot": [],
            "premises": [],
            "confidence": 0.0,
        },
        "error": "",
        "time_started": time.time(),
    }

    logger.info(f"Pipeline started: {question[:100]}...")

    # Thuc thi graph
    result = graph.invoke(initial_state)

    elapsed = time.time() - initial_state["time_started"]
    final = result.get("final_answer", {})

    logger.info(
        f"Pipeline finished in {elapsed:.1f}s — "
        f"Answer: {final.get('answer')}, Confidence: {final.get('confidence')}"
    )

    return {
        "task_type": result.get("task_type"),
        "answer": final.get("answer"),
        "explanation": final.get("explanation"),
        "fol": final.get("fol"),
        "cot": final.get("cot"),
        "premises": final.get("premises"),
        "confidence": final.get("confidence"),
        "solver_used": final.get("solver_used"),
    }
