"""
EXACT 2026 — Configuration Module
Load cấu hình từ config/setting.yaml + biến môi trường (.env).
"""
import os
import sys
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml

from src.utils.logger import logger

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SETTING_FILE = _PROJECT_ROOT / "config" / "setting.yaml"


# ── Pydantic Config Models ──────────────────────────────────────────────────

class AppConfig(BaseModel):
    project_name: str
    version: str
    debug: bool = False


class LLMConfig(BaseModel):
    model_id: str = "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B"
    temperature: float = 0.0
    max_new_tokens: int = 768
    load_in_4bit: bool = True   # Quantization 4-bit cho tiet kiem VRAM


class RagConfig(BaseModel):
    reranker: str = "BAAI/bge-reranker-base"


class EmbeddingConfig(BaseModel):
    model_name: str = "BAAI/bge-m3"


class RetrievalConfig(BaseModel):
    threshold: float = 0.5
    top_k: int = 10
    rerank_top_n: int = 3


class StorageConfig(BaseModel):
    data_dir: str = "data"
    vector_db: str = "storage/vector_db"
    collection_name: str = "exact"


class PipelineConfig(BaseModel):
    """Cấu hình timeout cho pipeline — đảm bảo tổng ≤ 60 giây."""
    global_timeout: int = 55       # Giây — dành 5s cho API overhead
    solver_timeout: int = 10       # Timeout mỗi lần chạy solver
    max_retry: int = 1             # 1 lan retry (tiet kiem thoi gian)
    llm_generate_timeout: int = 15 # Timeout cho LLM sinh code


class LangsmithConfig(BaseModel):
    project: str = "EXACT 2026"
    endpoint: str = "https://api.smith.langchain.com"


# ── Main Settings ────────────────────────────────────────────────────────────

class Settings(BaseSettings):
    """Cấu hình toàn cục — merge từ YAML + biến môi trường."""
    langsmith_api_key: str | None = Field(None, alias="LANGSMITH_API_KEY")

    app: AppConfig
    llm: LLMConfig
    rag: RagConfig
    embedding: EmbeddingConfig
    retrieval: RetrievalConfig
    storage: StorageConfig
    pipeline: PipelineConfig
    langsmith: LangsmithConfig

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


# ── Load Settings ────────────────────────────────────────────────────────────

def load_setting() -> Settings:
    """Đọc cấu hình từ setting.yaml."""
    if not _SETTING_FILE.exists():
        raise FileNotFoundError(f"Không tìm thấy file cấu hình: {_SETTING_FILE}")

    with open(_SETTING_FILE, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    return Settings(**raw)


try:
    settings = load_setting()
    logger.info(f"[OK] Loaded settings for: {settings.app.project_name} v{settings.app.version}")

    # Cấu hình LangSmith tracing nếu có API key
    if settings.langsmith_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_ENDPOINT"] = settings.langsmith.endpoint
        os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langsmith.project
        logger.info(f"LangSmith tracing enabled: {settings.langsmith.project}")

except Exception as e:
    logger.error(f"[ERROR] Lỗi khi load cấu hình: {e}")
    raise
