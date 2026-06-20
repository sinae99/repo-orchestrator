#!/usr/bin/env python3
"""Priority-class action: scan manifests and apply drop-requests + ensure-medium."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

KNOWN_CLASSES = ("critical", "high", "medium", "low")
DEFAULT_MISSING_CLASS = "medium"


def load_yaml():
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


def effective_priority(spec: dict, missing_class: str = DEFAULT_MISSING_CLASS) -> str:
    raw = spec.get("priorityClassName")
    if raw is None or raw == "":
        return missing_class
    return str(raw)


def classify_manifest(path: str, yaml_mod, missing_class: str = DEFAULT_MISSING_CLASS) -> dict[str, Any] | None:
    try:
        with open(path, encoding="utf-8") as handle:
            docs = list(yaml_mod.safe_load_all(handle.read()))
    except (OSError, ValueError, yaml_mod.YAMLError):  # type: ignore[attr-defined]
        return None

    templates: list[dict[str, Any]] = []
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        for spec in pod_specs(doc):
            raw = spec.get("priorityClassName")
            templates.append(
                {
                    "effective_class": effective_priority(spec, missing_class),
                    "explicit": raw is not None and raw != "",
                    "raw_priority_class": raw,
                }
            )

    if not templates:
        return {
            "file": path,
            "pod_templates": 0,
            "effective_classes": [],
            "primary_class": None,
            "templates": [],
        }

    effective_classes = [item["effective_class"] for item in templates]
    primary = max(set(effective_classes), key=effective_classes.count)

    return {
        "file": path,
        "pod_templates": len(templates),
        "effective_classes": effective_classes,
        "primary_class": primary,
        "templates": templates,
    }


def aggregate_breakdown(
    paths: list[str],
    missing_class: str = DEFAULT_MISSING_CLASS,
    known_classes: tuple[str, ...] = KNOWN_CLASSES,
) -> dict[str, Any]:
    yaml_mod = load_yaml()
    by_manifest: list[dict[str, Any]] = []
    findings: dict[str, list[str]] = {cls: [] for cls in known_classes}
    other: dict[str, list[str]] = {}
    skipped_files: list[str] = []

    total_templates = 0
    medium_explicit = 0
    medium_implicit = 0

    for path in paths:
        info = classify_manifest(path, yaml_mod, missing_class)
        if info is None:
            skipped_files.append(path)
            continue
        if info["pod_templates"] == 0:
            continue

        by_manifest.append(info)
        total_templates += info["pod_templates"]
        primary = info["primary_class"]
        if primary is None:
            continue

        for template in info["templates"]:
            cls = template["effective_class"]
            if cls == missing_class:
                if template["explicit"]:
                    medium_explicit += 1
                else:
                    medium_implicit += 1

        if primary in findings:
            if path not in findings[primary]:
                findings[primary].append(path)
        else:
            other.setdefault(primary, [])
            if path not in other[primary]:
                other[primary].append(path)

    counts = {cls: len(findings[cls]) for cls in known_classes}
    counts.update({cls: len(files) for cls, files in other.items()})

    return {
        "rule": f"manifests without priorityClassName are classified as {missing_class}",
        "missing_priority_class_maps_to": missing_class,
        "priority_classes": list(known_classes),
        "summary": {
            "total_manifests_scanned": len(paths),
            "manifests_with_pod_templates": len(by_manifest),
            "total_pod_templates": total_templates,
            "counts_per_class": counts,
            "medium_breakdown": {
                "explicit_priorityClassName_medium": medium_explicit,
                "implicit_no_priorityClassName": medium_implicit,
                "total_medium_templates": medium_explicit + medium_implicit,
            },
        },
        "findings": findings,
        "other_classes": other,
        "by_manifest": by_manifest,
        "skipped_unparseable": skipped_files,
    }


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


@dataclass(frozen=True)
class StripTarget:
    section: str
    occurrence: int


def strip_targets(
    docs: list[Any],
    priority_classes: set[str],
    missing_class: str = "medium",
) -> list[StripTarget]:
    targets: list[StripTarget] = []
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
                        targets.append(StripTarget(section, occurrence))
                    occurrence += 1
    return targets


def remove_requests_lines(content: str, targets: list[StripTarget]) -> str:
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


def apply_manifest(
    content: str,
    docs: list[Any],
    *,
    ensure_priority_class: str | None = "medium",
    drop_priority_classes: set[str] | None = None,
    missing_class: str = "medium",
) -> tuple[str, bool, bool, bool]:
    """Drop resource requests, then add priorityClassName where absent."""
    drop_priority_classes = drop_priority_classes or {"medium", "low"}
    current = content
    ensured = False
    dropped = False

    targets = strip_targets(docs, drop_priority_classes, missing_class)
    if targets:
        updated = remove_requests_lines(current, targets)
        if updated != current:
            dropped = True
            current = updated

    if ensure_priority_class and specs_missing_priority_class(docs) > 0:
        updated = add_priority_class_lines(current, ensure_priority_class)
        if updated != current:
            ensured = True
            current = updated

    return current, ensured or dropped, ensured, dropped


def cmd_breakdown(args: argparse.Namespace) -> int:
    if args.file_list:
        paths = [
            line.strip()
            for line in Path(args.file_list).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    else:
        paths = args.paths

    if not paths:
        print("ERROR: no manifest paths provided", file=sys.stderr)
        return 2

    report = aggregate_breakdown(paths, missing_class=args.missing_class)
    payload = json.dumps(report, indent=2, sort_keys=False) + "\n"

    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    ensure_class = args.ensure_priority_class.strip() or None
    drop_classes = {
        item.strip()
        for item in args.drop_priority_classes.split(",")
        if item.strip()
    }
    if not ensure_class and not drop_classes:
        print("ERROR: nothing to do", file=sys.stderr)
        return 2

    yaml_mod = load_yaml()
    original, docs = load_documents(args.path, yaml_mod)
    new_content, changed, ensured, dropped = apply_manifest(
        original,
        docs,
        ensure_priority_class=ensure_class,
        drop_priority_classes=drop_classes,
        missing_class=args.missing_class,
    )

    if not changed:
        if args.report_json:
            print(json.dumps({"ensured_class": False, "dropped_requests": False}))
        return 0

    if args.check:
        if args.report_json:
            print(json.dumps({"ensured_class": ensured, "dropped_requests": dropped}))
        return 3

    with open(args.path, "w", encoding="utf-8") as handle:
        handle.write(new_content)

    if args.report_json:
        print(json.dumps({"ensured_class": ensured, "dropped_requests": dropped}))
    return 3


def main() -> int:
    parser = argparse.ArgumentParser(description="Priority-class scan and manifest edits.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    breakdown = subparsers.add_parser("breakdown", help="Classify manifests and write JSON report")
    breakdown.add_argument("--output", help="Write JSON report to this path")
    breakdown.add_argument("--file-list", help="Newline-separated manifest paths")
    breakdown.add_argument(
        "--missing-class",
        default=DEFAULT_MISSING_CLASS,
        help=f"Class when priorityClassName is absent (default: {DEFAULT_MISSING_CLASS})",
    )
    breakdown.add_argument("paths", nargs="*", help="Manifest file paths")
    breakdown.set_defaults(func=cmd_breakdown)

    apply_cmd = subparsers.add_parser("apply", help="Drop requests and ensure priorityClassName")
    apply_cmd.add_argument("path", help="Kubernetes manifest path")
    apply_cmd.add_argument(
        "--ensure-priority-class",
        default="medium",
        help="priorityClassName to add when absent (default: medium)",
    )
    apply_cmd.add_argument(
        "--drop-priority-classes",
        default="medium,low",
        help="Comma-separated classes whose requests are removed (default: medium,low)",
    )
    apply_cmd.add_argument(
        "--missing-class",
        default="medium",
        help="Effective class when priorityClassName is absent (default: medium)",
    )
    apply_cmd.add_argument(
        "--check",
        action="store_true",
        help="Do not write; exit 3 when a modification would be made",
    )
    apply_cmd.add_argument(
        "--report-json",
        action="store_true",
        help="Print per-file change details as JSON on stdout",
    )
    apply_cmd.set_defaults(func=cmd_apply)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
