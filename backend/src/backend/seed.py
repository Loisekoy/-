from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_session_factory
from backend.models import BodyPart, Exercise, TrainingGoal

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
                )
            )
        else:
            existing_exercise.image_url = existing_exercise.image_url or image_url
    db.commit()


def main() -> None:
    with get_session_factory()() as db:
        seed_database(db)
    print("Seeded training goals, body parts, and exercises.")


if __name__ == "__main__":
    main()
