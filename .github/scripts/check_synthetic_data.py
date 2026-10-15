#!/usr/bin/env python3
"""Fail unless every data file in this repository is declared synthetic (SYNTHETIC_DATA_POLICY.md).

A data file (``.csv .tsv .jsonl .ndjson .parquet .sql .xlsx ...`` and JSON outside ``.github``,
except package/TypeScript configs, ``*.schema.json`` and placeholder-only ``*.example.json``)
must sit in a directory covered by a ``SYNTHETIC_MANIFEST.json`` (in that directory or an
ancestor) that sets ``"synthetic": true`` and names ``generator``, ``seed`` and ``description``.
Its text is also checked for shapes of real personal data: e-mail addresses outside reserved
domains and US social-security numbers. Matched values are never printed, only file and line.

Standard library only, so CI needs nothing installed: ``python3 .github/scripts/check_synthetic_data.py``.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

DATA_SUFFIXES = {
    ".csv",
    ".tsv",
    ".jsonl",
    ".ndjson",
    ".parquet",
    ".avro",
    ".orc",
    ".xlsx",
    ".xls",
    ".sql",
    ".sqlite",
    ".db",
    ".dump",
    ".json",
}
CONFIG_JSON = {
    "package.json",
    "package-lock.json",
    "tsconfig.json",
    "renovate.json",
    "SYNTHETIC_MANIFEST.json",
}
REQUIRED = {"synthetic", "generator", "seed", "description"}
EMAIL = re.compile(r"[A-Za-z0-9._%+-]{1,64}@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,24})")
RESERVED = re.compile(r"(?i)(?:^|\.)(?:example\.(?:com|net|org)|example|test|invalid|localhost)$")
SSN = re.compile(r"(?<!\d)(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}(?!\d)")


def files(root: Path) -> list[Path]:
    """Tracked files (falls back to every file when this is not a git checkout)."""
    done = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True, check=False)  # noqa: S607
    if done.returncode == 0:
        return [root / line for line in done.stdout.splitlines() if line]
    return [p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts]


def is_data(rel: Path) -> bool:
    """True for files that hold data rather than configuration."""
    if rel.parts and rel.parts[0] == ".github":
        return False
    if rel.suffix.lower() == ".json" and (
        rel.name in CONFIG_JSON or rel.name.endswith((".schema.json", ".example.json"))
    ):
        return False  # configuration, JSON Schemas and placeholder-only example documents
    return rel.suffix.lower() in DATA_SUFFIXES


def manifest_ok(root: Path, rel: Path) -> bool:
    """True when the nearest ``SYNTHETIC_MANIFEST.json`` above ``rel`` is valid."""
    for parent in rel.parents:
        candidate = root / parent / "SYNTHETIC_MANIFEST.json"
        if candidate.is_file():
            try:
                meta = json.loads(candidate.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return False
            return isinstance(meta, dict) and meta.keys() >= REQUIRED and meta.get("synthetic") is True
    return False


def main() -> int:
    """Print each violation (file and line, never the value) and exit 1 if there is any."""
    root = Path.cwd()
    problems: list[str] = []
    for path in files(root):
        rel = path.relative_to(root)
        if not is_data(rel):
            continue
        if not manifest_ok(root, rel):
            problems.append(f"{rel}: data file without a valid SYNTHETIC_MANIFEST.json")
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(lines, start=1):
            if any(not RESERVED.search(m.group(1)) for m in EMAIL.finditer(line)):
                problems.append(f"{rel}:{number}: e-mail address outside the reserved domains")
            if SSN.search(line):
                problems.append(f"{rel}:{number}: looks like a social-security number")
    for problem in problems:
        print(f"SYNTHETIC-DATA-POLICY {problem}")  # noqa: T201 (CLI output)
    print(f"synthetic-data check: {len(problems)} problem(s)")  # noqa: T201 (CLI output)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
