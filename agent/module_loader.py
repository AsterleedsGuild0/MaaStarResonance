"""类似 NoneBot 的模组加载器"""
import importlib
import os
import re
from typing import Set, Optional

from logger import logger


class Module:
    def __init__(self, name: str, module):
        self.name = name
        self.module = module

    def __repr__(self):
        return f"<Module name={self.name}>"


def load_module(module_name: str, no_fast: bool = False) -> Optional[Module]:
    """加载单个模组模块"""
    try:
        module = importlib.import_module(module_name)
        if no_fast and getattr(module, "fast", False):
            return None
        logger.info(f"Load {module_name} successfully.")
        return Module(module_name, module)
    except Exception as e:
        logger.error(f"Load {module_name} failed: {e}")
        return None


def load_modules(plugin_dir: str,
                 module_prefix: str,
                 no_fast: bool = False,
                 recursive: bool = True) -> Set[Module]:
    """
    从指定目录加载模组

    Args:
        plugin_dir (str): 模组目录
        module_prefix (str): 模块导入前缀，例如 'agent'
        no_fast (bool): 是否跳过 fast 模式模组
        recursive (bool): 是否递归加载子包

    Returns:
        Set[Module]: 成功加载的模组集合
    """
    loaded_plugins: Set[Module] = set()

    if not os.path.exists(plugin_dir):
        raise FileNotFoundError(f"模组目录不存在: {plugin_dir}")

    for name in os.listdir(plugin_dir):
        path = os.path.join(plugin_dir, name)

        # 跳过隐藏文件或非法模块名
        if name.startswith('_'):
            continue

        # 目录（包）
        if os.path.isdir(path):
            if not os.path.exists(os.path.join(path, '__init__.py')):
                continue
            # 递归加载子包
            if recursive:
                sub_prefix = f"{module_prefix}.{name}"
                sub_plugins = load_modules(path, sub_prefix, no_fast, recursive)
                loaded_plugins.update(sub_plugins)
            else:
                plugin = load_module(f"{module_prefix}.{name}", no_fast)
                if plugin:
                    loaded_plugins.add(plugin)

        # 单个 .py 文件
        elif os.path.isfile(path) and name.endswith('.py'):
            module_name = re.match(r'([_A-Za-z0-9]+)\.py', name)
            if not module_name:
                continue
            plugin = load_module(f"{module_prefix}.{module_name.group(1)}", no_fast)
            if plugin:
                loaded_plugins.add(plugin)

    return loaded_plugins
