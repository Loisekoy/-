# SQL Query Demonstrations

以下查詢以 PostgreSQL 為準，對應「資料庫系統」課程要求的 JOIN、搜尋、GROUP BY 與 Aggregate Functions。API 實作位於 `backend/src/backend/routers/`。

## 1. Exercise search with JOIN

```sql
SELECT
    e.exercise_id,
    e.exercise_name,
    bp.name_en AS body_part,
    e.difficulty_level,
    e.equipment
FROM exercises AS e
JOIN body_parts AS bp
  ON bp.body_part_id = e.body_part_id
WHERE e.is_active = TRUE
  AND e.exercise_name ILIKE '%press%'
ORDER BY e.exercise_name;
```

## 2. Complete workout plan

```sql
SELECT
    wp.plan_name,
    pd.day_number,
    pd.focus_summary,
    pe.exercise_order,
    e.exercise_name,
    bp.name_en AS body_part,
    pe.target_sets,
    pe.target_reps,
    pe.rest_seconds
FROM workout_plans AS wp
JOIN plan_days AS pd
  ON pd.plan_id = wp.plan_id
JOIN plan_exercises AS pe
  ON pe.plan_day_id = pd.plan_day_id
JOIN exercises AS e
  ON e.exercise_id = pe.exercise_id
JOIN body_parts AS bp
  ON bp.body_part_id = e.body_part_id
WHERE wp.user_id = :user_id
  AND wp.status = 'active'
ORDER BY pd.day_number, pe.exercise_order;
```

## 3. Training Volume by session

`Training Volume = SUM(weight_kg × reps)`，暖身組不納入工作量。

```sql
SELECT
    ws.session_id,
    ws.session_name,
    ws.started_at,
    COUNT(wset.workout_set_id) AS working_sets,
    SUM(wset.weight_kg * wset.reps) AS training_volume_kg
FROM workout_sessions AS ws
JOIN workout_sets AS wset
  ON wset.session_id = ws.session_id
WHERE ws.user_id = :user_id
  AND ws.status = 'completed'
  AND wset.is_warmup = FALSE
GROUP BY ws.session_id, ws.session_name, ws.started_at
ORDER BY ws.started_at DESC;
```

## 4. Weekly workout frequency and volume

```sql
SELECT
    DATE_TRUNC('week', ws.started_at) AS week_start,
    COUNT(DISTINCT ws.session_id) AS workout_count,
    COUNT(wset.workout_set_id) AS working_sets,
    COALESCE(SUM(wset.weight_kg * wset.reps), 0) AS training_volume_kg
FROM workout_sessions AS ws
LEFT JOIN workout_sets AS wset
  ON wset.session_id = ws.session_id
 AND wset.is_warmup = FALSE
WHERE ws.user_id = :user_id
  AND ws.status = 'completed'
GROUP BY DATE_TRUNC('week', ws.started_at)
ORDER BY week_start;
```

## 5. Most-trained body part

```sql
SELECT
    bp.body_part_id,
    bp.name_en,
    COUNT(wset.workout_set_id) AS set_count
FROM workout_sets AS wset
JOIN workout_sessions AS ws
  ON ws.session_id = wset.session_id
JOIN exercises AS e
  ON e.exercise_id = wset.exercise_id
JOIN body_parts AS bp
  ON bp.body_part_id = e.body_part_id
WHERE ws.user_id = :user_id
  AND ws.status = 'completed'
  AND wset.is_warmup = FALSE
GROUP BY bp.body_part_id, bp.name_en
ORDER BY set_count DESC, bp.name_en
LIMIT 1;
```

## 6. Exercise history

```sql
SELECT
    e.exercise_id,
    e.exercise_name,
    COUNT(wset.workout_set_id) AS set_count,
    MAX(wset.weight_kg) AS max_weight_kg,
    SUM(wset.weight_kg * wset.reps) AS total_volume_kg
FROM workout_sets AS wset
JOIN workout_sessions AS ws
  ON ws.session_id = wset.session_id
JOIN exercises AS e
  ON e.exercise_id = wset.exercise_id
WHERE ws.user_id = :user_id
  AND ws.status = 'completed'
  AND wset.is_warmup = FALSE
GROUP BY e.exercise_id, e.exercise_name
ORDER BY set_count DESC, e.exercise_name;
```

## 7. Body Weight History

```sql
SELECT recorded_on, weight_kg
FROM body_records
WHERE user_id = :user_id
ORDER BY recorded_on;
```
