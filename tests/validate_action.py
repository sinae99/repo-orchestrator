#!/usr/bin/env python3
"""Validate reporker action contract.

Checks for every action under ansible/actions/ (or a single named action):
  - meta.yml exists and parses with mode in {read, write}
  - tasks/main.yml exists
  - header comment: # Action: <name> (read|write)
  - sets changed_files somewhere
  - includes _shared/tasks/write_action_report.yml

Exit 0 on success, 1 on any failure.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("validate_action: PyYAML is required (python3 -c 'import yaml')", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
ACTIONS = ROOT / "ansible" / "actions"

SKIP_DIRS = {"_shared", "_template"}


def load_yaml(path: Path):
    with path.open() as f:
        return yaml.safe_load(f) or {}


def validate_action(name: str) -> list[str]:
    errors: list[str] = []
    action_dir = ACTIONS / name
    meta_path = action_dir / "meta.yml"
    tasks_path = action_dir / "tasks" / "main.yml"

    if not action_dir.is_dir():
        return [f"{name}: action directory missing"]

    if not meta_path.is_file():
        errors.append(f"{name}: missing meta.yml")
        meta = {}
    else:
        try:
            data = load_yaml(meta_path)
        except yaml.YAMLError as exc:
            errors.append(f"{name}: meta.yml parse error: {exc}")
            data = {}
        meta = data.get("action") or {}
        if not isinstance(meta, dict):
            errors.append(f"{name}: meta.yml 'action:' must be a mapping")
            meta = {}
        mode = str(meta.get("mode", "")).lower()
        if mode not in ("read", "write"):
            errors.append(f"{name}: meta.yml action.mode must be 'read' or 'write' (got {mode!r})")
        meta_name = meta.get("name")
        if meta_name and meta_name != name:
            errors.append(f"{name}: meta.yml action.name={meta_name!r} does not match directory")
        scan_filter = meta.get("scan_filter")
        if scan_filter:
            sf = action_dir / str(scan_filter)
            if not sf.is_file():
                errors.append(f"{name}: scan_filter path missing: {scan_filter}")

    if not tasks_path.is_file():
        errors.append(f"{name}: missing tasks/main.yml")
        return errors

    text = tasks_path.read_text()
    header = re.search(
        r"^#\s*Action:\s*(\S+)\s*\((read|write)\)\s*$",
        text,
        re.MULTILINE,
    )
    if not header:
        errors.append(
            f"{name}: tasks/main.yml must start with '# Action: {name} (read|write)' header"
        )
    else:
        hdr_name, hdr_mode = header.group(1), header.group(2)
        if hdr_name != name:
            errors.append(f"{name}: header name {hdr_name!r} does not match directory")
        meta_mode = str(meta.get("mode", "")).lower()
        if meta_mode and hdr_mode != meta_mode:
            errors.append(
                f"{name}: header mode ({hdr_mode}) does not match meta.yml mode ({meta_mode})"
            )

    if "changed_files" not in text:
        errors.append(f"{name}: tasks/main.yml must set changed_files ([] for read)")

    if "write_action_report.yml" not in text:
        errors.append(
            f"{name}: tasks/main.yml must include _shared/tasks/write_action_report.yml"
        )

    return errors


def iter_actions(only: str | None) -> list[str]:
    if only:
        return [only]
    names = []
    for path in sorted(ACTIONS.iterdir()):
        if not path.is_dir():
            continue
        if path.name in SKIP_DIRS or path.name.startswith("."):
            continue
        if (path / "tasks" / "main.yml").is_file() or (path / "meta.yml").is_file():
            names.append(path.name)
    return names


def main() -> int:
    only = sys.argv[1] if len(sys.argv) > 1 else None
    names = iter_actions(only)
    if only and only not in names and not (ACTIONS / only).is_dir():
        print(f"validate_action: action not found: {only}", file=sys.stderr)
        return 1

    all_errors: list[str] = []
    for name in names:
        errs = validate_action(name)
        if errs:
            all_errors.extend(errs)
            print(f"  [--]  {name}")
            for e in errs:
                print(f"         {e}")
        else:
            print(f"  [ok]  {name}")

    if all_errors:
        print(f"\n{len(all_errors)} validation error(s).", file=sys.stderr)
        return 1

    print(f"\n{len(names)} action(s) OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
