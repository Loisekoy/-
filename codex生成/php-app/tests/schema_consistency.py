#!/usr/bin/env python3
"""Verify that the canonical PostgreSQL DDL still matches the reviewed schema manifest."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DDL_PATH = ROOT / "php-app" / "database" / "postgres.sql"
MANIFEST_PATH = ROOT / "docs" / "schema_manifest.json"


def parse_schema(sql: str) -> tuple[set[str], set[tuple[str, str, str, str]]]:
    tables: set[str] = set()
    relationships: set[tuple[str, str, str, str]] = set()
    table_pattern = re.compile(
        r"CREATE\s+TABLE\s+([a-z_]+)\s*\((.*?)\n\);",
        re.IGNORECASE | re.DOTALL,
    )
    reference_pattern = re.compile(
        r"^\s*([a-z_]+)\s+[^,\n]*?REFERENCES\s+([a-z_]+)\s*\(\s*([a-z_]+)\s*\)",
        re.IGNORECASE | re.MULTILINE,
    )
    for table_match in table_pattern.finditer(sql):
        child_table = table_match.group(1).lower()
        if child_table == "schema_migrations":
            continue
        tables.add(child_table)
        for reference in reference_pattern.finditer(table_match.group(2)):
            relationships.add(
                (
                    child_table,
                    reference.group(1).lower(),
                    reference.group(2).lower(),
                    reference.group(3).lower(),
                )
            )
    return tables, relationships


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    actual_tables, actual_relationships = parse_schema(DDL_PATH.read_text(encoding="utf-8"))
    expected_tables = set(manifest["tables"])
    expected_relationships = {tuple(item) for item in manifest["relationships"]}

    failures: list[str] = []
    if actual_tables != expected_tables:
        failures.append(
            f"tables differ; missing={sorted(expected_tables - actual_tables)}, "
            f"unexpected={sorted(actual_tables - expected_tables)}"
        )
    if actual_relationships != expected_relationships:
        failures.append(
            "relationships differ; "
            f"missing={sorted(expected_relationships - actual_relationships)}, "
            f"unexpected={sorted(actual_relationships - expected_relationships)}"
        )
    if len(actual_tables) != manifest["application_table_count"]:
        failures.append("application_table_count does not match parsed DDL")
    if len(actual_relationships) != manifest["foreign_key_count"]:
        failures.append("foreign_key_count does not match parsed DDL")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print(
        "PASS: schema manifest matches PostgreSQL DDL "
        f"({len(actual_tables)} tables, {len(actual_relationships)} foreign keys)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
