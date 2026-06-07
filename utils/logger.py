"""
KRONOS_X_AGENT 統一日誌模組
提供彩色主控台輸出與滾動檔案記錄功能。
"""

import os
import logging
from logging.handlers import RotatingFileHandler

# -----------------------------------------------------------------------
# 日誌目錄與檔案設定
# -----------------------------------------------------------------------
_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
_LOG_FILE = os.path.join(_LOG_DIR, "kronos.log")

# 滾動檔案參數
_MAX_BYTES = 5 * 1024 * 1024   # 5 MB
_BACKUP_COUNT = 3

# -----------------------------------------------------------------------
# ANSI 色碼 (僅用於主控台)
# -----------------------------------------------------------------------
_COLORS = {
    "DEBUG":    "\033[36m",   # 青色
    "INFO":     "\033[32m",   # 綠色
    "WARNING":  "\033[33m",   # 黃色
    "ERROR":    "\033[31m",   # 紅色
    "CRITICAL": "\033[35m",   # 紫色
}
_RESET = "\033[0m"


class _ColoredFormatter(logging.Formatter):
    """帶有 ANSI 色碼的日誌格式器 (僅供主控台使用)"""

    def __init__(self, fmt: str = None, datefmt: str = None):
        super().__init__(fmt=fmt, datefmt=datefmt)

    def format(self, record: logging.LogRecord) -> str:
        color = _COLORS.get(record.levelname, "")
        original_levelname = record.levelname
        record.levelname = f"{color}{record.levelname}{_RESET}"
        result = super().format(record)
        record.levelname = original_levelname
        return result


# -----------------------------------------------------------------------
# 全域初始化 (只執行一次)
# -----------------------------------------------------------------------
_initialized = False


def _ensure_initialized():
    """確保日誌目錄與根 logger 已完成初始化"""
    global _initialized
    if _initialized:
        return

    os.makedirs(_LOG_DIR, exist_ok=True)

    # 取得根 logger 的 KRONOS 命名空間
    root = logging.getLogger("kronos")
    root.setLevel(logging.DEBUG)

    # 避免重複加入 handler
    if not root.handlers:
        # --- 主控台 handler (彩色) ---
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_fmt = _ColoredFormatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(console_fmt)
        root.addHandler(console_handler)

        # --- 滾動檔案 handler ---
        file_handler = RotatingFileHandler(
            _LOG_FILE,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_fmt = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_fmt)
        root.addHandler(file_handler)

    _initialized = True


# -----------------------------------------------------------------------
# 對外 API
# -----------------------------------------------------------------------
def get_logger(name: str) -> logging.Logger:
    """
    取得已設定好的 logger 實例。

    Args:
        name: 模組或元件名稱，例如 "decision.rule_based"

    Returns:
        logging.Logger: 已掛載主控台與檔案 handler 的 logger

    Usage::

        from utils.logger import get_logger
        logger = get_logger("decision.rule_based")
        logger.info("Decision engine started")
    """
    _ensure_initialized()
    return logging.getLogger(f"kronos.{name}")
