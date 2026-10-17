# Changelog

## 2026-10-16

- 動作資料匯入工具會驗證並匯入本機資料集全部 1,324 筆動作，同時複製每筆 JPG 與 GIF。
- 匯入可重跑；既有動作若有內容變更會建立新版本，不會覆寫課表與訓練歷史引用的舊版本。
- 動作庫顯示完整總筆數並提供每頁 24 筆的上一頁／下一頁導覽。
- 課表建立改為「自己規劃」與「電腦規劃」兩種模式；自己規劃可選 2 至 6 天、挑選與排序動作，並調整組數、次數與休息。
- 電腦規劃升級為 `rules-v2-randomized`，優先排除最近三份課表與本份課表已使用的動作，再從合法候選中隨機選擇。

## v1.1.2 — 2026-10-16

### Fixed

- 休息倒數只會在一組資料成功儲存後啟動；未儲存時固定顯示「儲存一組後開始」。
- 訓練頁新增以 `workout_sessions.started_at` 計算的總訓練時間，重新整理後仍會延續。
- 修正沒有進行中場次時 API 回傳空本文造成的 `0 / 0` 假場次畫面，現在正確回傳 JSON `null`。
- 取消訓練支援目前 `/cancel` 與舊版 `/cancelled` 路徑；無組數也能取消並寫入 `ended_at`。
- 新增取消流程回歸測試，並完成桌面與手機版實際瀏覽器驗收。

## v1.1.1 — 2026-10-14

### Fixed

- 本機舊版 15 表 SQLite 現在會先建立備份，再保留資料升級至 20 表 v1.1，避免登入因缺少 `login_failures` 而回傳 503。
- 首頁資料庫摘要由過時的 15 TABLES 修正為 20 TABLES。
- API 將 SQLite 的無時區時間字串正規化為 UTC `YYYY-MM-DDTHH:mm:ssZ`，前端會正確顯示台北時間。
- 新增 SQLite 升級回歸測試，驗證規劃快照、動作版本、場次快照與既有組數均能保存。
- JWT 現在固定驗證 HS256 Header 與必要欄位；CSRF 改為綁定目前 Access Token 的 HMAC Signed Double-Submit Token。
- 規則式課表依 SRS 3.11 修正天數模板、目標處方、八部位週覆蓋與時間上限。
- 動作目錄、History 與 Dashboard 補上合法篩選、分頁、台北日期與 28 天預設區間。
- 歷史明細可修正既有組數；管理端可建立動作新版本並維護固定參考資料說明。
- 新增 72 頁 SRS 對照實作狀態與公開部署前驗證邊界。

## v1.1 — 2026-10-06

### Added

- 新增不可變 `exercise_versions` 與 `workout_session_exercises`，保存動作名稱、圖片 URL、說明、處方與順序的歷史快照。
- 新增 `planning_profiles` 與 `planning_profile_body_parts`，保存產課當下的目標、年齡、身高、體重、體重日期、經驗、天數、時間與偏好部位。
- 新增 `login_failures` 滑動視窗限流事件表、跨 Worker 原子鎖定與每日清理腳本。
- 新增版本化 SQL Migration、Schema Manifest、一致性檢查與 PostgreSQL 完整性測試。
- 新增 R01–R25 正式 ERD、教師意見追蹤表與 v1.1 驗證報告。

### Changed

- Schema 統一為 20 張應用資料表、25 條外鍵；PostgreSQL 與 SQLite 測試鏡像同步。
- 公斤欄位統一為 `NUMERIC(6,2)`，並補上體重、外加重量與身高的邊界驗證。
- 開始運動改為鎖定使用者並建立來源與場次動作快照；同一使用者最多一筆 `in_progress`。
- 來源課表有進行中場次時禁止修改；當場目標可獨立調整，不回寫模板。
- Dashboard 將「總訓練量」明確改為「外加重量訓練量」，另列總次數與徒手次數。
- 正式 SRS 更新為 v1.1，含 55 頁 DOCX／PDF、最新目錄、20 表資料字典、25 FK、31 個驗收案例。

### Security

- JWT 僅保存 `sub`、`jti`、`iat`、`exp`；角色與管理員資格由資料庫即時判定。
- Access Token 改由 Secure／HttpOnly／SameSite=Strict Cookie 傳送。
- 寫入 API 增加同源 Origin／Referer 與 double-submit CSRF 驗證。
- 來源 IP 只接受明確設定的可信代理；限流只保存 HMAC 後的 `ip_hash`。

### Database Integrity

- completed 場次必須至少一組；刪最後一組、刪最後場次動作快照及直接完成空場次均在 COMMIT 時拒絕。
- 已引用動作版本不可覆寫或刪除。
- Profile 完成後至少保留一筆體重；最後一筆可修改但不可刪除。
- 場次來源、動作版本與課表日的跨表關係由 Trigger 驗證。

### Validation

- PHP lint、SQLite smoke、JavaScript syntax 與 Schema Manifest：PASS。
- PostgreSQL Fresh Schema、Migration、Trigger、歷史快照、平行開始運動與排程清理：PASS。
- Microsoft Word 原生 PDF 匯出與 55／55 頁視覺檢查：PASS。
- 正式雲端 P95 與 200 人負載測試尚未執行，不列為已通過。
