"""
EXACT 2026 — Sandbox Executor
Chạy code Z3/SymPy an toàn trong subprocess có timeout.

CẢI TIẾN so với code cũ:
- Phân loại lỗi rõ ràng (syntax, import, runtime, timeout)
- Tự động parse kết quả (ANSWER: / FINAL_ANSWER:)
- Trả về object có cấu trúc thay vì raw string
"""
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Optional

from src.core.config import settings
from src.utils.logger import logger
from src.utils.output_parser import parse_answer


@dataclass
class ExecutionResult:
    """Kết quả thực thi code trong sandbox."""
    success: bool                          # Code chạy thành công?
    stdout: str = ""                       # Standard output
    stderr: str = ""                       # Standard error
    answer: str = ""                       # Đáp án đã parse (ANSWER: / FINAL_ANSWER:)
    error_type: Optional[str] = None       # "syntax" | "import" | "runtime" | "timeout" | None
    error_message: Optional[str] = None    # Chi tiết lỗi


def execute_code(
    code: str,
    timeout: int = None,
) -> ExecutionResult:
    """Chạy code Python trong subprocess an toàn.

    Args:
        code: Code Python cần chạy (Z3 hoặc SymPy).
        timeout: Timeout tính bằng giây (mặc định từ config).

    Returns:
        ExecutionResult object.
    """
    if timeout is None:
        timeout = settings.pipeline.solver_timeout

    if not code or not code.strip():
        return ExecutionResult(
            success=False,
            error_type="empty",
            error_message="Không có code để thực thi",
        )

    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if result.returncode == 0:
            # Thành công → parse đáp án
            answer = parse_answer(stdout)
            logger.info(f"[OK] Solver thành công — Answer: {answer}")
            return ExecutionResult(
                success=True,
                stdout=stdout,
                stderr=stderr,
                answer=answer,
            )
        else:
            # Lỗi runtime → phân loại lỗi
            error_type = _classify_error(stderr)
            logger.warning(f"[WARN] Solver lỗi ({error_type}): {stderr[:200]}")
            return ExecutionResult(
                success=False,
                stdout=stdout,
                stderr=stderr,
                error_type=error_type,
                error_message=stderr,
            )

    except subprocess.TimeoutExpired:
        logger.warning(f"[TIMEOUT] Solver timeout ({timeout}s)")
        return ExecutionResult(
            success=False,
            error_type="timeout",
            error_message=f"Quá thời gian thực thi ({timeout} giây)",
        )
    except Exception as e:
        logger.error(f"[ERROR] Lỗi không xác định khi chạy solver: {e}")
        return ExecutionResult(
            success=False,
            error_type="unknown",
            error_message=str(e),
        )


def _classify_error(stderr: str) -> str:
    """Phân loại lỗi dựa trên stderr output.

    Args:
        stderr: Standard error output.

    Returns:
        Loại lỗi: "syntax", "import", "runtime", hoặc "unknown".
    """
    if not stderr:
        return "unknown"

    stderr_lower = stderr.lower()

    if "syntaxerror" in stderr_lower:
        return "syntax"
    elif "modulenotfounderror" in stderr_lower or "importerror" in stderr_lower:
        return "import"
    elif "nameerror" in stderr_lower:
        return "name"
    elif "typeerror" in stderr_lower:
        return "type"
    elif "zerodivisionerror" in stderr_lower:
        return "math"
    elif any(kw in stderr_lower for kw in ["valueerror", "attributeerror", "keyerror"]):
        return "runtime"
    else:
        return "runtime"
