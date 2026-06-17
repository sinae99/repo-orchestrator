#!/usr/bin/env python3
"""Classify Kubernetes manifests by effective priorityClassName.

Rule: pod templates without priorityClassName are treated as medium.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

KNOWN_CLASSES = ("critical", "high", "medium", "low")
DEFAULT_MISSING_CLASS = "medium"


def _load_yaml():
    try:
        import yaml  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            "PyYAML is required. Install with: apt install python3-yaml "
            "or pip install pyyaml"
        ) from exc
    return yaml


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
            effective = effective_priority(spec, missing_class)
            templates.append(
                {
                    "effective_class": effective,
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
    yaml_mod = _load_yaml()
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


def manifest_matches_classes(
    path: str,
    target_classes: set[str],
    yaml_mod,
    missing_class: str = DEFAULT_MISSING_CLASS,
) -> bool:
    info = classify_manifest(path, yaml_mod, missing_class)
    if info is None or info["pod_templates"] == 0:
        return False
    return any(cls in target_classes for cls in info["effective_classes"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify K8s manifests by effective priority class.")
    parser.add_argument(
        "--output",
        help="Write JSON breakdown report to this path (default: stdout)",
    )
    parser.add_argument(
        "--file-list",
        help="Newline-separated manifest paths (use instead of positional paths for large scans)",
    )
    parser.add_argument(
        "--missing-class",
        default=DEFAULT_MISSING_CLASS,
        help=f"Class used when priorityClassName is absent (default: {DEFAULT_MISSING_CLASS})",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Manifest file paths",
    )
    args = parser.parse_args()

    if args.file_list:
        listed = [
            line.strip()
            for line in Path(args.file_list).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        paths = listed
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


if __name__ == "__main__":
    raise SystemExit(main())
