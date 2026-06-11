# EXACT 2026 — Solution Description

## Team Approach: Neurosymbolic Hybrid Pipeline

### Overview

We build an agentic AI system that combines **Large Language Models** (LLM) with **Symbolic Solvers** (Z3, SymPy) to answer educational questions accurately. The system uses a solver-first strategy: the LLM translates natural language problems into formal code, symbolic solvers verify the answer mathematically, and a fallback LLM reasoning path activates only when the solver fails.

### Architecture

```
Input (JSON) -> Classifier -> [Logic | Physics]

Logic path:    LLM generates Z3 code -> Execute -> If error: auto-repair -> Retry
Physics path:  RAG retrieves formulas -> LLM generates SymPy code -> Execute -> Retry

If solver succeeds -> Return solver answer (confidence 0.80-0.95)
If solver fails    -> LLM direct reasoning as fallback (confidence 0.60)
```

### Models Used

| Component | Model | Size | Source |
|-----------|-------|------|--------|
| Main LLM | DeepSeek-R1-0528-Qwen3-8B | 8B params | HuggingFace (open-source) |
| Quantization | BitsAndBytes NF4 | 4-bit | - |
| Embedding | BAAI/bge-m3 | 568M params | HuggingFace (open-source) |
| Reranker | BAAI/bge-reranker-base | 278M params | HuggingFace (open-source) |

All models are open-source and comply with the competition's 8B parameter limit.

### Key Techniques

1. **Iterative Refinement (Self-Correction):** When Z3/SymPy code fails, the error message is fed back to the LLM to generate corrected code. Maximum 1 retry to stay within 60-second budget.

2. **Hybrid RAG for Physics:** Combines BM25 (keyword) + Vector Search (semantic) + Reranking to find relevant physics formulas before solving.

3. **Sandboxed Execution:** Solver code runs in isolated subprocess with strict timeout (10s), preventing infinite loops or unsafe operations.

4. **Intelligent Answer Selection:** When both solver and direct LLM produce answers, the system compares results. Agreement increases confidence; disagreement defaults to the mathematically-verified solver answer.

### External Data

- **Physics Knowledge Base:** 15 curated physics formula documents covering capacitors, Coulomb's law, Ohm's law, circuit analysis, and unit conversions.
- **Training Data:** Physics and logic training examples from the official EXACT 2026 dataset, indexed in vector database for retrieval-augmented generation.

### Technology Stack

- **Orchestration:** LangGraph (LangChain)
- **Logic Solver:** Z3 Theorem Prover (Microsoft)
- **Math Solver:** SymPy
- **Vector Database:** Qdrant (embedded mode)
- **RAG Framework:** LlamaIndex
- **API:** FastAPI + Uvicorn

### Performance Optimization

- Solver-first sequential pipeline (avoids redundant LLM calls on single GPU)
- 4-bit quantization reduces VRAM from 16GB to ~5GB
- Deterministic generation (temperature=0, do_sample=False)
- max_new_tokens=1024 balances quality and speed
- Target: < 60 seconds per request on T4 GPU
