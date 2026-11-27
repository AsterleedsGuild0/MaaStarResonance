"""生成 MaaFwApp 配方及独立 Android 载荷，不改写桌面资源。"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tomllib
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.json_utils import remove_line_comments

ABIS = ("arm64-v8a", "x86_64")
START_NODE = "Android启动星痕共鸣"


def write_json(path: Path, data: Any) -> None:
    """写入可读的 UTF-8 JSON；JSON 配方也是合法的 YAML。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def framework_tag(version: str) -> str:
    """把框架的 PEP 440 固定版本转换为 GitHub release tag。"""
    match = re.fullmatch(r"(\d+\.\d+\.\d+)(?:(a|b|rc)(\d+))?", version)
    if not match:
        raise ValueError(f"Unsupported MaaFramework version: {version}")
    release, stage, number = match.groups()
    stages = {"a": "alpha", "b": "beta", "rc": "rc"}
    suffix = f"-{stages[stage]}.{number}" if stage else ""
    return f"v{release}{suffix}"


def read_requirements(path: Path) -> dict[str, str]:
    """Android 构建只接受固定版本，避免在开发机上解析平台相关依赖。"""
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        spec = line.split("#", 1)[0].strip()
        if not spec:
            continue
        match = re.fullmatch(r"([A-Za-z0-9_-]+)==([^\s;]+)", spec)
        if not match:
            raise ValueError(f"Android requirements must be pinned: {spec}")
        name, version = match.groups()
        name = name.lower().replace("_", "-")
        if name in result:
            raise ValueError(f"Duplicate Android requirement: {name}")
        result[name] = version
    return result


def load_config(project: Path = PROJECT_ROOT) -> dict[str, Any]:
    """检查桌面、Android 与 Agent Core 使用完全相同的框架版本。"""
    config = json.loads((project / "android/build-config.json").read_text(encoding="utf-8"))
    requirements = read_requirements(project / "requirements-android.txt")
    desktop = tomllib.loads((project / "pyproject.toml").read_text(encoding="utf-8"))
    pinned = config["maafw"]
    if requirements.get("maafw") != pinned or f"maafw=={pinned}" not in desktop["project"]["dependencies"]:
        raise ValueError("Desktop, Android and Agent Core MaaFramework pins disagree")
    if config["agentCore"]["tag"] != f"{config['agentCore']['python']}-maafw{framework_tag(pinned)[1:]}":
        raise ValueError("Agent Core tag does not match the pinned MaaFramework/Python")
    if not re.fullmatch(r"[0-9a-f]{40}", config["maaFwApp"]["revision"]):
        raise ValueError("MaaFwApp must be pinned to a complete commit SHA")
    return config


def prepare_payload(
    project: Path, output: Path, abi: str, version: str, version_code: int
) -> dict[str, str]:
    """组装资源、模型、Agent 和单 ABI 配方，返回 CI 需要的公开元数据。"""
    config = load_config(project)
    if abi not in ABIS:
        raise ValueError(f"Unsupported ABI: {abi}")
    if not 1 <= version_code <= 2_100_000_000:
        raise ValueError("Android versionCode is outside the supported range")
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", version):
        raise ValueError(f"Invalid Android versionName: {version}")
    models = project / "assets/MaaCommonAssets/OCR/ppocr_v5/zh_cn"
    for name in ("det.onnx", "rec.onnx", "keys.txt"):
        if not (models / name).is_file():
            raise FileNotFoundError(f"OCR submodule file is missing: {models / name}")

    interface = json.loads(remove_line_comments((project / "assets/interface.json").read_text(encoding="utf-8-sig")))
    if interface.get("interface_version") != 2 or not isinstance(interface.get("agent"), dict):
        raise ValueError("This project requires PI V2 with one Python Agent")
    output = output.resolve()
    payload = output / "payload"
    if project.resolve().is_relative_to(payload) or payload.is_relative_to((project / "assets").resolve()) or payload.is_relative_to((project / "agent").resolve()):
        raise ValueError("Android output must not replace project source directories")
    if payload.exists():
        shutil.rmtree(payload)
    payload.mkdir(parents=True)
    shutil.copytree(project / "assets/resource", payload / "resource")
    shutil.copytree(models, payload / "resource/base/model/ocr", dirs_exist_ok=True)
    shutil.copytree(
        project / "agent", payload / "agent",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", "plugins"),
    )
    for name in ("LICENSE", "README.md", "CONTACT"):
        shutil.copy2(project / name, payload / name)
    shutil.copy2(project / "static/img/logo_transparent.png", payload / "logo.png")
    interface["version"] = version
    interface["icon"] = "logo.png"
    interface["agent"] = {"child_exec": "python3", "child_args": ["agent/main.py"]}
    for key in ("mirrorchyan_rid", "mirrorchyan_multiplatform"):
        interface.pop(key, None)
    interface["task"].insert(0, {
        "name": "启动星痕共鸣",
        "entry": START_NODE,
        "description": "首次后台运行时先启动游戏到虚拟屏，再登录游戏并执行其他任务。",
    })
    write_json(payload / "interface.json", interface)
    write_json(payload / "resource/base/pipeline/android_start.json", {
        START_NODE: {
            "recognition": "DirectHit",
            "action": {"type": "StartApp", "param": {"package": config["gamePackage"]}},
        }
    })
    write_json(payload / "android-build.json", {
        "version": version, "versionCode": version_code, "abi": abi,
        "maaFwApp": config["maaFwApp"], "maafw": config["maafw"],
        "agentCore": config["agentCore"]["tag"],
    })
    write_json(output / "profile.json", {
        "assets": "payload",
        "include": ["interface.json", "resource/**", "agent/**", "logo.png", "LICENSE", "README.md", "CONTACT", "android-build.json"],
        "agent": {
            "sourceDir": "agent-dist", "abi": [abi],
            "runtimes": [{
                "location": "bundle", "executable": "bin/python3",
                "args": ["-u", "agent/main.py"],
                "env": {
                    "PYTHONHOME": "{bundle}/prefix",
                    "PYTHONPATH": "{bundle}/site-packages/pure.zip:{bundle}/site-packages",
                    "LD_LIBRARY_PATH": "{bundle}/prefix/lib:{bundle}/site-packages/chaquopy/lib:{nativeLibs}",
                    "MAAFW_BINARY_PATH": "{nativeLibs}",
                    "RAPIDFUZZ_IMPLEMENTATION": "python",
                },
            }],
        },
        "display": {"foreground": False, "presets": [{"label": "720P", "width": 1280, "height": 720, "dpi": 240}]},
        "app": {
            "id": config["app"]["applicationId"].rsplit(".", 1)[-1],
            "label": config["app"]["label"],
            "icon": "payload/logo.png",
        },
    })
    return {
        "app_repository": config["maaFwApp"]["repository"],
        "app_revision": config["maaFwApp"]["revision"],
        "maafw_tag": framework_tag(config["maafw"]),
        "version_name": version, "version_code": str(version_code),
        "application_id": config["app"]["applicationId"],
        "compile_sdk": str(config["compileSdk"]),
        "sdk_platform": config["sdkPlatform"],
        "build_tools": config["buildTools"], "ndk_version": config["ndkVersion"],
        "cmake_version": config["cmakeVersion"],
    }


def main() -> None:
    """提供本地与 Actions 共用的预处理入口。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--abi", choices=ABIS, required=True)
    parser.add_argument("--version")
    parser.add_argument("--version-code", type=int, required=True)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "android/.build")
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    project = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    version = args.version or f"{project['version']}-ci.{os.environ.get('GITHUB_RUN_NUMBER', '0')}.{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}.g{os.environ.get('GITHUB_SHA', 'local')[:7]}"
    metadata = prepare_payload(PROJECT_ROOT, args.output, args.abi, version, args.version_code)
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as stream:
            for key, value in metadata.items():
                stream.write(f"{key}={value}\n")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    print(f"MaaFwApp profile: {(args.output / 'profile.json').resolve()}")


if __name__ == "__main__":
    main()
