#!/usr/bin/env python3
"""Remove container resource requests from K8s manifests with selected priority classes."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
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


def effective_priority(spec: dict, missing_class: str = "medium") -> str:
    raw = spec.get("priorityClassName")
    if raw is None or raw == "":
        return missing_class
    return str(raw)


@dataclass(frozen=True)
class _StripTarget:
    section: str
    occurrence: int


def strip_targets(
    docs: list[Any],
    priority_classes: set[str],
    missing_class: str = "medium",
) -> list[_StripTarget]:
    targets: list[_StripTarget] = []
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        for spec in pod_specs(doc):
            if effective_priority(spec, missing_class) not in priority_classes:
                continue
            for section in ("containers", "initContainers"):
                occurrence = 0
                for container in spec.get(section) or []:
                    if not isinstance(container, dict):
                        continue
                    resources = container.get("resources")
                    if isinstance(resources, dict) and "requests" in resources:
                        targets.append(_StripTarget(section, occurrence))
                    occurrence += 1
    return targets


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


def _remove_requests_lines(content: str, targets: list[_StripTarget]) -> str:
    if not targets:
        return content

    pending = {(t.section, t.occurrence) for t in targets}
    lines = content.splitlines(keepends=True)
    current_section: str | None = None
    section_indent = -1
    container_occurrence = -1
    strip_requests = False
    in_resources = False
    resources_indent = -1
    skip_indent = -1
    keep: list[str] = []

    for line in lines:
        indent = _line_indent(line)
        key = _strip_key(line)

        if skip_indent >= 0:
            if indent > skip_indent:
                continue
            skip_indent = -1

        if key in ("containers", "initContainers") and ":" in line.lstrip():
            current_section = key
            section_indent = indent
            container_occurrence = -1
            strip_requests = False
            in_resources = False
            keep.append(line)
            continue

        if (
            current_section is not None
            and line.lstrip().startswith("- ")
            and indent >= section_indent
        ):
            container_occurrence += 1
            target_key = (current_section, container_occurrence)
            strip_requests = target_key in pending
            if strip_requests:
                pending.remove(target_key)
            in_resources = False
            keep.append(line)
            continue

        if (
            current_section is not None
            and indent <= section_indent
            and not line.lstrip().startswith("- ")
            and key not in ("containers", "initContainers")
        ):
            current_section = None
            section_indent = -1
            container_occurrence = -1
            strip_requests = False
            in_resources = False

        if strip_requests and key == "resources" and ":" in line.lstrip():
            in_resources = True
            resources_indent = indent
            keep.append(line)
            continue

        if strip_requests and in_resources and key == "requests" and ":" in line.lstrip():
            skip_indent = indent
            continue

        if in_resources and indent <= resources_indent:
            in_resources = False

        keep.append(line)

    cleaned: list[str] = []
    idx = 0
    while idx < len(keep):
        line = keep[idx]
        key = _strip_key(line)
        if key != "resources" or ":" not in line.lstrip():
            cleaned.append(line)
            idx += 1
            continue

        resources_indent = _line_indent(line)
        child_start = idx + 1
        child_end = child_start
        while child_end < len(keep):
            child_indent = _line_indent(keep[child_end])
            if child_indent <= resources_indent:
                break
            child_end += 1

        if child_start == child_end:
            idx += 1
            continue

        cleaned.extend(keep[idx:child_end])
        idx = child_end

    return "".join(cleaned)


def process_documents(
    docs: list[Any],
    priority_classes: set[str],
    missing_class: str = "medium",
) -> bool:
    return bool(strip_targets(docs, priority_classes, missing_class))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Drop resource requests for selected priorityClassName values."
    )
    parser.add_argument("path", help="Kubernetes manifest path")
    parser.add_argument(
        "--priority-classes",
        default="medium,low",
        help="Comma-separated priorityClassName values (default: medium,low)",
    )
    parser.add_argument(
        "--missing-class",
        default="medium",
        help="Effective class when priorityClassName is absent (default: medium)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Do not write; print CHANGED when a modification would be made",
    )
    args = parser.parse_args()

    priority_classes = {
        item.strip()
        for item in args.priority_classes.split(",")
        if item.strip()
    }
    if not priority_classes:
        print("ERROR: no priority classes configured", file=sys.stderr)
        return 2

    yaml_mod = _load_yaml()
    original, docs = load_documents(args.path, yaml_mod)
    targets = strip_targets(docs, priority_classes, args.missing_class)

    if not targets:
        return 0

    if args.check:
        return 3

    new_content = _remove_requests_lines(original, targets)
    if new_content == original:
        return 0

    with open(args.path, "w", encoding="utf-8") as handle:
        handle.write(new_content)
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
