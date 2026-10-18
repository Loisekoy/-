#!/usr/bin/env python3
"""Render clean high-resolution SRS diagrams from the reviewed relationship list."""

from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "diagrams"
OUT.mkdir(parents=True, exist_ok=True)

SLATE = "#334155"
MID = "#64748B"
PALE = "#F8FAFC"
BORDER = "#CBD5E1"
WHITE = "#FFFFFF"
INK = "#111827"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    choices = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    for candidate in choices:
        if Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size=size, index=1 if bold else 0)
            except OSError:
                continue
    return ImageFont.load_default()


def centered(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, size: int, *, color: str = INK, bold: bool = False) -> None:
    fnt = font(size, bold)
    lines = text.split("\n")
    heights = [draw.textbbox((0, 0), line, font=fnt)[3] for line in lines]
    total = sum(heights) + (len(lines) - 1) * 8
    y = box[1] + (box[3] - box[1] - total) / 2
    for line, height in zip(lines, heights):
        width = draw.textbbox((0, 0), line, font=fnt)[2]
        draw.text((box[0] + (box[2] - box[0] - width) / 2, y), line, font=fnt, fill=color)
        y += height + 8


def box(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], title: str, subtitle: str = "") -> None:
    draw.rounded_rectangle(xy, radius=10, fill=WHITE, outline=BORDER, width=3)
    centered(draw, (xy[0] + 12, xy[1] + 10, xy[2] - 12, xy[1] + 65), title, 26, color=SLATE, bold=True)
    if subtitle:
        centered(draw, (xy[0] + 12, xy[1] + 66, xy[2] - 12, xy[3] - 10), subtitle, 20, color=MID)


def arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], label: str = "") -> None:
    draw.line([start, end], fill=SLATE, width=4)
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = max((dx * dx + dy * dy) ** 0.5, 1)
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    tip = end
    left = (end[0] - ux * 16 + px * 8, end[1] - uy * 16 + py * 8)
    right = (end[0] - ux * 16 - px * 8, end[1] - uy * 16 - py * 8)
    draw.polygon([tip, left, right], fill=SLATE)
    if label:
        fnt = font(18)
        bbox = draw.textbbox((0, 0), label, font=fnt)
        x = (start[0] + end[0] - (bbox[2] - bbox[0])) / 2
        y = (start[1] + end[1]) / 2 - 28
        draw.rectangle((x - 5, y - 2, x + bbox[2] - bbox[0] + 5, y + bbox[3] - bbox[1] + 3), fill=PALE)
        draw.text((x, y), label, font=fnt, fill=MID)


def canvas(title: str, width: int = 2000, height: int = 1120) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (width, height), WHITE)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, width, 92), fill=SLATE)
    centered(draw, (30, 10, width - 30, 82), title, 34, color=WHITE, bold=True)
    return img, draw


def architecture() -> None:
    img, draw = canvas("系統架構與資料流")
    boxes = {
        "browser": (90, 260, 470, 500),
        "php": (800, 210, 1210, 550),
        "db": (1530, 260, 1910, 500),
        "cron": (1530, 720, 1910, 930),
        "ai": (800, 750, 1210, 950),
    }
    box(draw, boxes["browser"], "使用者瀏覽器", "HTML / CSS / JavaScript\nRWD，同源 Fetch API")
    box(draw, boxes["php"], "PHP 8.4 Web Application", "REST API / 欄位驗證\nSession 授權 / CSRF\n交易 / 規則式排課")
    box(draw, boxes["db"], "PostgreSQL 16", "20 張應用資料表\n25 條 FK / Trigger / Index")
    box(draw, boxes["cron"], "Render Cron", "每日 03:00（Asia/Taipei）\n清理過期 Session 與限流事件")
    box(draw, boxes["ai"], "選用模型服務", "OpenAI-compatible API\n金鑰僅存於伺服器環境變數")
    arrow(draw, (470, 380), (800, 380), "HTTPS / HttpOnly Cookie / CSRF")
    arrow(draw, (1210, 380), (1530, 380), "PDO / 參數化 SQL / 交易")
    arrow(draw, (1000, 550), (1000, 750), "選用；回傳後端再驗證")
    arrow(draw, (1720, 720), (1720, 500), "cleanup-expired.php")
    img.save(OUT / "architecture_v1_1.png", dpi=(220, 220))


def relationship_diagram(title: str, nodes: list[tuple[str, str]], edges: list[tuple[int, int, str]]) -> Image.Image:
    img, draw = canvas(title, 2100, 1250)
    cols = 3
    positions: list[tuple[int, int, int, int]] = []
    w, h = 520, 175
    for index, (name, note) in enumerate(nodes):
        row, col = divmod(index, cols)
        x = 100 + col * 690
        y = 160 + row * 260
        positions.append((x, y, x + w, y + h))
        box(draw, positions[-1], name, note)
    for source, target, label in edges:
        a, b = positions[source], positions[target]
        start = ((a[0] + a[2]) // 2, a[3])
        end = ((b[0] + b[2]) // 2, b[1])
        if abs(end[1] - start[1]) < 30:
            start = (a[2], (a[1] + a[3]) // 2)
            end = (b[0], (b[1] + b[3]) // 2)
        arrow(draw, start, end, label)
    return img


def erds() -> None:
    relationship_diagram(
        "帳號、目前偏好與登入保護 ERD（R01–R07）",
        [
            ("USERS", "PK user_id\nFK training_goal_id"),
            ("USER_AUTH", "PK auth_id\nFK user_id / UQ email"),
            ("USER_SESSIONS", "PK user_session_id\nFK auth_id / expires_at"),
            ("ADMINS", "PK/FK user_id"),
            ("TRAINING_GOALS", "PK training_goal_id"),
            ("USER_BODY_PARTS", "PK user_id + body_part_id\npriority"),
            ("BODY_PARTS", "PK body_part_id"),
            ("BODY_RECORDS", "PK body_record_id\nFK user_id / UQ date"),
            ("LOGIN_FAILURES", "PK login_failure_id\nip_hash / failed_at\n（無 FK）"),
        ],
        [(0, 1, "R01 1:1"), (1, 2, "R02 1:N"), (0, 3, "R03 1:0..1"), (4, 0, "R04 1:N"), (0, 5, "R05 1:N"), (6, 5, "R06 1:N"), (0, 7, "R07 1:N")],
    ).save(OUT / "erd_accounts_v1_1.png", dpi=(220, 220))

    relationship_diagram(
        "課表與規劃輸入 ERD（R10–R18）",
        [
            ("USERS", "PK user_id"),
            ("WORKOUT_PLANS", "PK workout_plan_id\nFK user_id / self FK"),
            ("PLANNING_PROFILES", "PK/FK workout_plan_id\n規劃時快照"),
            ("TRAINING_GOALS", "PK training_goal_id"),
            ("PLANNING_PROFILE_BODY_PARTS", "PK plan_id + part_id"),
            ("BODY_PARTS", "PK body_part_id"),
            ("PLAN_DAYS", "PK plan_day_id\nFK workout_plan_id"),
            ("PLAN_EXERCISES", "PK plan_exercise_id\nFK day / version"),
            ("EXERCISE_VERSIONS", "PK exercise_version_id\n不可變版本"),
        ],
        [(0, 1, "R10 1:N"), (1, 1, "R11 self"), (1, 2, "R12 1:1"), (3, 2, "R13 1:N"), (2, 4, "R14 1:N"), (5, 4, "R15 1:N"), (1, 6, "R16 1:N"), (6, 7, "R17 1:N"), (8, 7, "R18 1:N")],
    ).save(OUT / "erd_plans_v1_1.png", dpi=(220, 220))

    relationship_diagram(
        "動作身份與不可變版本 ERD（R08–R09）",
        [
            ("BODY_PARTS", "PK body_part_id\n主要肌群"),
            ("EXERCISES", "PK exercise_id\nFK body_part_id\nis_active"),
            ("EXERCISE_VERSIONS", "PK exercise_version_id\nFK exercise_id\nUQ (exercise_id, version_no)\n名稱 / 難度 / 器材 / 說明 / 圖片"),
        ],
        [(0, 1, "R08 1:N"), (1, 2, "R09 1:N")],
    ).save(OUT / "erd_exercises_v1_1.png", dpi=(220, 220))

    relationship_diagram(
        "運動場次、來源快照與實際組數 ERD（R19–R25）",
        [
            ("USERS", "PK user_id"),
            ("WORKOUT_SESSIONS", "PK workout_session_id\nFK user_id / status"),
            ("WORKOUT_SESSION_PLANS", "PK/FK session_id\nFK plan_day_id"),
            ("PLAN_DAYS", "PK plan_day_id"),
            ("WORKOUT_SESSION_EXERCISES", "PK session_exercise_id\nFK session / plan_exercise / version\n當場目標快照"),
            ("PLAN_EXERCISES", "PK plan_exercise_id"),
            ("EXERCISE_VERSIONS", "PK exercise_version_id"),
            ("WORKOUT_SETS", "PK workout_set_id\nFK session_exercise_id\nUQ (session_exercise_id, set_number)"),
        ],
        [(0, 1, "R19 1:N"), (1, 2, "R20 1:1"), (3, 2, "R21 1:N"), (1, 4, "R22 1:N"), (5, 4, "R23 1:N"), (6, 4, "R24 1:N"), (4, 7, "R25 1:N")],
    ).save(OUT / "erd_workouts_v1_1.png", dpi=(220, 220))


if __name__ == "__main__":
    architecture()
    erds()
    print(f"Rendered diagrams in {OUT}")
