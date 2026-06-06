"""
EXACT 2026 — Logger Module
Cấu hình logging cho project, tương thích Windows encoding (cp1258).
Emoji được tự động thay thế trên console, giữ nguyên trong file log.
"""
import logging
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_LOG_DIR = _PROJECT_ROOT / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)


class _SafeConsoleHandler(logging.StreamHandler):
    """StreamHandler tự động encode-safe cho Windows console.
    
    Thay vì crash khi gặp emoji, tự động replace bằng ký tự '?'.
    """
    def emit(self, record):
        try:
            msg = self.format(record)
            # Encode rồi decode lại với errors='replace' để loại bỏ ký tự lỗi
            safe_msg = msg.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
                sys.stdout.encoding or "utf-8", errors="replace"
            )
            sys.stdout.write(safe_msg + self.terminator)
            sys.stdout.flush()
        except Exception:
            self.handleError(record)


def _setup_logger() -> logging.Logger:
    """Khởi tạo logger với console + file handler."""
    _logger = logging.getLogger("exact")
    _logger.setLevel(logging.DEBUG)

    # Tránh duplicate handlers nếu import nhiều lần
    if _logger.handlers:
        return _logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler — safe encoding
    console_handler = _SafeConsoleHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    _logger.addHandler(console_handler)

    # File handler — UTF-8 đầy đủ (emoji hiển thị OK)
    file_handler = logging.FileHandler(
        _LOG_DIR / "exact_2026.log", encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    _logger.addHandler(file_handler)

    return _logger


logger = _setup_logger()
