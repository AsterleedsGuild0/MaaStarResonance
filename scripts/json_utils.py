"""桌面与 Android 打包共用的 JSON 行注释处理。"""

from pathlib import Path


def remove_line_comments(json_text: str) -> str:
    """删除 // 行注释，保留字符串内的 URL、转义字符和换行。"""
    result: list[str] = []
    i = 0
    n = len(json_text)
    in_string = False
    escape = False
    while i < n:
        ch = json_text[i]
        if in_string:
            result.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            result.append(ch)
            i += 1
            continue
        if ch == "/" and i + 1 < n and json_text[i + 1] == "/":
            i += 2
            while i < n and json_text[i] not in ("\n", "\r"):
                i += 1
            if i < n:
                result.append(json_text[i])
                i += 1
            continue
        result.append(ch)
        i += 1
    return "".join(result)


def strip_interface_json_comments(path: Path) -> None:
    """原地移除成品 interface.json 的行注释。"""
    raw = path.read_text(encoding="utf-8-sig")
    path.write_text(remove_line_comments(raw), encoding="utf-8")
