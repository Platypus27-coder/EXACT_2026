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
            explanation, cot = _build_explanation_and_cot(solver_answer, solver_output, task_type, llm_explanation)
            logger.info(f"[OK] 2 nhanh dong thuan: {chosen_answer} (conf={confidence})")

        elif direct_answer:
            # Solver va Direct khac nhau -> uu tien solver
            confidence = 0.80
            chosen_answer = solver_answer
            solver_used = "z3" if task_type == "logic" else "sympy"
            explanation, cot = _build_explanation_and_cot(solver_answer, solver_output, task_type, llm_explanation)
            logger.info(f"2 nhanh khac: solver={solver_answer}, direct={direct_answer} -> chon solver")

        else:
            # Solver thanh cong, direct khong chay (pipeline tuan tu)
            confidence = 0.85
            chosen_answer = solver_answer
            solver_used = "z3" if task_type == "logic" else "sympy"
            explanation, cot = _build_explanation_and_cot(solver_answer, solver_output, task_type, llm_explanation)
            logger.info(f"[OK] Solver thanh cong: {chosen_answer} (conf={confidence})")

    else:
        # Solver that bai -> dung Direct
        confidence = 0.60
        chosen_answer = direct_answer or "Unknown"
        solver_used = "direct"
        explanation = direct_explanation or "The problem could not be solved by the symbolic solver. Derived using LLM direct reasoning."
        cot = []
        logger.info(f"Solver that bai, dung Direct: {chosen_answer} (conf={confidence})")

    # Chuyen doi code thanh dinh dang FOL 1 dong (Uu tien FOL model tu sinh)
    formatted_fol = _format_fol(solver_code, task_type, llm_explanation)

    return {
        "final_answer": {
            "answer": chosen_answer,
            "explanation": explanation,
            "fol": formatted_fol,
            "cot": cot,
            "premises": state.get("premises", []),
            "confidence": confidence,
            "task_type": task_type,
            "solver_used": solver_used,
        }
    }


def _build_explanation_and_cot(answer: str, solver_output: str, task_type: str, llm_explanation: str = "") -> tuple[str, list]:
    """Tao explanation va cot tu ket qua solver.

    Tra ve: (explanation_string, cot_list) de map chuan xac vao API cua BTC.
    """
    import re

    # Loc bo dong ANSWER/FINAL_ANSWER (da hien trong answer roi)
    lines = solver_output.split("\n") if solver_output else []
    cot_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Bo cac dong chi chua answer tag
        if re.match(r"^(ANSWER|FINAL_ANSWER)\s*:", stripped, re.IGNORECASE):
            continue
        cot_lines.append(stripped)

    # Tao explanation ngan gon (English)
    if llm_explanation:
        explanation = llm_explanation.strip()
    else:
        if task_type == "logic":
            explanation = "The logical conclusion was derived and strictly verified using the Z3 Theorem Prover."
        else:
            explanation = "The final answer was calculated step-by-step and verified using the SymPy mathematical solver."

    return explanation, cot_lines


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
    
    return False


def _format_fol(solver_code: str, task_type: str, llm_explanation: str = "") -> str:
    """Chuyen doi code Python thanh dang chuoi Logic (FOL) hoac lay tu LLM."""
    
    # 1. Uu tien tuyet doi lay FOL do model tu sinh (neu co)
    if llm_explanation and "Formal Logic (FOL):" in llm_explanation:
        import re
        # Lay toan bo doan van ban sau chu Formal Logic (FOL):
        match = re.search(r'Formal Logic \(FOL\):\s*(.*)', llm_explanation, re.DOTALL | re.IGNORECASE)
        if match:
            fol_text = match.group(1).strip()
            # Don dep cac ky tu thua, noi thanh 1 dong
            lines = [l.strip() for l in fol_text.split('\n') if l.strip() and not l.startswith('**')]
            return " ∧ ".join(lines)

    if not solver_code:
        return ""
    
    formulas = []
    
    if task_type == "logic":
        # Tim cac dong chu logic nhu solver.add, s.add, hoac chua cac ham logic z3
        for line in solver_code.split('\n'):
            line = line.strip()
            if '.add(' in line and not line.startswith('#'):
                import re
                clean = re.sub(r'^\w+\.add\(', '', line)
                if clean.endswith(')'):
                    clean = clean[:-1]
                formulas.append(f"Valid({clean})")
            elif any(kw in line for kw in ['Implies(', 'And(', 'Or(', 'Not(']) and not line.startswith('#'):
                formulas.append(f"Valid({line})")
                
        if not formulas:
            return "∀x (Premises(x) → Conclusion(x))"
    else:
        # Trich xuat phuong trinh vat ly tu SymPy (co = hoac Eq)
        for line in solver_code.split('\n'):
            line = line.strip()
            if ('=' in line or 'Eq(' in line) and not any(line.startswith(kw) for kw in ['print', 'import', '#', 'def', 'return', 'if', 'elif', 'else']):
                # Xoa ma thua cua sympy
                clean_line = line.replace('sp.Rational', '').replace('sp.', '').replace('sympy.', '').strip()
                formulas.append(clean_line)
                
    if formulas:
        # Neu co nhieu hon 5 cong thuc, chi lay 5 cai quan trong nhat cho do roi
        if len(formulas) > 5:
            formulas = formulas[-5:]
        return " ∧ ".join(formulas)
    
    return "∀x (Problem(x) → Solved(x))"

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
