import json
import urllib.error
import urllib.request

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_session_factory
from backend.models import Admin, BodyPart, Exercise, TrainingGoal
from backend.security import hash_password

GOALS = [
    (1, "muscle_gain", "增肌", "增加肌肉量與每週訓練量", 3, 10, 75),
    (2, "fat_loss", "減脂", "以規律訓練與較短休息建立活動量", 3, 12, 45),
    (3, "strength", "力量", "優先安排複合動作與較長休息", 5, 5, 150),
    (4, "general_fitness", "一般健身", "均衡發展主要肌群與訓練習慣", 3, 10, 60),
]

BODY_PARTS = [
    (1, "chest", "Chest", "胸"),
    (2, "back", "Back", "背"),
    (3, "shoulders", "Shoulders", "肩"),
    (4, "biceps", "Biceps", "二頭"),
    (5, "triceps", "Triceps", "三頭"),
    (6, "legs", "Legs", "腿"),
    (7, "glutes", "Glutes", "臀"),
    (8, "core", "Core", "核心"),
]

BODY_PART_IMAGE_URLS = {
    "chest": "/exercise-images/chest.svg",
    "back": "/exercise-images/back.svg",
    "shoulders": "/exercise-images/shoulders.svg",
    "biceps": "/exercise-images/biceps.svg",
    "triceps": "/exercise-images/triceps.svg",
    "legs": "/exercise-images/legs.svg",
    "glutes": "/exercise-images/glutes.svg",
    "core": "/exercise-images/core.svg",
}

FALLBACK_DETAIL_BY_BODY_PART = {
    "chest": {
        "target_muscles": ["pectorals"],
        "secondary_muscles": ["triceps", "shoulders"],
        "instructions": [
            "Set your shoulder blades back and down before the press.",
            "Lower the weight under control toward the chest line.",
            "Press back to the start while keeping your elbows stable.",
        ],
    },
    "back": {
        "target_muscles": ["latissimus dorsi", "middle back"],
        "secondary_muscles": ["biceps", "rear delts"],
        "instructions": [
            "Start each pull by moving the shoulder blades down and back.",
            "Pull with your elbows instead of only your hands.",
            "Return the weight slowly and keep your torso controlled.",
        ],
    },
    "shoulders": {
        "target_muscles": ["deltoids"],
        "secondary_muscles": ["triceps", "upper traps"],
        "instructions": [
            "Brace your core and keep the ribs down.",
            "Move the weight through a smooth, pain-free range of motion.",
            "Avoid shrugging at the top of each repetition.",
        ],
    },
    "biceps": {
        "target_muscles": ["biceps"],
        "secondary_muscles": ["forearms"],
        "instructions": [
            "Keep your elbows close to your sides.",
            "Curl the weight without swinging your torso.",
            "Lower slowly until the arms are nearly straight.",
        ],
    },
    "triceps": {
        "target_muscles": ["triceps"],
        "secondary_muscles": ["shoulders"],
        "instructions": [
            "Keep the upper arms stable.",
            "Extend through the elbows until the arms are straight.",
            "Pause briefly and control the return.",
        ],
    },
    "legs": {
        "target_muscles": ["quadriceps", "hamstrings"],
        "secondary_muscles": ["glutes", "calves"],
        "instructions": [
            "Plant your feet firmly before each repetition.",
            "Keep the knees tracking in the same direction as the toes.",
            "Move through a controlled range without bouncing.",
        ],
    },
    "glutes": {
        "target_muscles": ["glutes"],
        "secondary_muscles": ["hamstrings", "core"],
        "instructions": [
            "Brace the core before initiating the hip movement.",
            "Drive through the hips and squeeze the glutes at the top.",
            "Avoid over-arching the lower back.",
        ],
    },
    "core": {
        "target_muscles": ["abdominals"],
        "secondary_muscles": ["hip flexors", "lower back"],
        "instructions": [
            "Brace your trunk as if preparing for a light punch.",
            "Keep the spine neutral and breathe steadily.",
            "Stop if you feel sharp lower-back pain.",
        ],
    },
}

EXERCISES = [
    ("Push-Up", "chest", "beginner", "bodyweight", "compound", "徒手胸推動作。"),
    ("Machine Chest Press", "chest", "beginner", "machine", "compound", "器械胸推。"),
    ("Bench Press", "chest", "intermediate", "barbell", "compound", "槓鈴平板臥推。"),
    ("Incline Dumbbell Press", "chest", "intermediate", "dumbbell", "compound", "上斜啞鈴臥推。"),
    ("Cable Fly", "chest", "intermediate", "cable", "isolation", "滑輪夾胸。"),
    ("Lat Pulldown", "back", "beginner", "cable", "compound", "高位下拉。"),
    ("Seated Cable Row", "back", "beginner", "cable", "compound", "坐姿滑輪划船。"),
    ("Assisted Pull-Up", "back", "beginner", "machine", "compound", "輔助引體向上。"),
    ("Barbell Row", "back", "intermediate", "barbell", "compound", "槓鈴划船。"),
    ("Pull-Up", "back", "intermediate", "bodyweight", "compound", "引體向上。"),
    ("Machine Shoulder Press", "shoulders", "beginner", "machine", "compound", "器械肩推。"),
    ("Lateral Raise", "shoulders", "beginner", "dumbbell", "isolation", "啞鈴側平舉。"),
    ("Face Pull", "shoulders", "beginner", "cable", "isolation", "滑輪面拉。"),
    ("Dumbbell Shoulder Press", "shoulders", "intermediate", "dumbbell", "compound", "啞鈴肩推。"),
    ("Arnold Press", "shoulders", "advanced", "dumbbell", "compound", "阿諾肩推。"),
    ("Dumbbell Curl", "biceps", "beginner", "dumbbell", "isolation", "啞鈴彎舉。"),
    ("Cable Curl", "biceps", "beginner", "cable", "isolation", "滑輪彎舉。"),
    ("Hammer Curl", "biceps", "intermediate", "dumbbell", "isolation", "錘式彎舉。"),
    ("Barbell Curl", "biceps", "intermediate", "barbell", "isolation", "槓鈴彎舉。"),
    ("Triceps Pushdown", "triceps", "beginner", "cable", "isolation", "滑輪下壓。"),
    (
        "Overhead Triceps Extension",
        "triceps",
        "beginner",
        "dumbbell",
        "isolation",
        "過頭三頭伸展。",
    ),
    ("Close-Grip Bench Press", "triceps", "intermediate", "barbell", "compound", "窄握臥推。"),
    ("Skull Crusher", "triceps", "intermediate", "barbell", "isolation", "仰臥三頭伸展。"),
    ("Bodyweight Squat", "legs", "beginner", "bodyweight", "compound", "徒手深蹲。"),
    ("Goblet Squat", "legs", "beginner", "dumbbell", "compound", "高腳杯深蹲。"),
    ("Leg Press", "legs", "beginner", "machine", "compound", "腿推。"),
    ("Leg Curl", "legs", "beginner", "machine", "isolation", "腿彎舉。"),
    ("Barbell Squat", "legs", "intermediate", "barbell", "compound", "槓鈴深蹲。"),
    ("Romanian Deadlift", "legs", "intermediate", "barbell", "compound", "羅馬尼亞硬舉。"),
    ("Glute Bridge", "glutes", "beginner", "bodyweight", "compound", "臀橋。"),
    ("Cable Kickback", "glutes", "beginner", "cable", "isolation", "滑輪後踢。"),
    ("Hip Thrust", "glutes", "intermediate", "barbell", "compound", "槓鈴臀推。"),
    ("Bulgarian Split Squat", "glutes", "intermediate", "dumbbell", "compound", "保加利亞分腿蹲。"),
    ("Plank", "core", "beginner", "bodyweight", "compound", "平板支撐，以次數欄記錄秒數。"),
    ("Dead Bug", "core", "beginner", "bodyweight", "compound", "死蟲式。"),
    ("Crunch", "core", "beginner", "bodyweight", "isolation", "捲腹。"),
    ("Russian Twist", "core", "intermediate", "bodyweight", "compound", "俄羅斯轉體。"),
    ("Hanging Leg Raise", "core", "advanced", "bodyweight", "compound", "懸垂抬腿。"),
]

EXERCISEDB_NAME_ALIASES = {
    "Bench Press": "barbell bench press",
    "Barbell Squat": "barbell squat",
    "Lat Pulldown": "cable lat pulldown",
    "Seated Cable Row": "cable seated row",
    "Dumbbell Curl": "dumbbell bicep curl",
    "Hammer Curl": "dumbbell hammer curl",
    "Triceps Pushdown": "cable triceps pushdown",
    "Push-Up": "push-up",
    "Pull-Up": "pull-up",
    "Plank": "front plank",
}


def _normalize_name(value: str) -> str:
    return " ".join(value.lower().replace("-", " ").split())


def _fetch_exercisedb_catalogue() -> list[dict]:
    settings = get_settings()
    request = urllib.request.Request(
        settings.exercisedb_api_url,
        headers={"User-Agent": "fitness-tracking-management-system/1.0"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    data = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def _apply_exercisedb_details(db: Session) -> None:
    try:
        catalogue = _fetch_exercisedb_catalogue()
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return
    by_name = {_normalize_name(str(item.get("name", ""))): item for item in catalogue}
    exercises = db.scalars(select(Exercise)).all()
    for exercise in exercises:
        lookup_name = EXERCISEDB_NAME_ALIASES.get(exercise.exercise_name, exercise.exercise_name)
        match = by_name.get(_normalize_name(lookup_name))
        if match is None:
            continue
        exercise.external_exercise_id = match.get("exerciseId") or exercise.external_exercise_id
        exercise.gif_url = match.get("gifUrl") or exercise.gif_url
        exercise.target_muscles = match.get("targetMuscles") or exercise.target_muscles
        exercise.secondary_muscles = (
            match.get("secondaryMuscles") or exercise.secondary_muscles
        )
        exercise.instructions = match.get("instructions") or exercise.instructions


def _seed_admin(db: Session) -> None:
    settings = get_settings()
    if not settings.admin_bootstrap_password:
        return
    username = settings.admin_bootstrap_username.strip()
    admin = db.scalar(select(Admin).where(Admin.username == username))
    password_hash = hash_password(settings.admin_bootstrap_password)
    if admin is None:
        db.add(Admin(username=username, password_hash=password_hash))
    else:
        admin.password_hash = password_hash
        admin.is_active = True


def seed_database(db: Session) -> None:
    existing_goal_codes = set(db.scalars(select(TrainingGoal.goal_code)).all())
    for goal_id, code, name, description, sets, reps, rest in GOALS:
        if code not in existing_goal_codes:
            db.add(
                TrainingGoal(
                    training_goal_id=goal_id,
                    goal_code=code,
                    goal_name=name,
                    description=description,
                    default_sets=sets,
                    default_reps=reps,
                    default_rest_seconds=rest,
                )
            )

    existing_part_codes = set(db.scalars(select(BodyPart.body_part_code)).all())
    for display_order, code, name_en, name_zh in BODY_PARTS:
        if code not in existing_part_codes:
            db.add(
                BodyPart(
                    body_part_id=display_order,
                    body_part_code=code,
                    name_en=name_en,
                    name_zh=name_zh,
                    display_order=display_order,
                )
            )
    db.flush()

    part_ids = dict(db.execute(select(BodyPart.body_part_code, BodyPart.body_part_id)).all())
    existing_exercises = {
        exercise.exercise_name: exercise for exercise in db.scalars(select(Exercise)).all()
    }
    for name, part_code, difficulty, equipment, movement, description in EXERCISES:
        image_url = BODY_PART_IMAGE_URLS[part_code]
        fallback_detail = FALLBACK_DETAIL_BY_BODY_PART[part_code]
        existing_exercise = existing_exercises.get(name)
        if existing_exercise is None:
            db.add(
                Exercise(
                    exercise_name=name,
                    body_part_id=part_ids[part_code],
                    difficulty_level=difficulty,
                    equipment=equipment,
                    movement_type=movement,
                    description=description,
                    image_url=image_url,
                    target_muscles=fallback_detail["target_muscles"],
                    secondary_muscles=fallback_detail["secondary_muscles"],
                    instructions=fallback_detail["instructions"],
                )
            )
        else:
            existing_exercise.image_url = existing_exercise.image_url or image_url
            existing_exercise.target_muscles = (
                existing_exercise.target_muscles or fallback_detail["target_muscles"]
            )
            existing_exercise.secondary_muscles = (
                existing_exercise.secondary_muscles or fallback_detail["secondary_muscles"]
            )
            existing_exercise.instructions = (
                existing_exercise.instructions or fallback_detail["instructions"]
            )
    if get_settings().exercisedb_sync_on_seed:
        _apply_exercisedb_details(db)
    _seed_admin(db)
    db.commit()


def main() -> None:
    with get_session_factory()() as db:
        seed_database(db)
    print("Seeded training goals, body parts, and exercises.")


if __name__ == "__main__":
    main()
