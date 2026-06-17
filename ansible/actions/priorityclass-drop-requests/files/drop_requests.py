#!/usr/bin/env python3
"""Remove container resource requests from K8s manifests with selected priority classes."""

from __future__ import annotations

import argparse
import copy
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


def dump_documents(docs, yaml_mod) -> str:
    return yaml_mod.dump_all(
        docs,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )


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


def strip_requests(spec: dict, priority_classes: set[str]) -> bool:
    priority = spec.get("priorityClassName")
    if priority not in priority_classes:
        return False

    changed = False
    for key in ("containers", "initContainers"):
        for container in spec.get(key) or []:
            if not isinstance(container, dict):
                continue
            resources = container.get("resources")
            if not isinstance(resources, dict):
                continue
            if "requests" in resources:
                del resources["requests"]
                changed = True
            if not resources:
                del container["resources"]
                changed = True
    return changed


def process_documents(docs: list[Any], priority_classes: set[str]) -> bool:
    changed = False
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        for spec in pod_specs(doc):
            if strip_requests(spec, priority_classes):
                changed = True
    return changed


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
    updated = copy.deepcopy(docs)
    would_change = process_documents(updated, priority_classes)

    if not would_change:
        return 0

    if args.check:
        return 3

    new_content = dump_documents(updated, yaml_mod)
    if new_content == original:
        return 0

    with open(args.path, "w", encoding="utf-8") as handle:
        handle.write(new_content)
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
