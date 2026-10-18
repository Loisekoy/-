from __future__ import annotations

import math
import shutil
import zipfile
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor
from PIL import Image, ImageDraw, ImageFont


ROOT = Path("/Users/loise/Documents/資料庫")
OUT_DOCX = ROOT / "output" / "specification" / "Fitness_Tracking_Management_System_SRS.docx"
IMG_DIR = ROOT / "output" / "specification" / "images"
IMG_DIR.mkdir(parents=True, exist_ok=True)
OUT_DOCX.parent.mkdir(parents=True, exist_ok=True)

FONT_CJK = "PingFang TC"
FONT_BODY = "Arial"
FONT_CODE = "Menlo"
COLOR_TEXT = "202124"
COLOR_HEADING = "2F3A45"
COLOR_SUBHEADING = "536878"
COLOR_TABLE_HEADER = "44546A"
COLOR_TABLE_ALT = "F7F8FA"
COLOR_BORDER = "D9DEE5"
COLOR_CODE_BG = "F5F6F7"


def set_rfonts(element, ascii_font=FONT_BODY, east_asia_font=FONT_CJK):
    rPr = element.get_or_add_rPr()
    rFonts = rPr.rFonts
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), ascii_font)
    rFonts.set(qn("w:hAnsi"), ascii_font)
    rFonts.set(qn("w:eastAsia"), east_asia_font)
    rFonts.set(qn("w:cs"), ascii_font)


def set_style_font(style, size_pt=None, bold=None, color=None, ascii_font=FONT_BODY, east_asia_font=FONT_CJK):
    style.font.name = ascii_font
    if size_pt is not None:
        style.font.size = Pt(size_pt)
    if bold is not None:
        style.font.bold = bold
    if color:
        style.font.color.rgb = RGBColor.from_string(color)
    set_rfonts(style._element, ascii_font, east_asia_font)


def set_run_font(run, size_pt=None, bold=None, color=None, ascii_font=FONT_BODY, east_asia_font=FONT_CJK):
    run.font.name = ascii_font
    if size_pt is not None:
        run.font.size = Pt(size_pt)
    if bold is not None:
        run.font.bold = bold
    if color:
        run.font.color.rgb = RGBColor.from_string(color)
    set_rfonts(run._element, ascii_font, east_asia_font)


def set_cell_shading(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = tcPr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tcPr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=90, start=110, bottom=90, end=110):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = tcPr.first_child_found_in("w:tcMar")
    if tcMar is None:
        tcMar = OxmlElement("w:tcMar")
        tcPr.append(tcMar)
    for m, v in [("top", top), ("start", start), ("bottom", bottom), ("end", end)]:
        node = tcMar.find(qn(f"w:{m}"))
        if node is None:
            node = OxmlElement(f"w:{m}")
            tcMar.append(node)
        node.set(qn("w:w"), str(v))
        node.set(qn("w:type"), "dxa")


def set_table_borders(table, color=COLOR_BORDER, size="4"):
    tblPr = table._tbl.tblPr
    borders = tblPr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tblPr.append(borders)
    for edge in ["top", "left", "bottom", "right", "insideH", "insideV"]:
        tag = f"w:{edge}"
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), size)
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), color)


def set_repeat_table_header(row):
    trPr = row._tr.get_or_add_trPr()
    tbl_header = trPr.find(qn("w:tblHeader"))
    if tbl_header is None:
        tbl_header = OxmlElement("w:tblHeader")
        trPr.append(tbl_header)
    tbl_header.set(qn("w:val"), "true")


def set_update_fields_on_open(docx_path: Path) -> None:
    tmp = docx_path.parent / f".{docx_path.stem}_settings_patch"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    with zipfile.ZipFile(docx_path, "r") as z:
        z.extractall(tmp)
    settings = tmp / "word" / "settings.xml"
    from lxml import etree

    W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    ns = {"w": W_NS}
    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(str(settings), parser)
    root = tree.getroot()
    uf = root.find("w:updateFields", namespaces=ns)
    if uf is None:
        uf = etree.Element(f"{{{W_NS}}}updateFields")
        root.insert(0, uf)
    uf.set(f"{{{W_NS}}}val", "true")
    tree.write(str(settings), xml_declaration=True, encoding="UTF-8", standalone="yes")
    with zipfile.ZipFile(docx_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in tmp.rglob("*"):
            if p.is_file():
                z.write(p, p.relative_to(tmp).as_posix())
    shutil.rmtree(tmp)


def add_field_run(paragraph, field_code: str, display_text: str = ""):
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = f" {field_code} "
    sep = OxmlElement("w:fldChar")
    sep.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = display_text
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instr)
    run._r.append(sep)
    run._r.append(text)
    run._r.append(end)
    set_run_font(run, size_pt=9, color="6B7280")
    return run


def add_toc_field(paragraph):
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = ' TOC \\o "1-2" \\h \\z \\u '
    sep = OxmlElement("w:fldChar")
    sep.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "Table of contents will update when opened in Word."
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instr)
    run._r.append(sep)
    run._r.append(text)
    run._r.append(end)
    set_run_font(run, size_pt=10.5, color=COLOR_TEXT)


def draw_arrow(draw, p1, p2, color=(74, 85, 104), width=3):
    draw.line((p1, p2), fill=color, width=width)
    x1, y1 = p1
    x2, y2 = p2
    ang = math.atan2(y2 - y1, x2 - x1)
    L = 14
    a1 = (x2 - L * math.cos(ang - 0.45), y2 - L * math.sin(ang - 0.45))
    a2 = (x2 - L * math.cos(ang + 0.45), y2 - L * math.sin(ang + 0.45))
    draw.polygon([(x2, y2), a1, a2], fill=color)


def make_architecture_image(path: Path):
    W, H = 1600, 850
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    font_path = "/Library/Fonts/Arial Unicode.ttf"
    title = ImageFont.truetype(font_path, 42)
    head = ImageFont.truetype(font_path, 24)
    body = ImageFont.truetype(font_path, 18)
    small = ImageFont.truetype(font_path, 16)
    slate = (47, 58, 69)
    border = (139, 149, 160)
    fill = (247, 248, 250)
    accent = (68, 84, 106)

    d.text((90, 55), "System Architecture", font=title, fill=slate)
    d.text((92, 108), "Frontend, backend, and cloud database responsibilities", font=body, fill=(90, 98, 110))

    boxes = {
        "Browser": (90, 230, 360, 360, "User Browser\nRegister / Login\nProfile / Workout UI"),
        "Frontend": (510, 230, 800, 360, "React Frontend\nForms, Plans, Dashboard\nActive Workout UI"),
        "Backend": (950, 230, 1240, 360, "Backend API\nAuthentication\nRecommendation\nSQL Queries"),
        "Database": (950, 500, 1240, 630, "Cloud PostgreSQL\nPK / FK / JOIN\nWorkout History"),
        "Admin": (510, 500, 800, 630, "Admin Console\nExercise Database\nReference Data"),
    }
    for _, (x1, y1, x2, y2, text) in boxes.items():
        d.rounded_rectangle((x1, y1, x2, y2), radius=10, fill=fill, outline=border, width=2)
        lines = text.split("\n")
        d.text((x1 + 26, y1 + 24), lines[0], font=head, fill=slate)
        yy = y1 + 68
        for line in lines[1:]:
            d.text((x1 + 26, yy), line, font=body, fill=(45, 55, 65))
            yy += 30

    draw_arrow(d, (360, 295), (510, 295))
    draw_arrow(d, (800, 295), (950, 295))
    draw_arrow(d, (1095, 360), (1095, 500))
    draw_arrow(d, (800, 565), (950, 565))
    draw_arrow(d, (655, 500), (655, 360))
    d.text((92, 720), "Security note: DATABASE_URL and SECRET_KEY remain in environment variables. The frontend never receives database credentials.", font=small, fill=(85, 95, 105))
    img.save(path)


def make_erd_image(path: Path):
    W, H = 1350, 1700
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    font_path = "/Library/Fonts/Arial Unicode.ttf"
    title_font = ImageFont.truetype(font_path, 40)
    module_font = ImageFont.truetype(font_path, 22)
    box_font = ImageFont.truetype(font_path, 23)
    rel_font = ImageFont.truetype(font_path, 17)
    small_font = ImageFont.truetype(font_path, 15)
    line = (55, 70, 95)
    blue = (232, 238, 245)
    green = (235, 244, 239)
    yellow = (249, 244, 225)
    pink = (248, 235, 242)
    peach = (250, 241, 229)
    gray = (242, 244, 246)
    module_bg = (249, 250, 251)

    def center(text, y, font, fill=(47, 58, 69)):
        tw = d.textlength(text, font=font)
        d.text(((W - tw) / 2, y), text, font=font, fill=fill)

    def module(x, y, w, h, label):
        d.rounded_rectangle((x, y, x + w, y + h), radius=14, fill=module_bg, outline=(210, 216, 223), width=2)
        d.rectangle((x, y, x + w, y + 34), fill=(68, 84, 106))
        d.text((x + 16, y + 5), label, font=module_font, fill="white")

    def box(name, x, y, w=220, h=72, fill=blue):
        d.rounded_rectangle((x, y, x + w, y + h), radius=10, fill=fill, outline=line, width=3)
        tw = d.textlength(name, font=box_font)
        d.text((x + (w - tw) / 2, y + (h - 26) / 2), name, font=box_font, fill=(25, 37, 52))
        return {"x": x, "y": y, "w": w, "h": h}

    def side(b, s):
        x, y, w, h = b["x"], b["y"], b["w"], b["h"]
        return {"L": (x, y + h / 2), "R": (x + w, y + h / 2), "T": (x + w / 2, y), "B": (x + w / 2, y + h)}[s]

    def arrow(p1, p2, label):
        draw_arrow(d, p1, p2, color=line, width=3)
        mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
        bbox = d.textbbox((0, 0), label, font=small_font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        d.rounded_rectangle((mx - tw / 2 - 6, my - th / 2 - 18, mx + tw / 2 + 6, my - th / 2 + 5), radius=4, fill="white", outline=(210, 216, 223))
        d.text((mx - tw / 2, my - th / 2 - 15), label, font=small_font, fill=(25, 37, 52))

    center("Fitness Tracking Management System", 28, title_font)
    center("ER Diagram - Relationship Overview", 76, title_font)
    center("Detailed columns, PK, and FK are listed in the Data Dictionary section.", 125, rel_font, (85, 94, 105))

    module(55, 170, 1240, 300, "A. Account / Authentication")
    module(55, 505, 1240, 260, "B. Preference / Exercise Database")
    module(55, 805, 1240, 270, "C. Workout Plan")
    module(55, 1115, 1240, 380, "D. Start Workout / Tracking / History")

    tg = box("training_goals", 105, 235, 235, 74, yellow)
    users = box("users", 430, 235, 220, 74, blue)
    auth = box("user_auth", 760, 235, 220, 74, green)
    sess = box("user_sessions", 105, 365, 260, 74, green)
    admin = box("admins", 450, 365, 220, 74, green)
    br = box("body_records", 760, 365, 260, 74, gray)
    arrow(side(tg, "R"), side(users, "L"), "1:N")
    arrow(side(users, "R"), side(auth, "L"), "1:1")
    arrow(side(users, "B"), side(sess, "T"), "1:N")
    arrow(side(users, "B"), side(admin, "T"), "1:N")
    arrow(side(users, "B"), side(br, "T"), "1:N")
    d.text((105, 450), "users is the owner table. user_auth stores credentials separately from profile data.", font=rel_font, fill=(55, 70, 95))

    u2 = box("users", 105, 590, 190, 72, blue)
    ubp = box("user_body_parts", 375, 590, 260, 72, pink)
    bp = box("body_parts", 715, 590, 220, 72, pink)
    ex = box("exercises", 1015, 590, 220, 72, pink)
    arrow(side(u2, "R"), side(ubp, "L"), "1:N")
    arrow(side(ubp, "R"), side(bp, "L"), "N:1")
    arrow(side(bp, "R"), side(ex, "L"), "1:N")
    d.text((105, 705), "M:N relationship: users and body_parts are normalized through user_body_parts.", font=rel_font, fill=(55, 70, 95))

    u3 = box("users", 85, 900, 170, 72, blue)
    wp = box("workout_plans", 310, 900, 250, 72, peach)
    pd = box("plan_days", 620, 900, 210, 72, peach)
    pe = box("plan_exercises", 890, 900, 260, 72, peach)
    ex2 = box("exercises", 1165, 900, 150, 72, pink)
    arrow(side(u3, "R"), side(wp, "L"), "1:N")
    arrow(side(wp, "R"), side(pd, "L"), "1:N")
    arrow(side(pd, "R"), side(pe, "L"), "1:N")
    arrow(side(pe, "R"), side(ex2, "L"), "N:1")
    d.text((105, 1010), "Generated plans are stored as workout_plans, plan_days, and plan_exercises.", font=rel_font, fill=(55, 70, 95))

    u4 = box("users", 90, 1215, 170, 72, blue)
    pd2 = box("plan_days", 90, 1340, 210, 72, peach)
    ws = box("workout_sessions", 520, 1275, 280, 72, gray)
    sets = box("workout_sets", 905, 1275, 240, 72, gray)
    ex3 = box("exercises", 915, 1400, 220, 72, pink)
    arrow(side(u4, "R"), side(ws, "L"), "1:N")
    arrow(side(pd2, "R"), side(ws, "L"), "0:N")
    arrow(side(ws, "R"), side(sets, "L"), "1:N")
    arrow(side(ex3, "T"), side(sets, "B"), "1:N")
    d.text((105, 1460), "Start Workout creates workout_sessions with status = in_progress.", font=rel_font, fill=(55, 70, 95))
    d.text((105, 1490), "Each completed set is inserted into workout_sets immediately.", font=rel_font, fill=(55, 70, 95))
    d.text((105, 1520), "Workout History and Dashboard use JOIN + GROUP BY + aggregates across sessions and sets.", font=rel_font, fill=(55, 70, 95))
    d.rounded_rectangle((55, 1585, 1295, 1658), radius=14, fill="white", outline=(210, 216, 223), width=2)
    d.text((80, 1612), "Legend: 1:N = one-to-many, N:1 = many-to-one, 0:N = optional one-to-many. PK/FK details are defined in tables below.", font=rel_font, fill=(40, 55, 75))
    img.save(path)


def format_paragraph(paragraph, style_name=None):
    if style_name:
        paragraph.style = style_name
    for run in paragraph.runs:
        set_run_font(run, color=COLOR_TEXT)
    return paragraph


def add_p(doc, text="", style="Normal"):
    p = doc.add_paragraph(style=style)
    if text:
        run = p.add_run(text)
        set_run_font(run, color=COLOR_TEXT)
    return p


def add_bullet(doc, text, level=0):
    p = doc.add_paragraph(style="List Bullet" if level == 0 else "List Bullet 2")
    p.paragraph_format.left_indent = Cm(0.7 + level * 0.5)
    p.paragraph_format.first_line_indent = Cm(-0.25)
    p.paragraph_format.space_after = Pt(3)
    run = p.add_run(text)
    set_run_font(run, size_pt=10.5, color=COLOR_TEXT)
    return p


def add_heading(doc, text, level=1):
    p = doc.add_heading(text, level=level)
    for run in p.runs:
        set_run_font(run, color=COLOR_HEADING if level == 1 else COLOR_SUBHEADING, bold=True)
    return p


def add_caption(doc, text):
    p = doc.add_paragraph(style="Caption")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    set_run_font(run, size_pt=9, color="6B7280")
    return p


def add_code_block(doc, code):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    set_table_borders(table, color=COLOR_BORDER, size="4")
    cell = table.cell(0, 0)
    set_cell_shading(cell, COLOR_CODE_BG)
    set_cell_margins(cell, top=120, start=140, bottom=120, end=140)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    cell.text = ""
    lines = code.strip("\n").split("\n")
    for i, line in enumerate(lines):
        p = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.05
        run = p.add_run(line)
        set_run_font(run, size_pt=8.8, ascii_font=FONT_CODE, east_asia_font=FONT_CJK, color=COLOR_TEXT)
    doc.add_paragraph()


def add_table(doc, headers, rows, widths=None, font_size=9.3):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_borders(table)
    hdr = table.rows[0]
    set_repeat_table_header(hdr)
    for i, h in enumerate(headers):
        cell = hdr.cells[i]
        set_cell_shading(cell, COLOR_TABLE_HEADER)
        set_cell_margins(cell)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(h)
        set_run_font(run, size_pt=font_size, bold=True, color="FFFFFF")
    for r_idx, row in enumerate(rows):
        cells = table.add_row().cells
        for i, value in enumerate(row):
            cell = cells[i]
            if r_idx % 2 == 1:
                set_cell_shading(cell, COLOR_TABLE_ALT)
            set_cell_margins(cell)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            run = p.add_run(str(value))
            set_run_font(run, size_pt=font_size, color=COLOR_TEXT)
    if widths:
        for row in table.rows:
            for i, width in enumerate(widths):
                row.cells[i].width = Cm(width)
    doc.add_paragraph()
    return table


def add_image(doc, path: Path, width_in: float, caption: str):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run.add_picture(str(path), width=Inches(width_in))
    add_caption(doc, caption)


def add_cover(doc):
    for _ in range(6):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Fitness Tracking Management System")
    set_run_font(r, size_pt=25, bold=True, color=COLOR_HEADING)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("健身紀錄管理系統")
    set_run_font(r, size_pt=18, bold=True, color=COLOR_HEADING)
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Software Requirements Specification")
    set_run_font(r, size_pt=14, color=COLOR_SUBHEADING)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Database Systems Course Project")
    set_run_font(r, size_pt=12, color=COLOR_SUBHEADING)
    for _ in range(3):
        doc.add_paragraph()
    t = doc.add_table(rows=3, cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    set_table_borders(t)
    for row in t.rows:
        for cell in row.cells:
            set_cell_margins(cell, top=120, start=180, bottom=120, end=180)
    items = [("Version", "1.0"), ("Year", "2026"), ("Document Type", "Formal SRS Report")]
    for i, (k, v) in enumerate(items):
        c0, c1 = t.rows[i].cells
        set_cell_shading(c0, "F1F3F5")
        c0.width = Cm(4)
        c1.width = Cm(7)
        r = c0.paragraphs[0].add_run(k)
        set_run_font(r, size_pt=10.5, bold=True, color=COLOR_TEXT)
        r = c1.paragraphs[0].add_run(v)
        set_run_font(r, size_pt=10.5, color=COLOR_TEXT)
    for _ in range(7):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Prepared as a database-centered full-stack web application specification")
    set_run_font(r, size_pt=10, color="6B7280")
    doc.add_page_break()


def build_document():
    make_architecture_image(IMG_DIR / "architecture-formal.png")
    make_erd_image(IMG_DIR / "erd-formal.png")

    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.2)
    section.right_margin = Cm(2.2)
    section.different_first_page_header_footer = True

    styles = doc.styles
    set_style_font(styles["Normal"], size_pt=10.5, color=COLOR_TEXT)
    styles["Normal"].paragraph_format.line_spacing = 1.18
    styles["Normal"].paragraph_format.space_after = Pt(6)
    set_style_font(styles["Title"], size_pt=25, bold=True, color=COLOR_HEADING)
    set_style_font(styles["Heading 1"], size_pt=16, bold=True, color=COLOR_HEADING)
    styles["Heading 1"].paragraph_format.space_before = Pt(15)
    styles["Heading 1"].paragraph_format.space_after = Pt(7)
    set_style_font(styles["Heading 2"], size_pt=12.5, bold=True, color=COLOR_SUBHEADING)
    styles["Heading 2"].paragraph_format.space_before = Pt(10)
    styles["Heading 2"].paragraph_format.space_after = Pt(5)
    set_style_font(styles["Heading 3"], size_pt=11.2, bold=True, color=COLOR_TEXT)
    styles["Heading 3"].paragraph_format.space_before = Pt(8)
    styles["Heading 3"].paragraph_format.space_after = Pt(4)
    set_style_font(styles["Caption"], size_pt=9, color="6B7280")

    header = section.header
    hp = header.paragraphs[0]
    hp.text = ""
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = hp.add_run("Fitness Tracking Management System - SRS")
    set_run_font(r, size_pt=8.5, color="8A94A3")

    footer = section.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = fp.add_run("Page ")
    set_run_font(r, size_pt=8.5, color="8A94A3")
    add_field_run(fp, "PAGE", "1")
    r = fp.add_run(" of ")
    set_run_font(r, size_pt=8.5, color="8A94A3")
    add_field_run(fp, "NUMPAGES", "1")

    add_cover(doc)

    p = doc.add_paragraph()
    p.style = styles["Heading 1"]
    r = p.add_run("Table of Contents")
    set_run_font(r, size_pt=16, bold=True, color=COLOR_HEADING)
    p = doc.add_paragraph()
    add_toc_field(p)
    doc.add_page_break()

    add_heading(doc, "1. Project Overview", 1)
    add_heading(doc, "1.1 Project Background", 2)
    add_p(doc, "The developer currently has a regular fitness habit, but each gym visit often begins with uncertainty about what exercises to perform, which body parts to train, and how to record weight and repetitions in a useful way. Searching online or asking AI every time is inconvenient and leaves workout records scattered across different tools.")
    add_p(doc, "This project therefore designs a database-centered fitness tracking system that integrates training goals, workout plan generation, active workout recording, historical workout review, training volume statistics, and body weight history. The system stores users, authentication data, body parts, exercises, workout plans, workout sessions, workout sets, and body records in a relational database.")
    add_heading(doc, "1.2 Problem Statement", 2)
    for item in [
        "Fitness beginners and general gym users often do not know which exercises to perform on a given day.",
        "Paper notes or phone memos are not structured enough for SQL queries, long-term analysis, or dashboard statistics.",
        "Without login and user ownership, the system cannot reliably preserve personal workout history.",
        "Exercises, body parts, plans, sessions, and sets have clear relationships, making the project suitable for relational database design.",
    ]:
        add_bullet(doc, item)
    add_heading(doc, "1.3 Project Goals", 2)
    for item in [
        "Provide registration, login, and logout so each user can manage personal fitness data.",
        "Design a normalized relational database with clear primary keys, foreign keys, one-to-many relationships, and many-to-many relationships.",
        "Support CRUD operations for user profiles, preferred body parts, exercises, workout plans, workout sessions, workout sets, and body records.",
        "Provide workout history, training volume, weekly workout count, most trained body part, most used exercise, and body weight history.",
        "Implement a Start Workout button that creates an in-progress workout session and saves each completed set immediately.",
        "Deploy the application and cloud database so the final system does not rely on localhost.",
    ]:
        add_bullet(doc, item)
    add_heading(doc, "1.4 Scope", 2)
    add_p(doc, "Version 1.0 includes login and registration, database CRUD, workout plan generation, active workout tracking, historical records, and dashboard statistics. The first recommendation engine is rule-based and uses database records. A future LLM integration can be added later, but the database remains the core of the project.")
    add_heading(doc, "1.5 Email Validation Policy", 2)
    add_p(doc, "The first version validates email format and enforces uniqueness through the user_auth.email UNIQUE constraint. It does not send verification emails in version 1.0 because email verification would require a third-party email service, verification tokens, token expiration, resend logic, and additional error handling. The database still reserves email_verified and email_verified_at for future extension.")

    add_heading(doc, "2. System Architecture and Tech Stack", 1)
    add_heading(doc, "2.1 Recommended Architecture", 2)
    add_p(doc, "The system uses a frontend, backend API, and cloud PostgreSQL database. The frontend handles forms, workout plan views, active workout input, and dashboard pages. The backend handles authentication, authorization, business rules, recommendation logic, and SQL access. PostgreSQL stores all structured data.")
    add_image(doc, IMG_DIR / "architecture-formal.png", 6.2, "Figure 1. System Architecture")
    add_heading(doc, "2.2 Suggested Tech Stack", 2)
    add_table(
        doc,
        ["Layer", "Recommended Technology", "Purpose"],
        [
            ["Frontend", "React / Next.js / Vite", "Build user interface, profile forms, workout plan pages, active workout pages, and dashboard views."],
            ["Backend", "Node.js Express or Python FastAPI", "Handle API routes, login, authorization, database access, and recommendation logic."],
            ["Database", "PostgreSQL", "Cloud relational database with FK, JOIN, GROUP BY, aggregate queries, and indexes."],
            ["ORM / Query", "Prisma, SQLAlchemy, or raw SQL", "Manage schema migration and application queries. Important course queries can remain as raw SQL examples."],
            ["Deployment", "Render / Railway / Supabase / Neon / Vercel", "Deploy a public web application and cloud database."],
            ["Security", "bcrypt or argon2, JWT or secure session", "Hash passwords and manage login state safely."],
        ],
        widths=[3.4, 4.8, 8.0],
    )
    add_heading(doc, "2.3 High Level Data Flow", 2)
    for item in [
        "The user registers or logs in through the frontend.",
        "The backend validates credentials and creates a session or token.",
        "The user sets profile data, training goal, preferred body parts, weekly training days, and training duration.",
        "The backend queries exercises, body parts, and training goals to generate a workout plan.",
        "The user clicks Start Workout, and the backend creates a workout_sessions row.",
        "Each completed set is saved to workout_sets immediately.",
        "Dashboard queries use JOIN, GROUP BY, SUM, COUNT, and AVG to produce statistics.",
    ]:
        add_bullet(doc, item)

    add_heading(doc, "3. User Flow", 1)
    add_heading(doc, "3.1 Main Flow", 2)
    add_code_block(
        doc,
        """
Enter website
  -> Register / Login
  -> Create or update user profile
  -> Select training goal
  -> Select preferred body parts
  -> Select training days and workout duration
  -> Generate workout plan from database exercises and rule-based logic
  -> Review plan details and exercise references
  -> Click Start Workout
  -> Create workout_sessions row with status = in_progress
  -> Save each completed set into workout_sets
  -> Complete workout and update session status
  -> Review Workout History, Training Volume, and Body Weight History
        """,
    )
    add_heading(doc, "3.2 Start Workout Button Behavior", 2)
    for item in [
        "The user opens a plan day and clicks Start Workout.",
        "The backend creates one workout_sessions row with user_id and optional plan_day_id.",
        "The initial session status is in_progress.",
        "The active workout page shows exercises from plan_exercises.",
        "Each saved set inserts one row into workout_sets with exercise_id, set_number, weight_kg, and reps.",
        "When the user finishes, workout_sessions.status changes to completed and ended_at is recorded.",
        "If the user leaves midway, the in_progress session can be resumed.",
    ]:
        add_bullet(doc, item)
    add_heading(doc, "3.3 Roles", 2)
    add_table(
        doc,
        ["Role", "Description", "Main Permissions"],
        [
            ["Guest", "Unauthenticated visitor", "View landing page, register, and login."],
            ["User", "General fitness user", "Manage own profile, goals, plans, sessions, sets, and body records."],
            ["Admin", "System maintainer", "Maintain exercise database, body parts, training goals, and reference data."],
        ],
        widths=[3.0, 4.8, 8.4],
    )

    add_heading(doc, "4. Functional Requirements", 1)
    add_table(
        doc,
        ["ID", "Feature", "Requirement"],
        [
            ["FR-01", "Register", "Users can create an account with name, email, and password. The system checks email format, uniqueness, and password strength."],
            ["FR-02", "Login and Logout", "Users can log in and log out. The system creates and revokes user sessions."],
            ["FR-03", "Profile Management", "Users can create and update age, gender, height, weight, and training experience."],
            ["FR-04", "Training Goal", "Users can select Muscle Gain, Fat Loss, Strength, or General Fitness."],
            ["FR-05", "Preferred Body Parts", "Users can select multiple body parts through the user_body_parts junction table."],
            ["FR-06", "Exercise Database", "The system stores exercise name, body part, difficulty, equipment, description, and image URL."],
            ["FR-07", "Generate Workout Plan", "The system generates workout_plans, plan_days, and plan_exercises from user preferences and database exercises."],
            ["FR-08", "View Workout Plan", "Users can view day title, exercises, target sets, target reps, rest time, and image reference."],
            ["FR-09", "Start Workout", "Users can create an in-progress workout session from a plan day."],
            ["FR-10", "Record Sets", "Users can record exercise, set number, weight, reps, and completion time."],
            ["FR-11", "Workout History", "Users can query previous workouts with exercises, body parts, sets, weight, reps, and volume."],
            ["FR-12", "Dashboard", "The system shows total volume, weekly workout count, most trained body part, most used exercise, and weight trend."],
            ["FR-13", "Body Records", "Users can add and review body weight records."],
            ["FR-14", "Search", "Users can search exercises, body parts, and workout history."],
            ["FR-15", "Admin Management", "Admins can create, update, and deactivate exercise and reference data."],
        ],
        widths=[1.6, 3.3, 11.3],
        font_size=8.5,
    )
    add_heading(doc, "4.1 CRUD Mapping", 2)
    add_table(
        doc,
        ["Entity", "Create", "Read", "Update", "Delete"],
        [
            ["users", "Register", "Profile", "Edit profile", "Deactivate account"],
            ["training_goals", "Admin create", "Goal options", "Admin edit", "Admin deactivate"],
            ["body_parts", "Admin create", "Body part list", "Admin edit", "Admin deactivate"],
            ["user_body_parts", "Select preferences", "View preferences", "Replace preferences", "Remove preference"],
            ["exercises", "Admin create", "Exercise search", "Admin edit", "Admin deactivate"],
            ["workout_plans", "Generate plan", "Plan detail", "Regenerate or rename", "Delete plan"],
            ["workout_sessions", "Start workout", "Workout history", "Complete or cancel", "Delete own session"],
            ["workout_sets", "Save set", "Set history", "Edit weight or reps", "Delete set"],
            ["body_records", "Add record", "Weight history", "Edit record", "Delete record"],
        ],
        widths=[3.1, 3.2, 3.2, 3.2, 3.2],
        font_size=8.3,
    )

    add_heading(doc, "5. Database Design and ER Diagram", 1)
    add_heading(doc, "5.1 Database Design Principles", 2)
    for item in [
        "All important data is stored in PostgreSQL and not only in localStorage or a local database.",
        "Every major table has a primary key.",
        "Cross-table relationships use foreign keys to maintain referential integrity.",
        "Many-to-many relationships use junction tables, such as user_body_parts.",
        "Multiple body parts are not stored as a comma-separated VARCHAR field.",
        "Authentication data is separated into user_auth to avoid mixing password_hash with profile data.",
        "User-owned records include user_id so queries and updates can be scoped to the logged-in user.",
    ]:
        add_bullet(doc, item)
    add_image(doc, IMG_DIR / "erd-formal.png", 6.1, "Figure 2. Entity Relationship Diagram")
    add_heading(doc, "5.2 Entities Overview", 2)
    add_table(
        doc,
        ["Table", "Purpose"],
        [
            ["users", "Stores profile and user-owned settings."],
            ["user_auth", "Stores login email, password_hash, and email verification fields."],
            ["user_sessions", "Stores session token hash, expiration, and revoked time."],
            ["training_goals", "Stores training goal reference data."],
            ["body_parts", "Stores body part reference data."],
            ["user_body_parts", "Junction table between users and body_parts."],
            ["exercises", "Stores exercise name, body part, difficulty, equipment, description, and image URL."],
            ["workout_plans", "Stores generated training plans."],
            ["plan_days", "Stores day number and day focus in a workout plan."],
            ["plan_exercises", "Stores exercises assigned to each plan day."],
            ["workout_sessions", "Stores actual workout sessions created by Start Workout."],
            ["workout_sets", "Stores every completed set with weight and reps."],
            ["body_records", "Stores body weight and body composition records."],
            ["admins", "Stores admin role assignments."],
        ],
        widths=[4.0, 12.0],
    )
    add_heading(doc, "5.3 Relationships", 2)
    add_table(
        doc,
        ["Relationship", "Explanation"],
        [
            ["users 1:1 user_auth", "Each user has one credential record."],
            ["users 1:N user_sessions", "One user can have many login sessions."],
            ["training_goals 1:N users", "Many users can select the same training goal."],
            ["users M:N body_parts", "Resolved by user_body_parts."],
            ["body_parts 1:N exercises", "One body part can have many exercises."],
            ["users 1:N workout_plans", "One user can generate many plans."],
            ["workout_plans 1:N plan_days", "One plan contains multiple training days."],
            ["plan_days 1:N plan_exercises", "One training day contains multiple planned exercises."],
            ["exercises 1:N plan_exercises", "One exercise can appear in many plans."],
            ["users 1:N workout_sessions", "One user can complete many workout sessions."],
            ["workout_sessions 1:N workout_sets", "One workout session contains many set records."],
            ["exercises 1:N workout_sets", "One exercise can have many actual set records."],
            ["users 1:N body_records", "One user can have many body records."],
        ],
        widths=[5.4, 10.8],
    )

    add_heading(doc, "6. Data Dictionary", 1)
    data_tables = {
        "users": [
            ["user_id", "BIGSERIAL", "PK", "System-generated user ID."],
            ["name", "VARCHAR(100)", "NOT NULL", "User display name."],
            ["gender", "VARCHAR(20)", "NULL", "Optional gender."],
            ["age", "INT", "CHECK 10 to 100", "Age."],
            ["height_cm", "NUMERIC(5,2)", "CHECK > 0", "Height in centimeters."],
            ["weight_kg", "NUMERIC(5,2)", "CHECK > 0", "Current body weight."],
            ["training_experience", "VARCHAR(20)", "CHECK Beginner / Intermediate / Advanced", "Training experience level."],
            ["training_goal_id", "BIGINT", "FK -> training_goals", "Main training goal."],
            ["training_days_per_week", "INT", "CHECK 2 to 6", "Weekly training frequency."],
            ["training_duration_minutes", "INT", "CHECK 30 / 60 / 90", "Expected duration per workout."],
            ["created_at", "TIMESTAMP", "DEFAULT now()", "Creation time."],
            ["updated_at", "TIMESTAMP", "DEFAULT now()", "Last update time."],
        ],
        "user_auth": [
            ["auth_id", "BIGSERIAL", "PK", "Authentication record ID."],
            ["user_id", "BIGINT", "FK UNIQUE -> users", "One-to-one user reference."],
            ["email", "VARCHAR(255)", "NOT NULL UNIQUE", "Login email."],
            ["password_hash", "VARCHAR(255)", "NOT NULL", "Hashed password only."],
            ["email_verified", "BOOLEAN", "DEFAULT FALSE", "Reserved for future email verification."],
            ["email_verified_at", "TIMESTAMP", "NULL", "Future verification timestamp."],
            ["last_login_at", "TIMESTAMP", "NULL", "Last login time."],
            ["created_at", "TIMESTAMP", "DEFAULT now()", "Creation time."],
        ],
        "user_sessions": [
            ["session_id", "BIGSERIAL", "PK", "Session ID."],
            ["user_id", "BIGINT", "FK -> users", "Session owner."],
            ["session_token_hash", "VARCHAR(255)", "UNIQUE NOT NULL", "Hashed session token."],
            ["expires_at", "TIMESTAMP", "NOT NULL", "Expiration time."],
            ["revoked_at", "TIMESTAMP", "NULL", "Logout or revocation time."],
            ["created_at", "TIMESTAMP", "DEFAULT now()", "Creation time."],
        ],
        "training_goals": [
            ["training_goal_id", "BIGSERIAL", "PK", "Training goal ID."],
            ["goal_name", "VARCHAR(50)", "UNIQUE NOT NULL", "Muscle Gain, Fat Loss, Strength, or General Fitness."],
            ["description", "TEXT", "NULL", "Goal description."],
        ],
        "body_parts": [
            ["body_part_id", "BIGSERIAL", "PK", "Body part ID."],
            ["body_part_name", "VARCHAR(50)", "UNIQUE NOT NULL", "Chest, Back, Shoulders, Legs, Core, and related body parts."],
            ["description", "TEXT", "NULL", "Body part description."],
        ],
        "user_body_parts": [
            ["user_id", "BIGINT", "PK, FK -> users", "User ID."],
            ["body_part_id", "BIGINT", "PK, FK -> body_parts", "Preferred body part ID."],
            ["priority", "INT", "DEFAULT 1", "Preference priority."],
            ["created_at", "TIMESTAMP", "DEFAULT now()", "Creation time."],
        ],
        "exercises": [
            ["exercise_id", "BIGSERIAL", "PK", "Exercise ID."],
            ["exercise_name", "VARCHAR(120)", "UNIQUE NOT NULL", "Exercise name."],
            ["body_part_id", "BIGINT", "FK -> body_parts", "Primary trained body part."],
            ["difficulty_level", "VARCHAR(20)", "CHECK Beginner / Intermediate / Advanced", "Exercise difficulty."],
            ["equipment", "VARCHAR(100)", "NULL", "Equipment."],
            ["description", "TEXT", "NULL", "Exercise description."],
            ["image_url", "TEXT", "NULL", "Reference image URL."],
            ["is_active", "BOOLEAN", "DEFAULT TRUE", "Whether the exercise is active."],
        ],
        "workout_plans": [
            ["workout_plan_id", "BIGSERIAL", "PK", "Workout plan ID."],
            ["user_id", "BIGINT", "FK -> users", "Plan owner."],
            ["plan_name", "VARCHAR(120)", "NOT NULL", "Plan name."],
            ["training_goal_id", "BIGINT", "FK -> training_goals", "Goal used to generate plan."],
            ["days_per_week", "INT", "CHECK 2 to 6", "Training days per week."],
            ["duration_minutes", "INT", "CHECK 30 / 60 / 90", "Workout duration."],
            ["generated_by", "VARCHAR(30)", "DEFAULT rule_based", "Recommendation source."],
            ["created_at", "TIMESTAMP", "DEFAULT now()", "Creation time."],
        ],
        "plan_days": [
            ["plan_day_id", "BIGSERIAL", "PK", "Plan day ID."],
            ["workout_plan_id", "BIGINT", "FK -> workout_plans", "Parent workout plan."],
            ["day_number", "INT", "NOT NULL", "Day order."],
            ["day_title", "VARCHAR(120)", "NOT NULL", "Training focus title."],
            ["focus_notes", "TEXT", "NULL", "Notes for the day."],
        ],
        "plan_exercises": [
            ["plan_exercise_id", "BIGSERIAL", "PK", "Planned exercise ID."],
            ["plan_day_id", "BIGINT", "FK -> plan_days", "Parent plan day."],
            ["exercise_id", "BIGINT", "FK -> exercises", "Exercise."],
            ["exercise_order", "INT", "NOT NULL", "Display order."],
            ["target_sets", "INT", "NOT NULL", "Recommended sets."],
            ["target_reps", "VARCHAR(30)", "NOT NULL", "Recommended reps."],
            ["target_weight_note", "VARCHAR(120)", "NULL", "Weight guidance."],
            ["rest_seconds", "INT", "DEFAULT 60", "Rest time."],
        ],
        "workout_sessions": [
            ["workout_session_id", "BIGSERIAL", "PK", "Actual workout session ID."],
            ["user_id", "BIGINT", "FK -> users", "Session owner."],
            ["workout_plan_id", "BIGINT", "FK -> workout_plans NULL", "Optional source plan."],
            ["plan_day_id", "BIGINT", "FK -> plan_days NULL", "Optional source plan day."],
            ["session_date", "DATE", "DEFAULT CURRENT_DATE", "Workout date."],
            ["started_at", "TIMESTAMP", "DEFAULT now()", "Start time."],
            ["ended_at", "TIMESTAMP", "NULL", "End time."],
            ["status", "VARCHAR(20)", "CHECK in_progress / completed / cancelled", "Session status."],
            ["notes", "TEXT", "NULL", "Workout notes."],
        ],
        "workout_sets": [
            ["workout_set_id", "BIGSERIAL", "PK", "Set record ID."],
            ["workout_session_id", "BIGINT", "FK -> workout_sessions", "Parent workout session."],
            ["exercise_id", "BIGINT", "FK -> exercises", "Exercise performed."],
            ["set_number", "INT", "NOT NULL", "Set number."],
            ["weight_kg", "NUMERIC(6,2)", "CHECK >= 0", "Weight in kilograms."],
            ["reps", "INT", "CHECK > 0", "Repetitions."],
            ["volume", "NUMERIC(10,2)", "computed", "weight_kg * reps."],
            ["completed_at", "TIMESTAMP", "DEFAULT now()", "Completion time."],
        ],
        "body_records": [
            ["body_record_id", "BIGSERIAL", "PK", "Body record ID."],
            ["user_id", "BIGINT", "FK -> users", "Record owner."],
            ["record_date", "DATE", "NOT NULL", "Record date."],
            ["weight_kg", "NUMERIC(5,2)", "CHECK > 0", "Body weight."],
            ["body_fat_percentage", "NUMERIC(5,2)", "NULL", "Optional body fat percentage."],
            ["notes", "TEXT", "NULL", "Notes."],
            ["created_at", "TIMESTAMP", "DEFAULT now()", "Creation time."],
        ],
        "admins": [
            ["admin_id", "BIGSERIAL", "PK", "Admin ID."],
            ["user_id", "BIGINT", "FK UNIQUE -> users", "Admin user."],
            ["role", "VARCHAR(50)", "DEFAULT admin", "Admin role."],
            ["created_at", "TIMESTAMP", "DEFAULT now()", "Creation time."],
        ],
    }
    for table_name, rows in data_tables.items():
        add_heading(doc, table_name, 2)
        add_table(doc, ["Column", "Data Type", "Constraint", "Description"], rows, widths=[3.6, 3.6, 4.4, 4.6], font_size=8.2)

    add_heading(doc, "7. Primary Keys Foreign Keys Relationships and 3NF", 1)
    add_heading(doc, "7.1 Primary Keys", 2)
    for item in [
        "Major entity tables use BIGSERIAL surrogate primary keys.",
        "user_body_parts uses a composite primary key of user_id and body_part_id.",
        "workout_sets uses workout_set_id so each set can be edited or deleted independently.",
    ]:
        add_bullet(doc, item)
    add_heading(doc, "7.2 Foreign Keys", 2)
    add_code_block(
        doc,
        """
user_auth.user_id                 -> users.user_id
user_sessions.user_id             -> users.user_id
users.training_goal_id            -> training_goals.training_goal_id
user_body_parts.user_id           -> users.user_id
user_body_parts.body_part_id      -> body_parts.body_part_id
exercises.body_part_id            -> body_parts.body_part_id
workout_plans.user_id             -> users.user_id
workout_plans.training_goal_id    -> training_goals.training_goal_id
plan_days.workout_plan_id         -> workout_plans.workout_plan_id
plan_exercises.plan_day_id        -> plan_days.plan_day_id
plan_exercises.exercise_id        -> exercises.exercise_id
workout_sessions.user_id          -> users.user_id
workout_sessions.workout_plan_id  -> workout_plans.workout_plan_id
workout_sessions.plan_day_id      -> plan_days.plan_day_id
workout_sets.workout_session_id   -> workout_sessions.workout_session_id
workout_sets.exercise_id          -> exercises.exercise_id
body_records.user_id              -> users.user_id
admins.user_id                    -> users.user_id
        """,
    )
    add_heading(doc, "7.3 Constraints and Indexes", 2)
    add_table(
        doc,
        ["Index", "Reason"],
        [
            ["idx_user_auth_email", "Speeds up login by email."],
            ["idx_exercises_body_part_id", "Speeds up exercise filtering by body part."],
            ["idx_workout_sessions_user_date", "Speeds up workout history by user and date."],
            ["idx_workout_sets_session_id", "Speeds up set lookup for one workout session."],
            ["idx_body_records_user_date", "Speeds up body weight history queries."],
            ["idx_plan_days_plan_day_number", "Speeds up plan day ordering."],
        ],
        widths=[6.2, 9.8],
    )
    add_heading(doc, "7.4 3NF Normalization", 2)
    for item in [
        "First Normal Form is satisfied because fields store atomic values. Multiple body parts are stored in user_body_parts, not one comma-separated field.",
        "Second Normal Form is satisfied because non-key attributes in junction tables depend on the full key.",
        "Third Normal Form is satisfied because training goals, body parts, exercises, authentication, sessions, and body records are separated by subject.",
        "Authentication data is stored in user_auth instead of mixing password_hash with profile attributes.",
        "Actual workout records are separated into workout_sessions and workout_sets to avoid repeated session data.",
    ]:
        add_bullet(doc, item)

    add_heading(doc, "8. SQL Query Requirements", 1)
    add_heading(doc, "8.1 Create Insert Example", 2)
    add_code_block(
        doc,
        """
INSERT INTO users
  (name, gender, age, height_cm, weight_kg, training_experience,
   training_goal_id, training_days_per_week, training_duration_minutes)
VALUES
  ('Loise', 'Female', 21, 160, 50, 'Beginner', 1, 4, 60);
        """,
    )
    add_heading(doc, "8.2 Read with JOIN Workout History", 2)
    add_code_block(
        doc,
        """
SELECT
  ws.session_date,
  e.exercise_name,
  bp.body_part_name,
  wset.set_number,
  wset.weight_kg,
  wset.reps,
  (wset.weight_kg * wset.reps) AS set_volume
FROM workout_sessions ws
JOIN workout_sets wset
  ON ws.workout_session_id = wset.workout_session_id
JOIN exercises e
  ON wset.exercise_id = e.exercise_id
JOIN body_parts bp
  ON e.body_part_id = bp.body_part_id
WHERE ws.user_id = :user_id
ORDER BY ws.session_date DESC, e.exercise_name, wset.set_number;
        """,
    )
    add_heading(doc, "8.3 GROUP BY and Aggregate Weekly Training Volume", 2)
    add_code_block(
        doc,
        """
SELECT
  DATE_TRUNC('week', ws.session_date) AS training_week,
  SUM(wset.weight_kg * wset.reps) AS weekly_volume,
  COUNT(DISTINCT ws.workout_session_id) AS workout_count
FROM workout_sessions ws
JOIN workout_sets wset
  ON ws.workout_session_id = wset.workout_session_id
WHERE ws.user_id = :user_id
  AND ws.status = 'completed'
GROUP BY DATE_TRUNC('week', ws.session_date)
ORDER BY training_week DESC;
        """,
    )
    add_heading(doc, "8.4 Most Trained Body Part", 2)
    add_code_block(
        doc,
        """
SELECT
  bp.body_part_name,
  COUNT(*) AS total_sets,
  SUM(wset.weight_kg * wset.reps) AS total_volume
FROM workout_sets wset
JOIN workout_sessions ws
  ON ws.workout_session_id = wset.workout_session_id
JOIN exercises e
  ON e.exercise_id = wset.exercise_id
JOIN body_parts bp
  ON bp.body_part_id = e.body_part_id
WHERE ws.user_id = :user_id
GROUP BY bp.body_part_name
ORDER BY total_sets DESC;
        """,
    )
    doc.add_page_break()
    add_heading(doc, "8.5 Body Weight History", 2)
    add_code_block(
        doc,
        """
SELECT record_date, weight_kg
FROM body_records
WHERE user_id = :user_id
ORDER BY record_date ASC;
        """,
    )
    add_heading(doc, "8.6 Search Exercises", 2)
    add_code_block(
        doc,
        """
SELECT
  e.exercise_id,
  e.exercise_name,
  bp.body_part_name,
  e.difficulty_level,
  e.equipment
FROM exercises e
JOIN body_parts bp
  ON bp.body_part_id = e.body_part_id
WHERE LOWER(e.exercise_name) LIKE LOWER('%' || :keyword || '%')
   OR LOWER(bp.body_part_name) LIKE LOWER('%' || :keyword || '%')
ORDER BY e.exercise_name;
        """,
    )

    add_heading(doc, "9. Workout Recommendation Algorithm", 1)
    add_heading(doc, "9.1 Algorithm Goal", 2)
    add_p(doc, "Version 1.0 does not depend on an AI API. It uses database records and a rule-based recommendation algorithm to generate workout plans from training goal, training experience, preferred body parts, training days per week, and training duration.")
    add_heading(doc, "9.2 Rule Based Logic", 2)
    for item in [
        "Training experience determines sets, reps, rest seconds, and exercise difficulty.",
        "Beginner users receive beginner exercises and a smaller number of intermediate exercises.",
        "Muscle Gain uses moderate reps and higher volume. Strength uses lower reps and longer rest. Fat Loss uses higher reps and shorter rest. General Fitness uses moderate volume.",
        "days_per_week determines the split, such as full body, push-pull-legs, upper-lower, or focused body-part split.",
        "Preferred body parts appear more often, but other major muscle groups are still included.",
        "duration_minutes limits the number of exercises in each plan day.",
    ]:
        add_bullet(doc, item)
    add_heading(doc, "9.3 Pseudocode", 2)
    add_code_block(
        doc,
        """
Input: user_id

1. Read user profile, training goal, experience, days_per_week, and duration_minutes.
2. Read preferred body parts from user_body_parts.
3. Build weekly split according to days_per_week.
4. Add preferred body parts to the split with higher frequency.
5. For each day:
   a. Query candidate exercises by body_part_id and difficulty_level.
   b. Select exercises by preference, difficulty, and equipment availability.
   c. Decide target sets, reps, and rest time based on goal and experience.
   d. Insert plan_days and plan_exercises.
6. Return workout_plan_id and detailed plan.
        """,
    )
    add_heading(doc, "9.4 Example Output", 2)
    add_table(
        doc,
        ["Day", "Focus", "Exercises"],
        [
            ["Day 1", "Chest + Triceps", "Bench Press 3x10, Chest Press 3x12, Triceps Pushdown 3x12"],
            ["Day 2", "Back + Biceps", "Lat Pulldown 3x10, Seated Row 3x12, Bicep Curl 3x12"],
            ["Day 3", "Legs + Core", "Squat 3x10, Leg Press 3x12, Plank 3 sets"],
            ["Day 4", "Chest + Back", "Incline Press 3x10, Lat Pulldown 3x10, Cable Row 3x12"],
        ],
        widths=[2.0, 3.8, 10.3],
    )
    add_heading(doc, "9.5 Backend Validation", 2)
    for item in [
        "Confirm that user_id exists and belongs to the logged-in user.",
        "Confirm that selected body parts exist in body_parts.",
        "Confirm that chosen exercises are active exercises.",
        "Confirm that target sets, reps, and rest_seconds are reasonable.",
        "Return a clear error or fallback selection if not enough candidate exercises exist.",
    ]:
        add_bullet(doc, item)

    add_heading(doc, "10. Non Functional Requirements", 1)
    add_table(
        doc,
        ["Category", "Requirement"],
        [
            ["Security", "Passwords must be hashed with bcrypt or argon2. Users can only access their own data."],
            ["Privacy", "Email, profile data, workouts, and body records must not be exposed to other users."],
            ["Performance", "Common query fields need indexes, including email, user_id, session_date, and body_part_id."],
            ["Reliability", "Each completed set is saved immediately to reduce the risk of losing workout data."],
            ["Maintainability", "Schema migrations, seed data, README, and .env.example must be clear."],
            ["Deployment", "Source code is stored on GitHub. The application and PostgreSQL database are deployed in the cloud."],
            ["Environment Variables", "DATABASE_URL, SECRET_KEY, API keys, and passwords must not be committed to GitHub."],
            ["Responsive UI", "The active workout page must work well on both mobile and desktop devices."],
        ],
        widths=[4.0, 12.0],
    )
    add_heading(doc, "10.1 Environment Variables", 2)
    add_code_block(
        doc,
        """
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE
SECRET_KEY=replace-with-random-secret
JWT_EXPIRES_IN=7d
OPENAI_API_KEY=optional-future-llm-key
NODE_ENV=development
        """,
    )
    add_heading(doc, "10.2 GitHub Safety Rules", 2)
    for item in [
        ".env must not be committed.",
        ".env.example must be provided as a safe template.",
        "DATABASE_URL, SECRET_KEY, API keys, and passwords must not be hard-coded.",
        "README should explain environment variables without revealing real secrets.",
    ]:
        add_bullet(doc, item)

    add_heading(doc, "11. Acceptance Test Cases", 1)
    add_table(
        doc,
        ["ID", "Scenario", "Input or Action", "Expected Result"],
        [
            ["AT-01", "Register", "Enter valid name, email, and password.", "Create users and user_auth. Password is stored as hash."],
            ["AT-02", "Duplicate Email", "Register with an existing email.", "System rejects the request."],
            ["AT-03", "Login", "Enter correct email and password.", "Create a valid session and open dashboard."],
            ["AT-04", "Profile", "Edit age, height, weight, and experience.", "users row is updated."],
            ["AT-05", "Preferred Body Parts", "Select Chest and Back.", "Two user_body_parts rows are created."],
            ["AT-06", "Generate Plan", "Beginner, Muscle Gain, 4 days, Chest + Back.", "Create workout_plans, plan_days, and plan_exercises."],
            ["AT-07", "View Plan", "Open plan page.", "Show day title, exercise, sets, reps, rest, and image reference."],
            ["AT-08", "Start Workout", "Click Start Workout.", "Create workout_sessions with status in_progress."],
            ["AT-09", "Save Set", "Enter Bench Press 60 kg x 12.", "Create workout_sets and calculate set volume."],
            ["AT-10", "Complete Workout", "Click Finish Workout.", "Set session status to completed and save ended_at."],
            ["AT-11", "Workout History", "Open history page.", "JOIN query shows date, exercise, body part, sets, weight, reps, and volume."],
            ["AT-12", "Training Volume", "Open dashboard.", "GROUP BY and SUM show weekly training volume."],
            ["AT-13", "Weight History", "Add several body records.", "Body weight history is shown in date order."],
            ["AT-14", "Admin Exercise CRUD", "Admin creates or edits exercise.", "exercises table is updated."],
            ["AT-15", "Authorization", "User A requests User B data.", "API rejects the request."],
        ],
        widths=[1.6, 3.0, 5.3, 6.3],
        font_size=8.1,
    )

    add_heading(doc, "12. Deployment Plan", 1)
    add_heading(doc, "12.1 Required Deployment Outcome", 2)
    for item in [
        "Push source code to a GitHub repository.",
        "Deploy the web application to a public URL.",
        "Allow the instructor to open the URL without a GitHub account.",
        "Deploy PostgreSQL to the cloud instead of relying on localhost.",
        "Manage all sensitive values through environment variables.",
    ]:
        add_bullet(doc, item)
    add_heading(doc, "12.2 Suggested Cloud Setup", 2)
    add_table(
        doc,
        ["Component", "Option", "Notes"],
        [
            ["Frontend and Backend", "Render Web Service or Railway", "Suitable for a full-stack service."],
            ["Database", "Render PostgreSQL, Neon, or Supabase", "Provides a cloud DATABASE_URL."],
            ["Static Assets", "Public folder or image_url", "Exercise images can use public URLs in version 1.0."],
            ["GitHub", "Loisekoy repository", "Stores source code, README, schema, and migration files."],
        ],
        widths=[4.0, 5.0, 7.0],
    )
    add_heading(doc, "12.3 README Requirements", 2)
    for item in [
        "Project Description",
        "Database Design",
        "ER Diagram",
        "Installation",
        "Environment Variables",
        "Local Development",
        "Deployment",
        "Live Demo",
    ]:
        add_bullet(doc, item)

    add_heading(doc, "13. Database Course Highlights", 1)
    add_table(
        doc,
        ["Course Requirement", "How the Project Demonstrates It"],
        [
            ["Primary Key", "Every major table has a PK. user_body_parts uses a composite PK."],
            ["Foreign Key", "Users, exercises, plans, sessions, sets, and body records are connected through FK constraints."],
            ["1:N Relationship", "users -> workout_sessions and workout_sessions -> workout_sets."],
            ["M:N Relationship", "users <-> body_parts through user_body_parts."],
            ["Normalization", "Goals, body parts, exercises, authentication, sessions, and records are separated and satisfy 3NF."],
            ["CRUD", "Users, exercises, plans, sessions, sets, and body records support create, read, update, and delete cases."],
            ["JOIN", "Workout History joins sessions, sets, exercises, and body parts."],
            ["GROUP BY", "Weekly volume, most trained body part, and most used exercise require GROUP BY."],
            ["Aggregate Functions", "SUM, COUNT, and AVG support dashboard statistics."],
            ["Indexes", "Indexes support login, history, and common filtering queries."],
            ["Data Ownership", "All personal records are scoped by user_id."],
        ],
        widths=[4.8, 11.2],
    )

    add_heading(doc, "14. Conclusion", 1)
    add_p(doc, "Fitness Tracking Management System is a database-centered full-stack web application for a Database Systems course project. Its core value is the relational database design that connects users, authentication, goals, body parts, exercises, workout plans, workout sessions, workout sets, and body records. The design demonstrates primary keys, foreign keys, one-to-many relationships, many-to-many relationships, normalization, CRUD, JOIN, GROUP BY, aggregate functions, indexing, and data ownership.")
    add_p(doc, "The final implementation can use this specification as the reference for schema design, API behavior, dashboard queries, deployment, and project documentation.")

    doc.core_properties.title = "Fitness Tracking Management System SRS"
    doc.core_properties.subject = "Database Systems Course Project"
    doc.core_properties.author = "Loise"
    doc.core_properties.comments = "Formal SRS report generated for a database systems project."
    doc.save(OUT_DOCX)
    set_update_fields_on_open(OUT_DOCX)
    return OUT_DOCX


if __name__ == "__main__":
    print(build_document())
