"""项目级日志配置。"""

from __future__ import annotations

import sys
from datetime import datetime

from loguru import logger as _logger


def sink_function(message) -> None:
    """根据日志级别生成前缀并拼接消息"""
    try:
        record = message.record
        level_name = record.get('level', 'INFO').name
        prefix = level_name.lower() + ":"
        log_time = record.get('time', datetime.now()).strftime('%Y-%m-%d %H:%M:%S')
        msg = record.get('message', '')
        # 重新根据格式要求组合
        text = f"{prefix} [{log_time}] {msg}\n"
        sys.stdout.write(text)
        sys.stdout.flush()
    except Exception as e:
        sys.stderr.write(f"error: [LOG SINK ERROR] {e}\n")

# 重新配置默认输出，确保格式统一且线程安全。
# 注意：enqueue=True 会让 loguru 使用 multiprocessing.SimpleQueue，
# 而 Android (python-for-android) 的 Python 缺少 _multiprocessing C 扩展会导致崩溃；
# 本 agent 为单进程模型，enqueue 非必需，故关闭以兼容 Android。
_logger.remove()
_logger.add(
    sink_function,
    # level="INFO",
    level="DEBUG",
    enqueue=False,
    backtrace=True,
    diagnose=False,
)

logger = _logger

__all__ = ["logger"]
