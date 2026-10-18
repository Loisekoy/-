# Fitness Tracking Management System v1.1 驗證報告

日期：2026-10-06  
範圍：老師審查意見修訂版的文件、PHP 應用、PostgreSQL Schema、Migration、排程與測試  
原則：只記錄實際執行結果；效能門檻若未實測，不標示通過。

## 結果摘要

| 驗證項目 | 結果 | 實際證據 |
|---|---|---|
| PHP 語法 | PASS | 專案內全部 PHP 檔案逐一執行 `php -l`，無語法錯誤。 |
| SQLite 功能回歸 | PASS | `php tests/smoke.php` 全部斷言通過，涵蓋登入、Cookie／CSRF、CRUD、排課、開始運動、逐組儲存、最後一組保護、歷史與統計。 |
| Schema Manifest | PASS | `python3 tests/schema_consistency.py`：20 張應用表、25 條 FK 與 Manifest 一致。 |
| JavaScript 語法 | PASS | `node --check public/assets/app.js` 無錯誤。 |
| PostgreSQL Fresh Schema | PASS | 空白 PostgreSQL 16 測試庫成功執行 `database/postgres.sql` 與 `bin/setup.php`；實際統計為 20 表／25 FK。 |
| PostgreSQL Trigger／Constraint | PASS | `tests/postgres_integrity.php` 驗證 READ COMMITTED、跨場快照拒絕、動作版本不可變、最後一筆體重、completed 至少一組。 |
| completed 約束繞過 | PASS | 直接完成空場次、刪除 completed 最後一組、刪除其最後場次動作快照，三種操作均被拒絕並回滾。 |
| 平行開始運動 | PASS | 兩個獨立連線同時開始同一課表日，最後只有一筆 `in_progress`；回應為 201 與 200，兩者 ID 相同。 |
| 舊版 Migration | PASS | 由舊版 Schema 與代表資料執行 `20261006_teacher_review_v1_1.sql`；回填產課快照、動作版本與歷史後仍可查詢。 |
| 過期資料清理 | PASS | `cleanup-expired.php` 刪除 1 筆過期 Session 與 1 筆舊限流事件；1 筆有效 Session 保留。 |
| DOCX 結構 | PASS | Word 文件可編輯；含 Word Styles、自動目錄、35 個表格、5 張圖；目錄頁碼已更新。 |
| PDF 內容與版面 | PASS | Microsoft Word 原生匯出 A4 PDF，共 55 頁；PDF 文字可擷取；55／55 頁已渲染並目視檢查，無裁切、亂碼或表格超界。 |

## PostgreSQL 專屬驗證明細

隔離測試庫執行下列情境：

1. `SHOW transaction_isolation` 回傳 `read committed`。
2. Schema 實際統計為 20 張應用表與 25 條外鍵。
3. completed 空場次在 COMMIT 時被 deferred constraint trigger 拒絕。
4. completed 場次的最後一組不可刪除。
5. 刪除最後一個 `workout_session_exercises` 快照也無法繞過上一項限制。
6. `exercise_versions` 已引用版本禁止 UPDATE／DELETE。
7. Profile 完成後的最後一筆 `body_records` 不可刪除。
8. 兩個平行「開始運動」請求不會建立兩筆進行中場次。
9. 舊版資料 Migration 後仍保留 `Legacy Press`、50.00 kg、10 reps 的歷史顯示。
10. Migration 版本記錄為 `20261006_teacher_review_v1_1`。

## 文件品質檢查

- DOCX：`Fitness_Tracking_Management_System_SRS_中文版_正式修訂版_v1.1.docx`
- PDF：`Fitness_Tracking_Management_System_SRS_中文版_正式修訂版_v1.1.pdf`
- PDF 頁數：55
- 紙張：A4
- 目錄主要頁碼：專案概述 4、系統架構 6、功能需求 8、資料模型 23、驗收測試 50、參考資料 54、附錄 55
- ERD：圖 2 至圖 5，R01–R25 與資料庫外鍵對照
- 關鍵文字掃描：確認 `TC-16` 三種繞過、`TC-28` 圖片 URL 邊界、20 表／25 FK；未出現舊 19 表／23 FK 與誤植字串
- 全頁目視結果：封面、目錄、架構圖、ERD、資料字典、SQL、驗收表、參考資料與附錄均可讀

## 尚未宣稱通過的項目

1. NFR-01 的正式雲端 P95 回應時間。
2. NFR-02 的 200 個並行虛擬使用者、連續 5 分鐘負載測試。
3. 正式 Render Web Service、Render Cron 與 Cloud PostgreSQL 的實際部署驗收。
4. GitHub Push 與公開網址驗收。

上述項目需要正式雲端環境、公開網址與監測資料後才能判定，規格書僅定義門檻與測試方法。
