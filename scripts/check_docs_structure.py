from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = {
    ROOT / "docs/用户文档/用户手册入口.md": ["# 用户手册入口", "## 我应该先看哪一篇"],
    ROOT / "docs/开发者文档/QuickStart.md": [
        "# QuickStart",
        "## Github Pull Request 流程简述",
    ],
    ROOT / "docs/开发者文档/个性化配置.md": ["# 个性化配置", "## 代码格式化工具"],
    ROOT / "docs/开发者文档/开发者文档入口.md": [
        "# 开发者文档入口",
        "## 我应该先看哪一篇",
    ],
    ROOT / "docs/开发者文档/文档编写规范.md": ["# 文档编写规范", "## 模板一：入口页"],
    ROOT / "docs/开发者文档/文档维护流程.md": [
        "# 文档维护流程",
        "## 修改文档时的最小检查清单",
    ],
}


def main() -> int:
    errors: list[str] = []

    for path, required_strings in REQUIRED_FILES.items():
        if not path.exists():
            errors.append(f"missing file: {path.relative_to(ROOT)}")
            continue

        text = path.read_text(encoding="utf-8")
        for required in required_strings:
            if required not in text:
                errors.append(
                    f"missing section '{required}' in {path.relative_to(ROOT)}"
                )

    if errors:
        print("docs structure check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("docs structure check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
