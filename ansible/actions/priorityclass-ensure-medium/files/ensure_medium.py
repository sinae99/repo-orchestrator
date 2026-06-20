#!/usr/bin/env python3
"""Add priorityClassName to Kubernetes pod templates that omit it."""

from __future__ import annotations

import argparse
import sys
from typing import Any


def _load_yaml():
    try:
        import yaml  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            "PyYAML is required. Install with: apt install python3-yaml "
            "or pip install pyyaml"
        ) from exc
    return yaml


def load_documents(path: str, yaml_mod):
    with open(path, encoding="utf-8") as handle:
        content = handle.read()
    docs = list(yaml_mod.safe_load_all(content))
    return content, docs


def pod_specs(obj: Any, specs: list[dict] | None = None) -> list[dict]:
    if specs is None:
        specs = []
    if isinstance(obj, dict):
        containers = obj.get("containers")
        if isinstance(containers, list):
            specs.append(obj)
        for value in obj.values():
            pod_specs(value, specs)
    elif isinstance(obj, list):
        for item in obj:
            pod_specs(item, specs)
    return specs


def specs_missing_priority_class(docs: list[Any]) -> int:
    count = 0
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        for spec in pod_specs(doc):
            raw = spec.get("priorityClassName")
            if raw is None or raw == "":
                count += 1
    return count


def _line_indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _strip_key(line: str) -> str | None:
    stripped = line.lstrip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("- "):
        body = stripped[2:]
        if ":" in body:
            return body.split(":", 1)[0].strip()
        return None
    if ":" in stripped:
        return stripped.split(":", 1)[0].strip()
    return None


def _block_range(lines: list[str], idx: int, spec_indent: int) -> tuple[int, int]:
    parent_indent = max(spec_indent - 2, 0)
    start = idx
    while start > 0:
        if _line_indent(lines[start - 1]) < spec_indent:
            break
        start -= 1
    end = idx + 1
    while end < len(lines):
        stripped = lines[end].strip()
        if not stripped:
            end += 1
            continue
        if _line_indent(lines[end]) <= parent_indent:
            break
        end += 1
    return start, end


def _block_has_key(
    lines: list[str],
    start: int,
    end: int,
    spec_indent: int,
    key: str,
) -> bool:
    for line in lines[start:end]:
        if _line_indent(line) != spec_indent:
            continue
        if _strip_key(line) == key:
            return True
    return False


def _first_container_section_line(
    lines: list[str],
    start: int,
    end: int,
    spec_indent: int,
) -> int | None:
    for idx in range(start, end):
        key = _strip_key(lines[idx])
        if key in ("initContainers", "containers") and ":" in lines[idx].lstrip():
            if _line_indent(lines[idx]) == spec_indent:
                return idx
    return None


def add_priority_class_lines(content: str, class_name: str = "medium") -> str:
    lines = content.splitlines(keepends=True)
    insertions: list[int] = []
    seen_blocks: set[tuple[int, int]] = set()

    for idx, line in enumerate(lines):
        key = _strip_key(line)
        if key not in ("containers", "initContainers") or ":" not in line.lstrip():
            continue

        spec_indent = _line_indent(line)
        start, end = _block_range(lines, idx, spec_indent)
        block_key = (start, end)
        if block_key in seen_blocks:
            continue
        seen_blocks.add(block_key)

        if _block_has_key(lines, start, end, spec_indent, "priorityClassName"):
            continue

        first_line = _first_container_section_line(lines, start, end, spec_indent)
        if first_line is None:
            continue
        insertions.append(first_line)

    for idx in sorted(insertions, reverse=True):
        indent = " " * _line_indent(lines[idx])
        lines.insert(idx, f"{indent}priorityClassName: {class_name}\n")

    return "".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Add priorityClassName to pod templates that omit it."
    )
    parser.add_argument("path", help="Kubernetes manifest path")
    parser.add_argument(
        "--priority-class",
        default="medium",
        help="priorityClassName value to add (default: medium)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Do not write; exit 3 when a modification would be made",
    )
    args = parser.parse_args()

    priority_class = args.priority_class.strip()
    if not priority_class:
        print("ERROR: priority class must not be empty", file=sys.stderr)
        return 2

    yaml_mod = _load_yaml()
    original, docs = load_documents(args.path, yaml_mod)
    if specs_missing_priority_class(docs) == 0:
        return 0

    if args.check:
        return 3

    new_content = add_priority_class_lines(original, priority_class)
    if new_content == original:
        return 0

    with open(args.path, "w", encoding="utf-8") as handle:
        handle.write(new_content)
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
