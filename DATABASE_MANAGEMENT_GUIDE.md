# Fitness Tracking Management System Database Management Guide

本文件是給「資料庫系統」課程展示與維護用的資料庫管理指南。範例以 PostgreSQL 為主，本機測試可用 SQLite，但正式部署請使用 Cloud PostgreSQL。

## 1. 系統資料庫定位

本專案不是只有前端畫面，而是以資料庫設計為核心：

- 使用者資料存在 `users`
- 偏好部位用 `user_body_parts` junction table 表達 M:N
- Exercise Library 存在 `exercises`
- AI / fallback 產生的課表存在 `workout_plans`、`plan_days`、`plan_exercises`
- 實際訓練紀錄存在 `workout_sessions`、`workout_sets`
- 體重歷史存在 `body_records`
- LLM 呼叫狀態存在 `llm_generations`

## 2. Cloud Database 原則

正式 Demo 不可依賴 localhost database。Render Blueprint 會建立 Cloud PostgreSQL，並自動把 connection string 注入 `DATABASE_URL`。

```yaml
DATABASE_URL:
  fromDatabase:
    name: fitness-tracking-management-system-db
    property: connectionString
```

## 3. 敏感資料管理

不要把以下內容 commit 到 GitHub：

- `DATABASE_URL`
- `SECRET_KEY`
- `ADMIN_BOOTSTRAP_PASSWORD`
- `OPENAI_API_KEY`
- 任何 password / token / API key

只放在 `.env` 或雲端平台 environment variables。

## 4. 本機資料庫設定

建立 PostgreSQL database：

```bash
createdb fitness_tracker
```

設定 `backend/.env`：

```bash
DATABASE_URL=postgresql+psycopg://postgres:password@localhost:5432/fitness_tracker
SECRET_KEY=local-development-secret
ADMIN_BOOTSTRAP_USERNAME=admin
ADMIN_BOOTSTRAP_PASSWORD=local-admin-password
OPENAI_API_KEY=
```

## 5. Migration 指令

套用所有 migration：

```bash
cd backend
uv run alembic upgrade head
```

查看目前版本：

```bash
uv run alembic current
```

查看 migration history：

```bash
uv run alembic history
```

## 6. Seed 資料

Seed 會建立 training goals、body parts、exercises 與 admin bootstrap account。

```bash
cd backend
uv run fitness-seed
```

Seed 是 idempotent，可重複執行，不會重複建立相同 reference data。

## 7. 主要資料表

| Table | 類型 | 說明 |
|---|---|---|
| `training_goals` | reference | 訓練目標 |
| `body_parts` | reference | 身體部位 |
| `exercises` | master data | 動作資料庫 |
| `users` | entity | 匿名使用者 |
| `user_body_parts` | junction | User ↔ Body Part |
| `workout_plans` | transaction | 產生課表 |
| `plan_days` | transaction | 課表天 |
| `plan_exercises` | transaction | 每天動作 |
| `workout_sessions` | transaction | 實際訓練 |
| `workout_sets` | transaction | 每組紀錄 |
| `body_records` | transaction | 體重紀錄 |
| `llm_generations` | audit | LLM 狀態 |

## 8. Primary Keys

常見查詢：

```sql
SELECT table_name, constraint_name
FROM information_schema.table_constraints
WHERE constraint_type = 'PRIMARY KEY'
  AND table_schema = 'public'
ORDER BY table_name;
```

代表性 PK：

- `users.user_id`
- `exercises.exercise_id`
- `workout_plans.plan_id`
- `workout_sessions.session_id`
- `workout_sets.workout_set_id`
- `user_body_parts(user_id, body_part_id)`

## 9. Foreign Keys

查詢 FK：

```sql
SELECT
  tc.table_name,
  kcu.column_name,
  ccu.table_name AS foreign_table_name,
  ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
ORDER BY tc.table_name, kcu.column_name;
```

## 10. 1:N Relationships

範例：

- `users` 1:N `workout_plans`
- `workout_plans` 1:N `plan_days`
- `plan_days` 1:N `plan_exercises`
- `workout_sessions` 1:N `workout_sets`
- `users` 1:N `body_records`

## 11. M:N Relationship

User 與 Body Part 是 M:N：

```sql
SELECT u.name, bp.name_en, bp.name_zh
FROM users u
JOIN user_body_parts ubp ON ubp.user_id = u.user_id
JOIN body_parts bp ON bp.body_part_id = ubp.body_part_id;
```

不要把多個部位存在 `VARCHAR`，因為那會違反 1NF，也不利於 JOIN / GROUP BY。

## 12. 3NF 正規化說明

- 1NF：欄位保持 atomic value；多選 body parts 拆到 junction table
- 2NF：複合主鍵 `user_body_parts` 的 `selected_at` 依賴完整主鍵
- 3NF：`users` 不重複儲存 goal name 或 body part name；名稱存於 reference table

## 13. Exercise Library 管理

查詢所有 active exercises：

```sql
SELECT e.exercise_id, e.exercise_name_en, e.exercise_name_zh, bp.name_en AS body_part
FROM exercises e
JOIN body_parts bp ON bp.body_part_id = e.body_part_id
WHERE e.is_active = TRUE
ORDER BY bp.display_order, e.exercise_name_en;
```

## 14. Exercise GIF / Image 欄位

`exercises` 包含：

- `gif_url`
- `image_url`
- `target_muscles`
- `secondary_muscles`
- `instructions_en`
- `instructions_zh`

查詢缺少 GIF 的動作：

```sql
SELECT exercise_id, exercise_name_en, exercise_name_zh
FROM exercises
WHERE gif_url IS NULL;
```

## 15. LLM 產生紀錄

查詢 LLM 成功/失敗/fallback：

```sql
SELECT status, used_fallback, COUNT(*) AS count
FROM llm_generations
GROUP BY status, used_fallback
ORDER BY status;
```

查看最近紀錄：

```sql
SELECT provider, model, status, used_fallback, error_message, created_at
FROM llm_generations
ORDER BY created_at DESC
LIMIT 20;
```

## 16. Workout Plan 查詢

查詢某使用者 active plan：

```sql
SELECT plan_id, plan_name, algorithm_version, status, generated_at
FROM workout_plans
WHERE user_id = :user_id
  AND status = 'active';
```

## 17. Plan Day + Exercises JOIN

```sql
SELECT
  pd.day_number,
  pd.focus_summary,
  pe.exercise_order,
  e.exercise_name_zh,
  pe.target_sets,
  pe.target_reps,
  pe.rest_seconds
FROM workout_plans wp
JOIN plan_days pd ON pd.plan_id = wp.plan_id
JOIN plan_exercises pe ON pe.plan_day_id = pd.plan_day_id
JOIN exercises e ON e.exercise_id = pe.exercise_id
WHERE wp.plan_id = :plan_id
ORDER BY pd.day_number, pe.exercise_order;
```

## 18. Start Workout 的資料寫入

開始訓練會建立：

- `workout_sessions`
- `session_plan_days`

```sql
SELECT ws.session_id, ws.status, spd.plan_day_id
FROM workout_sessions ws
LEFT JOIN session_plan_days spd ON spd.session_id = ws.session_id
ORDER BY ws.started_at DESC;
```

## 19. 每組即時存入 Database

每完成一組會立刻寫入 `workout_sets`：

```sql
SELECT
  ws.session_id,
  e.exercise_name_zh,
  wset.set_number,
  wset.weight_kg,
  wset.reps,
  wset.weight_kg * wset.reps AS volume
FROM workout_sets wset
JOIN workout_sessions ws ON ws.session_id = wset.session_id
JOIN exercises e ON e.exercise_id = wset.exercise_id
ORDER BY wset.logged_at DESC;
```

## 20. Training Volume

Volume 定義：

```text
Volume = Weight × Reps
```

總訓練量：

```sql
SELECT COALESCE(SUM(weight_kg * reps), 0) AS total_volume_kg
FROM workout_sets
WHERE is_warmup = FALSE;
```

## 21. GROUP BY：部位訓練量

```sql
SELECT
  bp.name_en AS body_part,
  COUNT(wset.workout_set_id) AS sets,
  COALESCE(SUM(wset.weight_kg * wset.reps), 0) AS volume_kg
FROM body_parts bp
JOIN exercises e ON e.body_part_id = bp.body_part_id
JOIN workout_sets wset ON wset.exercise_id = e.exercise_id
JOIN workout_sessions ws ON ws.session_id = wset.session_id
WHERE ws.status = 'completed'
GROUP BY bp.body_part_id, bp.name_en
ORDER BY volume_kg DESC;
```

## 22. Aggregate：每週訓練次數

```sql
SELECT
  DATE_TRUNC('week', started_at) AS week,
  COUNT(*) AS sessions
FROM workout_sessions
WHERE status = 'completed'
GROUP BY DATE_TRUNC('week', started_at)
ORDER BY week DESC;
```

## 23. Most Used Exercise

```sql
SELECT
  e.exercise_name_en,
  e.exercise_name_zh,
  COUNT(wset.workout_set_id) AS set_count
FROM workout_sets wset
JOIN exercises e ON e.exercise_id = wset.exercise_id
GROUP BY e.exercise_id, e.exercise_name_en, e.exercise_name_zh
ORDER BY set_count DESC
LIMIT 10;
```

## 24. Body Weight History

```sql
SELECT recorded_on, weight_kg
FROM body_records
WHERE user_id = :user_id
ORDER BY recorded_on;
```

## 25. Indexes

重要 indexes：

- `ix_users_training_goal_id`
- `ix_user_body_parts_reverse`
- `ix_exercises_recommendation`
- `ix_workout_plans_user_generated`
- `uq_workout_plans_one_active`
- `ix_sessions_user_started`
- `ix_sessions_user_status`
- `ix_workout_sets_exercise_logged`
- `ix_llm_generations_user_created`

查詢 indexes：

```sql
SELECT indexname, tablename, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
```

## 26. Constraints

重要 constraints：

- `age BETWEEN 13 AND 100`
- `training_days_per_week IN (2,3,4,5,6)`
- `training_duration_minutes IN (30,45,60,90)`
- `target_sets BETWEEN 1 AND 6`
- `target_reps BETWEEN 1 AND 30`
- `rest_seconds BETWEEN 15 AND 300`
- `status IN ('in_progress','completed','abandoned','cancelled')`

## 27. Soft Delete Exercise

如果 exercise 已被 plan 或 workout set 引用，刪除時不真正刪 row，而是：

```sql
UPDATE exercises
SET is_active = FALSE
WHERE exercise_id = :exercise_id;
```

這可以保留歷史紀錄的 referential integrity。

## 28. Admin Bootstrap

設定：

```bash
ADMIN_BOOTSTRAP_USERNAME=admin
ADMIN_BOOTSTRAP_PASSWORD=your-password
```

執行：

```bash
uv run fitness-seed
```

seed 會把 password hash 後存入 `admins.password_hash`。

## 29. Render Cloud Database 檢查

部署後可透過網站檢查：

- `/api/health`
- `/database`
- `/api/database/overview`

也可在 Render shell 執行：

```bash
cd /app/backend
alembic current
fitness-seed
```

## 30. Backup

PostgreSQL backup：

```bash
pg_dump "$DATABASE_URL" > fitness_tracker_backup.sql
```

Restore：

```bash
psql "$DATABASE_URL" < fitness_tracker_backup.sql
```

## 31. 清除測試資料

小心：正式 demo 前不要任意清除 cloud data。

若只清除某個匿名 user：

```sql
DELETE FROM users
WHERE user_id = :user_id;
```

因為多數 child tables 使用 `ON DELETE CASCADE`，該 user 的 plans、sessions、sets、body records 會一起移除。

## 32. 常見問題

### 產生課表時沒有真的呼叫 LLM

檢查：

```sql
SELECT status, error_message, created_at
FROM llm_generations
ORDER BY created_at DESC
LIMIT 5;
```

若看到 `OPENAI_API_KEY is not configured`，代表尚未在 Render 設定 `OPENAI_API_KEY`。

### Admin 無法登入

確認 Render env 有設定：

- `ADMIN_BOOTSTRAP_USERNAME`
- `ADMIN_BOOTSTRAP_PASSWORD`

然後 redeploy 或執行 `fitness-seed`。

## 33. Demo Checklist

上台或交作業前請確認：

1. Public URL 可開啟
2. 不需要 Login / Register
3. 可建立 user
4. 可選 body parts
5. 可產生 workout plan
6. `/database` 看得到 tables / relationships / SQL examples
7. 可開始 `/workout/session/:id`
8. 每完成一組會出現在 `workout_sets`
9. 完成 session 後 `workout_sessions.status = 'completed'`
10. Dashboard training volume 有更新
11. Admin 能看到 user detail、plans、sets、LLM generation records
12. `OPENAI_API_KEY`、`DATABASE_URL`、password 沒有出現在 GitHub
