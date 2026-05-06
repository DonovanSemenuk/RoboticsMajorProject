"""Small YAML helpers for the project configuration files.

The ROS deployment uses YAML files for landmark locations, descriptions, and
sweep waypoints.  The course machines normally provide PyYAML through ROS/apt,
but the pure-Python unit-test environment used for this repository may not have
that package installed.  These helpers intentionally support only the small,
readable YAML subset used by this project:

* a top-level mapping;
* top-level list values such as ``landmarks:`` and ``waypoints:``;
* list items written as ``- key: value`` with optional indented continuation
  keys; and
* inline maps such as ``- { x: 1.0, y: 1.0 }``.

They are not a general-purpose YAML parser.  Keeping the supported subset small
makes the project's tests and command-line tools usable without downloading
extra Python packages, while still producing standard YAML that ROS tools can
read.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List


def _strip_comment(line: str) -> str:
    """Remove comments that are outside quoted strings."""
    quote = None
    escaped = False
    for i, ch in enumerate(line):
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch in ("'", '"'):
            if quote == ch:
                quote = None
            elif quote is None:
                quote = ch
        elif ch == "#" and quote is None:
            return line[:i]
    return line


def _split_key_value(text: str) -> tuple[str, str]:
    if ":" not in text:
        raise ValueError(f"Expected key/value pair, got {text!r}")
    key, value = text.split(":", 1)
    return key.strip(), value.strip()


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value == "":
        return ""
    if value in ("null", "Null", "NULL", "~"):
        return None
    if value in ("true", "True", "TRUE"):
        return True
    if value in ("false", "False", "FALSE"):
        return False
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _parse_inline_map(value: str) -> Dict[str, Any]:
    inner = value.strip()[1:-1].strip()
    if not inner:
        return {}
    result: Dict[str, Any] = {}
    for part in inner.split(","):
        key, raw = _split_key_value(part)
        result[key] = _parse_scalar(raw)
    return result


def _parse_list_item(value: str) -> Dict[str, Any]:
    value = value.strip()
    if value.startswith("{") and value.endswith("}"):
        return _parse_inline_map(value)
    key, raw = _split_key_value(value)
    return {key: _parse_scalar(raw)}


def safe_load(stream) -> Dict[str, Any]:
    """Parse the limited YAML subset used by this project."""
    text = stream.read() if hasattr(stream, "read") else str(stream)
    result: Dict[str, Any] = {}
    current_list: List[Dict[str, Any]] | None = None
    current_item: Dict[str, Any] | None = None

    for lineno, original in enumerate(text.splitlines(), start=1):
        clean = _strip_comment(original).rstrip()
        if not clean.strip():
            continue

        indent = len(clean) - len(clean.lstrip(" "))
        stripped = clean.strip()

        if indent == 0:
            key, raw = _split_key_value(stripped)
            if raw == "":
                current_list = []
                result[key] = current_list
                current_item = None
            else:
                result[key] = _parse_scalar(raw)
                current_list = None
                current_item = None
            continue

        if current_list is None:
            raise ValueError(f"Line {lineno}: indented value without a list header")

        if stripped.startswith("- "):
            current_item = _parse_list_item(stripped[2:])
            current_list.append(current_item)
            continue

        if current_item is None:
            raise ValueError(f"Line {lineno}: list continuation before first item")
        key, raw = _split_key_value(stripped)
        current_item[key] = _parse_scalar(raw)

    return result


def _quote_string(value: str) -> str:
    if value == "" or any(ch in value for ch in ":#{}[],\n") or value != value.strip():
        return '"' + value.replace('"', '\\"') + '"'
    return value


def _format_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return _quote_string(str(value))


def safe_dump(data: Dict[str, Any], stream, sort_keys: bool = False) -> None:
    """Write a simple top-level mapping as YAML."""
    keys: Iterable[str] = sorted(data) if sort_keys else data.keys()
    lines: List[str] = []
    for key in keys:
        value = data[key]
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                if not isinstance(item, dict):
                    lines.append(f"  - {_format_scalar(item)}")
                    continue
                item_keys = list(item.keys())
                if not item_keys:
                    lines.append("  - {}")
                    continue
                first, *rest = item_keys
                lines.append(f"  - {first}: {_format_scalar(item[first])}")
                for subkey in rest:
                    lines.append(f"    {subkey}: {_format_scalar(item[subkey])}")
        else:
            lines.append(f"{key}: {_format_scalar(value)}")
    stream.write("\n".join(lines) + "\n")
