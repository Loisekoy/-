from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image as RLImage,
    KeepTogether,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path("/Users/loise/Documents/資料庫")
OUT_DOCX = ROOT / "output/specification/Fitness_Tracking_Management_System_SRS_中文版.docx"
OUT_PDF = ROOT / "output/pdf/Fitness_Tracking_Management_System_SRS_中文版.pdf"
IMG_DIR = ROOT / "output/specification/images_zh"

FONT_CJK = "PingFang TC"
FONT_BODY = "Arial"
FONT_CODE = "Menlo"
PDF_FONT_PATH = Path("/Library/Fonts/Arial Unicode.ttf")
PDF_FONT_NAME = "ArialUnicode"

SLATE = "2F3A45"
SLATE_2 = "44546A"
MUTED = "5B6E7D"
GRID = "D6DCE2"
PALE = "F4F6F8"


FR_SECTIONS = [
    (
        "3.1 模組一：會員與權限管理 (Auth Module)",
        [
            (
                "使用者註冊",
                [
                    "觸發條件：使用者於前端點擊「註冊」按鈕。",
                    "輸入資料：Email (String)、密碼 (String，需符合基本複雜度規則)、姓名 (String)。",
                    "處理邏輯：檢查 Email 是否已被註冊；若已存在，回傳 HTTP 400 錯誤。密碼使用 bcrypt 進行雜湊處理，不儲存明文密碼。系統於 users 資料表新增使用者基本資料，並於 user_auth 資料表新增登入認證資料，預設角色為 USER。",
                    "輸出／回應：回傳 HTTP 201 Created、user_id 與 JWT Token。",
                ],
            ),
            (
                "使用者登入",
                [
                    "觸發條件：使用者於前端點擊「登入」按鈕。",
                    "輸入資料：Email (String)、密碼 (String)。",
                    "處理邏輯：根據 Email 查詢 user_auth 資料表，使用 bcrypt 比對輸入密碼與 password_hash。若驗證成功，產生包含 user_id 與 role 的 JWT Token，並可選擇於 user_sessions 新增登入紀錄。",
                    "輸出／回應：回傳 HTTP 200 OK、JWT Token 與使用者基本資料。",
                ],
            ),
            (
                "使用者登出",
                [
                    "觸發條件：使用者於前端點擊「登出」按鈕。",
                    "輸入資料：JWT Token。",
                    "處理邏輯：前端移除儲存在瀏覽器中的 Token；若系統有使用 user_sessions，則將該 session 標記為 revoked 或 expired。",
                    "輸出／回應：回傳 HTTP 200 OK 與登出成功訊息。",
                ],
            ),
        ],
    ),
    (
        "3.2 模組二：使用者基本資料管理 (User Profile Module)",
        [
            (
                "建立使用者基本資料",
                [
                    "觸發條件：使用者首次登入後，於前端填寫基本資料並點擊「儲存」。",
                    "輸入資料：姓名、性別、年齡、身高、體重、訓練經驗。",
                    "處理邏輯：驗證必填欄位是否完整，檢查年齡、身高與體重是否為合理正數，將資料寫入或更新 users 資料表，並使用 user_id 確保使用者只能修改自己的資料。",
                    "輸出／回應：回傳 HTTP 200 OK 與更新後的使用者基本資料。",
                ],
            ),
            (
                "查看與修改使用者基本資料",
                [
                    "觸發條件：使用者進入「個人資料」頁面或點擊「儲存修改」。",
                    "輸入資料：JWT Token，以及欲修改的姓名、性別、年齡、身高、體重與訓練經驗。",
                    "處理邏輯：從 JWT Token 取得 user_id，查詢或更新 users 資料表，不允許使用者查詢或修改其他人的資料。",
                    "輸出／回應：回傳 HTTP 200 OK 與查詢或修改成功訊息。",
                ],
            ),
        ],
    ),
    (
        "3.3 模組三：訓練目標與偏好部位管理 (Goal and Body Part Module)",
        [
            (
                "設定訓練目標與訓練時間",
                [
                    "觸發條件：使用者於設定流程中選擇訓練目標、每週訓練天數與每次訓練時間。",
                    "輸入資料：training_goal_id、training_days_per_week、training_duration_minutes。",
                    "處理邏輯：驗證 training_goal_id 是否存在於 training_goals，檢查每週訓練天數是否介於 2 至 6 天，並檢查每次訓練時間是否為 30、60 或 90 分鐘。驗證通過後更新 users 資料表。",
                    "輸出／回應：回傳 HTTP 200 OK 與設定成功訊息。",
                ],
            ),
            (
                "選擇想加強的身體部位",
                [
                    "觸發條件：使用者於設定流程中選擇一個或多個想加強的身體部位。",
                    "輸入資料：body_part_id List。",
                    "處理邏輯：驗證所有 body_part_id 是否存在於 body_parts。系統刪除該使用者原本的 user_body_parts 紀錄，再將新的 body_part_id List 逐筆寫入 user_body_parts。此表作為 users 與 body_parts 的 M:N junction table，不將多個身體部位存入同一個 VARCHAR 欄位。",
                    "輸出／回應：回傳 HTTP 200 OK 與偏好部位設定成功訊息。",
                ],
            ),
        ],
    ),
    (
        "3.4 模組四：Exercise Database 管理 (Exercise Module)",
        [
            (
                "查看與搜尋 Exercise",
                [
                    "觸發條件：使用者進入 Exercise Database 頁面或輸入搜尋條件。",
                    "輸入資料：keyword、body_part_id、difficulty_level 等可選條件。",
                    "處理邏輯：從 exercises 查詢運動動作，JOIN body_parts 取得對應身體部位，並依 exercise_name、body_part_name、difficulty_level 或 body_part_id 篩選資料。",
                    "輸出／回應：回傳 HTTP 200 OK 與 Exercise 清單。",
                ],
            ),
            (
                "新增、修改與刪除 Exercise",
                [
                    "觸發條件：管理者於後台新增、編輯或刪除 Exercise。",
                    "輸入資料：exercise_name、body_part_id、difficulty_level、equipment、description、image_url。",
                    "處理邏輯：驗證 body_part_id 是否存在，確認 difficulty_level 是否為 Beginner、Intermediate 或 Advanced。若 Exercise 已被 plan_exercises 或 workout_sets 使用，刪除時建議採用 soft delete 或停用狀態，避免破壞歷史紀錄。",
                    "輸出／回應：新增時回傳 HTTP 201 Created 與 exercise_id；修改或刪除時回傳 HTTP 200 OK。",
                ],
            ),
        ],
    ),
    (
        "3.5 模組五：課表產生與管理 (Workout Plan Module)",
        [
            (
                "自動產生建議課表",
                [
                    "觸發條件：使用者完成基本資料、訓練目標、偏好部位與訓練天數設定後，點擊「產生我的訓練課表」。",
                    "輸入資料：user_id。",
                    "處理邏輯：系統查詢 users、user_body_parts、body_parts 與 exercises，取得訓練目標、訓練經驗、每週訓練天數、每次訓練時間與候選動作。接著使用 Rule-Based Recommendation Algorithm 建立 weekly split，偏好部位會提高出現頻率，但仍保留其他主要肌群。最後寫入 workout_plans、plan_days 與 plan_exercises。",
                    "輸出／回應：回傳 HTTP 201 Created、workout_plan_id 與完整課表內容。",
                ],
            ),
            (
                "查看、修改與刪除課表",
                [
                    "觸發條件：使用者進入「我的課表」頁面，或對課表內容進行編輯與刪除。",
                    "輸入資料：workout_plan_id、plan_day_id、exercise_id、target_sets、target_reps、rest_seconds。",
                    "處理邏輯：根據 user_id 查詢 workout_plans，JOIN plan_days、plan_exercises、exercises 與 body_parts，依 day_number 與 exercise_order 排序。修改或刪除時需驗證該課表屬於目前登入使用者，並保持課表與歷史紀錄的關聯完整性。",
                    "輸出／回應：回傳 HTTP 200 OK 與課表內容或修改成功訊息。",
                ],
            ),
        ],
    ),
    (
        "3.6 模組六：開始運動與訓練紀錄 (Workout Tracking Module)",
        [
            (
                "開始運動",
                [
                    "觸發條件：使用者於課表頁面點擊「開始運動」按鈕。",
                    "輸入資料：user_id、plan_day_id。",
                    "處理邏輯：驗證使用者是否已登入，確認 plan_day_id 存在且屬於該使用者的課表。系統於 workout_sessions 新增一筆紀錄，session_date 設定為目前日期，status 預設為 in_progress。",
                    "輸出／回應：回傳 HTTP 201 Created、workout_session_id 與開始運動成功訊息。",
                ],
            ),
            (
                "新增與修改每組訓練紀錄",
                [
                    "觸發條件：使用者完成一組訓練後，輸入重量與次數並點擊「儲存」。",
                    "輸入資料：workout_session_id、exercise_id、set_number、weight_kg、reps。",
                    "處理邏輯：驗證 workout_session_id 是否存在且狀態為 in_progress，驗證 exercise_id 是否存在，確認 weight_kg 不小於 0 且 reps 大於 0。每完成一組即時寫入 workout_sets，避免資料遺失。若使用者修改紀錄，需確認該 workout_set 屬於目前登入使用者。",
                    "輸出／回應：新增時回傳 HTTP 201 Created 與 workout_set_id；修改時回傳 HTTP 200 OK。",
                ],
            ),
            (
                "完成訓練",
                [
                    "觸發條件：使用者完成所有訓練後點擊「完成訓練」。",
                    "輸入資料：workout_session_id。",
                    "處理邏輯：檢查 workout_session_id 是否存在且屬於目前登入使用者，將 workout_sessions.status 更新為 completed，完成後該 session 會出現在 Workout History。",
                    "輸出／回應：回傳 HTTP 200 OK 與完成訓練訊息。",
                ],
            ),
        ],
    ),
    (
        "3.7 模組七：歷史紀錄與統計分析 (History and Dashboard Module)",
        [
            (
                "查看 Workout History 與 Exercise History",
                [
                    "觸發條件：使用者進入 Workout History 頁面，或於某個 Exercise 點擊「查看歷史」。",
                    "輸入資料：user_id、可選日期範圍、exercise_id。",
                    "處理邏輯：根據 user_id 查詢 workout_sessions，JOIN workout_sets、exercises 與 body_parts，依 session_date 由新到舊排序。若查詢特定 Exercise，則依 exercise_id 篩選該動作的重量、次數、組數與日期。",
                    "輸出／回應：回傳 HTTP 200 OK 與歷史訓練紀錄。",
                ],
            ),
            (
                "計算 Training Volume 與 Dashboard",
                [
                    "觸發條件：使用者進入 Dashboard 或 History 頁面。",
                    "輸入資料：user_id、可選日期範圍。",
                    "處理邏輯：僅計算 status 為 completed 的 workout_sessions。每一組的訓練量公式為 Volume = weight_kg × reps。系統使用 SUM、COUNT、AVG、GROUP BY 與 JOIN 統計總訓練量、每週訓練次數、最常訓練部位、最常使用 Exercise 與體重變化。",
                    "輸出／回應：回傳 HTTP 200 OK 與 Dashboard 統計資料。",
                ],
            ),
        ],
    ),
    (
        "3.8 模組八：身體紀錄管理 (Body Record Module)",
        [
            (
                "新增、查看、修改與刪除體重紀錄",
                [
                    "觸發條件：使用者進入 Body Weight History 頁面並新增、查看、編輯或刪除體重紀錄。",
                    "輸入資料：record_date、weight_kg、notes、body_record_id。",
                    "處理邏輯：根據 JWT Token 取得 user_id，驗證 weight_kg 必須大於 0。新增時寫入 body_records；查看時依 record_date 由舊到新排序；修改或刪除時需確認該紀錄屬於目前登入使用者。",
                    "輸出／回應：新增時回傳 HTTP 201 Created 與 body_record_id；查詢、修改或刪除時回傳 HTTP 200 OK。",
                ],
            ),
        ],
    ),
]


def ensure_dirs() -> None:
    OUT_DOCX.parent.mkdir(parents=True, exist_ok=True)
    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/STHeiti Light.ttc",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size=size, index=0)
            except TypeError:
                return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def draw_round_rect(draw: ImageDraw.ImageDraw, box, fill, outline="#2F3A45", width=2, radius=8):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def draw_arrow(draw: ImageDraw.ImageDraw, start, end, fill="#2F3A45", width=2):
    draw.line([start, end], fill=fill, width=width)
    x1, y1 = start
    x2, y2 = end
    if abs(x2 - x1) >= abs(y2 - y1):
        direction = 1 if x2 > x1 else -1
        points = [(x2, y2), (x2 - 10 * direction, y2 - 6), (x2 - 10 * direction, y2 + 6)]
    else:
        direction = 1 if y2 > y1 else -1
        points = [(x2, y2), (x2 - 6, y2 - 10 * direction), (x2 + 6, y2 - 10 * direction)]
    draw.polygon(points, fill=fill)


def centered_text(draw: ImageDraw.ImageDraw, box, text, fnt, fill="#1F2933") -> None:
    x1, y1, x2, y2 = box
    lines = text.split("\n")
    heights = []
    widths = []
    for line in lines:
        b = draw.textbbox((0, 0), line, font=fnt)
        widths.append(b[2] - b[0])
        heights.append(b[3] - b[1])
    total_h = sum(heights) + (len(lines) - 1) * 6
    y = y1 + ((y2 - y1) - total_h) / 2
    for line, w, h in zip(lines, widths, heights):
        draw.text((x1 + ((x2 - x1) - w) / 2, y), line, font=fnt, fill=fill)
        y += h + 6


def make_architecture_image() -> Path:
    path = IMG_DIR / "system_architecture_zh.png"
    img = Image.new("RGB", (1500, 900), "white")
    d = ImageDraw.Draw(img)
    title = font(38)
    hfont = font(24)
    sfont = font(20)
    centered_text(d, (0, 35, 1500, 90), "系統架構圖", title)
    layers = [
        (80, 145, 1420, 255, "前端介面層", "React / Vite / Responsive UI\n註冊登入、建立資料、產生課表、開始運動、查看 Dashboard"),
        (80, 310, 1420, 420, "後端 API 層", "FastAPI REST API\n身份驗證、資料驗證、CRUD、課表產生、統計查詢"),
        (80, 475, 1420, 585, "服務與商業邏輯層", "Workout Recommendation Engine\n依目標、經驗、部位、每週天數與時間產生訓練安排"),
        (80, 640, 1420, 750, "資料庫層", "PostgreSQL Cloud Database\nusers、user_auth、exercises、workout_plans、workout_sessions、workout_sets、body_records"),
    ]
    for box in layers:
        x1, y1, x2, y2, heading, body = box
        draw_round_rect(d, (x1, y1, x2, y2), "#F7F9FB", "#B8C2CC", 2, 10)
        d.rectangle((x1, y1, x2, y1 + 32), fill="#44546A")
        d.text((x1 + 18, y1 + 5), heading, font=hfont, fill="white")
        centered_text(d, (x1 + 30, y1 + 40, x2 - 30, y2 - 10), body, sfont)
    for y in [255, 420, 585]:
        draw_arrow(d, (750, y + 12), (750, y + 52))
    d.text((105, 805), "資料流：使用者操作 → API 驗證 → 規則式課表產生與資料庫查詢 → 回傳前端顯示。", font=sfont, fill="#425466")
    img.save(path)
    return path


def make_erd_image() -> Path:
    path = IMG_DIR / "er_diagram_zh.png"
    img = Image.new("RGB", (1600, 1100), "white")
    d = ImageDraw.Draw(img)
    title = font(38)
    hfont = font(22)
    boxfont = font(21)
    small = font(17)
    centered_text(d, (0, 30, 1600, 90), "實體關係圖", title)

    groups = [
        (80, 130, 1520, 310, "A. 帳號與使用者資料"),
        (80, 350, 1520, 515, "B. 偏好部位與運動資料庫"),
        (80, 555, 1520, 730, "C. 建議課表"),
        (80, 770, 1520, 990, "D. 開始運動與歷史紀錄"),
    ]
    for x1, y1, x2, y2, text in groups:
        draw_round_rect(d, (x1, y1, x2, y2), "#FAFBFC", "#CBD5DF", 2, 10)
        d.rectangle((x1, y1, x2, y1 + 30), fill="#44546A")
        d.text((x1 + 15, y1 + 4), text, font=hfont, fill="white")

    def node(x, y, label, fill="#EDF2F7"):
        box = (x, y, x + 210, y + 55)
        draw_round_rect(d, box, fill, "#263B55", 2, 8)
        centered_text(d, box, label, boxfont)
        return box

    # A
    tg = node(170, 205, "training_goals", "#FFF8E6")
    users = node(500, 205, "users")
    auth = node(830, 205, "user_auth", "#ECF7F1")
    sessions = node(1160, 205, "user_sessions")
    admin = node(500, 265, "admins", "#ECF7F1")
    draw_arrow(d, (380, 232), (500, 232)); d.text((405, 208), "1:N", font=small, fill="#425466")
    draw_arrow(d, (710, 232), (830, 232)); d.text((735, 208), "1:1", font=small, fill="#425466")
    draw_arrow(d, (1040, 232), (1160, 232)); d.text((1065, 208), "1:N", font=small, fill="#425466")
    draw_arrow(d, (605, 260), (605, 265)); d.text((618, 250), "1:N", font=small, fill="#425466")

    # B
    u2 = node(170, 420, "users")
    ubp = node(500, 420, "user_body_parts", "#F7EEF6")
    bp = node(850, 420, "body_parts", "#F7EEF6")
    ex = node(1180, 420, "exercises", "#F7EEF6")
    for a, b, t in [(u2, ubp, "1:N"), (ubp, bp, "N:1"), (bp, ex, "1:N")]:
        draw_arrow(d, (a[2], (a[1]+a[3])//2), (b[0], (b[1]+b[3])//2)); d.text((a[2]+24, a[1]+6), t, font=small, fill="#425466")

    # C
    u3 = node(170, 625, "users")
    plans = node(470, 625, "workout_plans", "#FFF8E6")
    days = node(770, 625, "plan_days", "#FFF8E6")
    pex = node(1070, 625, "plan_exercises", "#FFF8E6")
    ex2 = node(1320, 625, "exercises", "#F7EEF6")
    for a, b, t in [(u3, plans, "1:N"), (plans, days, "1:N"), (days, pex, "1:N"), (pex, ex2, "N:1")]:
        draw_arrow(d, (a[2], (a[1]+a[3])//2), (b[0], (b[1]+b[3])//2)); d.text((a[2]+16, a[1]+4), t, font=small, fill="#425466")

    # D
    u4 = node(170, 845, "users")
    pd = node(170, 925, "plan_days", "#FFF8E6")
    ws = node(560, 885, "workout_sessions")
    sets = node(940, 885, "workout_sets")
    ex3 = node(1220, 925, "exercises", "#F7EEF6")
    br = node(560, 805, "body_records")
    draw_arrow(d, (380, 872), (560, 900)); d.text((415, 840), "1:N", font=small, fill="#425466")
    draw_arrow(d, (380, 952), (560, 920)); d.text((415, 932), "0:N", font=small, fill="#425466")
    draw_arrow(d, (770, 912), (940, 912)); d.text((805, 888), "1:N", font=small, fill="#425466")
    draw_arrow(d, (1150, 922), (1220, 950)); d.text((1165, 894), "N:1", font=small, fill="#425466")
    draw_arrow(d, (300, 845), (560, 832)); d.text((410, 810), "1:N", font=small, fill="#425466")

    d.text((100, 1030), "說明：users 為主要擁有者資料表；user_body_parts 為 M:N junction table；workout_sets 以每一組為最小紀錄單位。", font=small, fill="#425466")
    img.save(path)
    return path


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_cell_borders(cell, color: str = GRID) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = "w:" + edge
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "4")
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), color)


def set_cell_margin(cell, top=90, start=110, bottom=90, end=110) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    mar = tc_pr.first_child_found_in("w:tcMar")
    if mar is None:
        mar = OxmlElement("w:tcMar")
        tc_pr.append(mar)
    for m, v in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = mar.find(qn(f"w:{m}"))
        if node is None:
            node = OxmlElement(f"w:{m}")
            mar.append(node)
        node.set(qn("w:w"), str(v))
        node.set(qn("w:type"), "dxa")


def style_run(run, size=11, bold=False, color="111111", font_name=FONT_BODY):
    run.font.name = font_name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_CJK)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor.from_string(color)


def style_paragraph(paragraph, size=11, color="111111", align=None):
    if align is not None:
        paragraph.alignment = align
    paragraph.paragraph_format.line_spacing = 1.22
    paragraph.paragraph_format.space_after = Pt(7)
    paragraph.paragraph_format.space_before = Pt(0)
    for run in paragraph.runs:
        style_run(run, size=size, color=color)


def setup_doc_styles(doc: Document) -> None:
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = FONT_BODY
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_CJK)
    normal.font.size = Pt(11)
    normal.font.color.rgb = RGBColor.from_string("111111")
    for name, size, color in [
        ("Title", 26, SLATE),
        ("Heading 1", 19, SLATE),
        ("Heading 2", 14, MUTED),
        ("Heading 3", 12, SLATE_2),
        ("Caption", 10, "6B7C8F"),
    ]:
        style = styles[name]
        style.font.name = FONT_BODY
        style._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_CJK)
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor.from_string(color)
        if name.startswith("Heading") or name == "Title":
            style.font.bold = True
        style.paragraph_format.space_before = Pt(14 if name == "Heading 1" else 8)
        style.paragraph_format.space_after = Pt(6)
    code = styles.add_style("CodeBlockZH", 1)
    code.font.name = FONT_CODE
    code._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_CODE)
    code.font.size = Pt(9.2)
    code.font.color.rgb = RGBColor.from_string("111111")
    code.paragraph_format.line_spacing = 1.05
    code.paragraph_format.space_after = Pt(0)


def add_page_number(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run("Page ")
    style_run(run, 9, color="6B7C8F")
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    run_el = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = "1"
    run_el.append(t)
    fld.append(run_el)
    paragraph._p.append(fld)


def add_doc_header_footer(doc: Document) -> None:
    for section in doc.sections:
        header_p = section.header.paragraphs[0]
        header_p.text = "Fitness Tracking Management System — 系統規格書"
        header_p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        style_paragraph(header_p, size=9, color="6B7C8F")
        footer_p = section.footer.paragraphs[0]
        add_page_number(footer_p)


def add_heading(doc: Document, text: str, level: int) -> None:
    p = doc.add_heading(text, level=level)
    if level == 1:
        p.paragraph_format.page_break_before = False
    for run in p.runs:
        style_run(run, size=19 if level == 1 else 14 if level == 2 else 12, bold=True, color=SLATE if level == 1 else MUTED)


def add_para(doc: Document, text: str) -> None:
    p = doc.add_paragraph(text)
    style_paragraph(p)


def add_bullets(doc: Document, items: Sequence[str]) -> None:
    for item in items:
        p = doc.add_paragraph(item, style="List Bullet")
        style_paragraph(p)


def add_numbered(doc: Document, items: Sequence[str]) -> None:
    for item in items:
        p = doc.add_paragraph(item, style="List Number")
        style_paragraph(p)


def add_table(doc: Document, headers: Sequence[str], rows: Sequence[Sequence[str]], widths: Sequence[float] | None = None) -> None:
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    hdr_cells = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].text = h
        set_cell_shading(hdr_cells[i], SLATE_2)
        set_cell_borders(hdr_cells[i])
        set_cell_margin(hdr_cells[i])
        hdr_cells[i].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        for p in hdr_cells[i].paragraphs:
            for r in p.runs:
                style_run(r, size=9.5, bold=True, color="FFFFFF")
    for r_index, row in enumerate(rows):
        cells = table.add_row().cells
        for i, value in enumerate(row):
            cells[i].text = str(value)
            set_cell_shading(cells[i], "FFFFFF" if r_index % 2 == 0 else PALE)
            set_cell_borders(cells[i])
            set_cell_margin(cells[i])
            cells[i].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            for p in cells[i].paragraphs:
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.12
                for run in p.runs:
                    style_run(run, size=9.2, color="111111")
    if widths:
        for row in table.rows:
            for i, width in enumerate(widths):
                row.cells[i].width = Cm(width)
    doc.add_paragraph()


def add_code_block(doc: Document, code: str) -> None:
    clean = code.strip("\n")
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    set_cell_shading(cell, "F5F6F7")
    set_cell_borders(cell, "D4D8DD")
    set_cell_margin(cell, 120, 160, 120, 160)
    p = cell.paragraphs[0]
    p.style = doc.styles["CodeBlockZH"]
    p.text = clean
    for run in p.runs:
        style_run(run, size=9.2, color="111111", font_name=FONT_CODE)
        run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_CJK)
    doc.add_paragraph()


def add_functional_requirements_docx(doc: Document) -> None:
    add_heading(doc, "3. 功能性需求 (Functional Requirements, FR)", 1)
    for module_title, features in FR_SECTIONS:
        add_heading(doc, module_title, 2)
        for feature_title, details in features:
            add_heading(doc, feature_title, 3)
            add_bullets(doc, details)


def add_functional_requirements_pdf(story, st) -> None:
    story.append(p("3. 功能性需求 (Functional Requirements, FR)", st["h1"]))
    for module_title, features in FR_SECTIONS:
        story.append(p(module_title, st["h2"]))
        for feature_title, details in features:
            story.append(p(f"<b>{feature_title}</b>", st["body"]))
            for detail in details:
                story.append(p("• " + detail, st["body"]))


def add_toc(doc: Document) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = p.add_run()
    fld = OxmlElement("w:fldChar")
    fld.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = 'TOC \\o "1-2" \\h \\z \\u'
    fld2 = OxmlElement("w:fldChar")
    fld2.set(qn("w:fldCharType"), "separate")
    fld3 = OxmlElement("w:fldChar")
    fld3.set(qn("w:fldCharType"), "end")
    run._r.append(fld)
    run._r.append(instr)
    run._r.append(fld2)
    run._r.append(fld3)
    note = doc.add_paragraph("若 Word 顯示目錄尚未更新，請在目錄上按右鍵並選擇「更新功能變數」。")
    style_paragraph(note, size=10, color="6B7C8F")


def make_docx(arch_path: Path, erd_path: Path) -> None:
    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.1)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.15)
    section.right_margin = Cm(2.15)
    setup_doc_styles(doc)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("Fitness Tracking Management System")
    style_run(run, size=25, bold=False, color=SLATE)
    p.paragraph_format.space_before = Pt(90)
    p.paragraph_format.space_after = Pt(14)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("健身紀錄管理系統")
    style_run(run, size=22, bold=True, color=SLATE)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("軟體需求規格書")
    style_run(run, size=16, color=MUTED)

    add_table(
        doc,
        ["項目", "內容"],
        [
            ["文件用途", "大學「資料庫系統」課程專題規格書"],
            ["專題重點", "資料庫設計、關聯式資料模型、CRUD、SQL 查詢、訓練紀錄管理與統計分析"],
            ["系統類型", "Full-stack Database Web Application"],
            ["版本", "Version 1.0"],
            ["日期", "2026-09-30"],
        ],
        [5.0, 11.0],
    )
    add_para(doc, "本文件定義 Fitness Tracking Management System 的需求、系統架構、資料庫設計、ER Diagram、資料表欄位、Primary Key 與 Foreign Key、正規化、核心 SQL 查詢、驗收標準與部署計畫。專題以資料庫系統為核心，網站功能與介面設計皆圍繞資料建立、查詢、更新、刪除、資料關聯與統計分析而規劃。")
    doc.add_page_break()

    add_heading(doc, "目錄", 1)
    add_toc(doc)
    doc.add_page_break()

    add_heading(doc, "1. 專案概述", 1)
    add_heading(doc, "1.1 開發背景", 2)
    add_para(doc, "本專題的開發背景來自實際健身經驗。使用者雖然有健身習慣，但每次到健身房時常不知道當天應該安排哪些動作、要訓練哪些部位，以及如何依照自己的目標與程度調整課表。若每次都臨時上網查詢或詢問 AI，不但流程不連續，也不利於長期保存訓練紀錄與觀察進步情況。")
    add_para(doc, "因此，本系統希望整合使用者帳號、身體基本資料、健身目標、想加強的身體部位、Exercise Database、建議課表、開始運動、每組重量與次數紀錄，以及歷史統計 Dashboard。系統重點不是只做漂亮介面，而是建立一個結構完整、可查詢、可維護、可部署到雲端的資料庫應用系統。")
    add_heading(doc, "1.2 問題敘述", 2)
    add_bullets(doc, [
        "使用者缺少能依照個人目標與訓練經驗產生課表的工具。",
        "紙本或備忘錄式紀錄不容易統計每週訓練量、常練部位與常用動作。",
        "若沒有資料庫設計，訓練紀錄容易重複、遺失或難以查詢。",
        "課程專題需要展示 PK、FK、1:N、M:N、JOIN、GROUP BY、Aggregate Functions 與 3NF。",
    ])
    add_heading(doc, "1.3 專案目標", 2)
    add_bullets(doc, [
        "建立具登入與註冊功能的健身紀錄管理系統。",
        "讓每位使用者只能管理自己的資料，並透過 user_id 建立資料所有權。",
        "提供 Exercise Database、Workout Plan、Start Workout、Workout History、Body Weight History 與 Dashboard。",
        "使用 PostgreSQL 作為雲端資料庫，並讓網站可透過公開網址展示給老師測試。",
        "完整呈現資料庫設計、正規化、SQL 查詢與資料管理能力。",
    ])

    add_heading(doc, "2. 系統架構與技術選型", 1)
    add_heading(doc, "2.1 建議系統架構", 2)
    add_para(doc, "系統採用前後端分離架構。前端負責使用者操作流程與資料呈現；後端提供 REST API、身份驗證、資料驗證、課表產生邏輯與 SQL 查詢；資料庫使用 PostgreSQL 儲存所有帳號、課表、訓練紀錄與統計來源資料。")
    doc.add_picture(str(arch_path), width=Inches(6.4))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap = doc.add_paragraph("Figure 1. 系統架構圖", style="Caption")
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_heading(doc, "2.2 技術棧選型清單 (Tech Stack)", 2)
    add_table(doc, ["層級 (Layer)", "選用技術/工具", "選用理由與說明"], [
        ["前端 (Frontend)", "React / Vite / CSS", "建立響應式操作介面，支援使用者註冊登入、統計儀表板、課表查看與開始運動流程。"],
        ["後端 (Backend)", "FastAPI", "提供 REST API、資料驗證、登入驗證、課表產生邏輯與統計查詢處理。"],
        ["資料庫 (Database)", "PostgreSQL", "支援關聯式資料模型、ACID、Primary Key、Foreign Key、JOIN、GROUP BY 與 Aggregate 查詢。"],
        ["ORM / SQL", "SQLAlchemy 或 SQLModel", "管理資料模型、資料表關聯、SQL 查詢與 migration 串接。"],
        ["Migration", "Alembic", "追蹤資料庫 schema 版本，讓資料庫結構變更可以被管理與重現。"],
        ["部署 (Deployment)", "Render 或類似雲端平台", "部署 Web Service 與 Cloud PostgreSQL，產生公開網址供老師測試。"],
        ["敏感資料管理", "Environment Variables", "保存 DATABASE_URL、SECRET_KEY 等敏感資料，避免寫入 GitHub。"],
    ], [3.4, 4.2, 8.4])

    add_functional_requirements_docx(doc)

    add_heading(doc, "4. 功能需求", 1)
    add_table(doc, ["編號", "功能", "說明", "資料庫重點"], [
        ["FR-01", "註冊", "使用 email 與 password 建立帳號。", "user_auth 儲存 email 與 password_hash。"],
        ["FR-02", "登入", "驗證 email 與 password 後建立 session 或 token。", "user_sessions 或 token 驗證。"],
        ["FR-03", "基本資料管理", "新增、查看、修改個人資料。", "users CRUD。"],
        ["FR-04", "健身目標設定", "選擇增肌、減脂、力量或一般健身。", "users.training_goal_id FK。"],
        ["FR-05", "加強部位選擇", "可選多個 body parts。", "user_body_parts M:N junction table。"],
        ["FR-06", "Exercise Database", "提供動作名稱、部位、難度、器材與說明。", "exercises 與 body_parts 1:N。"],
        ["FR-07", "產生課表", "根據使用者資料與候選 exercises 產生 plan。", "workout_plans、plan_days、plan_exercises。"],
        ["FR-08", "開始運動", "按下按鈕後建立進行中的 workout session。", "workout_sessions.status = in_progress。"],
        ["FR-09", "紀錄每一組", "輸入重量、次數與第幾組。", "workout_sets 即時新增。"],
        ["FR-10", "歷史紀錄", "查看過去 session 與 exercise 紀錄。", "JOIN workout_sessions、workout_sets、exercises。"],
        ["FR-11", "統計 Dashboard", "顯示訓練量、每週次數、常練部位與常用動作。", "GROUP BY 與 Aggregate Functions。"],
        ["FR-12", "體重紀錄", "新增與查看 body weight history。", "body_records CRUD 與時間排序。"],
        ["FR-13", "管理功能", "管理 exercises、body parts 與目標資料。", "admins 與 reference tables。"],
    ], [1.8, 3.0, 5.2, 6.2])

    add_heading(doc, "5. CRUD 對應", 1)
    add_table(doc, ["資料表", "Create", "Read", "Update", "Delete"], [
        ["users", "註冊或建立 profile", "查看個人資料", "修改身高、體重、經驗", "刪除帳號或停用"],
        ["user_auth", "建立登入資料", "登入時查詢 email", "更新 password_hash", "刪除登入資料"],
        ["user_body_parts", "新增偏好部位", "查看偏好部位", "調整 priority", "移除偏好部位"],
        ["exercises", "管理員新增動作", "搜尋與課表候選", "修改難度或說明", "停用或刪除動作"],
        ["workout_plans", "產生課表", "查看目前課表", "重新命名或修改", "刪除課表"],
        ["workout_sessions", "開始運動", "查看歷史訓練", "完成或取消 session", "刪除錯誤紀錄"],
        ["workout_sets", "新增每組紀錄", "查看 exercise history", "修正重量或次數", "刪除錯誤 set"],
        ["body_records", "新增體重", "查看體重歷史", "修改數值", "刪除錯誤紀錄"],
    ], [3.5, 3.5, 4.0, 3.8, 3.2])

    add_heading(doc, "6. 資料庫設計", 1)
    add_heading(doc, "6.1 ER Diagram", 2)
    doc.add_picture(str(erd_path), width=Inches(6.6))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap = doc.add_paragraph("Figure 2. 實體關係圖", style="Caption")
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_heading(doc, "6.2 實體總覽", 2)
    add_table(doc, ["實體", "用途"], [
        ["users", "保存使用者個人資料與訓練設定，是多數資料的 owner table。"],
        ["user_auth", "保存登入認證資料，與 users 分離以符合安全與正規化需求。"],
        ["training_goals", "保存訓練目標代碼與說明。"],
        ["body_parts", "保存身體部位基本資料。"],
        ["user_body_parts", "使用者與 body_parts 的 M:N 關係表。"],
        ["exercises", "保存動作資料，並透過 body_part_id 對應主要訓練部位。"],
        ["workout_plans", "保存系統產生或使用者使用中的課表。"],
        ["plan_days", "保存課表中的第幾天與該天訓練主題。"],
        ["plan_exercises", "保存每一天安排的動作、組數、次數與休息時間。"],
        ["workout_sessions", "保存每次開始運動的 session。"],
        ["workout_sets", "保存每一組實際完成的重量與次數。"],
        ["body_records", "保存使用者體重與身體紀錄。"],
        ["admins", "保存管理員角色與管理權限。"],
    ], [4.2, 11.8])

    add_heading(doc, "7. Data Dictionary", 1)
    data_tables = {
        "users": [
            ["user_id", "SERIAL", "PK", "使用者識別碼"],
            ["name", "VARCHAR(100)", "NOT NULL", "使用者姓名"],
            ["gender", "VARCHAR(20)", "NULL", "性別"],
            ["age", "INTEGER", "CHECK age > 0", "年齡"],
            ["height_cm", "NUMERIC(5,2)", "CHECK height_cm > 0", "身高"],
            ["weight_kg", "NUMERIC(5,2)", "CHECK weight_kg > 0", "目前體重"],
            ["training_experience", "VARCHAR(20)", "CHECK", "Beginner / Intermediate / Advanced"],
            ["training_goal_id", "INTEGER", "FK", "對應 training_goals"],
            ["training_days_per_week", "INTEGER", "CHECK 2-6", "每週訓練天數"],
            ["training_duration_minutes", "INTEGER", "CHECK", "30 / 60 / 90 分鐘"],
        ],
        "user_auth": [
            ["auth_id", "SERIAL", "PK", "登入資料識別碼"],
            ["user_id", "INTEGER", "FK UNIQUE", "對應 users"],
            ["email", "VARCHAR(255)", "UNIQUE NOT NULL", "登入信箱"],
            ["password_hash", "VARCHAR(255)", "NOT NULL", "雜湊後密碼"],
            ["is_email_verified", "BOOLEAN", "DEFAULT FALSE", "第一版可保留欄位但不強制寄信驗證"],
            ["created_at", "TIMESTAMP", "DEFAULT NOW()", "建立時間"],
        ],
        "training_goals": [
            ["training_goal_id", "SERIAL", "PK", "目標識別碼"],
            ["goal_name", "VARCHAR(50)", "UNIQUE", "Muscle Gain / Fat Loss / Strength / General Fitness"],
            ["description", "TEXT", "NULL", "目標說明"],
        ],
        "body_parts": [
            ["body_part_id", "SERIAL", "PK", "身體部位識別碼"],
            ["body_part_name", "VARCHAR(50)", "UNIQUE", "Chest、Back、Legs 等"],
            ["description", "TEXT", "NULL", "部位說明"],
        ],
        "user_body_parts": [
            ["user_id", "INTEGER", "PK FK", "對應 users"],
            ["body_part_id", "INTEGER", "PK FK", "對應 body_parts"],
            ["priority", "INTEGER", "DEFAULT 1", "偏好優先順序"],
        ],
        "exercises": [
            ["exercise_id", "SERIAL", "PK", "動作識別碼"],
            ["exercise_name", "VARCHAR(120)", "NOT NULL", "動作名稱"],
            ["body_part_id", "INTEGER", "FK", "主要訓練部位"],
            ["difficulty_level", "VARCHAR(20)", "CHECK", "Beginner / Intermediate / Advanced"],
            ["equipment", "VARCHAR(100)", "NULL", "器材"],
            ["description", "TEXT", "NULL", "動作說明"],
            ["image_url", "TEXT", "NULL", "參考圖片 URL"],
        ],
        "workout_plans": [
            ["workout_plan_id", "SERIAL", "PK", "課表識別碼"],
            ["user_id", "INTEGER", "FK", "課表擁有者"],
            ["plan_name", "VARCHAR(120)", "NOT NULL", "課表名稱"],
            ["training_goal_id", "INTEGER", "FK", "課表目標"],
            ["created_at", "TIMESTAMP", "DEFAULT NOW()", "建立時間"],
        ],
        "plan_days": [
            ["plan_day_id", "SERIAL", "PK", "課表日識別碼"],
            ["workout_plan_id", "INTEGER", "FK", "對應 workout_plans"],
            ["day_number", "INTEGER", "NOT NULL", "第幾天"],
            ["day_title", "VARCHAR(120)", "NOT NULL", "當天主題"],
        ],
        "plan_exercises": [
            ["plan_exercise_id", "SERIAL", "PK", "課表動作識別碼"],
            ["plan_day_id", "INTEGER", "FK", "對應 plan_days"],
            ["exercise_id", "INTEGER", "FK", "對應 exercises"],
            ["exercise_order", "INTEGER", "NOT NULL", "動作順序"],
            ["target_sets", "INTEGER", "NOT NULL", "目標組數"],
            ["target_reps", "VARCHAR(30)", "NOT NULL", "目標次數"],
            ["rest_seconds", "INTEGER", "NULL", "休息秒數"],
        ],
        "workout_sessions": [
            ["workout_session_id", "SERIAL", "PK", "訓練 session 識別碼"],
            ["user_id", "INTEGER", "FK", "使用者"],
            ["plan_day_id", "INTEGER", "FK NULL", "來源課表日"],
            ["session_date", "DATE", "NOT NULL", "訓練日期"],
            ["status", "VARCHAR(20)", "CHECK", "in_progress / completed / cancelled"],
            ["notes", "TEXT", "NULL", "備註"],
        ],
        "workout_sets": [
            ["workout_set_id", "SERIAL", "PK", "每組紀錄識別碼"],
            ["workout_session_id", "INTEGER", "FK", "對應 workout_sessions"],
            ["exercise_id", "INTEGER", "FK", "對應 exercises"],
            ["set_number", "INTEGER", "NOT NULL", "第幾組"],
            ["weight_kg", "NUMERIC(6,2)", "CHECK >= 0", "重量"],
            ["reps", "INTEGER", "CHECK > 0", "次數"],
            ["created_at", "TIMESTAMP", "DEFAULT NOW()", "紀錄時間"],
        ],
        "body_records": [
            ["body_record_id", "SERIAL", "PK", "身體紀錄識別碼"],
            ["user_id", "INTEGER", "FK", "使用者"],
            ["record_date", "DATE", "NOT NULL", "紀錄日期"],
            ["weight_kg", "NUMERIC(5,2)", "CHECK > 0", "體重"],
            ["notes", "TEXT", "NULL", "備註"],
        ],
    }
    for table_name, rows in data_tables.items():
        add_heading(doc, table_name, 2)
        add_table(doc, ["欄位", "型別", "限制", "說明"], rows, [3.7, 3.4, 3.8, 5.3])

    add_heading(doc, "8. Primary Key Foreign Key 與 Relationships", 1)
    add_table(doc, ["關係", "型態", "說明"], [
        ["training_goals -> users", "1:N", "一個訓練目標可被多個使用者選擇。"],
        ["users -> user_auth", "1:1", "一個使用者對應一筆登入資料。"],
        ["users -> user_body_parts -> body_parts", "M:N", "使用 junction table 表示使用者偏好多個身體部位。"],
        ["body_parts -> exercises", "1:N", "一個身體部位可包含多個 exercises。"],
        ["users -> workout_plans", "1:N", "一個使用者可擁有多份課表。"],
        ["workout_plans -> plan_days", "1:N", "一份課表包含多個訓練日。"],
        ["plan_days -> plan_exercises", "1:N", "一個訓練日安排多個動作。"],
        ["exercises -> plan_exercises", "1:N", "同一個 exercise 可被不同課表重複引用。"],
        ["users -> workout_sessions", "1:N", "使用者可建立多次訓練 session。"],
        ["workout_sessions -> workout_sets", "1:N", "一次訓練包含多組紀錄。"],
        ["exercises -> workout_sets", "1:N", "每組紀錄對應一個實際執行的 exercise。"],
        ["users -> body_records", "1:N", "使用者可新增多筆體重紀錄。"],
    ], [5.5, 2.2, 8.3])

    add_heading(doc, "9. 正規化設計", 1)
    add_bullets(doc, [
        "第一正規化：每個欄位皆保存單一值；偏好部位不以逗號字串儲存在 users，而是拆成 user_body_parts。",
        "第二正規化：複合主鍵資料表 user_body_parts 中的 priority 依賴完整的 user_id 與 body_part_id 組合。",
        "第三正規化：training_goals、body_parts、exercises、user_auth 皆獨立成表，避免非鍵欄位間的傳遞相依。",
        "Workout Session 與 Workout Set 分離，避免在每一組紀錄重複保存 session 日期、狀態與備註。",
        "Authentication 資料與 Profile 資料分離，避免 users 同時承擔個人資料與密碼管理責任。",
    ])

    add_heading(doc, "10. SQL 查詢需求", 1)
    add_heading(doc, "10.1 新增使用者資料", 2)
    add_code_block(doc, """
INSERT INTO users
  (name, gender, age, height_cm, weight_kg, training_experience,
   training_goal_id, training_days_per_week, training_duration_minutes)
VALUES
  ('Loise', 'Female', 21, 160, 50, 'Beginner', 1, 4, 60);
""")
    add_heading(doc, "10.2 JOIN 查詢訓練歷史", 2)
    add_code_block(doc, """
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
""")
    add_heading(doc, "10.3 GROUP BY 與 Aggregate Functions", 2)
    add_code_block(doc, """
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
""")
    add_heading(doc, "10.4 最常訓練部位", 2)
    add_code_block(doc, """
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
""")
    add_heading(doc, "10.5 搜尋 Exercise", 2)
    add_code_block(doc, """
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
""")

    add_heading(doc, "11. 課表推薦演算法", 1)
    add_para(doc, "第一版不使用 AI API，而是採用資料庫資料與 rule based recommendation algorithm。系統會先讀取使用者的訓練目標、訓練經驗、偏好部位、每週訓練天數與每次訓練時間，再從 exercises 查詢符合難度與身體部位的候選動作。")
    add_code_block(doc, """
Input: user_id

1. 讀取 users 中的 profile、training_goal、days_per_week 與 duration
2. 讀取 user_body_parts 取得使用者想加強的 body parts
3. 建立 weekly split
   a. 依每週天數決定 Push / Pull / Legs / Upper / Lower 或 Full Body
   b. 使用者偏好部位提高出現頻率
   c. 仍保留主要肌群，避免課表過度偏向單一部位
4. For each plan day:
   a. 從 exercises 查詢候選動作
   b. 依 training_experience 過濾 difficulty_level
   c. 依 training_goal 決定 sets、reps、rest_seconds
   d. 寫入 workout_plans、plan_days、plan_exercises
5. 回傳完整 workout plan
""")
    add_table(doc, ["訓練目標", "建議組數與次數", "設計原則"], [
        ["Muscle Gain", "3-4 組，每組 8-12 下", "提高肌肥大訓練量。"],
        ["Fat Loss", "2-4 組，每組 12-15 下", "搭配較短休息與全身性動作。"],
        ["Strength", "3-5 組，每組 3-6 下", "以複合動作與較高重量為主。"],
        ["General Fitness", "2-3 組，每組 10-15 下", "均衡訓練主要肌群。"],
    ], [3.8, 4.3, 7.9])

    add_heading(doc, "12. 非功能需求", 1)
    add_bullets(doc, [
        "安全性：密碼不得明文儲存，必須使用 password_hash；DATABASE_URL 與 SECRET_KEY 必須使用 Environment Variables。",
        "可用性：公開網址可讓老師直接測試系統，無需登入 GitHub。",
        "資料完整性：所有 FK 必須維持參照完整性，必要欄位加上 NOT NULL 與 CHECK constraints。",
        "效能：常用查詢欄位，例如 email、user_id、session_date、body_part_id，應建立 index。",
        "可維護性：使用 migrations 管理 schema 變更，README 與 .env.example 必須清楚說明設定方式。",
        "響應式設計：手機與電腦皆可使用，特別是開始運動與記錄每組資料的流程。",
    ])

    add_heading(doc, "13. Indexes", 1)
    add_table(doc, ["Index", "用途"], [
        ["idx_user_auth_email", "登入時快速查詢 email。"],
        ["idx_exercises_body_part_id", "依身體部位搜尋動作。"],
        ["idx_workout_sessions_user_date", "依使用者與日期查詢歷史訓練。"],
        ["idx_workout_sets_session_id", "快速載入某次訓練的所有 sets。"],
        ["idx_body_records_user_date", "顯示體重歷史趨勢。"],
        ["idx_user_body_parts_user_id", "讀取使用者偏好部位。"],
    ], [6.0, 10.0])

    add_heading(doc, "14. 驗收測試案例", 1)
    add_table(doc, ["編號", "測試項目", "操作", "預期結果"], [
        ["AT-01", "註冊", "輸入 email 與 password。", "users 與 user_auth 各新增一筆資料。"],
        ["AT-02", "登入", "使用正確帳密登入。", "系統回傳有效 session 或 token。"],
        ["AT-03", "建立 profile", "輸入身高、體重、經驗與目標。", "users 資料完整保存。"],
        ["AT-04", "選擇多個部位", "選 Chest 與 Back。", "user_body_parts 新增兩筆資料。"],
        ["AT-05", "產生課表", "按下產生課表。", "workout_plans、plan_days、plan_exercises 皆有資料。"],
        ["AT-06", "開始運動", "按下 Start Workout。", "workout_sessions 新增 in_progress session。"],
        ["AT-07", "紀錄每一組", "輸入 60kg x 12。", "workout_sets 新增一筆資料。"],
        ["AT-08", "完成訓練", "按下完成。", "session 狀態改為 completed。"],
        ["AT-09", "Workout History", "查看歷史紀錄。", "以 JOIN 顯示日期、動作、重量與次數。"],
        ["AT-10", "Dashboard", "查看統計資料。", "正確顯示總訓練量、每週次數與常用動作。"],
    ], [1.6, 3.0, 5.0, 6.4])

    add_heading(doc, "15. 部署計畫", 1)
    add_table(doc, ["項目", "說明"], [
        ["GitHub Repository", "Source Code 存放於 GitHub，排除 .env 與敏感資訊。"],
        ["Web Service", "後端與前端部署至 Render 或其他雲端平台。"],
        ["Cloud Database", "PostgreSQL 部署於雲端，不能只存在 localhost。"],
        ["Environment Variables", "DATABASE_URL、SECRET_KEY、API KEY、Password 皆由平台環境變數設定。"],
        ["Public URL", "部署後提供公開網址，老師可直接開啟測試。"],
        ["README", "包含 Project Description、Database Design、ER Diagram、Installation、Environment Variables、Local Development、Deployment 與 Live Demo。"],
    ], [4.2, 11.8])

    add_heading(doc, "16. 資料庫課程重點對應", 1)
    add_table(doc, ["課程要求", "本專題如何展示"], [
        ["Primary Key", "每個主要資料表皆有 PK，junction table 使用 composite PK。"],
        ["Foreign Key", "users、exercises、plans、sessions、sets 之間使用 FK 維持完整性。"],
        ["1:N Relationship", "users -> workout_sessions；workout_sessions -> workout_sets。"],
        ["M:N Relationship", "users <-> body_parts 透過 user_body_parts 表示。"],
        ["Normalization", "training_goals、body_parts、exercises、auth、sessions 分離，符合 3NF。"],
        ["CRUD", "users、exercises、plans、sessions、sets、body_records 皆有 CRUD 情境。"],
        ["JOIN", "Workout History 與 Dashboard 需要 JOIN 多張表。"],
        ["GROUP BY", "每週訓練量、最常訓練部位與常用 exercise 都使用 GROUP BY。"],
        ["Aggregate Functions", "SUM(volume)、COUNT(session)、AVG(weight) 等。"],
        ["Indexes", "email、user_id、session_date、body_part_id 等欄位建立 index。"],
        ["Data Ownership", "所有個人資料都以 user_id 限制查詢與修改。"],
    ], [4.2, 11.8])

    add_heading(doc, "17. 結論", 1)
    add_para(doc, "Fitness Tracking Management System 是以關聯式資料庫為核心的健身紀錄管理系統。系統透過 users、user_auth、training_goals、body_parts、exercises、workout_plans、plan_days、plan_exercises、workout_sessions、workout_sets 與 body_records 建立完整資料模型，並支援註冊登入、課表產生、開始運動、即時紀錄每一組、歷史查詢與 Dashboard 統計。")
    add_para(doc, "本設計可展示資料庫系統課程要求的 PK、FK、1:N、M:N、3NF、CRUD、JOIN、GROUP BY、Aggregate Functions、Indexes 與雲端資料庫部署。後續實作時，應優先完成 schema、migration、seed data 與核心 API，再逐步完成前端流程與公開部署。")

    add_doc_header_footer(doc)
    doc.save(OUT_DOCX)


def pdf_styles():
    if PDF_FONT_PATH.exists():
        pdfmetrics.registerFont(TTFont(PDF_FONT_NAME, str(PDF_FONT_PATH)))
        base = PDF_FONT_NAME
    else:
        base = "Helvetica"
    styles = getSampleStyleSheet()
    return {
        "base": base,
        "title": ParagraphStyle("TitleZH", parent=styles["Title"], fontName=base, fontSize=25, leading=32, alignment=TA_CENTER, textColor=colors.HexColor("#2F3A45"), spaceAfter=16),
        "subtitle": ParagraphStyle("SubtitleZH", parent=styles["Normal"], fontName=base, fontSize=15, leading=22, alignment=TA_CENTER, textColor=colors.HexColor("#536878"), spaceAfter=18),
        "h1": ParagraphStyle("H1ZH", parent=styles["Heading1"], fontName=base, fontSize=19, leading=25, textColor=colors.HexColor("#2F3A45"), spaceBefore=18, spaceAfter=10),
        "h2": ParagraphStyle("H2ZH", parent=styles["Heading2"], fontName=base, fontSize=14, leading=20, textColor=colors.HexColor("#536878"), spaceBefore=10, spaceAfter=7),
        "body": ParagraphStyle("BodyZH", parent=styles["Normal"], fontName=base, fontSize=10.5, leading=16, textColor=colors.black, spaceAfter=7),
        "caption": ParagraphStyle("CaptionZH", parent=styles["Normal"], fontName=base, fontSize=9.5, leading=13, alignment=TA_CENTER, textColor=colors.HexColor("#6B7C8F"), spaceAfter=8),
        "code": ParagraphStyle("CodeZH", parent=styles["Code"], fontName=base, fontSize=8.3, leading=11, textColor=colors.black),
        "cell": ParagraphStyle("CellZH", parent=styles["Normal"], fontName=base, fontSize=8.7, leading=12),
        "head": ParagraphStyle("HeadZH", parent=styles["Normal"], fontName=base, fontSize=8.8, leading=12, textColor=colors.white),
    }


def p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text.replace("\n", "<br/>"), style)


def pdf_table(headers: Sequence[str], rows: Sequence[Sequence[str]], widths: Sequence[float], st) -> Table:
    data = [[p(h, st["head"]) for h in headers]]
    for row in rows:
        data.append([p(str(v), st["cell"]) for v in row])
    t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1, hAlign="CENTER")
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#44546A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#CBD5DF")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for i in range(1, len(data)):
        cmds.append(("BACKGROUND", (0, i), (-1, i), colors.white if i % 2 else colors.HexColor("#F4F6F8")))
    t.setStyle(TableStyle(cmds))
    return t


def code_block(code: str, st) -> Table:
    pre = Preformatted(code.strip("\n"), st["code"])
    t = Table([[pre]], colWidths=[16.2 * cm], hAlign="CENTER")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F6F7")),
        ("BOX", (0, 0), (-1, -1), 0.45, colors.HexColor("#D4D8DD")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def make_pdf(arch_path: Path, erd_path: Path) -> None:
    st = pdf_styles()
    doc = SimpleDocTemplate(str(OUT_PDF), pagesize=A4, rightMargin=1.8*cm, leftMargin=1.8*cm, topMargin=1.8*cm, bottomMargin=1.7*cm, title="Fitness Tracking Management System 中文版系統規格書", author="Loise")
    story = []

    def H1(text): return p(text, st["h1"])
    def H2(text): return p(text, st["h2"])
    def B(text): return p(text, st["body"])
    def bullets(items):
        return [B("• " + x) for x in items]

    story.append(Spacer(1, 2.0 * cm))
    story.append(p("Fitness Tracking Management System", st["title"]))
    story.append(p("健身紀錄管理系統<br/>軟體需求規格書", st["subtitle"]))
    story.append(pdf_table(["項目", "內容"], [
        ["文件用途", "大學「資料庫系統」課程專題規格書"],
        ["專題重點", "資料庫設計、關聯式資料模型、CRUD、SQL 查詢、訓練紀錄管理與統計分析"],
        ["系統類型", "Full-stack Database Web Application"],
        ["版本", "Version 1.0"],
        ["日期", "2026-09-30"],
    ], [4.0, 12.0], st))
    story.append(Spacer(1, 0.45 * cm))
    story.append(B("本文件定義 Fitness Tracking Management System 的需求、系統架構、資料庫設計、ER Diagram、資料表欄位、Primary Key 與 Foreign Key、正規化、核心 SQL 查詢與驗收標準。專題以資料庫系統為核心，網站功能與介面設計皆圍繞資料建立、查詢、更新、刪除、資料關聯與統計分析而規劃。"))
    story.append(PageBreak())

    story.append(H1("1. 專案概述"))
    story.append(H2("1.1 開發背景"))
    story.append(B("本專題的開發背景來自實際健身經驗。使用者雖然有健身習慣，但每次到健身房時常不知道當天應該安排哪些動作、要訓練哪些部位，以及如何依照自己的目標與程度調整課表。若每次都臨時上網查詢或詢問 AI，不但流程不連續，也不利於長期保存訓練紀錄與觀察進步情況。"))
    story.append(B("因此，本系統整合使用者帳號、身體基本資料、健身目標、想加強的身體部位、Exercise Database、建議課表、開始運動、每組重量與次數紀錄，以及歷史統計 Dashboard。系統重點不是只做漂亮介面，而是建立一個結構完整、可查詢、可維護、可部署到雲端的資料庫應用系統。"))
    story.append(H2("1.2 問題敘述"))
    story.extend(bullets(["使用者缺少能依照個人目標與訓練經驗產生課表的工具。", "紙本或備忘錄式紀錄不容易統計每週訓練量、常練部位與常用動作。", "若沒有資料庫設計，訓練紀錄容易重複、遺失或難以查詢。", "課程專題需要展示 PK、FK、1:N、M:N、JOIN、GROUP BY、Aggregate Functions 與 3NF。"]))
    story.append(H2("1.3 專案目標"))
    story.extend(bullets(["建立具登入與註冊功能的健身紀錄管理系統。", "讓每位使用者只能管理自己的資料，並透過 user_id 建立資料所有權。", "提供 Exercise Database、Workout Plan、Start Workout、Workout History、Body Weight History 與 Dashboard。", "使用 PostgreSQL 作為雲端資料庫，並讓網站可透過公開網址展示給老師測試。", "完整呈現資料庫設計、正規化、SQL 查詢與資料管理能力。"]))

    story.append(H1("2. 系統架構與技術選型"))
    story.append(B("系統採用前後端分離架構。前端負責使用者操作流程與資料呈現；後端提供 REST API、身份驗證、資料驗證、課表產生邏輯與 SQL 查詢；資料庫使用 PostgreSQL 儲存所有帳號、課表、訓練紀錄與統計來源資料。"))
    story.append(RLImage(str(arch_path), width=16.2 * cm, height=9.72 * cm))
    story.append(p("Figure 1. 系統架構圖", st["caption"]))
    story.append(H2("2.2 技術棧選型清單 (Tech Stack)"))
    story.append(pdf_table(["層級 (Layer)", "選用技術/工具", "選用理由與說明"], [
        ["前端 (Frontend)", "React / Vite / CSS", "建立響應式操作介面，支援使用者註冊登入、統計儀表板、課表查看與開始運動流程。"],
        ["後端 (Backend)", "FastAPI", "提供 REST API、資料驗證、登入驗證、課表產生邏輯與統計查詢處理。"],
        ["資料庫 (Database)", "PostgreSQL", "支援關聯式資料模型、ACID、Primary Key、Foreign Key、JOIN、GROUP BY 與 Aggregate 查詢。"],
        ["ORM / SQL", "SQLAlchemy 或 SQLModel", "管理資料模型、資料表關聯、SQL 查詢與 migration 串接。"],
        ["Migration", "Alembic", "追蹤資料庫 schema 版本，讓資料庫結構變更可以被管理與重現。"],
        ["部署 (Deployment)", "Render 或類似雲端平台", "部署 Web Service 與 Cloud PostgreSQL，產生公開網址供老師測試。"],
        ["敏感資料管理", "Environment Variables", "保存 DATABASE_URL、SECRET_KEY 等敏感資料，避免寫入 GitHub。"],
    ], [3.4, 3.7, 8.9], st))

    add_functional_requirements_pdf(story, st)

    story.append(H1("4. 功能需求"))
    story.append(pdf_table(["編號", "功能", "說明", "資料庫重點"], [
        ["FR-01", "註冊", "使用 email 與 password 建立帳號。", "user_auth 儲存 email 與 password_hash。"],
        ["FR-02", "登入", "驗證 email 與 password 後建立 session 或 token。", "user_sessions 或 token 驗證。"],
        ["FR-03", "基本資料管理", "新增、查看、修改個人資料。", "users CRUD。"],
        ["FR-04", "加強部位選擇", "可選多個 body parts。", "user_body_parts M:N junction table。"],
        ["FR-05", "Exercise Database", "提供動作名稱、部位、難度、器材與說明。", "exercises 與 body_parts 1:N。"],
        ["FR-06", "產生課表", "根據使用者資料與候選 exercises 產生 plan。", "三張課表資料表。"],
        ["FR-07", "開始運動", "按下按鈕後建立進行中的 workout session。", "workout_sessions.status = in_progress。"],
        ["FR-08", "紀錄每一組", "輸入重量、次數與第幾組。", "workout_sets 即時新增。"],
        ["FR-09", "歷史紀錄", "查看過去 session 與 exercise 紀錄。", "JOIN workout_sessions、workout_sets、exercises。"],
        ["FR-10", "統計 Dashboard", "顯示訓練量、每週次數、常練部位與常用動作。", "GROUP BY 與 Aggregate Functions。"],
    ], [1.6, 2.7, 5.1, 6.2], st))

    story.append(PageBreak())
    story.append(H1("5. 資料庫設計"))
    story.append(RLImage(str(erd_path), width=16.5 * cm, height=11.34 * cm))
    story.append(p("Figure 2. 實體關係圖", st["caption"]))
    story.append(pdf_table(["實體", "用途"], [
        ["users", "保存使用者個人資料與訓練設定，是多數資料的 owner table。"],
        ["user_auth", "保存登入認證資料，與 users 分離以符合安全與正規化需求。"],
        ["training_goals", "保存訓練目標代碼與說明。"],
        ["body_parts", "保存身體部位基本資料。"],
        ["user_body_parts", "使用者與 body_parts 的 M:N 關係表。"],
        ["exercises", "保存動作資料，並透過 body_part_id 對應主要訓練部位。"],
        ["workout_plans、plan_days、plan_exercises", "保存系統產生的建議課表。"],
        ["workout_sessions、workout_sets", "保存開始運動後的實際訓練紀錄。"],
        ["body_records", "保存使用者體重與身體紀錄。"],
    ], [5.2, 10.8], st))

    story.append(PageBreak())
    story.append(H1("6. Data Dictionary"))
    compact_rows = [
        ["users", "user_id PK；training_goal_id FK；name、gender、age、height_cm、weight_kg、training_experience、training_days_per_week、training_duration_minutes"],
        ["user_auth", "auth_id PK；user_id FK UNIQUE；email UNIQUE；password_hash；is_email_verified；created_at"],
        ["training_goals", "training_goal_id PK；goal_name UNIQUE；description"],
        ["body_parts", "body_part_id PK；body_part_name UNIQUE；description"],
        ["user_body_parts", "user_id PK FK；body_part_id PK FK；priority"],
        ["exercises", "exercise_id PK；body_part_id FK；exercise_name；difficulty_level；equipment；description；image_url"],
        ["workout_plans", "workout_plan_id PK；user_id FK；training_goal_id FK；plan_name；created_at"],
        ["plan_days", "plan_day_id PK；workout_plan_id FK；day_number；day_title"],
        ["plan_exercises", "plan_exercise_id PK；plan_day_id FK；exercise_id FK；exercise_order；target_sets；target_reps；rest_seconds"],
        ["workout_sessions", "workout_session_id PK；user_id FK；plan_day_id FK NULL；session_date；status；notes"],
        ["workout_sets", "workout_set_id PK；workout_session_id FK；exercise_id FK；set_number；weight_kg；reps；created_at"],
        ["body_records", "body_record_id PK；user_id FK；record_date；weight_kg；notes"],
    ]
    story.append(pdf_table(["資料表", "主要欄位與限制"], compact_rows, [4.2, 11.8], st))

    story.append(H1("7. Relationships 與 3NF"))
    story.append(pdf_table(["關係", "型態", "說明"], [
        ["training_goals -> users", "1:N", "一個訓練目標可被多個使用者選擇。"],
        ["users -> user_auth", "1:1", "一個使用者對應一筆登入資料。"],
        ["users -> user_body_parts -> body_parts", "M:N", "使用 junction table 表示使用者偏好多個身體部位。"],
        ["body_parts -> exercises", "1:N", "一個身體部位可包含多個 exercises。"],
        ["users -> workout_sessions -> workout_sets", "1:N", "使用者可建立多次訓練，每次訓練包含多組紀錄。"],
    ], [5.5, 2.0, 8.5], st))
    story.extend(bullets(["1NF：每個欄位皆保存單一值；偏好部位拆成 user_body_parts。", "2NF：複合主鍵資料表中的非鍵欄位依賴完整複合鍵。", "3NF：training_goals、body_parts、exercises、user_auth 獨立成表，避免傳遞相依。"]))

    story.append(PageBreak())
    story.append(H1("8. SQL 查詢需求"))
    for heading, code in [
        ("8.1 新增使用者資料", """INSERT INTO users
  (name, gender, age, height_cm, weight_kg, training_experience,
   training_goal_id, training_days_per_week, training_duration_minutes)
VALUES
  ('Loise', 'Female', 21, 160, 50, 'Beginner', 1, 4, 60);"""),
        ("8.2 JOIN 查詢訓練歷史", """SELECT
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
ORDER BY ws.session_date DESC, e.exercise_name, wset.set_number;"""),
        ("8.3 每週訓練量統計", """SELECT
  DATE_TRUNC('week', ws.session_date) AS training_week,
  SUM(wset.weight_kg * wset.reps) AS weekly_volume,
  COUNT(DISTINCT ws.workout_session_id) AS workout_count
FROM workout_sessions ws
JOIN workout_sets wset
  ON ws.workout_session_id = wset.workout_session_id
WHERE ws.user_id = :user_id
  AND ws.status = 'completed'
GROUP BY DATE_TRUNC('week', ws.session_date)
ORDER BY training_week DESC;"""),
        ("__PAGEBREAK__8.4 搜尋 Exercise", """SELECT
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
ORDER BY e.exercise_name;"""),
    ]:
        if heading.startswith("__PAGEBREAK__"):
            story.append(PageBreak())
            heading = heading.replace("__PAGEBREAK__", "")
        story.append(H2(heading))
        story.append(code_block(code, st))

    story.append(H1("9. 課表推薦演算法"))
    story.append(B("第一版不使用 AI API，而是採用資料庫資料與 rule based recommendation algorithm。系統會先讀取使用者的訓練目標、訓練經驗、偏好部位、每週訓練天數與每次訓練時間，再從 exercises 查詢符合難度與身體部位的候選動作。"))
    story.append(code_block("""Input: user_id

1. 讀取 users 中的 profile、training_goal、days_per_week 與 duration
2. 讀取 user_body_parts 取得使用者想加強的 body parts
3. 建立 weekly split
   a. 依每週天數決定 Push / Pull / Legs / Upper / Lower 或 Full Body
   b. 使用者偏好部位提高出現頻率
   c. 仍保留主要肌群，避免課表過度偏向單一部位
4. For each plan day:
   a. 從 exercises 查詢候選動作
   b. 依 training_experience 過濾 difficulty_level
   c. 依 training_goal 決定 sets、reps、rest_seconds
   d. 寫入 workout_plans、plan_days、plan_exercises
5. 回傳完整 workout plan""", st))

    story.append(H1("10. 非功能需求與部署計畫"))
    story.extend(bullets(["密碼不得明文儲存，必須使用 password_hash。", "DATABASE_URL、SECRET_KEY、API KEY、Password 皆使用 Environment Variables。", "PostgreSQL 必須部署在雲端，不能只存在 localhost。", "網站必須有公開網址，老師不需要 GitHub 帳號即可測試。", "README 必須包含 Project Description、Database Design、ER Diagram、Installation、Environment Variables、Local Development、Deployment 與 Live Demo。"]))
    story.append(pdf_table(["項目", "說明"], [
        ["GitHub Repository", "Source Code 存放於 GitHub，排除 .env 與敏感資訊。"],
        ["Web Service", "後端與前端部署至 Render 或其他雲端平台。"],
        ["Cloud Database", "PostgreSQL 部署於雲端。"],
        ["Public URL", "部署後提供公開網址，老師可直接開啟測試。"],
    ], [4.0, 12.0], st))

    story.append(H1("11. 驗收測試案例"))
    story.append(pdf_table(["編號", "測試項目", "預期結果"], [
        ["AT-01", "註冊", "users 與 user_auth 各新增一筆資料。"],
        ["AT-02", "登入", "系統回傳有效 session 或 token。"],
        ["AT-03", "選擇多個部位", "user_body_parts 新增多筆資料。"],
        ["AT-04", "產生課表", "workout_plans、plan_days、plan_exercises 皆有資料。"],
        ["AT-05", "開始運動", "workout_sessions 新增 in_progress session。"],
        ["AT-06", "紀錄每一組", "workout_sets 新增重量與次數。"],
        ["AT-07", "Dashboard", "正確顯示總訓練量、每週次數與常用動作。"],
    ], [2.0, 4.0, 10.0], st))

    story.append(H1("12. 資料庫課程重點對應"))
    story.append(pdf_table(["課程要求", "本專題如何展示"], [
        ["Primary Key", "每個主要資料表皆有 PK，junction table 使用 composite PK。"],
        ["Foreign Key", "users、exercises、plans、sessions、sets 之間使用 FK 維持完整性。"],
        ["1:N Relationship", "users -> workout_sessions；workout_sessions -> workout_sets。"],
        ["M:N Relationship", "users <-> body_parts 透過 user_body_parts。"],
        ["Normalization", "training_goals、body_parts、exercises、auth、sessions 分離，符合 3NF。"],
        ["CRUD", "users、exercises、plans、sessions、sets、body_records 皆有 CRUD 情境。"],
        ["JOIN", "Workout History 與 Dashboard 需要 JOIN 多張表。"],
        ["GROUP BY", "每週訓練量、最常訓練部位與常用 exercise 都使用 GROUP BY。"],
        ["Aggregate Functions", "SUM(volume)、COUNT(session)、AVG(weight) 等。"],
    ], [4.2, 11.8], st))

    story.append(H1("13. 結論"))
    story.append(B("Fitness Tracking Management System 是以關聯式資料庫為核心的健身紀錄管理系統。系統透過 users、user_auth、training_goals、body_parts、exercises、workout_plans、plan_days、plan_exercises、workout_sessions、workout_sets 與 body_records 建立完整資料模型，並支援註冊登入、課表產生、開始運動、即時紀錄每一組、歷史查詢與 Dashboard 統計。"))
    story.append(B("本設計可展示 PK、FK、1:N、M:N、3NF、CRUD、JOIN、GROUP BY、Aggregate Functions、Indexes 與雲端資料庫部署。"))

    def decorate(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont(st["base"], 8)
        canvas.setFillColor(colors.HexColor("#6B7C8F"))
        canvas.drawString(1.8 * cm, 1.0 * cm, "Fitness Tracking Management System 系統規格書")
        canvas.drawRightString(A4[0] - 1.8 * cm, 1.0 * cm, f"Page {doc_obj.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)


def main() -> None:
    ensure_dirs()
    arch = make_architecture_image()
    erd = make_erd_image()
    make_docx(arch, erd)
    make_pdf(arch, erd)
    print(OUT_DOCX)
    print(OUT_PDF)


if __name__ == "__main__":
    main()
