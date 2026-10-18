# Fitness Tracking Management System 實作狀態

日期：2026-10-18（總檢查更新）  
依據：`參考資料/Fitness_Tracking_Management_System_SRS_.pdf`（SRS v1.1，72 頁）  
文字基準：`參考資料/Fitness_Tracking_Management_System_SRS_.md`

## 本機功能狀態

FR-01 至 FR-18 的本機應用流程均已接入：帳號與可撤銷 Session、個人資料、目標與偏好、動作版本、規則式課表、課表封存、場次快照、逐組儲存與修正、完成／取消／刪除、歷史篩選與明細、Dashboard 日期統計、體重 CRUD，以及管理員動作與參考資料維護。

本次依 72 頁 SRS 補齊的重點：

- 舊版 15 表 SQLite 會先備份，再保留資料升級為 20 表／25 FK。
- JWT 固定驗證 HS256 Header、必要欄位與型別；正式環境拒絕預設或過短密鑰。
- CSRF 改為與 Access Token／Session 綁定的 HMAC Signed Double-Submit Token。
- JSON 未知欄位回 422；422 回應固定包含 `field_errors`。
- 動作搜尋支援名稱／部位、篩選與分頁，並提供單筆查詢。
- 規則式課表採 SRS 3.11 的 2–6 天模板、處方、八部位週覆蓋與精確時間公式。
- 場次、每組與終態操作以短交易及資料列鎖避免完成／儲存競爭。
- History 與 Dashboard 採台北日期、預設最近 28 天、最多 366 天；排名以穩定 ID 彙總。
- 前端提供日期／狀態／動作篩選、歷史組數修正、管理員版本編輯與參考說明編輯。
- 圖片失效會顯示「非此動作示範」，文字說明與紀錄功能不受影響。
- 訓練頁的休息計時器只在組數成功寫入後啟動；進入頁面時顯示等待文字，並提供獨立的總訓練計時器與取消流程。
- 課表刪除按鈕已改為「封存課表」，後台動作與參考資料欄位補上可程式辨識的 label 關聯。
- 容器每次啟動會依 `DEMO_ADMIN_PASSWORD` 同步課堂展示管理員帳號，避免 Neon／Render 既有帳號沿用舊雜湊。

## 已執行驗證

- 全部 PHP 檔案語法檢查：PASS。
- `tests/smoke.php` 完整 SQLite 流程：PASS。
- `tests/sqlite_migration.php` 舊資料原地升級：PASS。
- `tests/schema_consistency.py`：PASS（20 tables／25 foreign keys）。
- `node --check public/assets/app.js`：PASS。
- `tests/admin_bootstrap.php`：管理員初始密碼同步與舊密碼失效：PASS。
- `tests/ui_contract.php`：訓練計時器、取消／封存、表單標籤、Render 與維運契約：PASS。
- HTTP 安全檢查：缺 Origin 登入 403、合法登入 200、錯誤 CSRF 403、正確簽章 CSRF 登出 204。
- 實際瀏覽器：公開 Render 站管理員登入、管理後台與資料庫系統頁均可載入；Console 沒有 error／warning。訓練、課表與響應式畫面另有本機 QA 證據。

## 公開前仍須在部署環境驗證

下列項目需要隔離 PostgreSQL／正式託管環境，不能以本機 SQLite 或單次公開站抽查宣稱完成：

- `tests/postgres_integrity.php` 的 PostgreSQL Trigger、Constraint 與平行請求測試。
- 200 位虛擬使用者、P95、5 分鐘負載測試。
- Chrome、Safari、Edge 最新兩個主要版本的正式相容性矩陣。
- Cloud PostgreSQL TLS、HTTPS 重新導向、每日備份 7 份與獨立還原演練。

## 總檢查結論

- 本機自動化驗收與目前公開站核心管理流程：PASS。
- GitHub 分支 `codex/fitness-tracking-system` 已包含目前 Render 使用的 PHP 應用、測試、文件、完整動作媒體與 SHA-256 manifest。
- 規格書 FR-04 的 `90–250 cm` 文字與 TC-07／資料表的 `100–250 cm` 互相矛盾；實作以 TC-07／資料表為準，交件前需向老師確認。
- PostgreSQL 專屬約束、200 人負載、跨瀏覽器矩陣與備份還原仍是待取得外部測試證據的項目。
