"""
EXACT 2026 — Prompt Templates
Tất cả prompt templates cho pipeline: Z3, SymPy, Explanation, Classification.

CẢI TIẾN so với code cũ:
- Nhiều few-shot examples hơn
- Code Repair prompt (cho iterative refinement)
- Tối ưu cho model 8B (ngắn gọn, rõ ràng)
"""

COMPETITION_SYSTEM_PROMPT = """You are an expert educational AI assistant for the EXACT 2026 competition. For logic problems: analyze premises carefully, apply formal reasoning, and derive the correct conclusion. For physics problems: identify relevant formulas, show step-by-step calculations, and provide the final numerical answer with correct units. 
CRITICAL RULES FOR PHYSICS PYTHON CODE:
1. Explicitly define and assign all given numeric values to variables (e.g., m_val = 5, F_val = 25).
2. DO NOT call .evalf() on standard Python floats or integers (it causes AttributeError). Only use it on SymPy Expr objects. If unsure, use standard float().
Always think step-by-step inside <think>...</think> tags, then give your final answer inside <answer>...</answer> tags."""


# ═══════════════════════════════════════════════════════════════════════════════
# LOGIC — CODE REPAIR (Iterative Refinement)
# ═══════════════════════════════════════════════════════════════════════════════

Z3_REPAIR_PROMPT = """The following Z3 Python code produced an error. Fix the code.

ORIGINAL CODE:
```python
{code}
```

ERROR MESSAGE:
{error}

REQUIREMENTS:
1. Fix the error while preserving the original logic intent.
2. Make sure all variables are properly defined before use.
3. Always end with print("ANSWER: <result>").
4. Generate ONLY the corrected Python code block.

CORRECTED CODE:"""


# ═══════════════════════════════════════════════════════════════════════════════
# PHYSICS — CODE REPAIR (Iterative Refinement)
# ═══════════════════════════════════════════════════════════════════════════════

PHYSICS_REPAIR_PROMPT = """The following physics Python code produced an error. Fix the code.

ORIGINAL CODE:
```python
{code}
```

ERROR MESSAGE:
{error}

REQUIREMENTS:
1. Fix the error while preserving the physics calculations.
2. Make sure all imports are correct (use `import sympy as sp` or `import math`).
3. Always use SI units.
4. Always end with: `print(f"FINAL_ANSWER: {{value}} {{unit}}")` (combine multiple answers if needed).
5. Generate ONLY the corrected Python code block.

CORRECTED CODE:"""
