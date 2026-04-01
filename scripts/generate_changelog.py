"""
生成项目 CHANGELOG 的脚本

这个脚本读取 git 提交历史,按照约定式提交格式解析并生成格式化的 changelog。
相比 git-cliff,提供更灵活的控制和自定义逻辑。

关键特性:
- 智能获取真实 GitHub 用户名(支持多层策略)
- 完美处理 squash merge 的子提交展开
- 支持 emoji 格式的约定式提交
- 支持本地昵称映射配置文件

用户名获取策略(优先级从高到低):
1. 本地昵称映射: 从 .vscode/git-nickname-username.json 读取预定义映射
2. GitHub 邮箱格式提取: {id}+{username}@users.noreply.github.com -> username (自动)
3. GitHub API 查询: 使用 GITHUB_TOKEN 查询邮箱对应的用户名 (自动,推荐在 CI/CD 中使用)
4. 昵称回退: 使用原始 git 提交中的昵称 (当无法通过上述方式识别时)

用法:
    python scripts/generate_changelog.py [--output CHANGELOG.md] [--latest]

    # 本地测试示例 (使用昵称映射)
    python scripts/generate_changelog.py --latest

    # CI/CD 示例 (使用 token 查询所有用户名)
    GITHUB_TOKEN=${{ secrets.GITHUB_TOKEN }} python scripts/generate_changelog.py -o CHANGELOG.md

    # 指定昵称映射文件
    python scripts/generate_changelog.py --nickname-map .vscode/git-nickname-username.json
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

# ============================================================================
# 常量定义
# ============================================================================

# 默认昵称映射文件路径（相对于仓库根目录）
DEFAULT_NICKNAME_MAP_PATH = ".vscode/git-nickname-username.json"
DEFAULT_PR_AUTHOR_CACHE_PATH = ".vscode/changelog-pr-authors.json"

# 约定式提交正则: type[emoji](scope): message
CONVENTIONAL_COMMIT_PATTERN = re.compile(
    r"^(?P<type>\w+)(?P<emoji>[^\w\s:(]*)?(?:\((?P<scope>[^)]+)\))?\s*:\s*(?P<message>.+)$"
)

# GitHub noreply 邮箱正则: {id}+{username}@users.noreply.github.com
GITHUB_NOREPLY_EMAIL_PATTERN = re.compile(
    r"^(\d+)\+([^@]+)@users\.noreply\.github\.com$"
)
PR_NUMBER_PATTERN = re.compile(r"\(#(?P<number>\d+)\)$")
GITHUB_REPO_REMOTE_PATTERN = re.compile(
    r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+?)(?:\.git)?$",
    re.IGNORECASE,
)

# Git log 中需要过滤的干扰文本模式
NOISE_PATTERNS = frozenset(
    [
        "Bumps [",
        "Release notes",
        "Commits]",
        "updated-dependencies:",
        "dependency-name:",
        "dependency-version:",
        "dependency-type:",
        "update-type:",
        "Signed-off-by:",
    ]
)

# Footer 关键字
FOOTER_KEYWORDS = frozenset(["Co-authored-by", "Signed-off-by"])

# 提交类型到分组的映射
TYPE_GROUPS: dict[str, tuple[str, int]] = {
    "feat": ("✨ 新功能", 0),
    "fix": ("🐛 Bug修复", 1),
    "patch": ("🐛 Bug修复", 1),
    "perf": ("🚀 性能优化", 2),
    "refactor": ("🎨 代码重构", 3),
    "format": ("🥚 格式化", 4),
    "style": ("💄 样式", 5),
    "docs": ("📚 文档", 6),
    "chore": ("🧹 日常维护", 7),
    "git": ("🧹 日常维护", 7),
    "deps": ("🧩 修改依赖", 8),
    "build": ("🧩 修改依赖", 8),
    "revert": ("🔁 还原提交", 10),
    "test": ("🧪 测试", 11),
    "file": ("📦 文件变更", 12),
    "tag": ("📌 发布", 13),
    "config": ("🔧 配置文件", 14),
    "ci": ("⚙️ 持续集成", 15),
    "init": ("🎉 初始化", 16),
    "wip": ("🚧 进行中", 17),
}

DEFAULT_GROUP = ("其他变更", 99)
COMMIT_SEPARATOR = "---COMMIT-SEPARATOR---"
GIT_LOG_FORMAT = "%H|%an|%ae|%ai|%B"
GITHUB_API_REQUEST_INTERVAL_SECONDS = 0.3


# ============================================================================
# 数据模型
# ============================================================================


@dataclass
class Commit:
    """提交信息数据类"""

    hash: str
    message: str
    author: str
    email: str
    date: datetime
    type: str = ""
    scope: str = ""
    breaking: bool = False
    footers: dict[str, str] = field(default_factory=dict)
    original_message: str = ""
    github_username: str | None = None

    def __post_init__(self) -> None:
        """初始化后处理：保存原始消息并解析提交格式"""
        if not self.original_message:
            self.original_message = self.message
        self._parse_message()

    def _parse_message(self) -> None:
        """解析约定式提交消息"""
        lines = self.message.strip().split("\n")
        if not lines:
            return

        first_line = re.sub(r"^[-*]\s*", "", lines[0].strip())
        match = CONVENTIONAL_COMMIT_PATTERN.match(first_line)

        if match:
            self.type = match.group("type").lower()
            self.scope = match.group("scope") or ""
            self.message = match.group("message").strip()
        else:
            self._parse_non_conventional_message(first_line)

        self._parse_footers(lines[1:])

    def _parse_non_conventional_message(self, first_line: str) -> None:
        """解析非标准格式的提交消息"""
        if first_line.lower().startswith("revert"):
            self.type = "revert"
            self.message = first_line
            return

        # 尝试匹配带 emoji 的格式: type[emoji]: message
        emoji_match = re.match(r"^(\w+)([^:]*?):\s*(.+)$", first_line)
        if emoji_match:
            self.type = emoji_match.group(1).lower()
            self.message = emoji_match.group(3).strip()
        else:
            self.type = "chore"
            self.message = first_line

    def _parse_footers(self, lines: list[str]) -> None:
        """解析提交消息的 footer 部分"""
        for line in lines:
            line = line.strip()
            if ": " in line:
                key, value = line.split(": ", 1)
                if key in FOOTER_KEYWORDS:
                    self.footers[key] = value

    def get_display_message(self) -> str:
        """获取用于显示的消息（仅第一行）"""
        return self.message.split("\n")[0].strip()


# ============================================================================
# GitHub 用户名查询
# ============================================================================


class GitHubUserCache:
    """GitHub 用户名缓存与查询服务

    获取策略优先级:
    1. 本地昵称映射文件
    2. 从 GitHub noreply 邮箱格式提取
    3. 通过 GitHub API 查询
    4. 返回 None（由调用方决定回退策略）
    """

    GITHUB_API_HEADERS = {
        "Accept": "application/vnd.github.v3+json",
    }
    API_TIMEOUT = 5

    def __init__(
        self,
        email_to_names: dict[str, set[str]] | None = None,
        nickname_map: dict[str, str] | None = None,
    ) -> None:
        self.cache: dict[str, str | None] = {}
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.email_to_names = email_to_names or {}
        self.nickname_map = nickname_map or {}

    def get_github_username(self, author_name: str, author_email: str) -> str | None:
        """获取用户的真实 GitHub 用户名"""
        if not author_name:
            return None

        cache_key = f"{author_name}|{author_email}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        username = self._resolve_username(author_name, author_email)
        self.cache[cache_key] = username
        return username

    def _resolve_username(self, author_name: str, email: str) -> str | None:
        """按优先级解析用户名"""
        # 策略 1: 本地昵称映射
        if author_name in self.nickname_map:
            return self.nickname_map[author_name]

        # 策略 2: 从 noreply 邮箱提取
        if email:
            username = self._extract_from_noreply_email(email)
            if username:
                return username

        # 策略 3: API 查询
        if self.github_token and email:
            return self._fetch_via_api(email)

        return None

    def _extract_from_noreply_email(self, email: str) -> str | None:
        """从 GitHub noreply 邮箱提取用户名"""
        match = GITHUB_NOREPLY_EMAIL_PATTERN.match(email)
        return match.group(2) if match else None

    def _fetch_via_api(self, email: str) -> str | None:
        """通过 GitHub API 查询用户名"""
        # 优先用邮箱搜索
        username = self._api_search_by_email(email)
        if username:
            return username

        # 回退：尝试用关联的 git 用户名验证
        email_lower = email.lower()
        for name in self.email_to_names.get(email_lower, []):
            username = self._api_verify_username(name)
            if username:
                return username

        return None

    def _github_api_request(self, url: str) -> dict[str, Any] | None:
        """统一的 GitHub API 请求方法"""
        headers = {**self.GITHUB_API_HEADERS}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"

        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=self.API_TIMEOUT) as response:
                return json.loads(response.read().decode())
        except (URLError, json.JSONDecodeError, TimeoutError):
            return None

    def _api_search_by_email(self, email: str) -> str | None:
        """通过邮箱搜索 GitHub 用户"""
        data = self._github_api_request(
            f"https://api.github.com/search/users?q={email}+in:email"
        )
        if data:
            items = data.get("items", [])
            if items:
                return items[0].get("login")
        return None

    def _api_verify_username(self, username: str) -> str | None:
        """验证用户名是否存在并返回规范化名称"""
        data = self._github_api_request(f"https://api.github.com/users/{username}")
        return data.get("login") if data else None


# ============================================================================
# Changelog 生成器
# ============================================================================


class ChangelogGenerator:
    """Changelog 生成器

    从 Git 仓库读取提交历史，解析约定式提交格式，生成格式化的 changelog。
    """

    def __init__(
        self,
        repo_path: Path | None = None,
        nickname_map_path: Path | None = None,
        pr_author_cache_path: Path | None = None,
    ) -> None:
        self.repo_path = repo_path or Path.cwd()
        self.email_to_names = self._build_email_to_names_map()
        self.nickname_map = self._load_nickname_map(nickname_map_path)
        self.user_cache = GitHubUserCache(self.email_to_names, self.nickname_map)
        self.github_repo = self._detect_github_repo()
        self.pr_author_cache_path = (
            pr_author_cache_path
            if pr_author_cache_path is not None
            else self.repo_path / DEFAULT_PR_AUTHOR_CACHE_PATH
        )
        self.pr_commit_cache = self._load_pr_commit_cache()
        self.commit_pr_cache: dict[str, int | None] = {}
        self._last_github_api_request_at = 0.0

    def _load_nickname_map(self, nickname_map_path: Path | None) -> dict[str, str]:
        """加载昵称到用户名的映射文件"""
        if nickname_map_path is None:
            # 使用默认路径
            nickname_map_path = self.repo_path / DEFAULT_NICKNAME_MAP_PATH

        if not nickname_map_path.exists():
            return {}

        try:
            with open(nickname_map_path, encoding="utf-8") as f:
                data = json.load(f)
                # 过滤掉 $schema 等元数据字段
                return {
                    k: v for k, v in data.items()
                    if not k.startswith("$") and isinstance(v, str)
                }
        except (json.JSONDecodeError, OSError) as e:
            print(f"⚠️ 加载昵称映射文件失败: {e}", file=sys.stderr)
            return {}

    def _load_pr_commit_cache(self) -> dict[int, dict[str, list[dict[str, str | None]]]]:
        """加载 PR 作者缓存"""
        cache_path = self.pr_author_cache_path
        if not cache_path.exists():
            return {}

        try:
            with open(cache_path, encoding="utf-8") as f:
                raw_data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"⚠️ 加载 PR 作者缓存失败: {e}", file=sys.stderr)
            # JSON 无法解析或文件读写错误时，删除损坏的缓存文件，避免后续运行反复失败
            try:
                if cache_path.exists():
                    cache_path.unlink()
            except OSError as cleanup_error:
                print(f"⚠️ 删除损坏的 PR 作者缓存文件失败: {cleanup_error}", file=sys.stderr)
            return {}

        if not isinstance(raw_data, dict):
            # 结构异常时重置为一个空的缓存结构，避免后续一直读取无效数据
            try:
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
            except OSError as e:
                print(f"⚠️ 重置 PR 作者缓存文件失败: {e}", file=sys.stderr)
            return {}

        cache: dict[int, dict[str, list[dict[str, str | None]]]] = {}
        for pr_number_str, subjects in raw_data.items():
            if not isinstance(pr_number_str, str) or not pr_number_str.isdigit():
                continue
            if not isinstance(subjects, dict):
                continue

            normalized_subjects: dict[str, list[dict[str, str | None]]] = {}
            for subject, authors in subjects.items():
                if not isinstance(subject, str) or not isinstance(authors, list):
                    continue

                normalized_authors: list[dict[str, str | None]] = []
                for author in authors:
                    if not isinstance(author, dict):
                        continue
                    normalized_authors.append(
                        {
                            "author": author.get("author") or "",
                            "email": author.get("email") or "",
                            "github_username": author.get("github_username"),
                        }
                    )

                normalized_subjects[subject] = normalized_authors

            cache[int(pr_number_str)] = normalized_subjects

        return cache

    def _save_pr_commit_cache(self) -> None:
        """保存 PR 作者缓存到本地 JSON"""
        cache_path = self.pr_author_cache_path

        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            serializable_cache = {
                str(pr_number): subjects
                for pr_number, subjects in sorted(self.pr_commit_cache.items())
            }
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(serializable_cache, f, ensure_ascii=False, indent=2)
        except OSError as e:
            print(f"⚠️ 保存 PR 作者缓存失败: {e}", file=sys.stderr)

    @staticmethod
    def _clone_pr_commit_authors(
        authors_by_subject: dict[str, list[dict[str, str | None]]],
    ) -> dict[str, list[dict[str, str | None]]]:
        """复制 PR 作者数据，避免匹配阶段修改原缓存"""
        return {
            subject: [dict(author) for author in authors]
            for subject, authors in authors_by_subject.items()
        }

    def _run_git(self, *args) -> str:
        """运行 git 命令"""
        result = subprocess.run(
            ["git", "-C", str(self.repo_path), *args],
            capture_output=True,
            text=False,
            check=True,
        )
        return result.stdout.decode("utf-8")

    def _detect_github_repo(self) -> tuple[str, str] | None:
        """从 origin remote 中识别 GitHub 仓库"""
        try:
            remote_url = self._run_git("remote", "get-url", "origin").strip()
        except subprocess.CalledProcessError:
            return None

        match = GITHUB_REPO_REMOTE_PATTERN.search(remote_url)
        if not match:
            return None

        return match.group("owner"), match.group("repo")

    def _build_email_to_names_map(self) -> dict[str, set[str]]:
        """构建邮箱到用户名的映射 (同一邮箱可能有多个用户名)
        
        这用于当 API 搜索邮箱找不到结果时,
        尝试用关联的其他用户名去搜 API
        """
        mapping = defaultdict(set)
        try:
            output = self._run_git("log", "--all", "--format=%ae|%an")
            for line in output.strip().split("\n"):
                if not line or "|" not in line:
                    continue
                email, name = line.split("|", 1)
                mapping[email.lower()].add(name)
        except subprocess.CalledProcessError:
            pass
        return dict(mapping)

    def _get_tags(self) -> list[tuple[str, str]]:
        """获取所有 tag 及其对应的提交 hash（按版本号降序）"""
        output = self._run_git(
            "tag", "-l", "--sort=-version:refname",
            "--format=%(refname:short) %(objectname)"
        )
        return [
            (parts[0], parts[1])
            for line in output.strip().split("\n")
            if line and len(parts := line.split()) == 2
        ]

    def _parse_commit(self, commit_line: str) -> Commit | None:
        """解析 git log 输出的单个提交"""
        parts = commit_line.split("|", 4)
        if len(parts) < 5:
            return None

        hash_val, author, email, date_str, message_full = parts

        # 过滤 merge commit
        first_line = message_full.strip().split("\n")[0]
        if first_line.startswith("Merge pull request"):
            return None

        date = self._parse_date(date_str)
        clean_message, footers = self._extract_footers(message_full)

        return Commit(
            hash=hash_val,
            message=clean_message,
            author=author,
            email=email,
            date=date,
            footers=footers,
        )

    def _github_api_request(self, url: str) -> Any | None:
        """统一的 GitHub API 请求"""
        elapsed = time.monotonic() - self._last_github_api_request_at
        if elapsed < GITHUB_API_REQUEST_INTERVAL_SECONDS:
            time.sleep(GITHUB_API_REQUEST_INTERVAL_SECONDS - elapsed)

        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
        }
        github_token = os.getenv("GITHUB_TOKEN")
        if github_token:
            headers["Authorization"] = f"Bearer {github_token}"

        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=5) as response:
                self._last_github_api_request_at = time.monotonic()
                return json.loads(response.read().decode())
        except (URLError, json.JSONDecodeError, TimeoutError):
            self._last_github_api_request_at = time.monotonic()
            return None

    @staticmethod
    def _normalize_commit_subject(subject: str) -> str:
        """标准化提交标题，便于匹配 squash 子提交与 PR 原始提交"""
        first_line = subject.strip().split("\n")[0]
        first_line = re.sub(r"^[-*]\s*", "", first_line).strip()
        return re.sub(r"\s+", "", first_line).lower()

    @staticmethod
    def _extract_pr_number(message: str) -> int | None:
        """从提交标题末尾的 (#123) 提取 PR 编号"""
        first_line = message.strip().split("\n")[0]
        match = PR_NUMBER_PATTERN.search(first_line)
        return int(match.group("number")) if match else None

    def _find_pr_number_by_commit(self, commit_hash: str) -> int | None:
        """通过 merge 后的 commit 反查关联 PR 编号"""
        if commit_hash in self.commit_pr_cache:
            return self.commit_pr_cache[commit_hash]

        if not self.github_repo:
            self.commit_pr_cache[commit_hash] = None
            return None

        owner, repo = self.github_repo
        data = self._github_api_request(
            f"https://api.github.com/repos/{owner}/{repo}/commits/{commit_hash}/pulls"
        )
        pr_number = None
        if isinstance(data, list) and data:
            pr_number = data[0].get("number")

        self.commit_pr_cache[commit_hash] = pr_number
        return pr_number

    def _fetch_pr_commit_authors(
        self, pr_number: int
    ) -> dict[str, list[dict[str, str | None]]]:
        """获取 PR 中每个提交标题对应的作者信息"""
        if pr_number in self.pr_commit_cache:
            return self._clone_pr_commit_authors(self.pr_commit_cache[pr_number])

        if not self.github_repo:
            return {}

        owner, repo = self.github_repo
        page = 1
        authors_by_subject: dict[str, list[dict[str, str | None]]] = defaultdict(list)

        while True:
            data = self._github_api_request(
                "https://api.github.com/repos/"
                f"{owner}/{repo}/pulls/{pr_number}/commits?per_page=100&page={page}"
            )
            if not isinstance(data, list):
                return {}
            if not data:
                break

            for item in data:
                commit_info = item.get("commit") or {}
                author_info = commit_info.get("author") or {}
                subject = (commit_info.get("message") or "").split("\n", 1)[0].strip()
                normalized = self._normalize_commit_subject(subject)
                if not normalized:
                    continue

                github_author = item.get("author") or {}
                authors_by_subject[normalized].append(
                    {
                        "author": author_info.get("name") or "",
                        "email": author_info.get("email") or "",
                        "github_username": github_author.get("login"),
                    }
                )

            if len(data) < 100:
                break
            page += 1

        cached = dict(authors_by_subject)
        self.pr_commit_cache[pr_number] = cached
        self._save_pr_commit_cache()
        return self._clone_pr_commit_authors(cached)

    def _parse_date(self, date_str: str) -> datetime:
        """解析日期字符串"""
        try:
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %z")
        except ValueError:
            return datetime.now()

    def _extract_footers(self, message: str) -> tuple[str, dict[str, str]]:
        """从消息中提取 footer 并返回清理后的消息"""
        footers: dict[str, str] = {}
        clean_lines: list[str] = []

        for line in message.strip().split("\n"):
            stripped = line.strip()
            if stripped.startswith("Co-authored-by:") and ": " in stripped:
                key, value = stripped.split(": ", 1)
                footers[key] = value
            else:
                clean_lines.append(line)

        return "\n".join(clean_lines).strip(), footers

    def _filter_squash_commits(self, commits: list[Commit]) -> list[Commit]:
        """
        过滤和展开 squash merge 产生的提交
        
        策略:
        1. 检测 squash merge 提交(消息体中包含以 * 开头的子提交行)
        2. 将子提交行拆分为独立提交对象
        3. 保留原主提交的第一行
        4. 去重处理
        """
        result = []
        seen_messages = set()

        for commit in commits:
            # 使用原始完整消息来检测 squash 项
            lines = commit.original_message.strip().split("\n")
            first_line = lines[0].strip() if lines else ""

            # 检查是否是 squash merge: 消息体中有以 * 开头的子提交
            # 子提交格式: * type[emoji]: message (可能有空行)
            squash_items = []
            for line in lines[1:]:
                line_stripped = line.strip()
                if line_stripped.startswith("*") and ":" in line_stripped:
                    # 移除前导 * 和空白
                    squash_line = line_stripped.lstrip("* ").strip()
                    squash_items.append(squash_line)

            if squash_items:
                pr_number = self._extract_pr_number(first_line)
                if pr_number is None:
                    pr_number = self._find_pr_number_by_commit(commit.hash)
                pr_commit_authors = (
                    self._fetch_pr_commit_authors(pr_number) if pr_number else {}
                )

                # 这是一个 squash merge,将其展开
                
                # 1. 添加主提交的第一行(但要去重,如果内容太相似则跳过)
                if first_line and first_line not in seen_messages:
                    seen_messages.add(first_line)
                    result.append(commit)

                # 2. 处理子提交
                for squash_line in squash_items:
                    # 如果已经出现过,跳过(去重)
                    if squash_line in seen_messages:
                        continue

                    seen_messages.add(squash_line)
                    normalized = self._normalize_commit_subject(squash_line)
                    matched_author = None
                    if normalized in pr_commit_authors and pr_commit_authors[normalized]:
                        matched_author = pr_commit_authors[normalized].pop(0)

                    # 创建虚拟的子提交对象
                    sub_commit = Commit(
                        hash=commit.hash,  # 使用父提交的hash
                        message=squash_line,
                        author=(matched_author or {}).get("author") or commit.author,
                        email=(matched_author or {}).get("email") or commit.email,
                        date=commit.date,
                        footers={},
                        original_message=squash_line,
                        github_username=(matched_author or {}).get("github_username"),
                    )
                    result.append(sub_commit)
            else:
                # 不是 squash merge,直接添加(如果未出现过)
                if first_line and first_line not in seen_messages:
                    seen_messages.add(first_line)
                    result.append(commit)

        return result

    def _group_commits(self, commits: list[Commit]) -> dict[str, list[Commit]]:
        """按提交类型分组并按优先级排序"""
        groups: dict[str, list[Commit]] = defaultdict(list)

        for commit in commits:
            group_name, _ = TYPE_GROUPS.get(commit.type, DEFAULT_GROUP)
            groups[group_name].append(commit)

        # 构建分组名到优先级的映射
        group_order = {v[0]: v[1] for v in TYPE_GROUPS.values()}
        return dict(
            sorted(groups.items(), key=lambda x: group_order.get(x[0], 99))
        )

    def get_commits_for_version(
        self, tag: str | None = None, previous_tag: str | None = None
    ) -> list[Commit]:
        """获取指定版本的提交"""
        # 构建 git log 范围
        if previous_tag and tag:
            range_spec = f"{previous_tag}..{tag}"
        elif previous_tag:
            range_spec = f"{previous_tag}..HEAD"
        elif tag:
            range_spec = tag
        else:
            range_spec = "HEAD"

        try:
            output = self._run_git(
                "log", range_spec,
                f"--format={GIT_LOG_FORMAT}{COMMIT_SEPARATOR}",
                "--no-merges",
            )
        except subprocess.CalledProcessError:
            return []

        commits = [
            commit
            for block in output.split(COMMIT_SEPARATOR)
            if block.strip()
            and (commit := self._parse_commit(self._clean_commit_block(block)))
        ]

        return self._filter_squash_commits(commits)

    def _clean_commit_block(self, block: str) -> str:
        """清理提交消息块，移除干扰行"""
        lines = block.strip().split("\n")
        cleaned: list[str] = []

        for i, line in enumerate(lines):
            # 前 4 行是 hash|author|email|date（消息从第 5 行开始）
            if i < 4:
                cleaned.append(line)
                continue

            stripped = line.strip()

            # 保留 squash merge 子提交（以 * 开头）
            if stripped.startswith("* "):
                cleaned.append(line)
                continue

            # 跳过分隔线
            if re.match(r"^-+$", stripped):
                continue

            # 跳过干扰文本
            if self._is_noise_line(stripped):
                continue

            cleaned.append(line)

        return "\n".join(cleaned)

    @staticmethod
    def _is_noise_line(line: str) -> bool:
        """判断是否是需要过滤的干扰行"""
        return any(pattern in line for pattern in NOISE_PATTERNS)

    def generate_version_section(
        self,
        version: str,
        date: datetime | None = None,
        commits: list[Commit] | None = None,
    ) -> str:
        """生成单个版本的 changelog 内容"""
        lines = [self._format_version_header(version, date)]

        if not commits:
            return "\n".join(lines)

        for group_name, group_commits in self._group_commits(commits).items():
            lines.append(f"### {group_name}\n")
            lines.extend(self._format_commit_group(group_commits))
            lines.append("")  # 组间空行

        return "\n".join(lines)

    def _format_version_header(self, version: str, date: datetime | None) -> str:
        """格式化版本标题"""
        if version == "unreleased":
            return "## 未发布\n"

        date_str = date.strftime("%Y-%m-%d") if date else ""
        version_clean = (
            version.replace("tags/", "").replace("refs/tags/", "").lstrip("v")
        )
        return f"## {version_clean} ({date_str})\n"

    def _format_commit_group(self, commits: list[Commit]) -> list[str]:
        """格式化一组提交为 changelog 条目"""
        lines: list[str] = []

        # 先显示有 scope 的提交（按 scope 排序）
        scoped = sorted((c for c in commits if c.scope), key=lambda x: x.scope)
        for commit in scoped:
            lines.append(self._format_commit_line(commit, with_scope=True))

        # 再显示无 scope 的提交
        for commit in commits:
            if not commit.scope:
                lines.append(self._format_commit_line(commit, with_scope=False))

        return lines

    def _format_commit_line(self, commit: Commit, with_scope: bool) -> str:
        """格式化单个提交条目"""
        msg = commit.get_display_message()
        author = self._get_author_mention(commit)
        if with_scope:
            return f"- *({commit.scope})* {msg} {author}"
        return f"- {msg} {author}"

    def _get_author_mention(self, commit: Commit) -> str:
        """获取 GitHub @提及格式

        策略:
        1. 如果能获取真实 GitHub username，使用 @username（会被渲染为链接）
        2. 如果无法获取，只使用昵称（不加 @，避免链接到错误用户）
        3. 如果有 Co-authored-by，添加到括号中
        """
        github_username = commit.github_username or self.user_cache.get_github_username(
            commit.author, commit.email
        )

        # 只有确认是真实 GitHub 用户名时才使用 @ 前缀
        if github_username:
            mention = f"@{github_username}"
        else:
            # 无法确认时使用昵称，不加 @ 避免错误链接
            mention = commit.author

        if "Co-authored-by" in commit.footers:
            co_author = commit.footers["Co-authored-by"].split("<")[0].strip()
            return f"{mention} (Co-authored: {co_author})"

        return mention

    def generate_full_changelog(self, output_path: Path | None = None) -> str:
        """生成完整的 changelog"""
        lines = ["# 更新日志\n"]

        # 获取所有 tag
        tags = self._get_tags()

        # 添加未发布的提交
        if tags:
            latest_tag = tags[0][0]
            unreleased = self.get_commits_for_version(previous_tag=latest_tag)
            if unreleased:
                lines.append(self.generate_version_section("unreleased", commits=unreleased))

        # 为每个 tag 生成版本记录
        for i, (tag, tag_hash) in enumerate(tags):
            previous_tag = tags[i + 1][0] if i + 1 < len(tags) else None

            # 获取该版本的提交
            commits = self.get_commits_for_version(tag, previous_tag)

            # 获取 tag 的日期
            try:
                date_str = self._run_git(
                    "log", "-1", "--format=%ai", tag_hash
                ).strip()
                date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %z")
            except (subprocess.CalledProcessError, ValueError):
                date = None

            section = self.generate_version_section(tag, date, commits)
            lines.append(section)

        changelog = "\n".join(lines)

        if output_path:
            output_path.write_text(changelog, encoding="utf-8")
            print(f"✅ Changelog 已生成: {output_path}")

        return changelog

    def generate_latest_version(self) -> str:
        """生成最新版本的 changelog"""
        tags = self._get_tags()
        if not tags:
            return "## 未发布\n\n(暂无发布版本)\n"

        latest_tag, tag_hash = tags[0]
        previous_tag = tags[1][0] if len(tags) > 1 else None

        commits = self.get_commits_for_version(latest_tag, previous_tag)

        try:
            date_str = self._run_git("log", "-1", "--format=%ai", tag_hash).strip()
            date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %z")
        except (subprocess.CalledProcessError, ValueError):
            date = None

        return self.generate_version_section(latest_tag, date, commits)


def _find_markdownlint() -> str | None:
    """查找可用的 markdownlint 命令"""
    # 优先查找 markdownlint-cli2（更现代）
    for cmd in ["markdownlint-cli2", "markdownlint"]:
        if shutil.which(cmd):
            return cmd
    return None


def _run_markdownlint(file_path: Path, fix: bool = True) -> bool:
    """运行 markdownlint 格式化文件

    Args:
        file_path: 要格式化的文件路径
        fix: 是否自动修复

    Returns:
        是否成功执行
    """
    cmd = _find_markdownlint()
    if not cmd:
        return False

    try:
        args = [cmd]
        if fix:
            args.append("--fix")
        args.append(str(file_path))

        subprocess.run(args, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        # markdownlint 返回非零表示有问题，但 --fix 模式下已尝试修复
        return True
    except FileNotFoundError:
        return False


def _configure_stdio() -> None:
    """尽量避免 Windows 控制台输出 emoji 时发生编码错误"""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace") # type: ignore
            except (ValueError, OSError):
                pass


def main() -> None:
    """主函数"""
    import argparse

    _configure_stdio()

    parser = argparse.ArgumentParser(description="生成 CHANGELOG")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("CHANGELOG.md"),
        help="输出文件路径",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="只生成最新版本",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        help="Git 仓库路径(默认为当前目录)",
    )
    parser.add_argument(
        "--nickname-map",
        type=Path,
        help=f"昵称映射文件路径(默认为 {DEFAULT_NICKNAME_MAP_PATH})",
    )
    parser.add_argument(
        "--pr-author-cache",
        type=Path,
        help=f"PR 作者缓存文件路径(默认为 {DEFAULT_PR_AUTHOR_CACHE_PATH})",
    )
    parser.add_argument(
        "--no-format",
        action="store_true",
        help="禁用 markdownlint 格式化",
    )

    args = parser.parse_args()

    generator = ChangelogGenerator(
        args.repo,
        args.nickname_map,
        args.pr_author_cache,
    )

    try:
        if args.latest:
            content = generator.generate_latest_version()
            print(content)
        else:
            generator.generate_full_changelog(args.output)

            # 尝试使用 markdownlint 格式化
            if not args.no_format:
                lint_cmd = _find_markdownlint()
                if lint_cmd:
                    if _run_markdownlint(args.output, fix=True):
                        print(f"✅ 已使用 {lint_cmd} 格式化")
                else:
                    print(
                        "⚠️ 未找到 markdownlint，建议安装以自动格式化:\n"
                        "   npm install -g markdownlint-cli2\n"
                        "   或手动格式化 CHANGELOG.md",
                        file=sys.stderr,
                    )

    except subprocess.CalledProcessError as e:
        print(f"❌ Git 命令执行失败: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ 生成失败: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
