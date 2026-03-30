#!/usr/bin/env python3
"""
在本机一键生成多平台产物（当前支持: Windows / macOS / Linux）：

- 按矩阵(os × arch)下载 MaaFramework 预编译包并解压到 deps/
- 下载并解压 MFAAvalonia 到临时目录后合并 (不覆盖已有文件)
- 调用 install.py 生成 install/
- 打包为 releases/<tag>/MaaStarResonance-<os>-<arch>-<tag>.zip，并生成 SHA256SUMS.txt

依赖：仅使用 Python 标准库；不需要额外三方包。

用法示例：
    python scripts/build_all_platforms.py --tag v1.2.3
    python scripts/build_all_platforms.py --only-os win,linux --only-arch x86_64 --skip-deps
    GITHUB_TOKEN=xxxxx python scripts/build_all_platforms.py

注意：该脚本不进行“编译”，而是复用上游已发布的各平台二进制进行装配与打包。

已移除 Android 支持（历史遗留逻辑已清理）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Sequence
from urllib import request, error as urlerror
from zoneinfo import ZoneInfo
from datetime import datetime, timezone

# Ensure repo root is on sys.path so `python scripts/*.py` works outside package context.
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT_FOR_IMPORT = _SCRIPT_DIR.parent
if str(_REPO_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT_FOR_IMPORT))

from scripts.install import _strip_interface_json_comments


REPO_ROOT = (Path(__file__).parent / "..").resolve()
RELEASES_DIR = REPO_ROOT / "releases"
RELEASES_DIR.mkdir(parents=True, exist_ok=True)
SOURCE_COPY_DST_DIR = RELEASES_DIR / "source_code"
SOURCE_COPY_DST_DIR.mkdir(parents=True, exist_ok=True)
SUBMODULES_DIR = RELEASES_DIR / "submodules"
SUBMODULES_DIR.mkdir(parents=True, exist_ok=True)
INSTALL_PY = REPO_ROOT / "scripts/install.py"


PLATFORM_MATRIX: List[Tuple[str, str]] = [
    ("win", "aarch64"),
    ("win", "x86_64"),
    ("macos", "aarch64"),
    ("macos", "x86_64"),
    ("linux", "aarch64"),
    ("linux", "x86_64"),
]

# MFAAvalonia 文件名所需的映射
MFA_OS_MAP = {"win": "win", "macos": "osx", "linux": "linux"}
MFA_ARCH_MAP = {"x86_64": "x64", "aarch64": "arm64"}


def log_section(msg: str) -> None:
    print(f"\n=== {msg} ===")


def info(msg: str) -> None:
    print(msg)


def warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def fail(msg: str) -> None:
    print(f"[ERROR] {msg}")
    sys.exit(1)


def run(
    cmd: List[str], cwd: Optional[Path] = None, check: bool = True
) -> subprocess.CompletedProcess:
    info(f"$ {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None)
    if check and proc.returncode != 0:
        fail(f"命令失败，退出码 {proc.returncode}: {' '.join(cmd)}")
    return proc


def git_short_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(REPO_ROOT)
        )
        return out.decode().strip()
    except Exception:
        return "unknown"


def git_latest_tag_v() -> Optional[str]:
    try:
        out = subprocess.check_output(
            ["git", "describe", "--tags", "--match", "v*"], cwd=str(REPO_ROOT)
        )
        tag = out.decode().strip()
        return tag if tag.startswith("v") else None
    except Exception:
        return None


def gh_latest_release_tag(repo: str, token: Optional[str]) -> Optional[str]:
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    headers = {"User-Agent": "local-builder"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = request.Request(url, headers=headers)
    try:
        with request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            tag = data.get("tag_name")
            return tag if isinstance(tag, str) and tag.startswith("v") else None
    except Exception:
        return None


def compute_tag(explicit_tag: Optional[str], token: Optional[str]) -> str:
    if explicit_tag:
        if not re.match(r"^v\d+\.\d+\.\d+.*$", explicit_tag):
            warn("--tag 不是以 v 开头的语义化版本，仍将继续使用该值")
        return explicit_tag

    # 尝试使用当前引用上的 v* tag
    tag = git_latest_tag_v()
    if not tag:
        # 取远端最新发布的 tag
        tag = gh_latest_release_tag("AsterleedsGuild0/MaaStarResonance", token) or "v0.0.0"
    # 追加日期与短 SHA，形成类似 Actions 的非发布标记
    # today = datetime.now().strftime("%y%m%d")
    # 追加小时分钟，避免同一天多次构建冲突
    today = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%y%m%d%H%M")
    tag = f"{tag}-{today}-{git_short_sha()}"
    return tag


def api_get_json(url: str, token: Optional[str]) -> dict:
    headers = {"User-Agent": "local-builder"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = request.Request(url, headers=headers)
    with request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def get_latest_release_assets(repo: str, token: Optional[str]) -> List[dict]:
    data = api_get_json(f"https://api.github.com/repos/{repo}/releases/latest", token)
    assets = data.get("assets") or []
    if not assets:
        fail(f"未在 {repo} 最新发布中找到 assets")
    return assets


def get_latest_release_info(repo: str, token: Optional[str]) -> Tuple[str, List[dict]]:
    """返回 (tag_name, assets)。

    为后续缓存使用提供 tag 名字。"""
    return get_release_info(repo, token, version=None)


def get_release_info(
    repo: str, token: Optional[str], version: Optional[str] = None
) -> Tuple[str, List[dict]]:
    """获取指定版本或最新版本的 release 信息。

    Args:
        repo: GitHub 仓库名，格式为 owner/name
        token: GitHub token(可选)
        version: 指定版本标签，如 v2.0.0, 若为 None 则获取最新版本

    Returns:
        (tag_name, assets) 元组
    """
    if version:
        url = f"https://api.github.com/repos/{repo}/releases/tags/{version}"
        info(f"获取 {repo} 的指定版本: {version}")
    else:
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        info(f"获取 {repo} 的最新版本")

    data = api_get_json(url, token)
    tag_raw = data.get("tag_name")
    if not isinstance(tag_raw, str) or not tag_raw:
        fail(f"未能获取 {repo} 最新 release tag")
    tag = str(tag_raw)
    assets = data.get("assets") or []
    if not assets:
        fail(f"未在 {repo} 最新发布中找到 assets")
    return tag, assets


def wildcard_to_regex(pattern: str) -> re.Pattern:
    # 将简单 * 通配转为完整正则
    return re.compile("^" + re.escape(pattern).replace(r"\*", ".*") + "$")


def find_asset_by_pattern(assets: List[dict], pattern: str) -> Optional[dict]:
    rx = wildcard_to_regex(pattern)
    for a in assets:
        name = a.get("name", "")
        if rx.match(name):
            return a
    return None


def git_list_non_ignored_files(repo_root: Path) -> List[Path]:
    """使用 git 列出未被忽略的文件（包含已追踪与未忽略的未追踪文件）。"""
    try:
        out = subprocess.check_output(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=str(repo_root),
        )
        parts = [p for p in out.decode(errors="ignore").split("\0") if p]
        return [repo_root / p for p in parts]
    except Exception as e:
        fail(f"无法获取 git 文件列表: {e}")
        return []


def prepare_source_copy(repo_root: Path, dest_dir: Path) -> None:
    """清空并重建 releases/source_code，将未被 .gitignore 忽略的文件复制过去。

    显式排除以 releases/ 开头的路径，避免自包含复制。
    """
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    files = git_list_non_ignored_files(repo_root)
    for src in files:
        rel = src.relative_to(repo_root)
        # 跳过 releases/*，避免递归复制
        if str(rel).startswith("releases/") or str(rel) == "releases":
            continue
        target = dest_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if src.is_symlink():
            # 复制符号链接的目标内容
            try:
                data = src.read_bytes()
                target.write_bytes(data)
            except Exception:
                # 回退到常规复制
                shutil.copy2(src, target)
        elif src.is_file():
            shutil.copy2(src, target)
        # 目录由其中文件复制时自动创建，无需单独处理

    # 修改 agent/main.py 的内容, 将 # init_python_env() 的注释取消掉
    uncomment_lines = ["# init_python_env()"]

    agent_main = dest_dir / "agent" / "main.py"
    if agent_main.exists():
        try:
            text = agent_main.read_text(encoding="utf-8")
            new_text = text
            applied: List[str] = []
            for commented in uncomment_lines:
                target = commented.lstrip("#").strip()
                pattern = rf"^([ \t]*)#\s*{re.escape(target)}"
                if re.search(pattern, new_text, flags=re.MULTILINE):
                    new_text = re.sub(
                        pattern,
                        rf"\1{target}",
                        new_text,
                        flags=re.MULTILINE,
                    )
                    applied.append(target)
            if new_text != text:
                agent_main.write_text(new_text, encoding="utf-8")
                info("已取消 agent/main.py 中的注释: " + ", ".join(applied))
            else:
                info("agent/main.py 中未找到需要取消的注释")
        except Exception as e:
            warn(f"修改 agent/main.py 失败: {e}")
    else:
        warn("未找到 agent/main.py，无法取消注释 init_python_env()")
    agent_main = dest_dir / "agent" / "main.py"
    if agent_main.exists():
        try:
            text = agent_main.read_text(encoding="utf-8")
            new_text = re.sub(
                r"^[ \t]*#\s*init_python_env\(\)",
                "init_python_env()",
                text,
                flags=re.MULTILINE,
            )
            if new_text != text:
                agent_main.write_text(new_text, encoding="utf-8")
                info("已取消 agent/main.py 中的 init_python_env() 注释")
            else:
                info("agent/main.py 中未找到被注释的 init_python_env()")
        except Exception as e:
            warn(f"修改 agent/main.py 失败: {e}")
    else:
        warn("未找到 agent/main.py，无法取消注释 init_python_env()")

    # 读取并修改 assets/interface.json 中的 agent 字段
    ## 先将 assets/interface.json  中的 // 注释全部去掉
    _strip_interface_json_comments(dest_dir / "assets" / "interface.json")

    with open(dest_dir / "assets" / "interface.json", "r", encoding="utf-8") as f:
        interface = json.load(f)
    interface["agent"]["child_exec"] = "{PROJECT_DIR}/python/python.exe"
    interface["agent"]["child_args"] = ["{PROJECT_DIR}/agent/main.py"]
    with open(dest_dir / "assets" / "interface.json", "w", encoding="utf-8") as f:
        json.dump(interface, f, ensure_ascii=False, indent=4)

    # 拷贝 resource 目录
    shutil.copytree(
        repo_root / "resource",
        dest_dir / "resource",
        dirs_exist_ok=True,
    )


def ensure_ocr_in_source_copy(repo_root: Path, source_copy_dir: Path) -> None:
    """如果 OCR 模型目录在源代码副本中缺失，但在仓库本地存在，则补拷过去。

    该目录通常较大，可能被 .gitignore 忽略，但 install.py 的 configure_ocr_model 依赖其存在。
    """
    src = repo_root / "assets" / "MaaCommonAssets" / "OCR"
    dst = source_copy_dir / "assets" / "MaaCommonAssets" / "OCR"
    if not dst.exists():
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            info("检测到 OCR 目录未随源码副本复制，尝试从仓库本地补拷...")
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            # 明确提示缺失，install.py 将无法继续
            warn(
                "缺少 assets/MaaCommonAssets/OCR（OCR 模型）。请将其放置于仓库本地后重试。"
            )


def download(url: str, out_file: Path, token: Optional[str]) -> None:
    out_file.parent.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "local-builder"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = request.Request(url, headers=headers)
    info(f"下载: {url} -> {out_file}")
    with request.urlopen(req, timeout=600) as resp, open(out_file, "wb") as f:
        shutil.copyfileobj(resp, f)


def safe_unpack(archive: Path, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    # 交给 shutil.unpack_archive 处理常见格式(zip, tar, gztar, bztar, xztar)
    try:
        shutil.unpack_archive(str(archive), extract_dir=str(dest_dir))
    except shutil.ReadError as e:
        fail(f"无法解压 {archive.name}: {e}. 请手动解压后重试。")


def replace_deps_from_extracted(extracted_root: Path, deps_dir: Path) -> None:
    # 在解压根中寻找 bin/ 与 share/（可能存在一层目录包裹）
    candidates = [extracted_root]
    # 找到第一个包含 bin 或 share 的层次
    found_root = None
    for base in candidates + list(
        extracted_root.iterdir() if extracted_root.exists() else []
    ):
        if not base.exists() or not base.is_dir():
            continue
        if (base / "bin").is_dir() or (base / "share").is_dir():
            found_root = base
            break
    if not found_root:
        warn(f"在 {extracted_root} 未找到 bin/ 或 share/，可能包结构变化")
        found_root = extracted_root

    # 清空 deps/bin 与 deps/share 并写入
    if (deps_dir / "bin").exists():
        shutil.rmtree(deps_dir / "bin")
    if (deps_dir / "share").exists():
        shutil.rmtree(deps_dir / "share")
    (deps_dir / "bin").mkdir(parents=True, exist_ok=True)

    if (found_root / "bin").exists():
        shutil.copytree(found_root / "bin", deps_dir / "bin", dirs_exist_ok=True)
    if (found_root / "share").exists():
        shutil.copytree(found_root / "share", deps_dir / "share", dirs_exist_ok=True)


def copytree_ignore_existing(src: Path, dst: Path) -> None:
    """递归复制 src 到 dst，但不覆盖已存在的文件。"""
    for root, dirs, files in os.walk(src):
        rel = Path(root).relative_to(src)
        target_dir = dst / rel
        target_dir.mkdir(parents=True, exist_ok=True)
        for d in dirs:
            (target_dir / d).mkdir(parents=True, exist_ok=True)
        for f in files:
            s = Path(root) / f
            t = target_dir / f
            if not t.exists():
                shutil.copy2(s, t)


def sha256_of(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_one(
    os_name: str,
    arch: str,
    tag: str,
    token: Optional[str],
    skip_deps: bool,
    keep_archives: bool,
    keep_staging: bool,
    mfd_info: Tuple[str, List[dict]],
    mfa_info: Optional[Tuple[str, List[dict]]],
) -> Optional[Path]:
    log_section(f"构建 {os_name}-{arch}")
    # 为当前目标创建隔离的 staging 目录（位于 source_code 内）
    staging_root = RELEASES_DIR / ".build" / tag / f"staging-{os_name}-{arch}"
    staging_root.mkdir(parents=True, exist_ok=True)
    MFD_REPO = "MaaXYZ/MaaFramework"
    MFA_REPO = "SweetSmellFox/MFAAvalonia"
    mfd_tag, mfd_assets = mfd_info
    if mfa_info:
        mfa_tag, mfa_assets = mfa_info
    else:
        mfa_tag, mfa_assets = None, []

    # 0) 将 source_code 中的 "assets/**" 和 "**.py" 拷贝到 staging_root
    for asset in (SOURCE_COPY_DST_DIR / "assets").rglob("*"):
        if asset.is_file():
            rel = asset.relative_to(SOURCE_COPY_DST_DIR)
            target = staging_root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(asset, target)
    for py_file in SOURCE_COPY_DST_DIR.rglob("*.py"):
        if py_file.is_file():
            rel = py_file.relative_to(SOURCE_COPY_DST_DIR)
            target = staging_root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(py_file, target)
    # 额外：复制 agent 目录下的非 .py 资源（如 JSON），避免运行期缺失数据文件
    agent_src = SOURCE_COPY_DST_DIR / "agent"
    if agent_src.exists():
        copytree_ignore_existing(agent_src, staging_root / "agent")
    # 拷贝必要的 README 与 LICENSE 文件以及 pyproject.toml
    for doc in ["README.md", "LICENSE", "pyproject.toml"]:
        src = SOURCE_COPY_DST_DIR / doc
        if src.is_file():
            shutil.copy2(src, staging_root / doc)

    # 拷贝 resource 目录
    res_src = SOURCE_COPY_DST_DIR / "resource"
    res_dst = staging_root / "resource"
    if res_src.exists():
        shutil.copytree(
            res_src,
            res_dst,
            dirs_exist_ok=True,
        )
    else:
        warn("缺少 resource 目录，install.py 可能无法继续")

    # 1) 下载/准备 MaaFramework -> deps/bin, deps/share
    if not skip_deps:
        # 查找 MaaFramework 资产（使用预先获取并缓存的列表）
        maa_pattern = f"MAA-{os_name}-{arch}*"
        maa_asset = find_asset_by_pattern(mfd_assets, maa_pattern)
        if not maa_asset:
            warn(f"未找到 {MFD_REPO} 资产: {maa_pattern}，跳过 {os_name}-{arch}")
            return None
        # 缓存路径（基于上游 tag）
        cache_dir = SUBMODULES_DIR / "MaaFramework" / mfd_tag
        cache_dir.mkdir(parents=True, exist_ok=True)
        archive_path = cache_dir / maa_asset["name"]
        if not archive_path.exists():
            info(f"缓存缺失，下载 MaaFramework 资产到 {archive_path}")
            download(maa_asset["browser_download_url"], archive_path, token)
        else:
            info(f"复用已缓存 MaaFramework 资产: {archive_path.name}")
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            safe_unpack(archive_path, tmpdir)
            # replace_deps_from_extracted(tmpdir, deps_dir)
            # 将解压的 MaaFramework 内容复制到 build 目录的 deps/ 下。
            shutil.copytree(tmpdir, staging_root / "deps", dirs_exist_ok=True)
        # 不删除缓存文件；即使 keep_archives=False 也保留（缓存语义）
    else:
        info("--skip-deps: 跳过 MaaFramework 下载，期待使用 staging 内已存在的 deps/")

    # 2) 非 Android 下载 MFAAvalonia -> MFA/<os>-<arch>/
    mfa_dst_dir: Optional[Path] = None
    if not skip_deps:
        os_token = MFA_OS_MAP[os_name]
        arch_token = MFA_ARCH_MAP[arch]
        mfa_dst_dir = staging_root / "MFA"
        mfa_dst_dir.mkdir(parents=True, exist_ok=True)
        if mfa_tag is None:
            warn("未获取 MFAAvalonia release 信息，跳过 MFA 部分")
        else:
            mfa_pattern = f"MFAAvalonia-*-{os_token}-{arch_token}*"
            mfa_asset = find_asset_by_pattern(mfa_assets, mfa_pattern)
            if mfa_asset:
                cache_dir = SUBMODULES_DIR / "MFAAvalonia" / mfa_tag
                cache_dir.mkdir(parents=True, exist_ok=True)
                mfa_archive = cache_dir / mfa_asset["name"]
                if not mfa_archive.exists():
                    info(f"缓存缺失，下载 MFAAvalonia 资产到 {mfa_archive}")
                    download(mfa_asset["browser_download_url"], mfa_archive, token)
                else:
                    info(f"复用已缓存 MFAAvalonia 资产: {mfa_archive.name}")
                safe_unpack(mfa_archive, mfa_dst_dir)
            else:
                warn(f"未找到 {MFA_REPO} 资产: {mfa_pattern}，将仅生成核心产物")
    elif skip_deps:
        info("--skip-deps: 跳过 MFAAvalonia 下载")

    # 3) 调用 staging_root/install.py 生成基础产物
    install_dir = staging_root / "install"
    cmd = [sys.executable, "scripts/install.py", tag, os_name, arch]
    run(cmd, cwd=staging_root)

    if not install_dir.exists():
        fail("staging/install 未生成，install.py 执行可能失败")

    # 4) 合并 MFA 到 install/（不覆盖现有文件）
    if mfa_dst_dir and any(mfa_dst_dir.iterdir()):
        info("合并 MFA 到 install/ (忽略已存在)")
        copytree_ignore_existing(mfa_dst_dir, install_dir)

    # 5) 打包并返回包路径
    (RELEASES_DIR / tag).mkdir(parents=True, exist_ok=True)
    artifact_name = f"MaaStarResonance-{os_name}-{arch}-{tag}"
    base = RELEASES_DIR / tag / artifact_name
    archive_file = shutil.make_archive(str(base), "zip", root_dir=str(install_dir))
    # 清理 staging
    if not keep_staging:
        try:
            shutil.rmtree(staging_root)
        except Exception:
            pass
    info(f"产物: {archive_file}")
    return Path(archive_file)


def write_release_metadata(
    tag: str, artifacts: List[Path], upstream: Optional[dict] = None
) -> None:
    """在 releases/<tag>/ 下写入 SHA256SUMS.txt 与 release.json。"""
    rel_dir = RELEASES_DIR / tag
    # 写 SHA256SUMS
    lines = []
    for p in artifacts:
        lines.append(f"{sha256_of(p)}  {p.name}")
    (rel_dir / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # 写 release.json（简版）
    meta = {
        "tag": tag,
        "created_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "git": {
            "short_sha": git_short_sha(),
        },
        "artifacts": [{"file": p.name, "sha256": sha256_of(p)} for p in artifacts],
    }
    if upstream:
        meta["upstream"] = upstream
    (rel_dir / "release.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_github_token_from_config() -> Optional[str]:
    """从 scripts/config.toml 加载 github_token（若存在）。优先级最高。"""
    cfg_path = REPO_ROOT / "scripts" / "config.toml"
    if not cfg_path.exists():
        return None
    try:
        # Python 3.11+ 标准库
        import tomllib  # type: ignore

        data = tomllib.loads(cfg_path.read_text(encoding="utf-8"))
        token = data.get("github_token")
        if isinstance(token, str) and token.strip():
            return token.strip()
    except Exception as e:
        warn(f"读取 scripts/config.toml 失败: {e}")
    return None


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="在本机装配并打包多平台产物")
    ap.add_argument(
        "--tag", dest="tag", help="版本标签，如 v1.2.3；若省略，将自动生成临时标记"
    )
    ap.add_argument(
        "--maafw-version",
        dest="maafw_version",
        help="指定 MaaFramework 版本标签，如 v2.0.0；若省略，使用最新版本",
    )
    ap.add_argument(
        "--mfaa-version",
        dest="mfaa_version",
        help="指定 MFAAvalonia 版本标签，如 v1.5.0；若省略，使用最新版本",
    )
    ap.add_argument(
        "--skip-deps",
        action="store_true",
        help="跳过依赖(MaaFramework/MFAAvalonia)下载",
    )
    ap.add_argument("--keep-archives", action="store_true", help="保留下载的压缩包")
    ap.add_argument(
        "--keep-staging",
        action="store_true",
        help="保留 staging 工作目录（默认构建完成后清理）",
    )
    ap.add_argument(
        "--github-token", dest="token", help="可选 GitHub Token(提升速率限制)"
    )
    ap.add_argument("--only-os", help="仅构建指定 OS，逗号分隔，例如: win,linux")
    ap.add_argument(
        "--only-arch", help="仅构建指定架构，逗号分隔，例如: x86_64,aarch64"
    )
    ap.add_argument("--exclude", help="排除的 <os>:<arch>，逗号分隔，例如: win:x86_64")
    return ap.parse_args(argv)


def filter_matrix(
    only_os: Optional[str], only_arch: Optional[str], exclude: Optional[str]
) -> List[Tuple[str, str]]:
    matrix = PLATFORM_MATRIX[:]
    if only_os:
        allowed_os = {x.strip() for x in only_os.split(",") if x.strip()}
        matrix = [m for m in matrix if m[0] in allowed_os]
    if only_arch:
        allowed_arch = {x.strip() for x in only_arch.split(",") if x.strip()}
        matrix = [m for m in matrix if m[1] in allowed_arch]
    if exclude:
        ex_set = {
            tuple(x.strip().split(":", 1)) for x in exclude.split(",") if ":" in x
        }
        matrix = [m for m in matrix if m not in ex_set]
    return matrix


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)

    # 准备 releases/source_code：基于 .gitignore 复制仓库内容
    log_section("准备源代码副本 releases/source_code")
    prepare_source_copy(REPO_ROOT, SOURCE_COPY_DST_DIR)
    # 补拷 OCR 模型（若有）
    ensure_ocr_in_source_copy(REPO_ROOT, SOURCE_COPY_DST_DIR)
    # 清理构建目录
    shutil.rmtree(RELEASES_DIR / ".build", ignore_errors=True)

    # 读取 token 优先级：scripts/config.toml > CLI 参数 > 环境变量
    token = (
        load_github_token_from_config() or args.token or os.environ.get("GITHUB_TOKEN")
    )
    tag = compute_tag(args.tag, token)
    log_section(f"版本标记: {tag}")

    matrix = filter_matrix(args.only_os, args.only_arch, args.exclude)
    if not matrix:
        warn("没有需要构建的目标")
        return 0

    # 预先获取上游 release 信息（减少重复请求与下载）
    log_section("获取上游依赖 release 信息（用于缓存）")
    selected_maafw_version = args.maafw_version or os.environ.get("MAAFW_VERSION")
    selected_mfaa_version = args.mfaa_version or os.environ.get("MFAA_VERSION")
    if selected_maafw_version:
        info(f"使用指定的 MaaFramework 版本: {selected_maafw_version}")
    else:
        info("未指定 MaaFramework 版本，使用最新版本")
    if selected_mfaa_version:
        info(f"使用指定的 MFAAvalonia 版本: {selected_mfaa_version}")
    else:
        info("未指定 MFAAvalonia 版本，使用最新版本")

    maafw_info: Tuple[str, List[dict]] = get_release_info(
        "MaaXYZ/MaaFramework", token, version=selected_maafw_version
    )
    mfa_avalonia_info: Optional[Tuple[str, List[dict]]] = None
    try:
        mfa_avalonia_info = get_release_info(
            "SweetSmellFox/MFAAvalonia", token, version=selected_mfaa_version
        )
    except Exception as e:
        warn(f"获取 MFAAvalonia release 失败: {e} — 将跳过 MFA 部分")

    artifacts: List[Path] = []
    for os_name, arch in matrix:
        try:
            artifact = build_one(
                os_name,
                arch,
                tag,
                token,
                args.skip_deps,
                args.keep_archives,
                args.keep_staging,
                maafw_info,
                mfa_avalonia_info,
            )
            if artifact:
                artifacts.append(artifact)
        except SystemExit:
            raise
        except Exception as e:
            warn(f"构建 {os_name}-{arch} 失败: {e}")

    if artifacts:
        upstream_meta = {
            "MaaFramework": {"tag": maafw_info[0]},
        }
        if mfa_avalonia_info:
            upstream_meta["MFAAvalonia"] = {"tag": mfa_avalonia_info[0]}
        write_release_metadata(tag, artifacts, upstream=upstream_meta)
        log_section("完成")
        for p in artifacts:
            info(f"生成: {p}")
        info(f"目录: {RELEASES_DIR / tag}")
        return 0
    else:
        warn("没有成功的产物。")
        return 2


if __name__ == "__main__":
    sys.exit(main())
