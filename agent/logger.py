"""项目级日志配置。"""

from __future__ import annotations

import sys
from datetime import datetime

from loguru import logger as _logger


def sink_function(message) -> None:
    """根据日志级别生成前缀并拼接消息"""
    try:
        record = message.record
        level_name = record.get("level", "INFO").name
        prefix = level_name.lower() + ":"
        log_time = record.get("time", datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
        msg = record.get("message", "")
        # 重新根据格式要求组合
        text = f"{prefix} [{log_time}] {msg}\n"
        sys.stdout.write(text)
        sys.stdout.flush()
    except Exception as e:
        sys.stderr.write(f"error: [LOG SINK ERROR] {e}\n")


# 重新配置默认输出，确保格式统一且线程安全。
_logger.remove()
_logger.add(
    sink_function,
    # level="INFO",
    level="DEBUG",
    enqueue=True,
    backtrace=True,
    diagnose=False,
)

logger = _logger

__all__ = ["logger", "sink_function"]
