"""
EXACT 2026 — FastAPI Application
API endpoint chính cho cuộc thi: POST /solve

Yêu cầu cuộc thi:
- Nhận JSON query → trả JSON (answer + explanation)
- Tối đa 60 giây cho mỗi request
- Structured output
"""
import asyncio
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.agent.schema import SolveRequest, SolveResponse
from src.agent.graph import run_pipeline
from src.core.config import settings
from src.utils.logger import logger


# ── Lifespan (khởi tạo khi server start) ────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Khởi tạo resources khi server bắt đầu."""
    logger.info(f"Starting {settings.app.project_name} v{settings.app.version}")
    from src.agent.graph import get_graph
    get_graph()
    
    # BẮT BUỘC: Pre-load Model vào VRAM ngay khi bật Server
    # Nếu không, request đầu tiên sẽ mất 2 phút để load model và bị văng Timeout 60s của BTC!
    logger.info(f"Đang Pre-load model '{settings.llm.model_id}' vào VRAM. Vui lòng đợi...")
    from src.llm.factory import LLMFactory
    LLMFactory.create_client(purpose="code").get_llm()
    # BẮT BUỘC 2: Pre-load hệ thống RAG (Embedding + Reranker) và nạp Vector DB
    logger.info("Đang Pre-load RAG Models (bge-m3, reranker) và Qdrant Vector DB...")
    from src.retrieval.engine import Retriever
    Retriever()
    
    logger.info("[OK] Server ready! Model đã nằm sẵn trong GPU.")
    yield
    logger.info("Server shutting down")


# ── FastAPI App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app.project_name,
    version=settings.app.version,
    description="EXACT 2026 — Agentic AI for Logic & Physics Reasoning",
    lifespan=lifespan,
)

# CORS (cho phép gọi từ mọi origin — cần cho deployment)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.post("/solve", response_model=SolveResponse)
async def solve(request: SolveRequest):
    """Endpoint chính — nhận câu hỏi, trả đáp án + giải thích.

    - Tối đa 60 giây (55s pipeline + 5s overhead)
    - Tự động phân loại logic/physics
    - Chạy solver + fallback song song
    """
    start_time = time.time()
    logger.info(f"Received request: {request.question[:100]}...")

    try:
        # Chạy pipeline với timeout (BTC yêu cầu < 60s)
        result = await asyncio.wait_for(
            asyncio.to_thread(
                run_pipeline,
                question=request.question,
                premises=request.premises,
            ),
            timeout=60.0,  # Hard timeout 60 giây
        )

        elapsed = time.time() - start_time
        logger.info(f"Request completed in {elapsed:.2f}s")

        return SolveResponse(
            answer=result.get("answer", "Unknown"),
            explanation=result.get("explanation", ""),
            fol=result.get("fol"),
            cot=result.get("cot"),
            premises=result.get("premises"),
            confidence=result.get("confidence"),
            task_type=result.get("task_type"),
            solver_used=result.get("solver_used"),
        )

    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        logger.error(f"[TIMEOUT] Request timeout after {elapsed:.2f}s")
        raise HTTPException(
            status_code=504,
            detail="Request timeout: Vượt quá 60 giây cho phép",
        )
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[ERROR] Request failed after {elapsed:.2f}s: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}",
        )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "project": settings.app.project_name,
        "version": settings.app.version,
    }
