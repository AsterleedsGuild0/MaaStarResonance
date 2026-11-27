"""校验固定 Agent Core，并组装两个 ABI 可复现的 Android Python 依赖。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from email.parser import BytesParser
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from android.prepare import ABIS, load_config, read_requirements


def sha256_file(path: Path) -> str:
    """流式计算下载产物的 SHA-256。"""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_core_archive(
    path: Path, abi: str, config: dict[str, Any]
) -> dict[str, Any]:
    """拒绝损坏、错误 ABI 或与客户端框架版本不一致的内核。"""
    core = config["agentCore"]
    if sha256_file(path) != core["sha256"][abi]:
        raise ValueError(f"Agent Core SHA-256 mismatch: {path}")
    with tarfile.open(path) as archive:
        entry = archive.extractfile(f"{abi}/bundle/agent-core.json")
        if entry is None:
            raise ValueError("Agent Core manifest is missing")
        manifest = json.load(entry)
    if (
        manifest["abi"] != abi
        or manifest["python"] != core["python"]
        or manifest["provides"].get("maafw") != config["maafw"]
        or not {"numpy", "strenum"}.issubset(manifest["provides"])
    ):
        raise ValueError("Agent Core ABI, Python or MaaFramework does not match")
    return manifest


def verify_pure_wheel(path: Path, version: str) -> None:
    """防止把宿主平台编译的 RapidFuzz wheel 带进 Android。"""
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        wheel = next(name for name in names if name.endswith(".dist-info/WHEEL"))
        metadata = next(
            name for name in names if name.endswith(".dist-info/METADATA")
        )
        wheel_info = BytesParser().parsebytes(archive.read(wheel))
        package = BytesParser().parsebytes(archive.read(metadata))
        tags = wheel_info.get_all("Tag", [])
        if (
            package["Name"].lower() != "rapidfuzz"
            or package["Version"] != version
            or wheel_info["Root-Is-Purelib"].lower() != "true"
            or not tags
            or any(not tag.endswith("-none-any") for tag in tags)
            or any(name.endswith((".so", ".pyd", ".dll", ".dylib")) for name in names)
        ):
            raise ValueError(f"RapidFuzz must be a pure Python wheel: {path}")


def build_runtime(abi: str, app_root: Path, output: Path) -> None:
    """调用固定外壳的 Android wheel 安装器，不经过 P4A 或宿主依赖解析。"""
    config = load_config()
    requirements = read_requirements(PROJECT_ROOT / "requirements-android.txt")
    core = config["agentCore"]
    downloads = output / "downloads" / core["tag"]
    downloads.mkdir(parents=True, exist_ok=True)
    filename = f"agent-core-{core['python']}-{abi}.tar.gz"
    archive = downloads / filename
    if not archive.is_file():
        url = (
            f"https://github.com/{core['repository']}/releases/download/"
            f"{core['tag']}/{filename}"
        )
        request = urllib.request.Request(url, headers={"User-Agent": "MaaStarResonance"})
        part = archive.with_suffix(".part")
        with urllib.request.urlopen(request, timeout=120) as source:
            with part.open("wb") as target:
                while chunk := source.read(1024 * 1024):
                    target.write(chunk)
        part.replace(archive)
    manifest = verify_core_archive(archive, abi, config)
    print(f"Verified Agent Core: {abi}, CPython {manifest['python']}", flush=True)

    wheels = output / "wheels"
    wheels.mkdir(parents=True, exist_ok=True)
    version = requirements["rapidfuzz"]
    existing = list(wheels.glob(f"rapidfuzz-{version}-*.whl"))
    if not existing:
        subprocess.run(
            [
                sys.executable, "-m", "pip", "wheel", "--no-deps",
                "--no-binary=rapidfuzz", "--config-settings=wheel.cmake=false",
                "--wheel-dir", str(wheels), f"rapidfuzz=={version}",
            ],
            check=True,
        )
        existing = list(wheels.glob(f"rapidfuzz-{version}-*.whl"))
    if len(existing) != 1:
        raise ValueError("Expected exactly one RapidFuzz pure Python wheel")
    verify_pure_wheel(existing[0], version)

    environment = os.environ.copy()
    environment["PIP_FIND_LINKS"] = str(wheels.resolve())
    subprocess.run(
        [
            sys.executable, str(app_root / "scripts/build_agent_bundle.py"),
            "--core", str(archive.resolve()), "--abi", abi,
            "--out", str((output / "agent-dist").resolve()),
            "--requirements", str(PROJECT_ROOT / "requirements-android.txt"),
            "--no-deps", "--work", str((output / "runtime-cache").resolve()),
        ],
        env=environment,
        check=True,
    )
    bundle = output / "agent-dist" / abi / "bundle"
    if not (bundle / "bin/python3").is_file():
        raise ValueError("Android Python executable is missing")
    with zipfile.ZipFile(bundle / "site-packages/pure.zip") as packages:
        required = {
            "maa/__init__.py", "loguru/__init__.py", "rapidfuzz/__init__.py",
            "toml/__init__.py", "tzdata/__init__.py",
        }
        missing = required - set(packages.namelist())
        if missing:
            raise ValueError(f"Android Python packages are missing: {sorted(missing)}")
    print(f"Verified Android runtime: {bundle}")


def main() -> None:
    """提供本地与 Actions 共用的运行时组装命令。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--abi", choices=ABIS, required=True)
    parser.add_argument(
        "--app-root", type=Path, default=PROJECT_ROOT / "android/MaaFwApp"
    )
    parser.add_argument(
        "--output", type=Path, default=PROJECT_ROOT / "android/.build"
    )
    args = parser.parse_args()
    build_runtime(args.abi, args.app_root.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
