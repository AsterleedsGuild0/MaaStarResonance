from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = {
    ROOT / "docs/新手指南/新手指南入口.md": ["# 新手指南入口", "## 按流程阅读"],
    ROOT / "docs/功能文档/功能文档入口.md": ["# 功能文档入口", "## 功能索引"],
    ROOT / "docs/开发者文档/QuickStart.md": [
        "# QuickStart",
        "## Github Pull Request 流程简述",
    ],
    ROOT / "docs/开发者文档/开发者文档入口.md": [
        "# 开发者文档入口",
        "## 我应该先看哪一篇",
    ],
    ROOT / "docs/关于/关于我们.md": ["# 星痕共鸣 MAA 小助手", "## 声明与许可"],
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
