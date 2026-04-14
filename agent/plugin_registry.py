"""插件注册表 - 维护已加载插件的全局注册表。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent.logger import logger


@dataclass
class PluginInfo:
    """插件信息数据类。"""

    name: str
    display_name: str
    version: str
    description: str
    author: str
    module: Any
    metadata: dict[str, Any]


class PluginRegistry:
    """插件注册表单例类，管理所有已加载的插件。"""

    _instance: PluginRegistry | None = None
    _plugins: dict[str, PluginInfo] = {}

    def __new__(cls) -> PluginRegistry:
        """实现单例模式。"""
        if cls._instance is None:
            instance = super().__new__(cls)
            cls._instance = instance
        assert cls._instance is not None
        return cls._instance

    @classmethod
    def get_instance(cls) -> PluginRegistry:
        """获取插件注册表单例实例。

        Returns:
            PluginRegistry: 插件注册表实例
        """
        if cls._instance is None:
            cls._instance = cls()
        assert cls._instance is not None
        return cls._instance

    def register(
        self,
        name: str,
        module: Any,
        metadata: dict[str, Any],
    ) -> None:
        """注册已加载的插件。

        Args:
            name: 插件唯一标识符
            module: 插件模块对象
            metadata: 插件元数据字典
        """
        plugin_info = PluginInfo(
            name=name,
            display_name=metadata.get("display_name", name),
            version=metadata.get("version", "unknown"),
            description=metadata.get("description", ""),
            author=metadata.get("author", "unknown"),
            module=module,
            metadata=metadata,
        )
        self._plugins[name] = plugin_info
        logger.debug(
            f"插件已注册: {plugin_info.display_name} "
            f"v{plugin_info.version} (by {plugin_info.author})"
        )

    def is_available(self, name: str) -> bool:
        """检查插件是否可用。

        Args:
            name: 插件名称

        Returns:
            bool: 插件是否已加载且可用
        """
        return name in self._plugins

    def get_plugin(self, name: str) -> Any | None:
        """获取插件模块。

        Args:
            name: 插件名称

        Returns:
            Any | None: 插件模块对象，如果不存在则返回 None
        """
        plugin_info = self._plugins.get(name)
        if plugin_info is not None:
            return plugin_info.module
        logger.warning(f"尝试访问未注册的插件: {name}")
        return None

    def get_api(self, plugin_name: str, api_name: str) -> Any | None:
        """获取插件导出的 API。

        Args:
            plugin_name: 插件名称
            api_name: API 名称（类名或函数名）

        Returns:
            Any | None: API 对象，如果不存在则返回 None
        """
        plugin_info = self._plugins.get(plugin_name)
        if plugin_info is None:
            logger.warning(f"插件 {plugin_name} 未注册")
            return None

        # 从 exports 获取 API 路径
        exports = plugin_info.metadata.get("exports", {})
        api_path = exports.get(api_name)

        if not api_path:
            logger.warning(
                f"插件 {plugin_name} 未导出 API: {api_name}"
            )
            return None

        # 解析 API 路径 (例如: "packet_capture.PacketCapture")
        try:
            parts = api_path.split(".")
            obj = plugin_info.module

            for part in parts[1:]:  # 跳过模块名本身
                obj = getattr(obj, part)

            return obj
        except AttributeError as e:
            logger.error(
                f"无法从插件 {plugin_name} 获取 API {api_name}: {e}"
            )
            return None

    def get_all_plugins(self) -> dict[str, PluginInfo]:
        """获取所有已注册插件的信息。

        Returns:
            dict[str, PluginInfo]: 插件名称到插件信息的映射
        """
        return self._plugins.copy()

    def unregister(self, name: str) -> bool:
        """注销插件（用于热重载等场景）。

        Args:
            name: 插件名称

        Returns:
            bool: 是否成功注销
        """
        if name in self._plugins:
            plugin_info = self._plugins.pop(name)
            logger.debug(f"插件已注销: {plugin_info.display_name}")
            return True
        logger.warning(f"尝试注销不存在的插件: {name}")
        return False

    def clear(self) -> None:
        """清空所有已注册的插件（用于测试）。"""
        self._plugins.clear()
        logger.debug("插件注册表已清空")


__all__ = ["PluginRegistry", "PluginInfo"]
