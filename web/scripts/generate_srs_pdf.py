from __future__ import annotations

from datetime import date
from html import escape
from pathlib import Path
from textwrap import wrap

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    LongTable,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path("/Users/loise/Documents/資料庫")
OUT_DIR = ROOT / "output" / "pdf"
IMG_DIR = ROOT / "output" / "specification" / "images"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT = OUT_DIR / "Fitness_Tracking_Management_System_SRS.pdf"

FONT_PATH = Path("/Library/Fonts/Arial Unicode.ttf")
if not FONT_PATH.exists():
    raise FileNotFoundError(f"Missing CJK font: {FONT_PATH}")

pdfmetrics.registerFont(TTFont("SRS-CJK", str(FONT_PATH)))
pdfmetrics.registerFont(TTFont("SRS-CJK-Bold", str(FONT_PATH)))


styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="SRSNormal",
        fontName="SRS-CJK",
        fontSize=10.5,
        leading=16,
        alignment=TA_LEFT,
        spaceAfter=6,
    )
)
styles.add(
    ParagraphStyle(
        name="SRSTitle",
        fontName="SRS-CJK-Bold",
        fontSize=26,
        leading=34,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#2F3A45"),
        spaceAfter=16,
    )
)
styles.add(
    ParagraphStyle(
        name="SRSSubtitle",
        fontName="SRS-CJK",
        fontSize=13,
        leading=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#536878"),
        spaceAfter=8,
    )
)
styles.add(
    ParagraphStyle(
        name="SRSH1",
        fontName="SRS-CJK-Bold",
        fontSize=18,
        leading=24,
        textColor=colors.HexColor("#2F3A45"),
        spaceBefore=8,
        spaceAfter=10,
    )
)
styles.add(
    ParagraphStyle(
        name="SRSH2",
        fontName="SRS-CJK-Bold",
        fontSize=14,
        leading=20,
        textColor=colors.HexColor("#536878"),
        spaceBefore=6,
        spaceAfter=7,
    )
)
styles.add(
    ParagraphStyle(
        name="SRSH3",
        fontName="SRS-CJK-Bold",
        fontSize=12,
        leading=17,
        textColor=colors.HexColor("#2D3748"),
        spaceBefore=4,
        spaceAfter=5,
    )
)
styles.add(
    ParagraphStyle(
        name="SRSSmall",
        fontName="SRS-CJK",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#4A5568"),
        wordWrap="CJK",
    )
)
styles.add(
    ParagraphStyle(
        name="SRSCode",
        fontName="Courier",
        fontSize=8.2,
        leading=11.5,
        backColor=colors.HexColor("#F7FAFC"),
        borderColor=colors.HexColor("#CBD5E0"),
        borderWidth=0.4,
        borderPadding=5,
        wordWrap="CJK",
    )
)
styles.add(
    ParagraphStyle(
        name="SRSCaption",
        fontName="SRS-CJK",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#718096"),
        alignment=TA_CENTER,
        spaceAfter=6,
    )
)
styles.add(
    ParagraphStyle(
        name="SRSTH",
        fontName="SRS-CJK-Bold",
        fontSize=8.6,
        leading=11.5,
        textColor=colors.white,
        wordWrap="CJK",
    )
)
styles.add(
    ParagraphStyle(
        name="SRSTD",
        fontName="SRS-CJK",
        fontSize=8.1,
        leading=11.2,
        wordWrap="CJK",
    )
)


def P(text: str, style: str = "SRSNormal") -> Paragraph:
    return Paragraph(escape(text).replace("\n", "<br/>"), styles[style])


def H1(text: str) -> Paragraph:
    return P(text, "SRSH1")


def H2(text: str) -> Paragraph:
    return P(text, "SRSH2")


def H3(text: str) -> Paragraph:
    return P(text, "SRSH3")


def bullet(items: list[str]) -> list[Paragraph]:
    return [P(f"• {item}") for item in items]


def code_block(text: str) -> Paragraph:
    lines: list[str] = []
    for raw_line in text.strip("\n").splitlines():
        if len(raw_line) <= 92:
            lines.append(raw_line)
        else:
            lines.extend(wrap(raw_line, width=92, subsequent_indent="    "))
    pre = Preformatted("\n".join(lines), styles["SRSCode"])
    t = Table([[pre]], colWidths=[16.0 * cm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F6F7")),
                ("BOX", (0, 0), (-1, -1), 0.35, colors.HexColor("#D9DEE5")),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return t


def table(
    headers: list[str],
    rows: list[list[str]],
    col_widths: list[float],
    repeat_rows: int = 1,
    font_size: float = 8.1,
) -> LongTable:
    data = [[P(h, "SRSTH") for h in headers]]
    for row in rows:
        data.append([P(cell, "SRSTD") for cell in row])
    t = LongTable(data, colWidths=col_widths, repeatRows=repeat_rows, splitByRow=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#44546A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "SRS-CJK-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "SRS-CJK"),
                ("FONTSIZE", (0, 0), (-1, -1), font_size),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def static_table(rows: list[list[str]], col_widths: list[float]) -> Table:
    data = [[P(cell, "SRSTD") for cell in row] for row in rows]
    t = Table(data, colWidths=col_widths)
    t.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E0")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EDF2F7")),
                ("FONTNAME", (0, 0), (0, -1), "SRS-CJK-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return t


def scaled_image(path: Path, max_width: float, max_height: float) -> Image:
    img = Image(str(path))
    ratio = min(max_width / img.imageWidth, max_height / img.imageHeight)
    img.drawWidth = img.imageWidth * ratio
    img.drawHeight = img.imageHeight * ratio
    img.hAlign = "CENTER"
    return img


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("SRS-CJK", 8)
    canvas.setFillColor(colors.HexColor("#718096"))
    canvas.drawString(1.6 * cm, 1.0 * cm, "Fitness Tracking Management System SRS")
    canvas.drawRightString(A4[0] - 1.6 * cm, 1.0 * cm, f"Page {doc.page}")
    canvas.restoreState()


story = []

story.append(Spacer(1, 1.5 * cm))
story.append(P("Fitness Tracking Management System", "SRSTitle"))
story.append(P("健身紀錄管理系統 — Software Requirements Specification", "SRSSubtitle"))
story.append(Spacer(1, 0.7 * cm))
story.append(
    static_table(
        [
            ["文件用途", "大學「資料庫系統」課程專題規格書"],
            ["專題重點", "資料庫設計、關聯式資料模型、CRUD、SQL 查詢、訓練紀錄管理與統計分析"],
            ["系統類型", "Full-stack Database Web Application"],
            ["版本", "Version 1.0"],
            ["日期", date.today().isoformat()],
        ],
        [4.0 * cm, 11.8 * cm],
    )
)
story.append(Spacer(1, 1 * cm))
story.append(
    P(
        "本文件定義 Fitness Tracking Management System 的需求、資料庫設計、ER Diagram、資料表欄位、"
        "Primary Key / Foreign Key、Relationship、Normalization、核心 SQL 查詢與驗收標準。"
        "本專題以資料庫系統為核心，網站功能與介面皆圍繞資料建立、資料查詢、資料更新、資料刪除、"
        "資料關聯、統計與管理而設計。",
    )
)
story.append(PageBreak())

story.append(H1("文件目錄"))
for item in [
    "1. Project Overview 專案概述",
    "2. System Architecture and Tech Stack 系統架構與技術",
    "3. User Flow 使用者流程",
    "4. Functional Requirements 功能需求",
    "5. Database Design and ER Diagram 資料庫設計與 ERD",
    "6. Data Dictionary 資料表規格",
    "7. PK / FK / Relationships and 3NF",
    "8. SQL Query Requirements",
    "9. Workout Recommendation Algorithm",
    "10. Non-Functional Requirements",
    "11. Acceptance Test Cases",
    "12. Environment Variables and Deployment",
    "13. Database Course Highlights",
]:
    story.append(P(item))
story.append(PageBreak())

story.append(H1("1. Project Overview 專案概述"))
story.append(H2("1.1 Project Background 開發背景"))
story.append(
    P(
        "開發者目前本身有健身習慣，但每次到健身房時，常常不知道當天應該安排哪些訓練動作、"
        "該訓練哪些身體部位，以及重量與次數要如何記錄。若每次都臨時上網查資料或詢問 AI，"
        "不但流程不方便，也會讓訓練紀錄分散在不同地方，難以長期追蹤進步。"
    )
)
story.append(
    P(
        "因此，本專題希望建立一套整合「健身目標設定、訓練課表規劃、開始運動、每組訓練紀錄、"
        "歷史紀錄查詢、訓練量統計與體重變化追蹤」的資料庫系統。系統透過資料庫保存使用者、"
        "身體部位、動作、課表、實際訓練 Session、每組 Set 與 Body Records，並透過 SQL 查詢產生"
        " Workout History、Training Volume、最常訓練部位等統計資訊。"
    )
)
story.append(H2("1.2 Problem Statement 問題描述"))
story.extend(
    bullet(
        [
            "健身者常不知道今天該做哪些動作，臨時查詢會降低訓練效率。",
            "紙本或備忘錄紀錄缺乏結構化資料，不容易查詢、統計與分析。",
            "若沒有使用者帳號與資料擁有權，無法長期保存個人訓練與身體資料。",
            "健身動作、身體部位、課表與訓練紀錄之間具有明確關聯，適合用關聯式資料庫設計。",
        ]
    )
)
story.append(H2("1.3 Project Goals 專案目標"))
story.extend(
    bullet(
        [
            "提供註冊、登入、登出功能，讓每位使用者管理自己的健身資料。",
            "建立正規化的關聯式資料庫，清楚呈現 PK、FK、1:N 與 M:N 關係。",
            "支援使用者基本資料、健身目標、想加強部位、Exercise Database、Workout Plan、Workout Session、Workout Set 與 Body Records 管理。",
            "提供 Create、Read、Update、Delete、Search、JOIN、GROUP BY、Aggregate Functions 等資料庫功能。",
            "提供「開始運動」按鈕，將課表轉成實際 Workout Session，並即時保存每一組 Weight / Reps。",
            "提供 Dashboard、Workout History、Training Volume、Body Weight History 與常用 Exercise 統計。",
            "可部署至公開網址，資料庫部署於雲端，不依賴 localhost。",
        ]
    )
)
story.append(H2("1.4 Scope 範圍"))
story.append(
    P(
        "第一版系統會實作完整登入註冊、資料庫 CRUD、課表產生、開始運動、訓練紀錄與統計 Dashboard。"
        "推薦課表可先使用資料庫資料加上 Rule-Based Algorithm；若未來需要，可保留 LLM API 介面，"
        "但本專題核心仍是資料庫設計與資料管理，不會把資料庫需求簡化成只依賴外部 AI。"
    )
)
story.append(H2("1.5 Email Validation Policy"))
story.append(
    P(
        "第一版註冊功能會要求 Email 欄位不可為空、格式正確且不可重複，並透過 users.email 的 UNIQUE "
        "constraint 確保帳號唯一性。第一版不寄送 Email verification 信，原因是寄信驗證會增加第三方 "
        "Email service、verification token、token expiry、resend flow 與信件錯誤處理，會讓專題範圍變大。"
        "本課程專題重點是資料庫系統，因此第一版優先完成 account data design、password_hash、PK/FK、"
        "資料關聯、訓練紀錄與統計查詢。資料庫會預留 email_verified 與 email_verified_at 欄位，方便未來擴充。"
    )
)
story.append(PageBreak())

story.append(H1("2. System Architecture and Tech Stack 系統架構與技術"))
story.append(H2("2.1 Recommended Architecture"))
story.append(
    P(
        "系統建議採用前後端分離或輕量 full-stack 架構。Frontend 負責表單、課表、開始運動、紀錄與 Dashboard；"
        "Backend 負責 authentication、business logic、recommendation algorithm、SQL query 與資料驗證；"
        "PostgreSQL 負責保存所有結構化資料。"
    )
)
arch = IMG_DIR / "architecture-formal.png"
if arch.exists():
    story.append(scaled_image(arch, 15.5 * cm, 8.2 * cm))
    story.append(P("Figure 1. System Architecture", "SRSCaption"))
story.append(H2("2.2 Suggested Tech Stack"))
story.append(
    table(
        ["Layer", "Recommended Technology", "Purpose"],
        [
            ["Frontend", "React / Next.js / Vite", "建立使用者介面、表單、Dashboard、Workout Tracking 頁面。"],
            ["Backend", "Node.js Express 或 Python FastAPI", "處理 API、登入驗證、資料庫操作、推薦演算法。"],
            ["Database", "PostgreSQL", "雲端關聯式資料庫，支援 FK、JOIN、GROUP BY、Aggregate、Index。"],
            ["ORM / Query", "Prisma / SQLAlchemy / raw SQL", "管理 schema migration 與資料庫操作。課程展示可保留重要 raw SQL。"],
            ["Deployment", "Render / Railway / Supabase / Neon / Vercel", "部署公開網址與雲端資料庫。"],
            ["Security", "bcrypt / argon2, JWT or secure session", "密碼雜湊與登入狀態管理。"],
        ],
        [3 * cm, 5 * cm, 8 * cm],
    )
)
story.append(H2("2.3 High-Level Data Flow"))
story.extend(
    bullet(
        [
            "User 在 Frontend 註冊或登入。",
            "Backend 驗證 Email、Password，並建立 Session 或 JWT。",
            "User 設定個人資料、健身目標、想加強部位與每週訓練天數。",
            "Backend 從 exercises、body_parts、training_goals 讀取候選資料並產生 workout_plans。",
            "User 點擊「開始運動」後，Backend 建立 workout_sessions。",
            "每完成一組，Frontend 呼叫 API 將 weight、reps、set_number 寫入 workout_sets。",
            "Dashboard 透過 JOIN、GROUP BY、SUM、COUNT、AVG 查詢統計結果。",
        ]
    )
)
story.append(PageBreak())

story.append(H1("3. User Flow 使用者流程"))
story.append(H2("3.1 Main Flow"))
story.append(
    code_block(
        """
進入網站
  ↓
註冊 / 登入
  ↓
建立或更新基本資料
  ↓
選擇 Training Goal
  ↓
選擇想加強的 Body Parts
  ↓
選擇每週訓練天數與每次訓練時間
  ↓
系統根據資料庫 Exercise + Rule-Based Algorithm 產生 Workout Plan
  ↓
查看每日課表與每個動作的說明 / 圖片參考
  ↓
點擊「開始運動」
  ↓
建立 workout_sessions 狀態為 in_progress
  ↓
每完成一組立即新增 workout_sets
  ↓
完成訓練後把 workout_sessions 更新為 completed
  ↓
查看 Workout History / Training Volume / Body Weight History
        """
    )
)
story.append(H2("3.2 Start Workout Button 行為"))
story.extend(
    bullet(
        [
            "使用者在課表日頁面點擊「開始運動」。",
            "系統根據 user_id、plan_day_id 建立一筆 workout_sessions。",
            "workout_sessions.status 初始值為 in_progress。",
            "頁面顯示當天所有 plan_exercises，使用者可輸入每組 weight 與 reps。",
            "每按一次「儲存本組」，就新增一筆 workout_sets。",
            "使用者按「完成訓練」後，workout_sessions.status 改為 completed，ended_at 記錄完成時間。",
            "若使用者中途離開，系統仍能從 in_progress session 回復未完成訓練。",
        ]
    )
)
story.append(H2("3.3 Roles"))
story.append(
    table(
        ["Role", "Description", "Main Permissions"],
        [
            ["Guest", "尚未登入使用者", "可查看首頁、註冊、登入。"],
            ["User", "一般健身使用者", "管理自己的 profile、目標、課表、訓練紀錄與體重紀錄。"],
            ["Admin", "系統管理者", "管理 exercise database、body_parts、training_goals 與必要的資料維護。"],
        ],
        [3 * cm, 5 * cm, 8 * cm],
    )
)
story.append(PageBreak())

story.append(H1("4. Functional Requirements 功能需求"))
functional_rows = [
    ["FR-01", "Register", "使用者可以使用 name、email、password 建立帳號。系統必須檢查 email 格式、唯一性與 password 強度。"],
    ["FR-02", "Login / Logout", "使用者可以登入系統，系統建立 user session；使用者也可以登出並使 session 失效。"],
    ["FR-03", "Profile Management", "使用者可建立與更新年齡、性別、身高、體重、訓練經驗。"],
    ["FR-04", "Training Goal", "使用者可選擇 Muscle Gain、Fat Loss、Strength、General Fitness。"],
    ["FR-05", "Preferred Body Parts", "使用者可選擇多個想加強部位，使用 M:N junction table user_body_parts。"],
    ["FR-06", "Exercise Database", "系統保存 exercise_name、body_part、difficulty、equipment、description、image_url。"],
    ["FR-07", "Generate Workout Plan", "根據使用者目標、經驗、部位、天數與時間，自動產生 workout plan、plan days 與 plan exercises。"],
    ["FR-08", "View Workout Plan", "使用者可查看每天的訓練主題、動作、組數、次數、休息秒數與圖片參考。"],
    ["FR-09", "Start Workout", "使用者可點擊開始運動，建立 workout_sessions 並開始逐組紀錄。"],
    ["FR-10", "Record Sets", "使用者可紀錄每組 exercise、set_number、weight、reps、是否完成。"],
    ["FR-11", "Workout History", "使用者可查詢歷史訓練日期、動作、重量、次數、組數與訓練量。"],
    ["FR-12", "Dashboard", "系統顯示總訓練量、每週訓練次數、最常訓練部位、最常使用 exercise、體重趨勢。"],
    ["FR-13", "Body Records", "使用者可新增與查詢體重紀錄，支援 body weight history chart。"],
    ["FR-14", "Search", "使用者可搜尋 exercise、body part、workout history。"],
    ["FR-15", "Admin Management", "管理者可新增、修改、刪除 exercises、body parts 與 training goals。"],
]
story.append(table(["ID", "Feature", "Requirement"], functional_rows, [1.6 * cm, 4 * cm, 10.5 * cm]))
story.append(H2("4.1 CRUD Mapping"))
story.append(
    table(
        ["Entity", "Create", "Read", "Update", "Delete"],
        [
            ["users", "Register", "Profile", "Edit profile", "Deactivate account"],
            ["training_goals", "Admin", "Goal options", "Admin edit", "Admin delete / deactivate"],
            ["body_parts", "Admin", "Body part list", "Admin edit", "Admin delete / deactivate"],
            ["user_body_parts", "Select body parts", "User preferences", "Replace preferences", "Remove preference"],
            ["exercises", "Admin create", "Exercise list/search", "Admin edit", "Admin delete / deactivate"],
            ["workout_plans", "Generate plan", "Plan detail", "Regenerate / rename", "Delete plan"],
            ["workout_sessions", "Start workout", "Workout history", "Complete / cancel", "Delete own session"],
            ["workout_sets", "Save set", "Set history", "Edit weight/reps", "Delete set"],
            ["body_records", "Add record", "Weight history", "Edit record", "Delete record"],
        ],
        [3.3 * cm, 3.2 * cm, 3.2 * cm, 3.2 * cm, 3.2 * cm],
    )
)
story.append(PageBreak())

story.append(H1("5. Database Design and ER Diagram 資料庫設計與 ERD"))
story.append(H2("5.1 Database Design Principles"))
story.extend(
    bullet(
        [
            "所有重要資料皆儲存在 PostgreSQL，不依賴 localStorage 或 localhost-only database。",
            "每個資料表都有 Primary Key。",
            "跨表關係使用 Foreign Key，確保 referential integrity。",
            "使用 junction table 表達 M:N 關係，例如 user_body_parts。",
            "避免把多個值直接塞入 VARCHAR，例如不可把 Chest, Back, Legs 存在 users.preferred_parts。",
            "將 authentication 資料拆分到 user_auth，避免 password_hash 與一般 profile 混在一起。",
            "所有與使用者相關的資料必須包含 user_id，確保資料擁有權與查詢範圍。",
        ]
    )
)
erd = IMG_DIR / "erd-formal.png"
if erd.exists():
    story.append(scaled_image(erd, 16.2 * cm, 19.0 * cm))
    story.append(P("Figure 2. Entity Relationship Diagram", "SRSCaption"))
story.append(PageBreak())

story.append(H2("5.2 Entities Overview"))
entity_rows = [
    ["users", "保存使用者基本資料與 profile。"],
    ["user_auth", "保存登入用 email、password_hash、email 驗證狀態。"],
    ["user_sessions", "保存登入 session、過期時間與撤銷狀態。"],
    ["training_goals", "保存健身目標 master data。"],
    ["body_parts", "保存身體部位 master data。"],
    ["user_body_parts", "User 與 Body Part 的 M:N junction table。"],
    ["exercises", "保存動作資料、難度、器材、圖片與說明。"],
    ["workout_plans", "保存使用者產生的訓練計畫。"],
    ["plan_days", "保存課表中的第幾天與當日訓練主題。"],
    ["plan_exercises", "保存每天安排哪些 exercise、組數、次數、休息時間。"],
    ["workout_sessions", "保存一次實際訓練紀錄，對應開始運動後的 session。"],
    ["workout_sets", "保存實際完成的每一組 weight / reps。"],
    ["body_records", "保存體重與身體紀錄。"],
    ["admins", "保存管理者權限資料。"],
]
story.append(table(["Table", "Purpose"], entity_rows, [4.5 * cm, 11.5 * cm]))

story.append(H2("5.3 Relationships"))
relationship_rows = [
    ["users 1:1 user_auth", "每位使用者一組登入憑證。"],
    ["users 1:N user_sessions", "一位使用者可以有多次登入 session。"],
    ["training_goals 1:N users", "多位使用者可以選同一個目標。"],
    ["users M:N body_parts", "透過 user_body_parts 表達多選加強部位。"],
    ["body_parts 1:N exercises", "一個 body part 可對應多個 exercises。"],
    ["users 1:N workout_plans", "一位使用者可產生多份課表。"],
    ["workout_plans 1:N plan_days", "一份課表包含多個訓練日。"],
    ["plan_days 1:N plan_exercises", "一天課表包含多個動作。"],
    ["exercises 1:N plan_exercises", "一個動作可以被安排到多份課表。"],
    ["users 1:N workout_sessions", "一位使用者有多次實際訓練。"],
    ["workout_sessions 1:N workout_sets", "一次訓練包含多組 set 紀錄。"],
    ["exercises 1:N workout_sets", "每組紀錄都對應一個 exercise。"],
    ["users 1:N body_records", "一位使用者可保存多筆體重紀錄。"],
]
story.append(table(["Relationship", "Explanation"], relationship_rows, [5.5 * cm, 10.5 * cm]))
story.append(PageBreak())

story.append(H1("6. Data Dictionary 資料表規格"))

tables = {
    "users": [
        ["user_id", "BIGSERIAL", "PK", "系統產生的使用者 ID。"],
        ["name", "VARCHAR(100)", "NOT NULL", "使用者名稱。"],
        ["gender", "VARCHAR(20)", "CHECK optional", "性別，可選填。"],
        ["age", "INT", "CHECK age BETWEEN 10 AND 100", "年齡。"],
        ["height_cm", "NUMERIC(5,2)", "CHECK > 0", "身高公分。"],
        ["weight_kg", "NUMERIC(5,2)", "CHECK > 0", "目前體重公斤。"],
        ["training_experience", "VARCHAR(20)", "CHECK Beginner/Intermediate/Advanced", "訓練經驗。"],
        ["training_goal_id", "BIGINT", "FK -> training_goals", "主要訓練目標。"],
        ["training_days_per_week", "INT", "CHECK BETWEEN 2 AND 6", "每週訓練天數。"],
        ["training_duration_minutes", "INT", "CHECK IN 30/60/90", "每次訓練時間。"],
        ["created_at", "TIMESTAMP", "DEFAULT now()", "建立時間。"],
        ["updated_at", "TIMESTAMP", "DEFAULT now()", "更新時間。"],
    ],
    "user_auth": [
        ["auth_id", "BIGSERIAL", "PK", "登入資料 ID。"],
        ["user_id", "BIGINT", "FK UNIQUE -> users", "一對一連到 users。"],
        ["email", "VARCHAR(255)", "NOT NULL UNIQUE", "登入 Email。"],
        ["password_hash", "VARCHAR(255)", "NOT NULL", "雜湊後密碼，不存明文。"],
        ["email_verified", "BOOLEAN", "DEFAULT FALSE", "第一版預留，不寄驗證信。"],
        ["email_verified_at", "TIMESTAMP", "NULL", "未來 email 驗證完成時間。"],
        ["last_login_at", "TIMESTAMP", "NULL", "最近登入時間。"],
        ["created_at", "TIMESTAMP", "DEFAULT now()", "建立時間。"],
    ],
    "user_sessions": [
        ["session_id", "BIGSERIAL", "PK", "登入 session ID。"],
        ["user_id", "BIGINT", "FK -> users", "所屬使用者。"],
        ["session_token_hash", "VARCHAR(255)", "UNIQUE NOT NULL", "Session token 的 hash。"],
        ["expires_at", "TIMESTAMP", "NOT NULL", "到期時間。"],
        ["revoked_at", "TIMESTAMP", "NULL", "登出或撤銷時間。"],
        ["created_at", "TIMESTAMP", "DEFAULT now()", "建立時間。"],
    ],
    "training_goals": [
        ["training_goal_id", "BIGSERIAL", "PK", "訓練目標 ID。"],
        ["goal_name", "VARCHAR(50)", "UNIQUE NOT NULL", "Muscle Gain / Fat Loss / Strength / General Fitness。"],
        ["description", "TEXT", "NULL", "目標描述。"],
    ],
    "body_parts": [
        ["body_part_id", "BIGSERIAL", "PK", "身體部位 ID。"],
        ["body_part_name", "VARCHAR(50)", "UNIQUE NOT NULL", "Chest / Back / Legs 等。"],
        ["description", "TEXT", "NULL", "部位描述。"],
    ],
    "user_body_parts": [
        ["user_id", "BIGINT", "PK, FK -> users", "使用者 ID。"],
        ["body_part_id", "BIGINT", "PK, FK -> body_parts", "想加強部位 ID。"],
        ["priority", "INT", "DEFAULT 1", "偏好優先順序。"],
        ["created_at", "TIMESTAMP", "DEFAULT now()", "建立時間。"],
    ],
    "exercises": [
        ["exercise_id", "BIGSERIAL", "PK", "動作 ID。"],
        ["exercise_name", "VARCHAR(120)", "UNIQUE NOT NULL", "動作名稱。"],
        ["body_part_id", "BIGINT", "FK -> body_parts", "主要訓練部位。"],
        ["difficulty_level", "VARCHAR(20)", "CHECK Beginner/Intermediate/Advanced", "難度。"],
        ["equipment", "VARCHAR(100)", "NULL", "器材。"],
        ["description", "TEXT", "NULL", "動作說明。"],
        ["image_url", "TEXT", "NULL", "參考圖片網址。"],
        ["is_active", "BOOLEAN", "DEFAULT TRUE", "是否啟用。"],
    ],
    "workout_plans": [
        ["workout_plan_id", "BIGSERIAL", "PK", "課表 ID。"],
        ["user_id", "BIGINT", "FK -> users", "課表擁有者。"],
        ["plan_name", "VARCHAR(120)", "NOT NULL", "課表名稱。"],
        ["training_goal_id", "BIGINT", "FK -> training_goals", "產生課表時的目標。"],
        ["days_per_week", "INT", "CHECK BETWEEN 2 AND 6", "每週天數。"],
        ["duration_minutes", "INT", "CHECK IN 30/60/90", "每次時間。"],
        ["generated_by", "VARCHAR(30)", "DEFAULT rule_based", "rule_based 或 future_llm。"],
        ["created_at", "TIMESTAMP", "DEFAULT now()", "建立時間。"],
    ],
    "plan_days": [
        ["plan_day_id", "BIGSERIAL", "PK", "課表日 ID。"],
        ["workout_plan_id", "BIGINT", "FK -> workout_plans", "所屬課表。"],
        ["day_number", "INT", "NOT NULL", "第幾天。"],
        ["day_title", "VARCHAR(120)", "NOT NULL", "例如 Chest + Triceps。"],
        ["focus_notes", "TEXT", "NULL", "當日重點說明。"],
    ],
    "plan_exercises": [
        ["plan_exercise_id", "BIGSERIAL", "PK", "課表動作 ID。"],
        ["plan_day_id", "BIGINT", "FK -> plan_days", "所屬課表日。"],
        ["exercise_id", "BIGINT", "FK -> exercises", "安排的動作。"],
        ["exercise_order", "INT", "NOT NULL", "動作順序。"],
        ["target_sets", "INT", "NOT NULL", "建議組數。"],
        ["target_reps", "VARCHAR(30)", "NOT NULL", "建議次數，例如 8-12。"],
        ["target_weight_note", "VARCHAR(120)", "NULL", "重量建議。"],
        ["rest_seconds", "INT", "DEFAULT 60", "組間休息秒數。"],
    ],
    "workout_sessions": [
        ["workout_session_id", "BIGSERIAL", "PK", "實際訓練 session ID。"],
        ["user_id", "BIGINT", "FK -> users", "訓練者。"],
        ["workout_plan_id", "BIGINT", "FK -> workout_plans NULL", "可由課表開始，也可自由訓練。"],
        ["plan_day_id", "BIGINT", "FK -> plan_days NULL", "對應哪一天課表。"],
        ["session_date", "DATE", "DEFAULT CURRENT_DATE", "訓練日期。"],
        ["started_at", "TIMESTAMP", "DEFAULT now()", "開始時間。"],
        ["ended_at", "TIMESTAMP", "NULL", "完成時間。"],
        ["status", "VARCHAR(20)", "CHECK in_progress/completed/cancelled", "訓練狀態。"],
        ["notes", "TEXT", "NULL", "訓練備註。"],
    ],
    "workout_sets": [
        ["workout_set_id", "BIGSERIAL", "PK", "每組紀錄 ID。"],
        ["workout_session_id", "BIGINT", "FK -> workout_sessions", "所屬訓練 session。"],
        ["exercise_id", "BIGINT", "FK -> exercises", "所屬動作。"],
        ["set_number", "INT", "NOT NULL", "第幾組。"],
        ["weight_kg", "NUMERIC(6,2)", "CHECK >= 0", "重量公斤。"],
        ["reps", "INT", "CHECK > 0", "次數。"],
        ["volume", "NUMERIC(10,2)", "Generated or computed", "weight_kg * reps。"],
        ["completed_at", "TIMESTAMP", "DEFAULT now()", "完成時間。"],
    ],
    "body_records": [
        ["body_record_id", "BIGSERIAL", "PK", "身體紀錄 ID。"],
        ["user_id", "BIGINT", "FK -> users", "所屬使用者。"],
        ["record_date", "DATE", "NOT NULL", "紀錄日期。"],
        ["weight_kg", "NUMERIC(5,2)", "CHECK > 0", "體重。"],
        ["body_fat_percentage", "NUMERIC(5,2)", "NULL", "體脂率，可選。"],
        ["notes", "TEXT", "NULL", "備註。"],
        ["created_at", "TIMESTAMP", "DEFAULT now()", "建立時間。"],
    ],
    "admins": [
        ["admin_id", "BIGSERIAL", "PK", "管理者 ID。"],
        ["user_id", "BIGINT", "FK UNIQUE -> users", "哪位 user 是 admin。"],
        ["role", "VARCHAR(50)", "DEFAULT admin", "admin 或 super_admin。"],
        ["created_at", "TIMESTAMP", "DEFAULT now()", "建立時間。"],
    ],
}

for table_name, rows in tables.items():
    story.append(H2(table_name))
    story.append(table(["Column", "Data Type", "Constraint", "Description"], rows, [3.4 * cm, 3.6 * cm, 4.4 * cm, 4.8 * cm]))

story.append(PageBreak())

story.append(H1("7. PK / FK / Relationships and 3NF"))
story.append(H2("7.1 Primary Keys"))
story.extend(
    bullet(
        [
            "每個主要 entity table 使用 BIGSERIAL 作為 surrogate primary key。",
            "user_body_parts 使用 composite primary key (user_id, body_part_id)，避免同一使用者重複選同一身體部位。",
            "workout_sets 使用 workout_set_id 作為 PK，方便逐組新增、修改與刪除。",
        ]
    )
)
story.append(H2("7.2 Foreign Keys"))
story.append(
    code_block(
        """
user_auth.user_id              -> users.user_id
user_sessions.user_id          -> users.user_id
users.training_goal_id         -> training_goals.training_goal_id
user_body_parts.user_id        -> users.user_id
user_body_parts.body_part_id   -> body_parts.body_part_id
exercises.body_part_id         -> body_parts.body_part_id
workout_plans.user_id          -> users.user_id
workout_plans.training_goal_id -> training_goals.training_goal_id
plan_days.workout_plan_id      -> workout_plans.workout_plan_id
plan_exercises.plan_day_id     -> plan_days.plan_day_id
plan_exercises.exercise_id     -> exercises.exercise_id
workout_sessions.user_id       -> users.user_id
workout_sessions.workout_plan_id -> workout_plans.workout_plan_id
workout_sessions.plan_day_id   -> plan_days.plan_day_id
workout_sets.workout_session_id -> workout_sessions.workout_session_id
workout_sets.exercise_id       -> exercises.exercise_id
body_records.user_id           -> users.user_id
admins.user_id                 -> users.user_id
        """
    )
)
story.append(H2("7.3 Constraints"))
story.extend(
    bullet(
        [
            "users.age 限制合理範圍，避免錯誤資料。",
            "users.training_days_per_week 限制 2 至 6。",
            "users.training_duration_minutes 限制 30、60、90。",
            "user_auth.email 使用 UNIQUE，避免帳號重複。",
            "workout_sets.reps 必須大於 0，weight_kg 不可小於 0。",
            "workout_sessions.status 僅允許 in_progress、completed、cancelled。",
            "plan_exercises.target_sets 必須大於 0，exercise_order 用於排序。",
        ]
    )
)
story.append(H2("7.4 Indexes"))
story.append(
    table(
        ["Index", "Reason"],
        [
            ["idx_user_auth_email", "加速登入時用 email 查詢。"],
            ["idx_exercises_body_part_id", "加速依身體部位搜尋 exercise。"],
            ["idx_workout_sessions_user_date", "加速查詢使用者歷史訓練。"],
            ["idx_workout_sets_session_id", "加速查詢某次訓練的所有 sets。"],
            ["idx_body_records_user_date", "加速體重歷史查詢。"],
            ["idx_plan_days_plan_day_number", "加速課表日排序。"],
        ],
        [6 * cm, 10 * cm],
    )
)
story.append(H2("7.5 3NF Normalization 說明"))
story.extend(
    bullet(
        [
            "1NF：所有欄位皆為 atomic values；多個 body parts 不存在同一個欄位，而是使用 user_body_parts。",
            "2NF：複合主鍵表 user_body_parts 中的非鍵欄位 priority 依賴整個 composite key。",
            "3NF：training goal、body part、exercise 分離成獨立資料表，避免 name 與 description 重複儲存在 users 或 workout records。",
            "Authentication 資料拆分為 user_auth，避免 users profile 中混入 password_hash 與登入狀態。",
            "實際訓練紀錄拆分為 workout_sessions 與 workout_sets，避免重複 session 資料並支援一對多關係。",
        ]
    )
)
story.append(PageBreak())

story.append(H1("8. SQL Query Requirements"))
story.append(H2("8.1 Create / Insert Example"))
story.append(
    code_block(
        """
INSERT INTO users
  (name, gender, age, height_cm, weight_kg, training_experience,
   training_goal_id, training_days_per_week, training_duration_minutes)
VALUES
  ('Loise', 'Female', 21, 160, 50, 'Beginner', 1, 4, 60);
        """
    )
)
story.append(H2("8.2 Read with JOIN: Workout History"))
story.append(
    code_block(
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
JOIN workout_sets wset ON ws.workout_session_id = wset.workout_session_id
JOIN exercises e ON wset.exercise_id = e.exercise_id
JOIN body_parts bp ON e.body_part_id = bp.body_part_id
WHERE ws.user_id = :user_id
ORDER BY ws.session_date DESC, e.exercise_name, wset.set_number;
        """
    )
)
story.append(H2("8.3 GROUP BY and Aggregate: Weekly Training Volume"))
story.append(
    code_block(
        """
SELECT
  DATE_TRUNC('week', ws.session_date) AS training_week,
  SUM(wset.weight_kg * wset.reps) AS weekly_volume,
  COUNT(DISTINCT ws.workout_session_id) AS workout_count
FROM workout_sessions ws
JOIN workout_sets wset ON ws.workout_session_id = wset.workout_session_id
WHERE ws.user_id = :user_id
  AND ws.status = 'completed'
GROUP BY DATE_TRUNC('week', ws.session_date)
ORDER BY training_week DESC;
        """
    )
)
story.append(H2("8.4 Most Trained Body Part"))
story.append(
    code_block(
        """
SELECT
  bp.body_part_name,
  COUNT(*) AS total_sets,
  SUM(wset.weight_kg * wset.reps) AS total_volume
FROM workout_sets wset
JOIN workout_sessions ws ON ws.workout_session_id = wset.workout_session_id
JOIN exercises e ON e.exercise_id = wset.exercise_id
JOIN body_parts bp ON bp.body_part_id = e.body_part_id
WHERE ws.user_id = :user_id
GROUP BY bp.body_part_name
ORDER BY total_sets DESC;
        """
    )
)
story.append(PageBreak())
story.append(H2("8.5 Body Weight History"))
story.append(
    code_block(
        """
SELECT record_date, weight_kg
FROM body_records
WHERE user_id = :user_id
ORDER BY record_date ASC;
        """
    )
)
story.append(H2("8.6 Search Exercises"))
story.append(
    code_block(
        """
SELECT e.exercise_id, e.exercise_name, bp.body_part_name, e.difficulty_level, e.equipment
FROM exercises e
JOIN body_parts bp ON bp.body_part_id = e.body_part_id
WHERE LOWER(e.exercise_name) LIKE LOWER('%' || :keyword || '%')
   OR LOWER(bp.body_part_name) LIKE LOWER('%' || :keyword || '%')
ORDER BY e.exercise_name;
        """
    )
)
story.append(PageBreak())

story.append(H1("9. Workout Recommendation Algorithm"))
story.append(H2("9.1 Algorithm Goal"))
story.append(
    P(
        "第一版不使用 AI API，改以資料庫資料與 Rule-Based Recommendation Algorithm 產生課表。"
        "演算法必須根據 training goal、training experience、preferred body parts、training days per week "
        "與 training duration 產生合理課表。使用者偏好的 body parts 會增加出現頻率，但仍不可完全忽略其他主要肌群。"
    )
)
story.append(H2("9.2 Rule-Based Logic"))
story.extend(
    bullet(
        [
            "依 training_experience 決定每個動作的 sets、reps、rest_seconds。",
            "Beginner 優先安排 Beginner 或少量 Intermediate exercises。",
            "Muscle Gain 使用 8-12 reps、較多 volume；Strength 使用 3-6 reps、較長休息；Fat Loss 使用 10-15 reps、較短休息；General Fitness 使用中等組數與次數。",
            "依 days_per_week 選擇 split，例如 2 days 全身、3 days Push/Pull/Legs、4 days Upper/Lower 或偏好部位加強、5-6 days 更細分。",
            "preferred body parts 增加該部位在 plan_days 中的出現頻率。",
            "每個 plan_day 根據 duration_minutes 限制 exercises 數量。",
        ]
    )
)
story.append(H2("9.3 Pseudocode"))
story.append(
    code_block(
        """
Input: user_id
1. Read user profile, training goal, experience, days_per_week, duration_minutes.
2. Read preferred body parts from user_body_parts.
3. Build weekly split according to days_per_week.
4. Add preferred body parts to split with higher frequency.
5. For each day:
   a. Query candidate exercises by body_part_id and difficulty_level.
   b. Select exercises by priority: matching preference, difficulty, equipment availability.
   c. Decide sets/reps/rest based on goal and experience.
   d. Insert plan_days and plan_exercises.
6. Return workout_plan_id and detailed plan.
        """
    )
)
story.append(H2("9.4 Example Output"))
story.append(
    table(
        ["Day", "Focus", "Exercises"],
        [
            ["Day 1", "Chest + Triceps", "Bench Press 3x10, Chest Press 3x12, Triceps Pushdown 3x12"],
            ["Day 2", "Back + Biceps", "Lat Pulldown 3x10, Seated Row 3x12, Bicep Curl 3x12"],
            ["Day 3", "Legs + Core", "Squat 3x10, Leg Press 3x12, Plank 3 sets"],
            ["Day 4", "Chest + Back", "Incline Press 3x10, Lat Pulldown 3x10, Cable Row 3x12"],
        ],
        [2.2 * cm, 4.1 * cm, 9.7 * cm],
    )
)
story.append(H2("9.5 Backend Validation"))
story.extend(
    bullet(
        [
            "產生課表前確認 user_id 存在且屬於登入使用者。",
            "確認 selected body_parts 都存在於 body_parts。",
            "確認 exercises 都是 active exercises。",
            "確認 plan_exercises.target_sets、target_reps、rest_seconds 合理。",
            "若未找到足夠候選 exercises，回傳清楚錯誤或使用 fallback body part。"
        ]
    )
)
story.append(PageBreak())

story.append(H1("10. Non-Functional Requirements 非功能需求"))
story.append(
    table(
        ["Category", "Requirement"],
        [
            ["Security", "密碼不可明文保存，必須使用 bcrypt 或 argon2 hash。API 必須確認使用者只能讀寫自己的資料。"],
            ["Privacy", "使用者資料、Email、訓練紀錄與體重紀錄不可公開給其他使用者。"],
            ["Performance", "常用查詢欄位需建立 index，例如 email、user_id、session_date、body_part_id。"],
            ["Reliability", "訓練過程每完成一組立即寫入資料庫，避免離開頁面導致紀錄遺失。"],
            ["Maintainability", "Schema migration、seed data、README 與 .env.example 必須清楚。"],
            ["Deployment", "Source code 放在 GitHub；Database 部署在 Cloud；公開網址不需要 GitHub 帳號即可使用。"],
            ["Environment Variables", "DATABASE_URL、SECRET_KEY、API KEY、Email service key 等敏感資料不得寫入 GitHub。"],
            ["Responsive UI", "手機與電腦皆可使用，尤其開始運動與輸入每組紀錄頁面要適合手機操作。"],
        ],
        [4 * cm, 12 * cm],
    )
)
story.append(H2("10.1 Environment Variables"))
story.append(
    code_block(
        """
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE
SECRET_KEY=replace-with-random-secret
JWT_EXPIRES_IN=7d
OPENAI_API_KEY=optional-future-llm-key
NODE_ENV=development
        """
    )
)
story.append(H2("10.2 GitHub Safety Rules"))
story.extend(
    bullet(
        [
            ".env 不可 commit。",
            "必須提供 .env.example 作為範本。",
            "DATABASE_URL、SECRET_KEY、API KEY、Password 不可直接寫入程式碼或 README。",
            "README 應說明如何設定環境變數，但不能放真實密碼。",
        ]
    )
)
story.append(PageBreak())

story.append(H1("11. Acceptance Test Cases 驗收測試"))
test_rows = [
    ["AT-01", "Register", "輸入合法 name、email、password。", "建立 users 與 user_auth，password 存為 hash。"],
    ["AT-02", "Duplicate Email", "使用已存在 email 註冊。", "系統拒絕並顯示 email already exists。"],
    ["AT-03", "Login", "使用正確 email/password 登入。", "建立有效 session 並進入 dashboard。"],
    ["AT-04", "Profile", "新增或修改 age、height、weight、experience。", "users 資料正確更新。"],
    ["AT-05", "Preferred Body Parts", "選擇 Chest、Back。", "user_body_parts 新增兩筆資料。"],
    ["AT-06", "Generate Plan", "Beginner、Muscle Gain、4 days、Chest+Back。", "建立 workout_plans、plan_days、plan_exercises。"],
    ["AT-07", "View Plan", "開啟課表頁。", "顯示 Day title、exercise、sets、reps、rest、image。"],
    ["AT-08", "Start Workout", "點擊開始運動。", "建立 workout_sessions 且 status 為 in_progress。"],
    ["AT-09", "Save Set", "輸入 Bench Press 60kg x 12。", "新增 workout_sets，volume 可由 weight*reps 計算。"],
    ["AT-10", "Complete Workout", "點擊完成訓練。", "workout_sessions.status 改成 completed 並寫入 ended_at。"],
    ["AT-11", "Workout History", "查詢歷史訓練。", "透過 JOIN 顯示日期、exercise、body part、sets、weight、reps。"],
    ["AT-12", "Training Volume", "查看 Dashboard。", "使用 SUM / GROUP BY 顯示每週訓練量。"],
    ["AT-13", "Weight History", "新增多筆體重紀錄。", "Body Weight History 按日期排序顯示。"],
    ["AT-14", "Admin Exercise CRUD", "管理者新增/修改 exercise。", "exercises 資料正確異動。"],
    ["AT-15", "Authorization", "User A 嘗試查 User B 資料。", "API 拒絕存取。"],
]
story.append(table(["ID", "Scenario", "Input / Action", "Expected Result"], test_rows, [1.5 * cm, 3.2 * cm, 5.1 * cm, 6.2 * cm]))
story.append(PageBreak())

story.append(H1("12. Deployment Plan 部署計畫"))
story.append(H2("12.1 Required Deployment Outcome"))
story.extend(
    bullet(
        [
            "系統程式碼 push 到 GitHub repository。",
            "Web application 部署到雲端並產生公開網址。",
            "老師取得網址後，不需要 GitHub 帳號即可直接測試。",
            "Database 必須部署到雲端 PostgreSQL，不可只存在 localhost。",
            "所有敏感資料透過 Environment Variables 管理。",
        ]
    )
)
story.append(H2("12.2 Suggested Cloud Setup"))
story.append(
    table(
        ["Component", "Option", "Notes"],
        [
            ["Frontend / Backend", "Render Web Service 或 Railway", "適合部署 full-stack service。"],
            ["Database", "Render PostgreSQL / Neon / Supabase", "提供雲端 DATABASE_URL。"],
            ["Static Assets", "public folder 或 image_url", "Exercise 圖片可先用公開圖片 URL。"],
            ["GitHub", "Loisekoy repository", "保存 source code、README、schema、migration。"],
        ],
        [4 * cm, 5 * cm, 7 * cm],
    )
)
story.append(H2("12.3 README Must Include"))
story.extend(
    bullet(
        [
            "Project Description",
            "Database Design",
            "ER Diagram",
            "Installation",
            "Environment Variables",
            "Local Development",
            "Deployment",
            "Live Demo",
        ]
    )
)
story.append(PageBreak())

story.append(H1("13. Database Course Highlights"))
story.append(
    table(
        ["Course Requirement", "How This Project Demonstrates It"],
        [
            ["Primary Key", "每個主要 table 都有 PK，junction table 使用 composite PK。"],
            ["Foreign Key", "users、exercises、plans、sessions、sets 之間使用 FK 維持資料完整性。"],
            ["1:N Relationship", "users -> workout_sessions；workout_sessions -> workout_sets。"],
            ["M:N Relationship", "users <-> body_parts 透過 user_body_parts。"],
            ["Normalization", "training_goals、body_parts、exercises、auth、sessions 分離，符合 3NF。"],
            ["CRUD", "users、exercises、plans、sessions、sets、body_records 都有 CRUD 情境。"],
            ["JOIN", "Workout History 與 Dashboard 需要 JOIN 多張表。"],
            ["GROUP BY", "每週訓練量、最常訓練部位、常用 exercise 都使用 GROUP BY。"],
            ["Aggregate Functions", "SUM(volume)、COUNT(session)、AVG(weight) 等。"],
            ["Indexes", "email、user_id、session_date、body_part_id 等欄位建立 index。"],
            ["Data Ownership", "所有個人資料依 user_id 限制查詢與修改。"],
        ],
        [5 * cm, 11 * cm],
    )
)
story.append(H1("14. Conclusion 結論"))
story.append(
    P(
        "Fitness Tracking Management System 不只是健身紀錄網站，而是一個以關聯式資料庫為核心的完整資料庫系統專題。"
        "系統透過使用者帳號、訓練目標、身體部位、Exercise Database、Workout Plan、Workout Session、Workout Set "
        "與 Body Records 建立完整資料模型，並展示 PK、FK、1:N、M:N、3NF、CRUD、JOIN、GROUP BY、Aggregate Functions "
        "與 Dashboard 統計查詢。此設計可支援後續實作、雲端部署與老師透過公開網址測試。"
    )
)


doc = SimpleDocTemplate(
    str(OUTPUT),
    pagesize=A4,
    rightMargin=1.6 * cm,
    leftMargin=1.6 * cm,
    topMargin=1.5 * cm,
    bottomMargin=1.5 * cm,
    title="Fitness Tracking Management System SRS",
    author="Loise",
)

doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUTPUT)
