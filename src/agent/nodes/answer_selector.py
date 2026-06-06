"""
EXACT 2026 — Answer Selector Node

So sanh ket qua tu solver va direct, chon dap an tot nhat.
Tao explanation de doc cho nguoi dung.

Logic chon:
1. Solver thanh cong (khong co direct) -> dung solver, confidence 0.85
2. Solver thanh cong + direct dong thuan -> confidence 0.95
3. Solver thanh cong + direct khac -> uu tien solver, confidence 0.80
4. Solver that bai -> dung direct, confidence 0.60
"""
from src.agent.state import AgentState
from src.utils.logger import logger


def answer_selector_node(state: AgentState) -> dict:
    """Chon dap an cuoi cung va tao explanation.

    Args:
        state: Trang thai chua solver_result va direct_result.

    Returns:
        Dict cap nhat final_answer.
    """
    solver = state.get("solver_result", {})
    direct = state.get("direct_result", {})
    task_type = state.get("task_type", "unknown")

    solver_success = solver.get("success", False)
    solver_answer = solver.get("answer", "").strip()
    solver_output = solver.get("code_output", "").strip()
    solver_code = solver.get("generated_code", "")
    llm_explanation = solver.get("llm_explanation", "").strip()

    direct_answer = direct.get("answer", "").strip()
    direct_explanation = direct.get("explanation", "").strip()

    logger.info(
        f"[Answer Selector] Solver: {'OK' if solver_success else 'FAIL'} "
        f"({solver_answer}) | Direct: ({direct_answer})"
    )

    # -- Quyet dinh --
    if solver_success and solver_answer:
        if direct_answer and _answers_match(solver_answer, direct_answer):
            # Ca 2 dong thuan
            confidence = 0.95
            chosen_answer = solver_answer
            solver_used = "z3" if task_type == "logic" else "sympy"
            explanation = _build_explanation(solver_answer, solver_output, task_type, llm_explanation)
            logger.info(f"[OK] 2 nhanh dong thuan: {chosen_answer} (conf={confidence})")

        elif direct_answer:
            # Solver va Direct khac nhau -> uu tien solver
            confidence = 0.80
            chosen_answer = solver_answer
            solver_used = "z3" if task_type == "logic" else "sympy"
            explanation = _build_explanation(solver_answer, solver_output, task_type, llm_explanation)
            logger.info(f"2 nhanh khac: solver={solver_answer}, direct={direct_answer} -> chon solver")

        else:
            # Solver thanh cong, direct khong chay (pipeline tuan tu)
            confidence = 0.85
            chosen_answer = solver_answer
            solver_used = "z3" if task_type == "logic" else "sympy"
            explanation = _build_explanation(solver_answer, solver_output, task_type, llm_explanation)
            logger.info(f"[OK] Solver thanh cong: {chosen_answer} (conf={confidence})")

    else:
        # Solver that bai -> dung Direct
        confidence = 0.60
        chosen_answer = direct_answer or "Unknown"
        solver_used = "direct"
        explanation = direct_explanation or "Khong the giai bang solver, su dung LLM suy luan truc tiep."
        logger.info(f"Solver that bai, dung Direct: {chosen_answer} (conf={confidence})")

    return {
        "final_answer": {
            "answer": chosen_answer,
            "explanation": explanation,
            "fol": solver_code,
            "cot": [],
            "premises": state.get("premises", []),
            "confidence": confidence,
            "task_type": task_type,
            "solver_used": solver_used,
        }
    }


def _build_explanation(answer: str, solver_output: str, task_type: str, llm_explanation: str = "") -> str:
    """Tao explanation tu ket qua solver va LLM.

    Lay cac dong Step/print tu stdout cua solver lam loi giai va ket hop voi loi giai tu LLM (neu co).
    """
    import re

    # Loc bo dong ANSWER/FINAL_ANSWER (da hien trong answer roi)
    lines = solver_output.split("\n") if solver_output else []
    explanation_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Bo cac dong chi chua answer tag
        if re.match(r"^(ANSWER|FINAL_ANSWER)\s*:", stripped, re.IGNORECASE):
            continue
        explanation_lines.append(stripped)

    steps = "\n".join(explanation_lines)

    final_exp = ""
    if llm_explanation:
        final_exp = f"**Lập luận (LLM):**\n{llm_explanation}\n\n"

    if steps and steps != answer:
        # Co buoc giai tu solver -> dung lam explanation
        solver_name = "Z3 Theorem Prover" if task_type == "logic" else "SymPy"
        final_exp += f"**Chi tiết thực thi ({solver_name}):**\n{steps}"
        return final_exp.strip()
    else:
        if final_exp:
            return final_exp.strip()
        # Khong co buoc giai hoac buoc giai trung dap an -> tra ve explanation co ban
        if task_type == "logic":
            return f"Kết quả được xác minh tự động bằng Z3 Theorem Prover."
        else:
            return f"Đã tính toán và kiểm chứng chính xác bằng SymPy Sandbox."


def _answers_match(answer1: str, answer2: str) -> bool:
    """So sanh 2 dap an (case-insensitive, ho tro so va text).

    Args:
        answer1: Dap an thu nhat.
        answer2: Dap an thu hai.

    Returns:
        True neu 2 dap an giong nhau.
    """
    if not answer1 or not answer2:
        return False

    a1 = answer1.strip().lower()
    a2 = answer2.strip().lower()

    # So sanh truc tiep
    if a1 == a2:
        return True

    # So sanh chua nhau
    if a1 in a2 or a2 in a1:
        return True

    # So sanh so
    try:
        import re
        nums1 = re.findall(r"[-+]?\d*\.?\d+(?:e[-+]?\d+)?", a1)
        nums2 = re.findall(r"[-+]?\d*\.?\d+(?:e[-+]?\d+)?", a2)
        if nums1 and nums2:
            return abs(float(nums1[0]) - float(nums2[0])) < 1e-6
    except (ValueError, IndexError):
        pass

    return False
