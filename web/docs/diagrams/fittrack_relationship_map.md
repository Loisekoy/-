# FitTrack Pro 資料庫關係圖

這是一張給初學者看的總覽圖。先看資料如何連接，再回到
`web/php-app/database/postgres.sql` 查看每個欄位、限制與 Trigger。

## 一、資料表關係總覽

```mermaid
erDiagram
    TRAINING_GOALS ||--o{ USERS : "訓練目標"
    USERS ||--|| USER_AUTH : "登入資料"
    USER_AUTH ||--o{ USER_SESSIONS : "登入工作階段"
    USERS ||--o| ADMINS : "管理員資格"

    USERS ||--o{ BODY_RECORDS : "體重紀錄"
    USERS ||--o{ USER_BODY_PARTS : "偏好部位"
    BODY_PARTS ||--o{ USER_BODY_PARTS : "被選擇"

    BODY_PARTS ||--o{ EXERCISES : "所屬部位"
    EXERCISES ||--o{ EXERCISE_VERSIONS : "動作版本"

    USERS ||--o{ WORKOUT_PLANS : "擁有課表"
    WORKOUT_PLANS ||--o| PLANNING_PROFILES : "規劃快照"
    PLANNING_PROFILES ||--o{ PLANNING_PROFILE_BODY_PARTS : "規劃部位"
    BODY_PARTS ||--o{ PLANNING_PROFILE_BODY_PARTS : "被規劃"
    WORKOUT_PLANS ||--o{ PLAN_DAYS : "訓練日"
    PLAN_DAYS ||--o{ PLAN_EXERCISES : "課表動作"
    EXERCISE_VERSIONS ||--o{ PLAN_EXERCISES : "被安排"
    WORKOUT_PLANS ||--o{ WORKOUT_PLANS : "複製來源"

    WORKOUT_SESSIONS ||--o| WORKOUT_SESSION_PLANS : "使用哪一天"
    PLAN_DAYS ||--o{ WORKOUT_SESSION_PLANS : "被開始"
    WORKOUT_SESSIONS ||--o{ WORKOUT_SESSION_EXERCISES : "訓練快照"
    PLAN_EXERCISES ||--o{ WORKOUT_SESSION_EXERCISES : "來源動作"
    EXERCISE_VERSIONS ||--o{ WORKOUT_SESSION_EXERCISES : "當時版本"
    WORKOUT_SESSION_EXERCISES ||--o{ WORKOUT_SETS : "實際組數"

    SCHEMA_MIGRATIONS {
        varchar version PK
        timestamptz applied_at
    }
    LOGIN_FAILURES {
        bigint login_failure_id PK
        char ip_hash
        timestamptz failed_at
    }
```

### 圖上的符號

| 符號 | 意思 |
|---|---|
| `||--||` | 一對一，例如 `users` 與 `user_auth` |
| `||--o{` | 一對多，例如一位會員有很多體重紀錄 |
| `USER_BODY_PARTS` | 中間表，負責實作多對多 |
| `EXERCISE_VERSIONS` | 不覆蓋舊資料的版本表 |
| `WORKOUT_SESSION_EXERCISES` | 開始訓練時建立的快照表 |

## 二、使用者實際操作時的資料流

```mermaid
flowchart TD
    A[使用者註冊或登入] --> B[users + user_auth]
    B --> C[user_sessions]
    C --> D[編輯個人資料與體重]
    D --> E[body_records]
    D --> F[user_body_parts]

    B --> G[建立課表]
    G --> H[workout_plans]
    H --> I[plan_days]
    I --> J[plan_exercises]
    J --> K[exercise_versions]

    H --> L[開始訓練]
    L --> M[workout_sessions]
    M --> N[workout_session_exercises 快照]
    N --> O[workout_sets]
    O --> P[完成或取消訓練]

    Q[管理員停用會員] --> R[user_auth.is_active = false]
    R --> S[撤銷 user_sessions]
    S --> T[會員下次請求回傳 401]
```

## 三、最重要的理解方式

1. `users` 是「誰」。
2. `exercises` 是「哪個動作」。
3. `workout_plans` 是「預計要做什麼」。
4. `workout_sessions` 是「這次實際做了什麼」。
5. `workout_sets` 是「每個動作實際完成的第幾組、重量與次數」。
6. `exercise_versions` 和 `workout_session_exercises` 共同保護歷史資料不被後續修改破壞。
