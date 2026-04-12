"""插件加载器 - 扫描、验证、加载插件，管理插件生命周期。"""

from __future__ import annotations

import importlib
import importlib.metadata
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent.logger import logger
from agent.plugin_registry import PluginRegistry


@dataclass
class PluginMetadata:
    """插件元数据数据类。"""

    name: str
    display_name: str
    version: str
    description: str
    author: str
    license: str
    pyz_file: str
    entry_point: str
    dependencies: list[str]
    system_requirements: dict[str, Any]
    exports: dict[str, str]
    plugin_dir: Path

    @classmethod
    def from_dict(cls, data: dict[str, Any], plugin_dir: Path) -> PluginMetadata:
        """从字典创建插件元数据。

        Args:
            data: 插件元数据字典
            plugin_dir: 插件目录路径

        Returns:
            PluginMetadata: 插件元数据对象
        """
        return cls(
            name=str(data["name"]),
            display_name=str(data.get("display_name") or data["name"]),
            version=str(data.get("version") or "unknown"),
            description=str(data.get("description") or ""),
            author=str(data.get("author") or "unknown"),
            license=str(data.get("license") or "unknown"),
            pyz_file=str(data["pyz_file"]),
            entry_point=str(data["entry_point"]),
            dependencies=list(data.get("dependencies") or []),
            system_requirements=dict(data.get("system_requirements") or {}),
            exports=dict(data.get("exports") or {}),
            plugin_dir=plugin_dir,
        )


class PluginLoader:
    """插件加载器类，负责插件的发现、验证和加载。"""

    def __init__(self, plugins_dir: Path):
        """初始化插件加载器。

        Args:
            plugins_dir: 插件根目录路径
        """
        self.plugins_dir = Path(plugins_dir)
        self.registry = PluginRegistry.get_instance()

    def discover_plugins(self) -> list[PluginMetadata]:
        """扫描并返回所有可用插件的元数据。

        Returns:
            list[PluginMetadata]: 发现的插件元数据列表
        """
        plugins = []

        if not self.plugins_dir.exists():
            logger.warning(f"插件目录不存在: {self.plugins_dir}")
            return plugins

        for plugin_dir in self.plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue

            metadata = self.validate_plugin(plugin_dir)
            if metadata:
                plugins.append(metadata)

        logger.info(f"发现 {len(plugins)} 个插件")
        return plugins

    def validate_plugin(self, plugin_dir: Path) -> PluginMetadata | None:
        """验证插件目录结构和元数据。

        Args:
            plugin_dir: 插件目录路径

        Returns:
            PluginMetadata | None: 验证通过返回元数据，否则返回 None
        """
        plugin_json = plugin_dir / "plugin.json"

        if not plugin_json.exists():
            logger.debug(f"跳过目录 {plugin_dir.name}: 缺少 plugin.json")
            return None

        try:
            with open(plugin_json, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"插件 {plugin_dir.name} 的 plugin.json 格式错误: {e}")
            return None
        except Exception as e:
            logger.error(f"读取插件 {plugin_dir.name} 的 plugin.json 失败: {e}")
            return None

        required_fields = ["name", "pyz_file", "entry_point"]
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            logger.error(
                f"插件 {plugin_dir.name} 的 plugin.json 缺少必需字段: "
                f"{', '.join(missing_fields)}"
            )
            return None

        try:
            metadata = PluginMetadata.from_dict(data, plugin_dir)
        except Exception as e:
            logger.error(f"解析插件 {plugin_dir.name} 的元数据失败: {e}")
            return None

        pyz_path = plugin_dir / metadata.pyz_file
        if not pyz_path.exists():
            logger.error(
                f"插件 {metadata.name} 的 .pyz 文件不存在: {metadata.pyz_file}"
            )
            return None

        if not self._check_system_requirements(metadata):
            return None

        logger.debug(f"插件验证通过: {metadata.display_name} v{metadata.version}")
        return metadata

    @staticmethod
    def _check_system_requirements(metadata: PluginMetadata) -> bool:
        """检查插件的系统要求。

        Args:
            metadata: 插件元数据

        Returns:
            bool: 系统要求是否满足
        """
        sys_req = metadata.system_requirements

        if "platform" in sys_req:
            required_platform = sys_req["platform"].lower()
            current_platform = sys.platform

            if required_platform == "windows" and not current_platform.startswith("win"):
                logger.warning(
                    f"插件 {metadata.name} 需要 Windows 平台，当前平台: {current_platform}"
                )
                return False
            elif required_platform == "linux" and current_platform != "linux":
                logger.warning(
                    f"插件 {metadata.name} 需要 Linux 平台，当前平台: {current_platform}"
                )
                return False
            elif required_platform == "darwin" and current_platform != "darwin":
                logger.warning(
                    f"插件 {metadata.name} 需要 macOS 平台，当前平台: {current_platform}"
                )
                return False

        if "min_python_version" in sys_req:
            min_version = sys_req["min_python_version"]
            current_version = f"{sys.version_info.major}.{sys.version_info.minor}"
            if current_version < min_version:
                logger.warning(
                    f"插件 {metadata.name} 需要 Python {min_version}+，"
                    f"当前版本: {current_version}"
                )
                return False

        if "notes" in sys_req:
            logger.info(f"插件 {metadata.name} 系统要求: {sys_req['notes']}")

        return True

    @staticmethod
    def check_dependencies(metadata: PluginMetadata) -> list[str]:
        """检查插件依赖，返回缺失的依赖列表。

        Args:
            metadata: 插件元数据

        Returns:
            list[str]: 缺失的依赖文件路径列表
        """
        missing_deps = []

        for dep in metadata.dependencies:
            dep_path = metadata.plugin_dir / dep

            if not dep_path.exists():
                logger.warning(f"插件 {metadata.name} 的依赖文件不存在: {dep}")
                missing_deps.append(dep)
                continue

            wheel_name = dep_path.name
            package_name = wheel_name.split("-")[0]

            try:
                importlib.metadata.version(package_name)
                logger.debug(f"依赖 {package_name} 已安装")
            except importlib.metadata.PackageNotFoundError:
                logger.debug(f"依赖 {package_name} 未安装")
                missing_deps.append(dep)

        return missing_deps

    def install_dependencies(self, metadata: PluginMetadata) -> bool:
        """从插件 deps/ 目录安装依赖。

        Args:
            metadata: 插件元数据

        Returns:
            bool: 是否成功安装所有依赖
        """
        deps_dir = metadata.plugin_dir / "deps"
        if not deps_dir.exists():
            logger.debug(f"插件 {metadata.name} 没有 deps/ 目录，跳过依赖安装")
            return True

        # 获取 deps/ 目录下所有 .whl 文件
        wheel_files = list(deps_dir.glob("*.whl"))
        
        if not wheel_files:
            logger.debug(f"插件 {metadata.name} 的 deps/ 目录中没有 wheel 文件")
            return True

        logger.info(f"开始安装插件 {metadata.name} 的依赖 (共 {len(wheel_files)} 个)...")

        try:
            cmd = [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--no-index",
                "--find-links",
                str(deps_dir),
                *[str(whl) for whl in wheel_files],
            ]

            logger.debug(f"执行命令: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                logger.error(
                    f"插件 {metadata.name} 依赖安装失败:\n{result.stderr}"
                )
                return False

            logger.info(f"插件 {metadata.name} 依赖安装成功")
            return True

        except Exception as e:
            logger.exception(f"插件 {metadata.name} 依赖安装异常: {e}")
            return False

    def load_plugin(self, metadata: PluginMetadata) -> bool:
        """加载插件到 Python 环境。

        Args:
            metadata: 插件元数据

        Returns:
            bool: 是否成功加载插件
        """
        pyz_path = metadata.plugin_dir / metadata.pyz_file

        try:
            pyz_path_str = str(pyz_path.absolute())
            if pyz_path_str not in sys.path:
                sys.path.insert(0, pyz_path_str)
                logger.debug(f"已将 {pyz_path_str} 添加到 sys.path")

            module = importlib.import_module(metadata.entry_point)
            logger.debug(f"成功导入模块: {metadata.entry_point}")

            self.registry.register(
                metadata.name,
                module,
                {
                    "display_name": metadata.display_name,
                    "version": metadata.version,
                    "description": metadata.description,
                    "author": metadata.author,
                    "license": metadata.license,
                    "exports": metadata.exports,
                    "system_requirements": metadata.system_requirements,
                },
            )

            logger.info(
                f"插件加载成功: {metadata.display_name} v{metadata.version}"
            )
            return True

        except ImportError as e:
            logger.error(f"插件 {metadata.name} 导入失败: {e}")
            return False
        except Exception as e:
            logger.exception(f"插件 {metadata.name} 加载异常: {e}")
            return False

    def load_all(self) -> dict[str, str]:
        """加载所有插件，返回加载结果。

        Returns:
            dict[str, str]: 插件名称到加载状态的映射
                状态值: "loaded" (成功), "failed" (失败), "deps_failed" (依赖安装失败)
        """
        results = {}
        plugins = self.discover_plugins()

        for metadata in plugins:
            if not self.install_dependencies(metadata):
                results[metadata.name] = "deps_failed"
                logger.warning(
                    f"插件 {metadata.display_name} 因依赖安装失败而跳过加载"
                )
                continue

            if self.load_plugin(metadata):
                results[metadata.name] = "loaded"
            else:
                results[metadata.name] = "failed"

        return results


__all__ = ["PluginLoader", "PluginMetadata"]