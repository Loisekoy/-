#!/usr/bin/env python3
"""Compare the SRS R01-R25 mapping table with the schema manifest."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from docx import Document


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: verify_srs_relationships.py SRS.docx schema_manifest.json", file=sys.stderr)
        return 2

    document_path = Path(sys.argv[1])
    manifest_path = Path(sys.argv[2])
    document = Document(document_path)

    rows: list[tuple[str, str, str]] = []
    for table in document.tables:
        for row in table.rows:
            cells = [" ".join(cell.text.split()) for cell in row.cells]
            if cells and re.fullmatch(r"R\d{2}", cells[0]):
                rows.append((cells[0], cells[1], cells[2]))

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected: list[tuple[str, str, str]] = []
    for index, (child, field, parent, _parent_field) in enumerate(
        manifest["relationships"], start=1
    ):
        expected.append((f"R{index:02d}", f"{parent} → {child}", field))

    mismatches = [
        (expected_row, actual_row)
        for expected_row, actual_row in zip(expected, rows)
        if expected_row != actual_row
    ]

    print(f"document_rows={len(rows)}")
    print(f"manifest_rows={len(expected)}")
    print(f"mismatches={len(mismatches)}")
    print("labels=" + ",".join(row[0] for row in rows))
    for expected_row, actual_row in mismatches:
        print(f"expected={expected_row}; actual={actual_row}")

    return 0 if len(rows) == len(expected) == 25 and not mismatches else 1


if __name__ == "__main__":
    raise SystemExit(main())
