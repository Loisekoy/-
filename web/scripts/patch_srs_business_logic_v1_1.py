#!/usr/bin/env python3
"""Apply the verified business-logic corrections to the retained v1.1 DOCX."""

from __future__ import annotations

import copy
import os
import re
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


DOCX = Path("/Users/loise/Documents/資料庫/參考資料/Fitness_Tracking_Management_System_SRS_中文版_正式修訂版_v1.1.docx")
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
XML = "{http://www.w3.org/XML/1998/namespace}"

FUTURE_TEXT = (
    "5. 未來擴充的徒手等效負荷 = 場次開始時體重快照 × 具版本的動作係數 × reps；"
    "估算值必須與實際外加重量分開顯示，本版不使用未定義係數。"
)


def paragraph_text(paragraph: ET.Element) -> str:
    return "".join(node.text or "" for node in paragraph.iter(W + "t"))


def set_paragraph_text(paragraph: ET.Element, text: str) -> None:
    texts = list(paragraph.iter(W + "t"))
    if not texts:
        run = ET.SubElement(paragraph, W + "r")
        node = ET.SubElement(run, W + "t")
        node.text = text
        return
    texts[0].text = text
    for node in texts[1:]:
        node.text = ""


def patch_security_and_formatting(root: ET.Element) -> dict[str, int]:
    """Keep the final SRS wording explicit and repair small caption/spacing defects."""
    counts = {
        "security_stack": 0,
        "backend_wording": 0,
        "cookie_header_spacing": 0,
        "table_caption_spacing": 0,
    }
    database_old = (
        "20 張應用表、25 條 FK，支援 Trigger、部分唯一索引、JOIN、GROUP BY 與 Aggregate。"
    )
    database_new = (
        "20 張應用表、25 條 FK，支援 Trigger、部分唯一索引、JOIN、GROUP BY 與 Aggregate；"
        "登入限流事件存於 login_failures，配合 advisory lock 在多個 PHP Worker 間共享，"
        "不依賴 Redis 或單一程序記憶體。"
    )

    for paragraph in root.iter(W + "p"):
        text = paragraph_text(paragraph)
        new_text = text
        if database_old in new_text:
            new_text = new_text.replace(database_old, database_new)
            counts["security_stack"] += 1
        if "路由、欄位驗證、Session 授權、排課與 JSON API。" in new_text:
            new_text = new_text.replace(
                "路由、欄位驗證、Session 授權、排課與 JSON API。",
                "路由、欄位驗證、Cookie／JWT Session 驗證、排課與 JSON API。",
            )
            counts["backend_wording"] += 1
        if "Set-CookieHeader" in new_text:
            new_text = new_text.replace("Set-CookieHeader", "Set-Cookie Header")
            counts["cookie_header_spacing"] += 1

        caption = re.match(r"^(表 4\.2\.\d+)\s*([A-Za-z][A-Za-z0-9_]*)$", new_text)
        if caption:
            repaired = f"{caption.group(1)} {caption.group(2)}"
            if repaired != new_text:
                new_text = repaired
                counts["table_caption_spacing"] += 1

        if new_text != text:
            set_paragraph_text(paragraph, new_text)

    return counts


def patch_settings(settings_root: ET.Element) -> None:
    update_fields = settings_root.find(W + "updateFields")
    if update_fields is None:
        update_fields = ET.SubElement(settings_root, W + "updateFields")
    update_fields.set(W + "val", "true")


def mark_toc_dirty(root: ET.Element) -> None:
    for paragraph in root.iter(W + "p"):
        instruction = "".join(node.text or "" for node in paragraph.iter(W + "instrText"))
        if "TOC " not in instruction:
            continue
        for field_char in paragraph.iter(W + "fldChar"):
            if field_char.get(W + "fldCharType") == "begin":
                field_char.set(W + "dirty", "true")


def update_toc_from_pdf(pdf_path: Path) -> None:
    """Update cached TOC page numbers from the rendered PDF outline."""
    from docx import Document
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    page_map: dict[str, int] = {}

    def walk(items) -> None:
        for item in items:
            if isinstance(item, list):
                walk(item)
            elif isinstance(item, dict) and "/Title" in item:
                page_map[str(item["/Title"])] = reader.get_destination_page_number(item) + 1

    walk(reader.outline)
    doc = Document(DOCX)
    updated = 0
    removed = 0
    missing: list[str] = []
    for paragraph in list(doc.paragraphs):
        if paragraph.style.name.lower() not in ("toc 1", "toc 2", "目錄 13", "目錄 23"):
            continue
        texts = paragraph._p.xpath(".//w:t")
        if len(texts) < 2:
            continue
        title = paragraph.text.rsplit("\t", 1)[0]
        if title not in page_map:
            if title.startswith("附錄 A"):
                paragraph._element.getparent().remove(paragraph._element)
                removed += 1
                continue
            missing.append(title)
            continue
        texts[-1].text = str(page_map[title])
        updated += 1

    if missing:
        raise RuntimeError(f"TOC headings missing from PDF outline: {missing}")

    fd, temporary_name = tempfile.mkstemp(prefix=DOCX.stem + "-toc-", suffix=".docx", dir=str(DOCX.parent))
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        doc.save(temporary)
        with zipfile.ZipFile(temporary, "r") as check:
            if check.testzip() is not None:
                raise RuntimeError("TOC-updated DOCX ZIP validation failed")
        os.replace(temporary, DOCX)
    finally:
        if temporary.exists():
            temporary.unlink()

    print(f"toc_entries_updated={updated}")
    print(f"stale_toc_entries_removed={removed}")
    print(f"pdf_pages={len(reader.pages)}")


def main() -> None:
    if not DOCX.exists():
        raise SystemExit(f"DOCX not found: {DOCX}")

    with zipfile.ZipFile(DOCX, "r") as source:
        document_xml = source.read("word/document.xml")
        root = ET.fromstring(document_xml)
        body = root.find(W + "body")
        if body is None:
            raise RuntimeError("word/document.xml has no document body")

        changed_total = 0
        corrected_typo = 0
        corrected_formula = 0
        for text_node in root.iter(W + "t"):
            if text_node.text and "total_reps=43" in text_node.text:
                text_node.text = text_node.text.replace("total_reps=43", "total_reps=45")
                changed_total += 1
            if text_node.text and "估算糸數" in text_node.text:
                text_node.text = text_node.text.replace("估算糸數", "估算係數")
                corrected_typo += 1
            if text_node.text and "系數須保存於具版本" in text_node.text:
                text_node.text = text_node.text.replace("系數須保存於具版本", "係數須保存於具版本")
                corrected_typo += 1
            if text_node.text and "current_weight_kg × coefficient × reps 計算。係數須" in text_node.text:
                text_node.text = text_node.text.replace(
                    "current_weight_kg × coefficient × reps 計算。係數須",
                    "session_body_weight_snapshot_kg × coefficient × reps 計算。"
                    "未來實作須在開始運動時將體重快照保存於場次或專用快照表；係數須",
                )
                corrected_formula += 1

        formatting_counts = patch_security_and_formatting(root)

        existing = any(paragraph_text(p) == FUTURE_TEXT for p in body.findall(W + "p"))
        inserted_future = False
        if not existing:
            paragraphs = body.findall(W + "p")
            previous_future = next(
                (p for p in paragraphs if paragraph_text(p).startswith("5. 未來若要提供「徒手等效負荷」")),
                None,
            )
            if previous_future is not None:
                set_paragraph_text(previous_future, FUTURE_TEXT)
                existing = True
        if not existing:
            paragraphs = body.findall(W + "p")
            anchor = next(
                (p for p in paragraphs if paragraph_text(p).startswith("4. 無訓練資料回 weighted_volume=0")),
                None,
            )
            if anchor is None:
                raise RuntimeError("FR-17 item 4 anchor not found")
            new_paragraph = ET.Element(W + "p")
            ppr = anchor.find(W + "pPr")
            if ppr is not None:
                new_paragraph.append(copy.deepcopy(ppr))
            set_paragraph_text(new_paragraph, FUTURE_TEXT)
            body.insert(list(body).index(anchor) + 1, new_paragraph)
            inserted_future = True

        if changed_total not in (0, 1):
            raise RuntimeError(f"Expected zero or one total_reps=43 replacement, found {changed_total}")

        settings_root = ET.fromstring(source.read("word/settings.xml"))
        patch_settings(settings_root)
        mark_toc_dirty(root)

        fd, temporary_name = tempfile.mkstemp(prefix=DOCX.stem + "-", suffix=".docx", dir=str(DOCX.parent))
        os.close(fd)
        temporary = Path(temporary_name)
        try:
            with zipfile.ZipFile(temporary, "w") as target:
                for item in source.infolist():
                    if item.filename == "word/document.xml":
                        data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                    elif item.filename == "word/settings.xml":
                        data = ET.tostring(settings_root, encoding="utf-8", xml_declaration=True)
                    else:
                        data = source.read(item.filename)
                    target.writestr(item, data)
            with zipfile.ZipFile(temporary, "r") as check:
                if check.testzip() is not None:
                    raise RuntimeError("Patched DOCX ZIP validation failed")
            os.replace(temporary, DOCX)
        finally:
            if temporary.exists():
                temporary.unlink()

    print(f"updated={DOCX}")
    print(f"total_reps_replacements={changed_total}")
    print(f"coefficient_typo_corrections={corrected_typo}")
    print(f"historical_formula_corrections={corrected_formula}")
    print(f"future_formula_inserted={inserted_future}")
    for key, value in formatting_counts.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 3 and sys.argv[1] == "--update-toc":
        update_toc_from_pdf(Path(sys.argv[2]))
    elif len(sys.argv) == 1:
        main()
    else:
        raise SystemExit("Usage: patch_srs_business_logic_v1_1.py [--update-toc rendered.pdf]")
