from fastapi.testclient import TestClient


def create_profile(client: TestClient) -> dict:
    response = client.post(
        "/api/users",
        json={
            "name": "Demo Student",
            "gender": None,
            "age": 22,
            "height_cm": 170,
            "weight_kg": 68.4,
            "training_experience": "beginner",
            "training_goal_id": 1,
            "training_days_per_week": 4,
            "training_duration_minutes": 60,
            "preferred_body_part_ids": [1, 2],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/admin/login",
        json={"username": "admin", "password": "admin-test-password"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_health_and_reference_catalogues(client: TestClient) -> None:
    assert client.get("/api/health").json() == {"status": "ok"}
    assert len(client.get("/api/reference/training-goals").json()) == 4
    assert len(client.get("/api/reference/body-parts").json()) == 8
    exercises = client.get("/api/reference/exercises").json()
    assert len(exercises) >= 30
    assert all(item["image_url"] for item in exercises)


def test_complete_onboarding_plan_workout_and_dashboard_flow(client: TestClient) -> None:
    profile = create_profile(client)
    user_id = profile["user_id"]
    assert profile["latest_weight_kg"] == "68.40"
    assert {part["body_part_code"] for part in profile["preferred_body_parts"]} == {
        "chest",
        "back",
    }

    plan_response = client.post(f"/api/users/{user_id}/plans/generate")
    assert plan_response.status_code == 201, plan_response.text
    plan = plan_response.json()
    assert plan["algorithm_version"] == "rules-v1"
    assert len(plan["days"]) == 4
    chest_days = sum(
        any(item["exercise"]["body_part"]["body_part_code"] == "chest" for item in day["exercises"])
        for day in plan["days"]
    )
    assert chest_days >= 2

    first_day = plan["days"][0]
    session_response = client.post(
        f"/api/users/{user_id}/workouts/sessions",
        json={"plan_day_id": first_day["plan_day_id"]},
    )
    assert session_response.status_code == 201, session_response.text
    workout = session_response.json()
    exercise_id = first_day["exercises"][0]["exercise"]["exercise_id"]

    for set_number, (weight, reps) in enumerate([(60, 12), (65, 10), (65, 8)], start=1):
        set_response = client.post(
            f"/api/users/{user_id}/workouts/sessions/{workout['session_id']}/sets",
            json={
                "exercise_id": exercise_id,
                "set_number": set_number,
                "weight_kg": weight,
                "reps": reps,
            },
        )
        assert set_response.status_code == 201, set_response.text

    completed = client.post(
        f"/api/users/{user_id}/workouts/sessions/{workout['session_id']}/complete"
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "completed"

    dashboard_response = client.get(f"/api/users/{user_id}/dashboard?days=28")
    assert dashboard_response.status_code == 200, dashboard_response.text
    dashboard = dashboard_response.json()
    assert dashboard["this_week_workouts"] == 1
    assert dashboard["total_completed_workouts"] == 1
    assert dashboard["total_training_volume_kg"] == 1890.0
    assert dashboard["completed_workouts"] == 1
    assert dashboard["working_sets"] == 3
    assert dashboard["training_volume_kg"] == 1890.0
    assert dashboard["most_trained_body_part"] == "Chest"

    headers = admin_headers(client)
    admin_dashboard = client.get("/api/admin/dashboard", headers=headers)
    assert admin_dashboard.status_code == 200, admin_dashboard.text
    assert admin_dashboard.json()["total_users"] == 1
    admin_users = client.get("/api/admin/users?search=Demo", headers=headers)
    assert admin_users.status_code == 200, admin_users.text
    assert admin_users.json()["total"] == 1
    admin_detail = client.get(f"/api/admin/users/{user_id}", headers=headers)
    assert admin_detail.status_code == 200, admin_detail.text
    assert admin_detail.json()["profile"]["name"] == "Demo Student"
    admin_stats = client.get("/api/admin/statistics", headers=headers)
    assert admin_stats.status_code == 200, admin_stats.text
    assert admin_stats.json()["total_users"] == 1

    database_response = client.get(f"/api/database/overview?user_id={user_id}")
    assert database_response.status_code == 200, database_response.text
    database_overview = database_response.json()
    assert {table["table_name"] for table in database_overview["tables"]} >= {
        "users",
        "exercises",
        "workout_sets",
    }
    assert any(
        relationship["from_table"] == "workout_sets"
        and relationship["to_table"] == "workout_sessions"
        for relationship in database_overview["relationships"]
    )
    assert any(example["rows"] for example in database_overview["query_examples"])


def test_profile_and_body_record_crud(client: TestClient) -> None:
    profile = create_profile(client)
    user_id = profile["user_id"]

    update_response = client.patch(
        f"/api/users/{user_id}",
        json={
            "name": "Updated Student",
            "training_days_per_week": 5,
            "preferred_body_part_ids": [3, 8],
        },
    )
    assert update_response.status_code == 200, update_response.text
    updated = update_response.json()
    assert updated["name"] == "Updated Student"
    assert updated["training_days_per_week"] == 5
    assert {part["body_part_code"] for part in updated["preferred_body_parts"]} == {
        "shoulders",
        "core",
    }

    create_weight = client.post(
        f"/api/users/{user_id}/body-records",
        json={"recorded_on": "2025-01-01", "weight_kg": 67.8, "notes": "baseline check"},
    )
    assert create_weight.status_code == 201, create_weight.text
    record_id = create_weight.json()["body_record_id"]

    duplicate_weight = client.post(
        f"/api/users/{user_id}/body-records",
        json={"recorded_on": "2025-01-01", "weight_kg": 68.0},
    )
    assert duplicate_weight.status_code == 409

    patch_weight = client.patch(
        f"/api/users/{user_id}/body-records/{record_id}",
        json={"recorded_on": "2025-01-02", "weight_kg": 67.5},
    )
    assert patch_weight.status_code == 200, patch_weight.text
    assert patch_weight.json()["weight_kg"] == "67.50"

    records = client.get(f"/api/users/{user_id}/body-records").json()
    assert len(records) == 2
    assert records[0]["recorded_on"] == "2025-01-02"

    delete_weight = client.delete(f"/api/users/{user_id}/body-records/{record_id}")
    assert delete_weight.status_code == 204
    remaining_record_id = client.get(f"/api/users/{user_id}/body-records").json()[0][
        "body_record_id"
    ]
    cannot_delete_last_weight = client.delete(
        f"/api/users/{user_id}/body-records/{remaining_record_id}"
    )
    assert cannot_delete_last_weight.status_code == 409


def test_exercise_search_and_crud_with_foreign_key_safe_delete(client: TestClient) -> None:
    bench_search = client.get("/api/reference/exercises?search=bench")
    assert bench_search.status_code == 200
    assert any(item["exercise_name"] == "Bench Press" for item in bench_search.json())

    public_create = client.post(
        "/api/exercises",
        json={
            "exercise_name": "Blocked Public Exercise",
            "body_part_id": 8,
            "difficulty_level": "beginner",
            "equipment": "Cable",
            "movement_type": "isolation",
            "description": "Public writes should require admin authentication.",
        },
    )
    assert public_create.status_code == 401

    headers = admin_headers(client)
    admin_exercises = client.get("/api/admin/exercises?search=bench", headers=headers)
    assert admin_exercises.status_code == 200
    assert any(item["exercise_name"] == "Bench Press" for item in admin_exercises.json())

    create_response = client.post(
        "/api/exercises",
        headers=headers,
        json={
            "exercise_name": "Cable Crunch Test",
            "body_part_id": 8,
            "difficulty_level": "beginner",
            "equipment": "Cable",
            "movement_type": "isolation",
            "description": "Test exercise for CRUD coverage.",
            "image_url": "/exercise-images/core.svg",
        },
    )
    assert create_response.status_code == 201, create_response.text
    exercise_id = create_response.json()["exercise_id"]
    assert create_response.json()["image_url"] == "/exercise-images/core.svg"

    duplicate_response = client.post(
        "/api/exercises",
        headers=headers,
        json={
            "exercise_name": "cable crunch test",
            "body_part_id": 8,
            "difficulty_level": "beginner",
            "equipment": "Cable",
            "movement_type": "isolation",
            "description": "Duplicate name should be rejected case-insensitively.",
        },
    )
    assert duplicate_response.status_code == 409

    update_response = client.patch(
        f"/api/exercises/{exercise_id}",
        headers=headers,
        json={"exercise_name": "Machine Crunch Test", "difficulty_level": "intermediate"},
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["exercise_name"] == "Machine Crunch Test"

    delete_response = client.delete(f"/api/exercises/{exercise_id}", headers=headers)
    assert delete_response.status_code == 204
    assert client.get("/api/reference/exercises?search=Machine%20Crunch%20Test").json() == []

    profile = create_profile(client)
    user_id = profile["user_id"]
    plan = client.post(f"/api/users/{user_id}/plans/generate").json()
    referenced_exercise = plan["days"][0]["exercises"][0]["exercise"]

    safe_delete = client.delete(
        f"/api/exercises/{referenced_exercise['exercise_id']}", headers=headers
    )
    assert safe_delete.status_code == 204
    inactive_search = client.get(
        "/api/reference/exercises",
        params={"include_inactive": True, "search": referenced_exercise["exercise_name"]},
    )
    assert inactive_search.status_code == 200
    assert any(item["is_active"] is False for item in inactive_search.json())


def test_plan_and_workout_set_editing_crud(client: TestClient) -> None:
    profile = create_profile(client)
    user_id = profile["user_id"]
    plan = client.post(f"/api/users/{user_id}/plans/generate").json()
    first_day = plan["days"][0]
    first_plan_exercise = first_day["exercises"][0]

    update_plan_exercise = client.patch(
        f"/api/users/{user_id}/plans/{plan['plan_id']}/exercises/{first_plan_exercise['plan_exercise_id']}",
        json={"target_sets": 4, "target_reps": 8, "notes": "Strength emphasis"},
    )
    assert update_plan_exercise.status_code == 200, update_plan_exercise.text
    changed = update_plan_exercise.json()["days"][0]["exercises"][0]
    assert changed["target_sets"] == 4
    assert changed["target_reps"] == 8

    session = client.post(
        f"/api/users/{user_id}/workouts/sessions",
        json={"plan_day_id": first_day["plan_day_id"]},
    ).json()
    exercise_id = first_plan_exercise["exercise"]["exercise_id"]

    set_response = client.post(
        f"/api/users/{user_id}/workouts/sessions/{session['session_id']}/sets",
        json={"exercise_id": exercise_id, "set_number": 1, "weight_kg": 40, "reps": 12},
    )
    assert set_response.status_code == 201, set_response.text
    set_id = set_response.json()["workout_set_id"]

    patch_set = client.patch(
        f"/api/users/{user_id}/workouts/sessions/{session['session_id']}/sets/{set_id}",
        json={"weight_kg": 42.5, "reps": 10, "notes": "felt solid"},
    )
    assert patch_set.status_code == 200, patch_set.text
    assert patch_set.json()["weight_kg"] == "42.50"

    delete_set = client.delete(
        f"/api/users/{user_id}/workouts/sessions/{session['session_id']}/sets/{set_id}"
    )
    assert delete_set.status_code == 204
    complete_empty = client.post(
        f"/api/users/{user_id}/workouts/sessions/{session['session_id']}/complete"
    )
    assert complete_empty.status_code == 409

    delete_session = client.delete(
        f"/api/users/{user_id}/workouts/sessions/{session['session_id']}"
    )
    assert delete_session.status_code == 204

    delete_plan = client.delete(f"/api/users/{user_id}/plans/{plan['plan_id']}")
    assert delete_plan.status_code == 204
