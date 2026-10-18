Fitness Tracking
Management System
健身紀錄管理系統
軟體需求規格書（SRS）
學⽣：S11359001 陳苾妏
指導老師：⾼啟洲

Fitness Tracking Management System — SRS v1.1
目錄
1. 專案概述 ...................................................................................................................................................... 4
1.1 開發背景與痛點 ...................................................................................................................................... 4
1.2 系統目標 ................................................................................................................................................. 4
1.3 目標使用者與權限 .................................................................................................................................. 5
2. 系統架構與技術棧 ........................................................................................................................................ 6
2.1 系統架構圖 ............................................................................................................................................. 6
2.2 技術棧選型清單 ...................................................................................................................................... 7
3. 功能性需求 ................................................................................................................................................... 8
3.1 共通規則 ................................................................................................................................................. 9
3.2 會員與權限管理 .................................................................................................................................... 10
3.3 使用者基本資料管理 ............................................................................................................................. 15
3.4 訓練目標與偏好管理 ............................................................................................................................. 16
3.5 運動動作與參考資料管理 ...................................................................................................................... 17
3.6 訓練課表產⽣與管理 ............................................................................................................................. 19
3.7 開始運動與每組紀錄 ............................................................................................................................. 21
3.8 歷史紀錄與統計分析 ............................................................................................................................. 24
3.9 身體紀錄管理 ........................................................................................................................................ 26
3.10 訓練狀態與介面回應 ........................................................................................................................... 28
3.11 規則式排課與版本記錄 ........................................................................................................................ 30
4. 資料模型與結構設計 .................................................................................................................................. 31
4.1 實體關係圖 ........................................................................................................................................... 31
4.2 資料表詳細規格 .................................................................................................................................... 35
4.3 外鍵關係與刪除政策 ............................................................................................................................. 48
4.4 隔離等級與併發交易協定 ...................................................................................................................... 51
4.5 資料庫完整性與觸發器 ......................................................................................................................... 53
4.6 正規化與完整歷史保存 ......................................................................................................................... 56
4.7 JWT 身分與資料庫授權 ......................................................................................................................... 59
第 2 頁

Fitness Tracking Management System — SRS v1.1
4.8 SQL 查詢與索引 .................................................................................................................................... 60
4.9 登⼊限流與過期資料清理 ...................................................................................................................... 62
5. 非功能性需求 ............................................................................................................................................. 64
5.1 效能需求 ............................................................................................................................................... 64
5.2 安全性需求 ........................................................................................................................................... 64
5.3 易用性與相容性 .................................................................................................................................... 66
5.4 資料可靠性與可維護性 ......................................................................................................................... 66
6. 驗收測試案例 ............................................................................................................................................. 67
6.1 功能驗收 ............................................................................................................................................... 67
7. 參考資料 .................................................................................................................................................... 72
第 3 頁

Fitness Tracking Management System — SRS v1.1
1. 專案概述
1.1 開發背景與痛點
本專題的開發動機來自我自⼰的健身經驗。我目前有健身習慣，但每次到健身房
時，經常不知道當天應該做哪些動作、安排哪些部位，以及如何依自⼰的目標與程度選擇
課表，因此需要先上網搜尋或詢問 AI。這些資訊分散在不同⼯具中，查詢與訓練紀錄無法
接續，也不⽅便比較每次的重量、次數與進步情況。
本系統整合會員資料、健身目標、偏好部位、運動動作資料庫、課表規劃與訓練紀
錄。使用者查看當日課表後可直接開始運動，每完成⼀組立即存⼊資料庫，並從歷史紀錄
與 Dashboard 觀察訓練量及體重變化。資料庫設計是專題核⼼，重點包含 PK、FK、正規
化、交易、查詢與管理。
1.2 系統目標
目標 可衡量的完成條件
完成基本資料與訓練設定後，可⼀次產⽣ 2–6 天課表；每日 3–6
課表規劃
個動作、組次及休息清楚可見；暖機後 API P95≤3 秒。
每組獨立保存；每組 API P95≤1 秒；相同內容重送不新增重複
持續紀錄
組；重新載⼊後以有效 Cookie 恢復已存資料。
完成 20 張應用資料表、25 條外鍵與跨表約束；正式環境以雲端
可查詢可管理
PostgreSQL 保存資料。
第 4 頁

Fitness Tracking Management System — SRS v1.1
1.3 目標使用者與權限
角⾊ 可執⾏操作 限制
不得讀取個⼈資料、課表、歷
訪客 查看公開首頁、註冊與登⼊。
史或管理介面。
管理本⼈資料、目標、課表、訓練組 僅限本⼈所有權；不得建立管
⼀般會員 USER
數、體重與統計。 理員資格或管理共用動作。
管理員資格由 admins 決定；本
具⼀般會員能⼒；另可管理動作及修
管理員 ADMIN 版無權瀏覽其他會員的私⼈訓
改固定參考資料說明。
練紀錄。
網站使用流程：公開首頁 → 註冊／登⼊ → 基本資料 → 目標與偏好 → 產⽣課表 →
查看今日動作與圖片 → 開始運動 → 逐組儲存 → 完成訓練 → 查看歷史與統計。網站可公
開存取，登⼊的是本系統帳號，不需要 GitHub 帳號。
首版範圍包含註冊登⼊、可撤銷登⼊狀態、個⼈資料、規則式排課、圖片參考、逐
組紀錄與統計；Email 寄信驗證、忘記密碼、支付、推播及 LLM 排課列為後續擴充。
第 5 頁

Fitness Tracking Management System — SRS v1.1
2. 系統架構與技術棧
2.1 系統架構圖
本系統採 PHP 網頁範本與同源 REST API。HTML、CSS 與 JavaScript 負責介面，PHP 負責產⽣
頁面、登⼊授權、欄位驗證與排課，並透過 PDO 讀寫 PostgreSQL。資料庫憑證只留在伺服器，瀏覽器
以 Fetch API 呼叫 /api 取得 JSON。
圖 1系統架構與資料互動
第 6 頁

Fitness Tracking Management System — SRS v1.1
2.2 技術棧選型清單
| 層級  | 選用技術／⼯具  | 選用理由與說明  |
| --- | -------- | -------- |
同源介面、Fetch API 與 RWD；不需額外前
| 前端  HTML / CSS / JavaScript  |     |     |
| ---------------------------- | --- | --- |
端編譯服務。
路由、欄位驗證、Cookie／JWT Session 驗
| 後端  | PHP 8.4 / Apache  |     |
| --- | ----------------- | --- |
證、排課與 JSON API。
20 張應用表、25 條 FK，支援 Trigger、部
分唯⼀索引、JOIN、GROUP BY 與
Aggregate；登⼊限流事件存於
| 資料庫  | PostgreSQL 16  |     |
| ---- | -------------- | --- |
login_failures，配合 advisory lock 在多個
PHP Worker 間共享，不依賴 Redis 或單⼀
程序記憶體。
⼿寫參數化 SQL、交易與列鎖；關閉模擬預
| 資料存取  | PDO / PDO_PGSQL  |     |
| ----- | ---------------- | --- |
備語句。
Versioned SQL Migration /  bin/migrate.php 執⾏版本化 SQL；
Schema 版本
Git  schema_migrations 記錄套用版本。
HS256 JWT / PHP  bcrypt cost=10；JWT 以 HttpOnly Cookie 傳
身分與密碼
|     | password_hash  送，jti 連回 user_sessions。  |     |
| --- | --------------------------------------- | --- |
Docker / Render /  Web Service 連線 Cloud PostgreSQL；敏感資
部署
|     | Environment Variables  | 料不進 Git。  |
| --- | ---------------------- | --------- |
Render Cron / cleanup- 每日 03:00（Asia/Taipei）分批清理過期
排程
|     | expired.php  | Session 與限流事件。  |
| --- | ------------ | --------------- |
SQLite smoke / PostgreSQL  功能回歸、Schema ⼀致性、Trigger、
測試
integration  Migration 與兩個平⾏開始請求。

第 7 頁

Fitness Tracking Management System — SRS v1.1
3. 功能性需求
前端與後端 API 使用同⼀網站來源。登⼊成功後，伺服器將效期 7,200 秒的 Access
JWT 放⼊ Secure、HttpOnly、SameSite=Strict Cookie；瀏覽器 JavaScript 無法讀取 Token。
寫⼊要求同時驗證 Origin／Referer 與 double-submit CSRF Token。系統不開放任意
CORS，所有新增、修改與刪除均由 PHP 重新驗證格式、所有權與權限。
本章使用 FR 編號標示各項功能需求，⽅便後續開發與測試對照。所有以 /api 開頭
的端點，皆為本版本預先規劃的前後端溝通介面，包含請求⽅式、輸⼊資料及回應內容。
系統完成開發後，須依第 6 章的驗收案例進⾏測試；本⽂件所列的功能與效能目標均為預
定要求，是否達成應以實際測試結果為準。
第 8 頁

Fitness Tracking Management System — SRS v1.1
3.1 共通規則
• 受保護 API 從 HttpOnly Cookie 取得 JWT，驗證簽章、exp、sub 與 jti 後，再 JOIN
user_sessions、user_auth 與 users 取得當前使用者。禁⽌以請求中的 user_id 作為授權依
據；查詢⼦表必須 JOIN 回擁有者。
• 查無資料或資料不屬於本⼈均回傳 404；缺少、過期、撤銷的 JWT 回傳 401；⼀般會員
呼叫管理端點回傳 403。
• PHP 統⼀驗證 JSON 欄位的型別、長度、範圍及日期；不合法回 422，資源重複或狀態
衝突回 409；成功查詢／更新回 200，新增 201，刪除 204。這些狀態碼由 PHP 控制器明
確設定。
• 錯誤 JSON 固定含 code、message；422 另含 field_errors。清單預設 page=1、
page_size=20，page_size 範圍 1–100。
• 多表寫⼊使用同⼀ PDO 連線。beginTransaction() 後、第⼀次資料查詢前執⾏ SET
TRANSACTION ISOLATION LEVEL READ COMMITTED；COMMIT 成功才回應成
功，任何 SQL 或提交錯誤均 rollBack()。錯誤訊息不得包含 SQL、憑證或他⼈資料。完
整併發協定見 4.4。
• 時間戳以 UTC 的 TIMESTAMPTZ 儲存；API 日期採 YYYY-MM-DD、時間戳採含 Z 的
ISO 8601。訓練日期由 started_at AT TIME ZONE 'Asia/Taipei' 取 DATE，週⼀為⼀週
起點。
API 採 UTF-8 JSON；整數欄位拒絕小數與布林值。重量／身⾼最多兩位小數，超過精
度回 422，不默默四捨五⼊；回傳 NUMERIC 採兩位小數字串，避免前端浮點誤差。⽂字
長度以 Unicode 字元計算，密碼例外按 UTF-8 bytes 計算且不得含 NUL。
清單回傳 {items, page, page_size, total}，page 必須為正整數；超過末頁回 items=[]。日
期範圍含起訖兩日，最多 366 日；只傳⼀端、格式錯誤或起日⼤於迄日回 422。未知 JSON
欄位⼀律回 422；PATCH 未提供的欄位維持原值。
第 9 頁

Fitness Tracking Management System — SRS v1.1
所有成功寫⼊均在 COMMIT 後回應。連線失敗時不可推斷寫⼊失敗：先重新查詢，再
重送同⼀組號；只有 FR-12、FR-13 及完成／取消具有明確重試規則。產課每次成功都建立
新版本，前端按鈕送出後禁用⾄請求結束，逾時先查看課表清單。
3.2 會員與權限管理
FR-01 使用者註冊
觸發條件：點擊「註冊」。
輸⼊資料：name 1–100 字、email 最長 255 字、password 10–72 UTF-8 bytes，⾄少含英⽂
字母與數字。
處理邏輯：
1. Email 去除頭尾空白並轉小寫，再驗證格式及唯⼀性；不接受使用者提交管理員角
⾊。
2. PHP 以 password_hash($password, PASSWORD_BCRYPT, ['cost' => 10]) 雜湊密碼，
salt 由函式自動產⽣。同⼀交易建立 users、user_auth、user_sessions；註冊不建
立 admins，角⾊固定為 USER。
3. 後端以固定 HS256 簽發 Access JWT，payload 僅含 sub、jti、iat、exp，不含 role。
sub 為使用者識別碼，jti 對應 user_sessions.user_session_id；效期為 7,200 秒（兩小
時），即 exp = iat + 7200，對應 session 設定相同到期時間。驗證時僅接受 HS256，不
依請求參數或 JWT Header 改變允許的演算法。
4. 成功提交後，由後端透過 Set-Cookie 將 Access JWT 寫⼊瀏覽器，不採用僅存放於前端
記憶體的⽅式。正式環境使用 HTTPS，Cookie 名稱為 __Host-fittrack_access，設
定 Secure、HttpOnly、SameSite=Strict、Path=/、Max-Age=7200，且不設
定 Domain。JWT 由瀏覽器保存並隨符合條件的 API 請求傳送，前端 JavaScript 不直
接讀取或保存 JWT
5. 註冊成功後自動登⼊。前端於首次載⼊或重新整理頁面（F5）後，呼叫 GET
/api/auth/session，由瀏覽器附帶 Access Cookie。後端驗證 JWT 簽章與到期時間，並
第 10 頁

Fitness Tracking Management System — SRS v1.1
確認對應 session 存在、未到期、未撤銷，且所屬使用者與 sub ⼀致。驗證成功後，回
傳使用者資料與資料庫中的目前角⾊，由前端恢復登⼊狀態；不得僅因前端記憶體清
空⽽要求重新登⼊。重新整理不重新簽發 JWT，也不延長原到期時間；登⼊有效性以
後端驗證結果為準。
6. 同時設定可由前端讀取的 __Host-fittrack_csrf Cookie，使用 Secure、
SameSite=Strict、Path=/、Max-Age=7200，不設定 HttpOnly 及 Domain。CSRF
Token 採用與目前 session 綁定、經 HMAC 保護的 Signed Double-Submit Cookie；後續
已登⼊的資料異動請求，須由前端將 Token 放⼊ X-CSRF-Token Header，後端驗證其
與 Cookie ⼀致、簽章正確且屬於目前 session。註冊請求尚未建立 session，須另外驗
證 Origin，缺少時改驗證 Referer；來源不符或無法確認時拒絕請求。
輸出／回應：
POST /api/auth/register → 201 Created；JSON 回傳 user_id、
role="USER" 與 expires_in=7200，並透過兩個獨立的 Set-Cookie Header 設定 Access Cookie
與 CSRF Cookie。Access Token 不出現在 JSON、URL、localStorage、sessionStorage 或日
誌中。
GET /api/auth/session → 驗證成功回傳 200 OK 與目前使用者資料，不回傳 Access
Token。
例外處理：
重複 Email 回傳 409 EMAIL_EXISTS；欄位不合法回傳 422；來源或 CSRF 驗證失敗
回傳 403。交易失敗須完整回滾，不得留下孤立的 users 紀錄，也不得發送登⼊ Cookie。登
⼊狀態查詢時，若 JWT 缺失、無效、到期，或 session 已失效，回傳 401 Unauthorized，前
端顯示未登⼊狀態並要求重新登⼊。
驗收對應：
TC-01、TC-02；相關資料表與 FK 見第 4 章。
第 11 頁

Fitness Tracking Management System — SRS v1.1
FR-02 登⼊與登出
觸發條件：點擊「登⼊」或「登出」；前端首次載⼊或重新整理頁面時，查詢並恢復登⼊
狀態。
輸⼊資料：登⼊輸⼊ email、password；登⼊後的身分驗證由瀏覽器附帶同源 Access
Cookie。登出、修改密碼及停用帳號等資料異動請求，另須於 X-CSRF-Token Header 提供
CSRF Token。
處理邏輯：
1. 驗證帳密並建立登⼊紀錄：
PHP 將 Email 去除頭尾空白並轉小寫，查詢 user_auth，以 password_verify() 比對密
碼，並確認帳號 is_active 為啟用。驗證成功後，建立新的 user_sessions 紀錄，並以固
定 HS256 簽發 Access JWT。Payload 僅含 sub、jti、iat、exp，不含 role；sub 為使用者識
別碼，jti 對應 user_sessions.user_session_id。JWT 與 session 效期均為 7,200 秒（兩小
時），到期時間⼀致。本版不導⼊ Refresh Token，逾期後須重新登⼊。PHP 的密碼比對
使用既有雜湊值，不重新產⽣雜湊後直接比較。
2. 透過 Cookie 保存登⼊憑證：
登⼊紀錄成功提交後，後端透過兩個獨立的 Set-Cookie Header 設定 Access Cookie 與
CSRF Cookie。正式環境使用 HTTPS，前端與 API 對外同源部署，設定如下：
Set-Cookie: __Host-fittrack_access=<JWT>; Max-Age=7200; Path=/; Secure; HttpOnly;
SameSite=Strict
Set-Cookie: __Host-fittrack_csrf=<CSRF_TOKEN>; Max-Age=7200; Path=/; Secure;
SameSite=Strict
兩個 Cookie 均不設定 Domain。Access JWT 由瀏覽器保存並隨符合條件的請求傳送，
前端 JavaScript 不得直接讀取 Access Cookie；CSRF Cookie 則不設定 HttpOnly，供前端讀
取。Access Token 不出現在 JSON、URL、localStorage、sessionStorage 或日誌中，也不採
用僅存放於前端記憶體的⽅式。
第 12 頁

Fitness Tracking Management System — SRS v1.1
3. 驗證 CSRF 防護：
CSRF Token 採用與目前 session 綁定、經 HMAC 保護的 Signed Double-Submit
Cookie。登⼊後的資料異動請求，後端須驗證 X-CSRF-Token Header 與 CSRF Cookie 的值
⼀致、HMAC 正確，且 Token 屬於目前 session；不得僅確認 Cookie 存在便放⾏。登⼊請
求尚未建立 session，須先驗證 Origin 是否符合伺服器設定的允許來源；缺少 Origin 時改
驗證 Referer 的來源。來源不符、為 null 或兩者皆缺少⽽無法確認時，拒絕請求。
4. 每次請求重新確認身分與權限：
每次受保護請求，後端皆須驗證 JWT 的必要欄位與型別、簽章、exp 及 iat，且僅接受
固定 HS256，不得依請求參數或 JWT Header 動態放寬允許的演算法。再
依 jti JOIN user_sessions、user_auth、users，確認 session 所屬使用者與 sub ⼀致、session
未到期、revoked_at 為空且帳號啟用。管理端點每次另⾏ LEFT JOIN 或查詢 admins 判定
目前管理員權限，不信任前端提供的角⾊，也不將 JWT 當作角⾊資訊來源。
5. 重新整理後恢復登⼊狀態：
前端首次載⼊、按 F5 或⼿機瀏覽器重新載⼊頁面時，呼叫 GET /api/auth/session，
由瀏覽器附帶 Access Cookie。後端依前項規則驗證成功後，回傳目前使用者資料與角
⾊，由前端恢復登⼊畫面。**只要 Cookie 仍存在且 JWT、session 與帳號狀態均有效，就
不因頁面重新整理⽽要求再次輸⼊帳密。**查詢登⼊狀態與⼀般操作均不重新簽發 JWT、
不重設 Cookie 保存期限，也不延長 session 的原到期時間。Cookie 的保存不依賴頁面中的
JavaScript 記憶體。
6. 登出及撤銷登⼊狀態：
登出請求通過身分與 CSRF 驗證後，將目前 user_sessions.revoked_at 設為伺服器現在
時間。撤銷成功提交後，以相同 Cookie 名稱、Path=/、無 Domain，搭配 Max-Age=0 清
除 Access Cookie 與 CSRF Cookie，並保留各自原有的安全屬性；前端同步清除記憶體中
的使用者資料。**不得只清除 Cookie ⽽保留有效 session。修改密碼或停用帳號時，須在
第 13 頁

Fitness Tracking Management System — SRS v1.1
同⼀交易完成資料更新並撤銷該帳號所有未撤銷 session，使原 JWT 無法再通過後續驗
證；若影響目前登⼊者，也須清除其登⼊ Cookie。
輸出／回應：
POST /api/auth/login → 200 OK，設定 Access／CSRF Cookie；JSON 回傳 user_id、
name、email、目前 role 與 expires_in=7200，不回傳 Access Token。
GET /api/auth/session → 驗證成功回傳 200 OK 與目前 user_id、name、email、role，不
重新設定登⼊期限。
POST /api/auth/logout → 撤銷成功回傳 204 No Content，清除 Access／CSRF Cookie，
不回傳 JSON。
登⼊及登⼊狀態查詢回應設定 Cache-Control: no-store，避免快取含有使用者資料的驗證
回應。
例外處理：
登⼊時，Email 不存在、密碼錯誤或帳號停用，統⼀回傳 401
INVALID_CREDENTIALS。受保護請求若 JWT 缺失、無效、到期，或 session 不存在、到
期、撤銷、帳號已停用，回傳 401 Unauthorized；前端清除使用者狀態並提示重新登⼊。
來源或 CSRF 驗證失敗回傳 403 Forbidden，不得執⾏資料異動；身分有效但不具管
理員權限時，管理端點回傳 403 Forbidden。
登⼊限流依 NFR-08 回傳 429 與 Retry-After；限流儲存不可用時回傳 503，不得繞
過。資料庫交易失敗須完整回滾，不得發出新的登⼊ Cookie，亦不得將未完成的 session 撤
銷回報為登出成功。
驗收對應：
TC-05，相關資料表與 FK 見第 4 章。
第 14 頁

Fitness Tracking Management System — SRS v1.1
FR-03 變更密碼與停用自⼰的帳號
觸發條件：在帳號設定確認變更密碼或停用。
輸⼊資料：current_password；變更密碼另傳 new_password（規則同 FR-01）。
處理邏輯：
1. PHP 以 password_verify() 驗證目前密碼，使用 password_hash() 產⽣新雜湊；更新
password_hash 與撤銷所有登⼊⼯作階段必須在同⼀交易完成。
2. 停用時將 user_auth.is_active 設為 FALSE 並撤銷所有⼯作階段；保留課表及歷史資料，
但禁⽌存取。此操作不等於物理刪除。
3. 管理員不得透過此介面變更他⼈密碼或停用他⼈；首版帳號停用不提供前端復原。
輸出／回應：PATCH /api/auth/password 或 POST /api/auth/deactivate → 204；前端回到
登⼊頁。
例外處理：目前密碼錯誤回 401；新密碼不合法回 422。
驗收對應：TC-06；相關資料表與 FK 見第 4 章。
3.3 使用者基本資料管理
FR-04 建立查看與修改基本資料
觸發條件：首次登⼊填寫資料，或在個⼈資料頁儲存。
輸⼊資料：name 1–100 字；gender 選填 Female／Male／Other；age 13–100；height_cm
90–250；weight_kg 20–500；training_experience 為 Beginner／Intermediate／Advanced。
處理邏輯：
1. GET /api/me 僅載⼊本⼈；尚未填寫的欄位回傳 NULL。設定完成前可以登⼊，但不能
產⽣課表。
2. PUT /api/me/profile 驗證所有必填值，鎖定 users，在同⼀交易更新 users、UPSERT 今
日 body_records，最後設定 profile_completed_at。只有 COMMIT 成功才視為基本資料
完成。
第 15 頁

Fitness Tracking Management System — SRS v1.1
3. 目前體重由 body_records 依 record_date DESC、body_record_id DESC 取得最新⼀筆；
users 不另存 weight_kg。profile_completed_at 非 NULL 的會員在資料庫層必須⾄少保有
⼀筆體重紀錄，因此產課與基本資料頁不會取得 NULL。
輸出／回應：GET /api/me 或 PUT /api/me/profile → 200；回傳 profile、目前體重、訓練
設定、依 priority 排序的偏好部位與目前 role。role 由後端查 admins 推導，只供介面顯
示，不能作為後端授權依據。
例外處理：缺少必填資料、範圍或等級錯誤回 422；不得修改其他使用者。初始體重寫⼊失
敗時整筆回滾，profile_completed_at 不得單獨留下。
驗收對應：TC-07；相關資料表與 FK 見第 4 章。
3.4 訓練目標與偏好管理
FR-05 設定訓練目標天數與時間
觸發條件：在訓練設定點擊儲存。
輸⼊資料：training_goal_id；training_days_per_week=2–6；training_duration_minutes ∈
{30,60,90}。
處理邏輯：
1. 確認 training_goal_id 存在；四種目標為增肌、減脂、⼒量與⼀般健身。
2. 在 users 更新選項；每份新課表另以 planning_profiles 與 planning_profile_body_parts 保
存當次輸⼊值及偏好順序。已發布課表與其輸⼊快照不因目前會員資料改變⽽更新。
輸出／回應：PUT /api/me/training-settings → 200。
例外處理：不存在的目標或無效天數／時間回 422。
驗收對應：TC-03；相關資料表與 FK 見第 4 章。
第 16 頁

Fitness Tracking Management System — SRS v1.1
FR-06 設定多個想加強部位
觸發條件：勾選部位並儲存。
輸⼊資料：body_part_ids：1–8 個互不重複的整數；陣列順序為優先順序。
處理邏輯：
1. 先驗證所有 ID 存在且不重複；在⼀個交易刪除本⼈舊關聯，再新增新的
user_body_parts。priority 按陣列順序設為 1 ⾄ N。
2. 任⼀ ID 失效時回滾整筆交易；複合主鍵防⽌重複部位，不使用逗號字串欄位。
輸出／回應：PUT /api/me/body-parts → 200；回傳已保存部位。
例外處理：空陣列、重複 ID、無效 ID 或超過 8 個回 422；原資料保留。
驗收對應：TC-03；相關資料表與 FK 見第 4 章。
3.5 運動動作與參考資料管理
FR-07 瀏覽搜尋與動作說明
觸發條件：開啟動作資料庫或點擊課表中的動作。
輸⼊資料：keyword 0–100 字；可選 body_part_id、difficulty_level；分頁參數。
處理邏輯：
1. 以參數化查詢取得 exercises 各自 MAX(version_no) 的 exercise_versions，依
exercises.body_part_id JOIN body_parts；keyword 比對該版本名稱與部位名稱。預設只
顯示 exercises.is_active=TRUE，依名稱及 exercise_id 排序。此為目前目錄，不用於歷史
顯示。
2. 回傳主要部位、難度、器材、動作說明與 image_url；圖片載⼊失敗時改用網站隨附且
標示「非此動作示範」的佔位圖，⽂字步驟仍可閱讀。
第 17 頁

Fitness Tracking Management System — SRS v1.1
輸出／回應：GET /api/exercises 或 GET /api/exercises/{id} → 200；無搜尋結果回空陣
列。
例外處理：非法篩選／分頁回 422；不存在的動作回 404。
驗收對應：TC-08；相關資料表與 FK 見第 4 章。
FR-08 管理運動動作
觸發條件：管理員新增編輯或移除動作。
輸⼊資料：exercise_name、body_part_id、difficulty_level、equipment、description、
image_url、is_active。識別與啟用狀態存 exercises，描述性內容存 exercise_versions，限制
見 4.2。
處理邏輯：
1. 管理端點在每次 Request 都由資料庫即時查詢 admins，不採信 JWT 內的角⾊。
image_url 只保存 HTTPS 圖片網址；後端不主動下載使用者提供的遠端內容，並驗證長
度與格式。動作描述修改會新增 exercise_versions，不覆寫舊版本。
2. 新增動作同交易建立 exercises 及版本 1。管理員修改名稱、器材、說明、圖片或難度
時，先鎖 exercises，再建立下⼀版 exercise_versions；舊版本不 UPDATE、不
DELETE。DELETE /api/admin/exercises/{id} 定義為停用 is_active=FALSE，非物理
刪除。
3. 同⼀ exercise_id 代表同⼀動作身份；本版主部位固定，修正主部位或動作身份須新增
exercise_id 並停用舊身份。名稱不同不代表不同動作，名稱不設跨版本 UNIQUE。版本
號由鎖內 MAX(version_no)+1 配置，UNIQUE(exercise_id,version_no) 防重複。
輸出／回應：POST /api/admin/exercises → 201；PATCH → 200；DELETE → 204。
例外處理：非管理員回 403；同⼀身份改主部位回 409；未核准圖片、無效欄位回 422。舊
課表保留原版本，新產⽣課表使用最新版本。
驗收對應：TC-09；相關資料表與 FK 見第 4 章。
第 18 頁

Fitness Tracking Management System — SRS v1.1
FR-09 維護訓練目標與身體部位說明
觸發條件：管理員編輯參考資料說明。
輸⼊資料：training_goal_id 或 body_part_id；description 最長 1,000 字。
處理邏輯：
1. 初始 migration/seed 建立四個目標與⼋個部位；首版名稱與集合固定，以便排課規則可
重現。
2. 管理員可讀取與修改 description；前端不提供新增、改名或刪除固定分類。此類擴充須
連同規則與 migration ⼀起調整。
輸出／回應：GET /api/reference → 200；PATCH /api/admin/training-goals/{id} 或
/api/admin/body-parts/{id} → 200。
例外處理：非管理員回 403；ID 不存在回 404；不支援的欄位回 422。
驗收對應：TC-10；相關資料表與 FK 見第 4 章。
3.6 訓練課表產⽣與管理
FR-10 產⽣建議課表
觸發條件：完成設定後點擊「產⽣我的訓練課表」。
輸⼊資料：無需傳 user_id；選用 plan_name 1–120 字。
處理邏輯：
1. 以登⼊者讀取基本資料、目標、偏好、天數與時間；任⼀必要設定缺漏時拒絕產⽣。
2. 依 3.11 固定規則，查詢啟用動作的最新 exercise_versions；只選難度不⾼於使用者等級
的版本，配置每日順序、組次與休息。
3. 依 4.4 鎖定並重新驗證輸⼊與候選版本；同⼀交易新增 workout_plans、
planning_profiles、planning_profile_body_parts、plan_days、plan_exercises，驗證後設
定 published_at。plan_exercises 僅保存 exercise_version_id，不重複保存 exercise_id、名
稱或圖片。任何步驟失敗全部回滾。
第 19 頁

Fitness Tracking Management System — SRS v1.1
輸出／回應：POST /api/plans/generate → 201，回傳 workout_plan_id、每日動作、部位、
圖片、組次、休息與預估時間。
例外處理：設定不完整回 422 PROFILE_INCOMPLETE；候選不⾜或約束無法滿⾜回 409
PLAN_CONSTRAINT_UNSATISFIED；不得保存半份課表。
驗收對應：TC-04、TC-23、TC-30；相關資料表與 FK 見第 4 章。
FR-11 查看、編輯與封存課表
觸發條件：進⼊「我的課表」、儲存課表調整或確認封存。介面不將封存標示為永久刪
除。
輸⼊資料：workout_plan_id；PATCH 可傳 plan_name 與 exercises 陣列，每項含
plan_exercise_id、exercise_id、target_sets、target_reps、rest_seconds 與選填
target_weight_kg。不得混⼊其他使用者或其他課表項目。
處理邏輯：
1. 讀取時 JOIN plan_days、plan_exercises 與固定 exercise_versions，依 day_number、
exercise_order 排序。課表有 in_progress 場次時，API 與 DB Trigger 均禁⽌修改或封存
來源課表。
2. 沒有進⾏中場次時，PATCH 在單⼀交易內確認所有權、動作仍啟用且數值合法，再更
新課表模板。已經開始的運動場次使用 workout_session_exercises 快照，所以不會被之
後的模板編輯回寫。
3. 進⾏中場次只允許調整本場 workout_session_exercises 的 target_sets、target_reps、
rest_seconds 與 target_weight_kg，不回寫 plan_exercises。DELETE /api/plans/{id} 是
軟封存 archived_at，不刪除來源關聯或歷史。
第 20 頁

Fitness Tracking Management System — SRS v1.1
輸出／回應：GET /api/plans、GET /api/plans/{id} → 200；PATCH /api/plans/{id} →
200；DELETE /api/plans/{id} → 204（軟封存）。PATCH /api/workout-
sessions/{sessionId}/exercises/{sessionExerciseId} → 200（僅調整本場）。
例外處理：非本⼈或不存在回 404；進⾏中場次鎖定來源課表時回 409 PLAN_IN_USE；無
效動作、組次、休息或重量回 422。
本版的 copied_from_plan_id 保留為日後「複製為新版課表」的來源欄位；現⾏介面
的 PATCH 是編輯沒有進⾏中場次的模板。歷史依場次快照還原，不以目前模板反推。
驗收對應：TC-11、TC-24；相關資料表與 FK 見第 4 章。
3.7 開始運動與每組紀錄
FR-12 開始或繼續運動
觸發條件：在當日課表點擊「開始運動」。
輸⼊資料：plan_day_id。
處理邏輯：
1. READ COMMITTED 交易先鎖 users；鎖成功後以另⼀個 SELECT 查目前 in_progress。
若已有同⼀ plan_day_id，回原場次與已存組數；另⼀日回 409。只有沒有進⾏中場次才
鎖來源課表並驗證所有權、published_at、archived_at 及動作啟用狀態。
2. 同⼀交易新增 workout_sessions、workout_session_plans，並把來源日的每個
plan_exercises 複製為 workout_session_exercises，保留 plan_exercise_id、
exercise_version_id、順序與目標組次／休息／重量。場次快照建立後，來源課表之後的
修改不影響該場歷史。
3. PostgreSQL 在 READ COMMITTED 下先以 SELECT ... FOR UPDATE 鎖定 users 資料
列，使同⼀使用者的兩個開始請求依序執⾏。部分唯⼀索引
uq_workout_sessions_user_active 是最後防線。同日雙擊的實測結果為⼀個 201、⼀個
200，兩者回傳同⼀ workout_session_id；不同日則回 409。
第 21 頁

Fitness Tracking Management System — SRS v1.1
輸出／回應：POST /api/workout-sessions → 新增 201，續練 200；回傳
workout_session_id、今日動作及已存組數。GET /api/workout-sessions/current 可取得進⾏
中場次。
例外處理：來源非本⼈或不存在回 404；另⼀日進⾏中回 409
WORKOUT_ALREADY_ACTIVE；新開始的來源已封存或動作停用回 409
PLAN_REQUIRES_UPDATE。既有同日場次續練不受事後封存影響。
驗收對應：TC-12、TC-13、TC-24；相關資料表與 FK 見第 4 章。
FR-13 每完成⼀組立即儲存
觸發條件：完成⼀組後按「儲存此組」。
輸⼊資料：workout_session_id 取自網址；JSON 傳 workout_session_exercise_id、
set_number 1–100、weight_kg 0–999.99、reps 1–999。不得另傳 user_id、exercise_id、名
稱或圖片。首版不開放課表外臨時加做；日後若開放，必須新增可說明來源的場次動作模
型，不能放寬 FK。
處理邏輯：
1. 後端以 workout_session_exercise_id JOIN 回 workout_sessions 驗證本⼈且
status=in_progress。workout_sets 的 FK 只能指向已建立的場次快照；
workout_session_exercises 的 Trigger 另驗證 plan_exercise_id 必須屬於本場來源日，後
端與 DB 雙重防⽌非法動作。
2. 以 UNIQUE(workout_session_exercise_id,set_number) 去除重送。同鍵同值重送回 200 與
既有結果，同鍵不同值回 409 SET_ALREADY_EXISTS，必須使用 FR-14 編輯。
3. 每組獨立 COMMIT 後才顯示「已儲存」；斷線或失敗顯示「未儲存」並保留欄位。重
新登⼊後可載⼊已存資料。
第 22 頁

Fitness Tracking Management System — SRS v1.1
輸出／回應：POST /api/workout-sessions/{id}/sets → 首次 201、相同資料重送 200；回傳
workout_set_id、set_volume=weight_kg×reps。
例外處理：場次完成／取消、同鍵不同值回 409；動作或數值無效回 422；非本⼈回 404。
驗收對應：TC-14；相關資料表與 FK 見第 4 章。
FR-14 修正或刪除每組紀錄
觸發條件：在訓練頁或歷史詳情編輯錯誤組數。
輸⼊資料：workout_set_id；PATCH 可修改 weight_kg、reps。
處理邏輯：
1. 經 workout_sets → workout_session_exercises → workout_sessions 驗證本⼈。允許修正
in_progress 或 completed 的 weight_kg、reps，不允許把組數移到其他場次動作，也不改
set_number。
2. cancelled 不可改組數。completed 刪除最後⼀組回 409；資料庫在提交前也檢查非空，不
能只靠前端與 API。需刪全部時使用刪除整場；本版不保存歷次數值修訂的稽核軌跡。
3. Dashboard 由實際資料重新彙總，下⼀次查詢必須反映更新／刪除結果。
輸出／回應：PATCH /api/workout-sets/{id} → 200；DELETE → 204。
例外處理：非本⼈回 404；取消場次或刪除完成場次最後⼀組回 409；數值無效回 422。
驗收對應：TC-15、TC-17；相關資料表與 FK 見第 4 章。
第 23 頁

Fitness Tracking Management System — SRS v1.1
FR-15 完成取消或刪除訓練
觸發條件：點擊「完成訓練」「取消本次訓練」或確認刪除歷史。
輸⼊資料：workout_session_id；notes 選填、最長 1,000 字。
處理邏輯：
1. 完成時先鎖本⼈場次並確認⾄少⼀組；將 in_progress 改為 completed 並填 ended_at。延
遲約束觸發器於 COMMIT 前確認仍有⼀組，否則回滾。重送完成回既有結果，不改結
束時間。
2. 取消時由 in_progress 改為 cancelled 並填 ended_at，保留 sets 但排除 Dashboard；重送
取消回既有結果且不改 ended_at。完成與取消互不可轉換。
3. 只允許刪除 completed／cancelled 場次；同⼀交易刪除場次及其 sets。進⾏中場次需先
取消。
輸出／回應：POST /api/workout-sessions/{id}/complete 或 /cancel → 200；DELETE
/api/workout-sessions/{id} → 204。
例外處理：空場次完成、非法狀態轉換或刪除進⾏中場次回 409；非本⼈回 404。
驗收對應：TC-16、TC-17、TC-25、TC-26；相關資料表與 FK 見第 4 章。
3.8 歷史紀錄與統計分析
FR-16 查看訓練與動作歷史
觸發條件：進⼊訓練歷史或查看某動作歷史。
輸⼊資料：start_date、end_date、exercise_id、status 選填；分頁參數。省略日期時採含今
日最近 28 天；只提供⼀端日期回 422。
處理邏輯：
1. Workout History 預設列出本⼈的 completed 與 cancelled 場次。查詢直接 JOIN
workout_sessions、workout_session_plans、plan_days 與 workout_plans，依 started_at
與 workout_session_id 倒序；不存在未實作的唯讀 View。
第 24 頁

Fitness Tracking Management System — SRS v1.1
2. 明細以 workout_sets → workout_session_exercises → exercise_versions 顯示當場固定的動
作名稱、器材、步驟、圖片、目標處⽅與實際組數；再由 exercise_versions.exercise_id
連回穩定動作身份與主部位。Exercise History 以穩定 exercise_id 篩選，不同版本視為
同⼀動作。
輸出／回應：GET /api/workout-sessions、GET /api/workout-sessions/{id} 或 GET
/api/exercises/{id}/history → 200；清單含 items 與分頁，明細含場次及 sets，無清單資料
回空陣列。
例外處理：日期起訖錯誤／超過 366 天回 422；非本⼈明細回 404。
驗收對應：TC-19；相關資料表與 FK 見第 4 章。
FR-17 訓練量與 Dashboard
觸發條件：開啟統計儀表板或變更日期篩選。
輸⼊資料：start_date、end_date；預設含今日的最近 28 天，最多 366 天。
處理邏輯：
1. 只計⼊本⼈ status=completed 的場次。weighted_volume（介面顯示「外加重量訓練
量」）= SUM(weight_kg×reps)；weight_kg=0 的徒⼿組不估算身體負荷，但仍納⼊
completed_sets、total_reps 與 bodyweight_reps。例如三組重量訓練分別為 60 kg × 12
次、65 kg × 10 次及 65 kg × 8 次，其外加重量訓練量為 1,890 kg·次。若另外完成⼀組
15 次的徒⼿動作，總完成次數為 45 次，其中外加重量動作為 30 次、徒⼿動作為 15
次。徒⼿動作不納⼊外加重量訓練量。
2. 外加重量訓練量使用 SUM(weight_kg*reps)，每週次數使用 COUNT(DISTINCT
workout_session_id)，另以 COUNT(*)、SUM(reps) 及 FILTER (WHERE weight_kg=0)
計算完成組數、總次數與徒⼿次數；日期以台北日期及週⼀分組。
3. 部位排名依固定動作身份的 body_part_id；動作排名依穩定 exercise_id 彙總所有版本。
兩者以完成組數 COUNT(*) 排名、ID 升序破同分。排⾏榜名稱取期間內最近⼀次完成
第 25 頁

Fitness Tracking Management System — SRS v1.1
紀錄所用版本，並標註「最近訓練時名稱」，不 JOIN 目前名稱。AVG(weight_kg) 用於
體重平均。
4. 無訓練資料回 weighted_volume=0、completed_sets=0、total_reps=0、
bodyweight_reps=0、每週次數 0 與空排⾏榜。完成基本資料後體重⾄少⼀筆；尚未完成
Profile 時體重趨勢為空並顯示引導，不讓前端直接對 NULL 做計算。
5. 未來擴充的徒手等效負荷 = 場次開始時體重快照 × 具版本的動作係數 × reps；估算值必須與實際外
加重量分開顯示，本版不使用未定義係數。
輸出／回應：GET /api/dashboard → 200；回傳 weighted_volume、completed_sets、
total_reps、bodyweight_reps、每週次數、部位與動作排⾏、體重趨勢。
例外處理：日期或範圍不合法回 422；尚未完成的組數不得影響正式統計。
驗收對應：TC-20；相關資料表與 FK 見第 4 章。
3.9 身體紀錄管理
FR-18 新增查看修改與刪除體重
觸發條件：進⼊體重歷史並新增、修正或刪除。
輸⼊資料：record_date 為 1900-01-01 ⾄台北今日；weight_kg 20–500；notes≤1,000 字；
body_record_id 用於修改／刪除。PATCH 可改日期、體重與 notes，新日期仍須唯⼀。
處理邏輯：
1. 每位使用者每天⼀筆；新增若日期已存在回 409，提示使用 PATCH 修改。
2. 查詢依 record_date 排序；修改與刪除均驗證本⼈。刪除最新紀錄後，目前體重回退到
上⼀筆；若該筆已是 Profile 完成後的最後⼀筆，資料庫與 API 均拒絕刪除，使用者只
能修改該筆或先新增另⼀日紀錄。
第 26 頁

Fitness Tracking Management System — SRS v1.1
輸出／回應：POST /api/body-records → 201；GET /api/body-records、PATCH /api/body-
records/{id} → 200；DELETE → 204。
例外處理：重複日期回 409；刪除最後⼀筆回 409 LAST_BODY_RECORD_REQUIRED；
未來日期或不合法體重回 422；非本⼈回 404。
驗收對應：TC-21；相關資料表與 FK 見第 4 章。
第 27 頁

Fitness Tracking Management System — SRS v1.1
3.10 訓練狀態與介面回應
| 目前狀態    | 操作與條件    |                    | 結果與資料庫變化  |
| ------- | -------- | ------------------ | --------- |
| 無進⾏中場次  | 開始本⼈課表日  | 201；同交易新增場次及來源關聯。  |           |
同日 200 回原 ID；另⼀日 409，不建
| in_progress  | 再次開始同日／另⼀日  |     |     |
| ------------ | ----------- | --- | --- |
立新場次。
201 新增⼀組；相同重送 200，筆數
| in_progress  | 儲存⼀組／完全相同重送  |     |     |
| ------------ | ------------ | --- | --- |
不變。
200；改 completed 並填 ended_at。空
| in_progress  | ⾄少⼀組後完成  |     |     |
| ------------ | -------- | --- | --- |
場次 409。
200；改 cancelled 並填 ended_at，保
in_progress  取消
留組數、排除統計。
| completed／ |     | 200 回原場次；ended_at 不改。改另 |     |
| ---------- | --- | ----------------------- | --- |
重送同種終⽌操作
| cancelled  |     |     | ⼀終態回 409。  |
| ---------- | --- | --- | ---------- |
允許修正；刪最後⼀組 409。新增組
| completed  | 修改／刪除既有組  |     |     |
| ---------- | --------- | --- | --- |
⼀律 409。
| cancelled  | 修改、刪除組或新增組  |                       | 409；只能刪除整場。  |
| ---------- | ----------- | --------------------- | ------------ |
| completed／ |             | 204；場次、來源關聯、sets 同交易刪 |              |
刪除整場
| cancelled  |     |     | 除。  |
| ---------- | --- | --- | --- |

第 28 頁

Fitness Tracking Management System — SRS v1.1
訓練頁依 workout_session_exercises.exercise_order 顯示當場快照的動作、部位、器
材、版本圖片與說明、目標組次、休息與輸⼊欄位。今天指使用者選擇的課表日，不依星
期猜測。使用者可調整本場目標，但不回寫來源課表。
介面必須區分「尚未儲存」「儲存中」「已儲存」「儲存失敗」。只有成功回應才
標示已儲存；失敗保留輸⼊並允許重試。F5 後瀏覽器會自動夾帶 HttpOnly Access
Cookie，前端呼叫 GET /api/auth/session 恢復使用者資料；Cookie 到期、被撤銷或帳號停
用才回到登⼊頁。已提交每組資料不受影響，未送出欄位只存在當前頁面。
第 29 頁

Fitness Tracking Management System — SRS v1.1
3.11 規則式排課與版本記錄
rules-v2-randomized 將 Beginner／Intermediate／Advanced 排為 1／2／3，只選不⾼於會員程度的
啟用動作最新版本。先安排⼋個部位週覆蓋，再優先增加使用者所選部位頻率；同⼀份課表不重
複同⼀ exercise_id。各部位候選動作在交易內洗牌，並優先選擇最近三份電腦課表未使用的動作；在候選充足時，連續兩份課表的動作重複率不⾼於 25%。此變更依 2026 年 10 月 16 日使用者要求，用來避免電腦規劃結果過度相同；保留原有程度、時間、部位覆蓋與處方規則。
2／3／4／5／6 天的部位模板分別採：① 胸背肩腿／⼆頭三頭臀核⼼；② 胸肩三頭
／背⼆頭核⼼／腿臀；③ 胸肩三頭／背⼆頭／腿臀核⼼／優先部位補強；④ 在前三天外加
上肢補強、下肢核⼼；⑤ 推／拉／腿核⼼各重複兩次。每日先保證 3 動作，依可用時間最
多 6 動作；補強日按偏好順位循環，且仍受每日時間限制。
增肌 3×10、減脂 3×12、⼒量 4×5、⼀般健身 2×12；休息分別 60／45／120／45 秒。
預估秒數 = 300 秒暖身 + Σ[sets×reps×3 + (sets−1)×rest] + (動作數−1)×60。只能在不破壞
覆蓋與最低 3 動作的前提下選 3–6 動作；無可⾏配置回 409，不能默默超過時間。
年齡、身⾼、體重保存為產課上下⽂，本版不以其推定安全負重；實際重量由使用
者輸⼊。候選版本、設定及偏好在持鎖交易內再次確認；保存輸⼊快照與完整輸出处⽅，
published_at 之前驗證全部條件。⼈⼯修訂沿用原規劃上下⽂，改天數或改目標需重新產
課。
第 30 頁

Fitness Tracking Management System — SRS v1.1
4. 資料模型與結構設計
本版共有 20 張應用資料表與 25 條外鍵。exercise_versions 保存不可變的動作版本；
planning_profiles 與 planning_profile_body_parts 保存產課當時的目標、年齡、身⾼、體
重、程度、天數、時間與偏好順序；workout_session_exercises 保存開始運動時的動作版本
與當場處⽅。login_failures 是跨 PHP Worker 共用的滑動視窗事件表。
4.1 實體關係圖
ERD 以 PK／FK／UQ 表示主鍵、外鍵與唯⼀鍵。R01–R25 與 4.3 節逐列 1:1 對應；login_failures 不指
向個⼈帳號⽽沒有 FK，因此不編 R 號。圖中重複出現的資料表代表同⼀實體，不是資料複製。
圖 2帳號、目前偏好與登⼊保護 ERD
第 31 頁

Fitness Tracking Management System — SRS v1.1
圖 3課表與規劃輸⼊ ERD
第 32 頁

Fitness Tracking Management System — SRS v1.1
圖 4動作身份與不可變版本 ERD
第 33 頁

Fitness Tracking Management System — SRS v1.1
圖 5運動場次、來源快照與實際組數 ERD
圖 5 的 workout_session_exercises 是場次快照：既保留來源 plan_exercise_id，也固定
exercise_version_id 及當場目標。workout_sets 只指向場次動作，不重複保存 exercise_id、
名稱或課表日。DB Trigger 驗證快照來源日與場次⼀致。
第 34 頁

Fitness Tracking Management System — SRS v1.1
4.2 資料表詳細規格
除標示可空者外⼀律 NOT NULL。主鍵 INTEGER 使用 GENERATED BY
DEFAULT AS IDENTITY；時間戳為 TIMESTAMPTZ，created_at 預設
CURRENT_TIMESTAMP。身⾼使用 NUMERIC(5,2) 並限制 100–250 cm；體重快照、體
重紀錄及訓練重量均使用 NUMERIC(6,2)。資料庫的 CHECK 負責結構範圍，PHP 另拒絕
超過兩位小數的輸⼊。
第 35 頁

Fitness Tracking Management System — SRS v1.1
表 4.2.1 users
|     | 欄位  |     | 型態與鍵  |     | 語意、預設值及約束  |     |
| --- | --- | --- | ----- | --- | ---------- | --- |
GENERATED BY DEFAULT AS
|     | user_id  |     | INTEGER；PK  |     |     |     |
| --- | -------- | --- | ----------- | --- | --- | --- |
IDENTITY；使用者識別碼。
|     | name  |     | VARCHAR(100)  |     | 去頭尾空白後 1–100 字。  |     |
| --- | ----- | --- | ------------- | --- | ---------------- | --- |
Female / Male / Other；未提供時
|     | gender  | VARCHAR(20)；可空  |     |     |     |     |
| --- | ------- | --------------- | --- | --- | --- | --- |
NULL。
|     | age  | SMALLINT；可空  |     | 13–100；完成 Profile 前可空。  |     |     |
| --- | ---- | ------------ | --- | ----------------------- | --- | --- |
100.00–250.00 cm；完成 Profile 前可
|     | height_cm  | NUMERIC(5,2)；可空  |     |     |     |     |
| --- | ---------- | ---------------- | --- | --- | --- | --- |
空。
Beginner / Intermediate /
| training_experience  |     | VARCHAR(20)；可空  |     |     |     |     |
| -------------------- | --- | --------------- | --- | --- | --- | --- |
Advanced。
| training_goal_id           |     | INTEGER；FK；可空  |     | → training_goals；RESTRICT。  |     |                |
| -------------------------- | --- | -------------- | --- | --------------------------- | --- | -------------- |
| training_days_per_week     |     | SMALLINT；可空    |     |                             |     | 2–6。           |
| training_duration_minutes  |     | SMALLINT；可空    |     |                             |     | 30 / 60 / 90。  |
完成基本資料並同交易建立初始體
| profile_completed_at  |     | TIMESTAMPTZ；可空  |     |     |     |     |
| --------------------- | --- | --------------- | --- | --- | --- | --- |
重後寫⼊。
DEFAULT
|     | created_at  |     | TIMESTAMPTZ  |     |     |     |
| --- | ----------- | --- | ------------ | --- | --- | --- |
CURRENT_TIMESTAMP。

第 36 頁

Fitness Tracking Management System — SRS v1.1
表 4.2.2 user_auth
| 欄位       | 型態與鍵           | 語意、預設值及約束  |
| -------- | -------------- | ---------- |
| auth_id  | INTEGER；PK；必填  | 認證資料識別碼。   |
→ users.user_id；UNIQUE；ON DELETE
| user_id  | INTEGER；FK；必填  |     |
| -------- | -------------- | --- |
CASCADE。
去頭尾空白並轉小寫；UNIQUE；格式由 API
| email  | VARCHAR(255)；—；必填  |     |
| ------ | ------------------ | --- |
驗證。
PHP password_hash() 產⽣ bcrypt hash，
| password_hash  | VARCHAR(255)；—；必填  |     |
| -------------- | ------------------ | --- |
cost=10；禁⽌明⽂密碼。
首版未啟用寄信驗證；不得把格式檢查當作信
| is_email_verified  | BOOLEAN；—；必填  |     |
| ------------------ | ------------- | --- |
箱驗證。 DEFAULT FALSE
停用後拒絕登⼊與所有受保護 API。 DEFAULT
| is_active  | BOOLEAN；—；必填  |     |
| ---------- | ------------- | --- |
TRUE
登⼊資料建立時間。 DEFAULT
| created_at  | TIMESTAMPTZ；—；必填  |     |
| ----------- | ----------------- | --- |
CURRENT_TIMESTAMP

第 37 頁

Fitness Tracking Management System — SRS v1.1
表 4.2.3 user_sessions
| 欄位  | 型態與鍵  |     | 語意、預設值及約束  |     |
| --- | ----- | --- | ---------- | --- |
user_session_id  UUID；PK  JWT jti；DEFAULT gen_random_uuid()。
| auth_id     | INTEGER；FK      |     | → user_auth.auth_id；ON DELETE CASCADE。  |     |
| ----------- | --------------- | --- | --------------------------------------- | --- |
| created_at  | TIMESTAMPTZ     |     | DEFAULT CURRENT_TIMESTAMP。              |     |
| expires_at  | TIMESTAMPTZ     |     | 必須晚於 created_at；登⼊後 7,200 秒。            |     |
| revoked_at  | TIMESTAMPTZ；可空  |     | 登出、改密碼或停用時寫⼊；非 NULL 即失效。                |     |

表 4.2.4 admins
| 欄位  |     | 型態與鍵  |     | 語意、預設值及約束  |
| --- | --- | ----- | --- | ---------- |
→ users.user_id；ON DELETE CASCADE；
| user_id  | INTEGER；PK/FK；必填  |     |     |     |
| -------- | ----------------- | --- | --- | --- |
每位使用者最多⼀筆。
由受信任的部署／管理程序授予；前端不得
| created_at  | TIMESTAMPTZ；—；必填  |     |     | 自⾏建立。 DEFAULT  |
| ----------- | ----------------- | --- | --- | -------------- |
CURRENT_TIMESTAMP

表 4.2.5 login_failures
| 欄位                | 型態與鍵       | 語意、預設值及約束                |     |     |
| ----------------- | ---------- | ------------------------ | --- | --- |
| login_failure_id  | BIGINT；PK  | 每次失敗驗密事件的 IDENTITY 識別值。  |     |     |
ip_hash  CHAR(64)  來源 IP 經 RATE_LIMIT_SECRET 做 HMAC-SHA-256；只
允許 64 個小寫⼗六進位字元。
| failed_at  | TIMESTAMPTZ  | DEFAULT CURRENT_TIMESTAMP；15 分鐘滑動視窗的 |     |     |
| ---------- | ------------ | ------------------------------------ | --- | --- |
事件時間。

第 38 頁

Fitness Tracking Management System — SRS v1.1
表 4.2.6 training_goals
| 欄位                | 型態與鍵           |     | 語意、預設值及約束  |
| ----------------- | -------------- | --- | ---------- |
| training_goal_id  | INTEGER；PK；必填  |     | 訓練目標識別碼。   |
UNIQUE；Muscle Gain / Fat Loss / Strength /
| goal_name  | VARCHAR(50)；—；必填  |     |     |
| ---------- | ----------------- | --- | --- |
General Fitness。
| description  | TEXT；—；可空  | 顯示用說明；最長 1,000 字。 DEFAULT NULL  |     |
| ------------ | ---------- | ------------------------------- | --- |

表 4.2.7 body_parts
| 欄位            | 型態與鍵           |     | 語意、預設值及約束  |
| ------------- | -------------- | --- | ---------- |
| body_part_id  | INTEGER；PK；必填  |     | 身體部位識別碼。   |
UNIQUE；Chest / Back / Shoulders / Biceps /
| body_part_name  | VARCHAR(50)；—；必填  |     |     |
| --------------- | ----------------- | --- | --- |
Triceps / Legs / Glutes / Core。
| description  | TEXT；—；可空  | 顯示用說明；最長 1,000 字。 DEFAULT NULL  |     |
| ------------ | ---------- | ------------------------------- | --- |

表 4.2.8 user_body_parts
| 欄位  | 型態與鍵  |     | 語意、預設值及約束  |
| --- | ----- | --- | ---------- |
user_id  INTEGER；PK/FK；必填  → users.user_id；ON DELETE CASCADE。
→ body_parts.body_part_id；ON DELETE
| body_part_id  | INTEGER；PK/FK；必填  |     |     |
| ------------- | ----------------- | --- | --- |
RESTRICT。
CHECK (priority BETWEEN 1 AND 8)；數字越
| priority  | SMALLINT；—；必填  |     |     |
| --------- | -------------- | --- | --- |
小越優先。 DEFAULT 1

第 39 頁

Fitness Tracking Management System — SRS v1.1
表 4.2.9 body_records
| 欄位              | 型態與鍵        |     | 語意、預設值及約束         |
| --------------- | ----------- | --- | ----------------- |
| body_record_id  | INTEGER；PK  |     | 身體紀錄識別碼。          |
| user_id         | INTEGER；FK  |     | → users；CASCADE。  |
不得晚於 CURRENT_DATE；
| record_date  | DATE  |     |     |
| ------------ | ----- | --- | --- |
UNIQUE(user_id,record_date)。
| weight_kg  | NUMERIC(6,2)  |     | 20.00–500.00 kg。  |
| ---------- | ------------- | --- | ----------------- |
| notes      | TEXT；可空       |     | 最多 1,000 字。       |

表 4.2.10 exercises
| 欄位           | 型態與鍵        |     | 語意、預設值及約束         |
| ------------ | ----------- | --- | ----------------- |
| exercise_id  | INTEGER；PK  |     | 動作穩定身份；IDENTITY。  |
DEFAULT TRUE；FALSE 排除新課表／新開始，不抹
| is_active  | BOOLEAN  |     |     |
| ---------- | -------- | --- | --- |
除既有歷史。
| created_at  | TIMESTAMPTZ  | DEFAULT CURRENT_TIMESTAMP。  |     |
| ----------- | ------------ | --------------------------- | --- |

第 40 頁

Fitness Tracking Management System — SRS v1.1
表 4.2.11 exercise_versions
| 欄位                   | 型態與鍵          | 語意、預設值及約束                            |
| -------------------- | ------------- | ------------------------------------ |
| exercise_version_id  | INTEGER；PK    | 完整描述版本識別值。                           |
| exercise_id          | INTEGER；FK    | → exercises；RESTRICT。                |
| version_no           | INTEGER       | >=1；UNIQUE(exercise_id,version_no)。  |
| exercise_name        | VARCHAR(120)  | 去空白後 1–120 字；名稱不是穩定身份。               |
difficulty_level  VARCHAR(20)  Beginner / Intermediate / Advanced。
| equipment    | VARCHAR(100)；可空  | 器材名稱；徒⼿可填 Bodyweight。           |
| ------------ | ---------------- | ------------------------------- |
| description  | TEXT             | 1–4,000 字；包含步驟與注意事項。            |
| image_url    | TEXT；可空          | 參考圖片的 HTTPS URL；最長 2,048 字。     |
| created_at   | TIMESTAMPTZ      | DEFAULT CURRENT_TIMESTAMP；版本建立後 |
禁⽌ UPDATE／DELETE。

第 41 頁

Fitness Tracking Management System — SRS v1.1
表 4.2.12 workout_plans
| 欄位               |     | 型態與鍵        |     | 語意、預設值及約束         |
| ---------------- | --- | ----------- | --- | ----------------- |
| workout_plan_id  |     | INTEGER；PK  |     | 課表識別值。            |
| user_id          |     | INTEGER；FK  |     | → users；CASCADE。  |
copied_from_plan_id  INTEGER；FK；可空  → workout_plans；RESTRICT；不得指向自⼰。
| plan_name  |     | VARCHAR(120)  |     | 去空白後 1–120 字。  |
| ---------- | --- | ------------- | --- | -------------- |
NOT NULL；DEFAULT
| published_at  |     | TIMESTAMPTZ  |     |     |
| ------------- | --- | ------------ | --- | --- |
CURRENT_TIMESTAMP。
| archived_at  | TIMESTAMPTZ；可空  |              | 軟封存時間；不可早於 created_at。      |     |
| ------------ | --------------- | ------------ | --------------------------- | --- |
| created_at   |                 | TIMESTAMPTZ  | DEFAULT CURRENT_TIMESTAMP。  |     |

第 42 頁

Fitness Tracking Management System — SRS v1.1
表 4.2.13 planning_profiles
| 欄位  | 型態與鍵  | 語意、預設值及約束  |     |
| --- | ----- | ---------- | --- |
workout_plan_id  INTEGER；PK/FK  → workout_plans；ON DELETE RESTRICT。
| training_goal_id    | INTEGER；FK    | → training_goals；RESTRICT。  |     |
| ------------------- | ------------- | --------------------------- | --- |
| age_snapshot        | SMALLINT      | 產課當時年齡；13–100。              |     |
| height_cm_snapshot  | NUMERIC(5,2)  | 產課當時身⾼；100.00–250.00 cm。    |     |
| weight_kg_snapshot  | NUMERIC(6,2)  | 產課當時最新體重；20.00–500.00 kg。   |     |
| weight_record_date  | DATE          | 快照體重所屬日期。                   |     |
experience_snapshot  VARCHAR(20)  Beginner / Intermediate / Advanced。
| training_days_per_week  | SMALLINT  | 2–6。           |     |
| ----------------------- | --------- | -------------- | --- |
| duration_minutes        | SMALLINT  | 30 / 60 / 90。  |     |
algorithm_version  VARCHAR(50)  rules-v1、llm-validated-v1 或 legacy-backfill-v1。
| captured_at  | TIMESTAMPTZ  | DEFAULT CURRENT_TIMESTAMP；規劃輸⼊捕捉 |     |
| ------------ | ------------ | -------------------------------- | --- |
時間。

表 4.2.14 planning_profile_body_parts
| 欄位  | 型態與鍵  |     | 語意、預設值及約束  |
| --- | ----- | --- | ---------- |
workout_plan_id  INTEGER；PK/FK  → planning_profiles；RESTRICT。
→ body_parts；RESTRICT；複合
| body_part_id  | INTEGER；PK/FK  |     |     |
| ------------- | -------------- | --- | --- |
PK(workout_plan_id,body_part_id)。
CHECK BETWEEN 1 AND 8；
| priority  | SMALLINT  | UNIQUE(workout_plan_id,priority)；發布驗證連續  |     |
| --------- | --------- | ---------------------------------------- | --- |
1…N。

第 43 頁

Fitness Tracking Management System — SRS v1.1
表 4.2.15 plan_days
| 欄位           | 型態與鍵           | 語意、預設值及約束  |
| ------------ | -------------- | ---------- |
| plan_day_id  | INTEGER；PK；必填  | 課表日識別碼。    |
workout_plan_id  INTEGER；FK；必填  → workout_plans.workout_plan_id；ON
DELETE RESTRICT。
day_number  SMALLINT；—；必填  CHECK (day_number BETWEEN 1 AND 6)。
| day_title  | VARCHAR(120)；—；必填  | 1–120 字；例如「第 1 天：胸、背、腿」。  |
| ---------- | ------------------ | ------------------------- |

表 4.2.16 plan_exercises
| 欄位                | 型態與鍵        | 語意、預設值及約束              |
| ----------------- | ----------- | ---------------------- |
| plan_exercise_id  | INTEGER；PK  | 課表動作識別值。               |
| plan_day_id       | INTEGER；FK  | → plan_days；RESTRICT。  |
exercise_version_id  INTEGER；FK  → exercise_versions；RESTRICT；固定描述版本。
exercise_order  SMALLINT  1–10；UNIQUE(plan_day_id,exercise_order)。
| target_sets       | SMALLINT         | 1–10。                 |
| ----------------- | ---------------- | --------------------- |
| target_reps       | SMALLINT         | 1–50。                 |
| rest_seconds      | SMALLINT         | 0–600 秒。              |
| target_weight_kg  | NUMERIC(6,2)；可空  | 0.00–999.99 kg；目標重量。  |

第 44 頁

Fitness Tracking Management System — SRS v1.1
表 4.2.17 workout_sessions
|                     | 欄位       |     | 型態與鍵        |     |     | 語意、預設值及約束         |
| ------------------- | -------- | --- | ----------- | --- | --- | ----------------- |
| workout_session_id  |          |     | INTEGER；PK  |     |     | 實際訓練場次識別值。        |
|                     | user_id  |     | INTEGER；FK  |     |     | → users；CASCADE。  |
in_progress / completed / cancelled；DEFAULT
|     | status  |     | VARCHAR(20)  |     |     |     |
| --- | ------- | --- | ------------ | --- | --- | --- |
in_progress。
|     | started_at  |                 | TIMESTAMPTZ  |     | DEFAULT CURRENT_TIMESTAMP。  |              |
| --- | ----------- | --------------- | ------------ | --- | --------------------------- | ------------ |
|     | ended_at    | TIMESTAMPTZ；可空  |              |     | 終⽌狀態必填且不得早於 started_at。     |              |
|     | notes       |                 | TEXT；可空      |     |                             | 最多 1,000 字。  |

表 4.2.18 workout_session_plans
| 欄位  |     | 型態與鍵  |     | 語意、預設值及約束  |     |     |
| --- | --- | ----- | --- | ---------- | --- | --- |
workout_session_id  INTEGER；PK/FK  → workout_sessions；CASCADE；每場恰⼀來源由延遲
觸發器保證。
| plan_day_id  |     | INTEGER；FK  |     | → plan_days；RESTRICT；不可 UPDATE／單獨  |     |     |
| ------------ | --- | ----------- | --- | ---------------------------------- | --- | --- |
DELETE。

第 45 頁

Fitness Tracking Management System — SRS v1.1
表 4.2.19 workout_session_exercises
| 欄位                           | 型態與鍵        | 語意、預設值及約束                    |
| ---------------------------- | ----------- | ---------------------------- |
| workout_session_exercise_id  | INTEGER；PK  | 場次動作快照識別值。                   |
| workout_session_id           | INTEGER；FK  | → workout_sessions；CASCADE。  |
plan_exercise_id  INTEGER；FK  → plan_exercises；RESTRICT；Trigger 驗證屬
於本場來源日。
exercise_version_id  INTEGER；FK  → exercise_versions；RESTRICT；必須等於來
源 plan_exercise 的版本。
| exercise_order  | SMALLINT  | 1–10； |
| --------------- | --------- | ----- |
UNIQUE(workout_session_id,exercise_order)。
| target_sets   | SMALLINT  | 1–10；可只調整本場。   |
| ------------- | --------- | -------------- |
| target_reps   | SMALLINT  | 1–50；可只調整本場。   |
| rest_seconds  | SMALLINT  | 0–600；可只調整本場。  |
target_weight_kg  NUMERIC(6,2)；可空  0.00–999.99；目標重量，不等於實際紀錄。
| created_at  | TIMESTAMPTZ  | DEFAULT CURRENT_TIMESTAMP。  |
| ----------- | ------------ | --------------------------- |

第 46 頁

Fitness Tracking Management System — SRS v1.1
表 4.2.20 workout_sets
| 欄位              | 型態與鍵        | 語意、預設值及約束   |
| --------------- | ----------- | ----------- |
| workout_set_id  | INTEGER；PK  | 每組實際訓練識別值。  |
workout_session_exercise_id  INTEGER；FK  → workout_session_exercises；CASCADE。
| set_number  | SMALLINT  | 1–100； |
| ----------- | --------- | ------ |
UNIQUE(workout_session_exercise_id,set_number)。
| weight_kg   | NUMERIC(6,2)  | 0.00–999.99；外加重量，0 表示徒⼿。    |
| ----------- | ------------- | --------------------------- |
| reps        | SMALLINT      | 1–999。                      |
| created_at  | TIMESTAMPTZ   | DEFAULT CURRENT_TIMESTAMP。  |

歷史明細不另外建立重複資料的 View；PHP 使用參數化 SQL 直接 JOIN workout_sessions、
workout_session_plans、workout_session_exercises、exercise_versions 與 workout_sets。若場次來源或快
照缺失，FK、NOT NULL 與 Trigger 先阻⽌寫⼊，巡檢仍可用 LEFT JOIN 找出異常。
第 47 頁

Fitness Tracking Management System — SRS v1.1
4.3 外鍵關係與刪除政策
| 編號  ⽗表 → ⼦表                     | ⼦表外鍵     | ⽗端 : ⼦端／刪除        |
| ------------------------------- | -------- | ----------------- |
| R01  users → user_auth          | user_id  | 1 : 0..1；CASCADE  |
| R02  user_auth → user_sessions  | auth_id  | 1 : 0..N；CASCADE  |
| R03  users → admins             | user_id  | 1 : 0..1；CASCADE  |
R04  training_goals → users  training_goal_id  1 : 0..N；RESTRICT
| R05  users → user_body_parts  | user_id  | 1 : 0..N；CASCADE  |
| ----------------------------- | -------- | ----------------- |
R06  body_parts → user_body_parts  body_part_id  1 : 0..N；RESTRICT
| R07  users → body_records  | user_id  | 1 : 0..N；CASCADE  |
| -------------------------- | -------- | ----------------- |
R08  body_parts → exercises  body_part_id  1 : 0..N；RESTRICT
R09  exercises → exercise_versions  exercise_id  1 : 0..N；RESTRICT
| R10  users → workout_plans  | user_id  | 1 : 0..N；CASCADE  |
| --------------------------- | -------- | ----------------- |
R11  workout_plans →  copied_from_plan_id  0..1 : 0..N；RESTRICT
workout_plans
| R12  workout_plans →  | workout_plan_id  | 1 : 0..1；RESTRICT  |
| --------------------- | ---------------- | ------------------ |
planning_profiles
| R13  training_goals →  | training_goal_id  | 1 : 0..N；RESTRICT  |
| ---------------------- | ----------------- | ------------------ |
planning_profiles
R14  planning_profiles →  workout_plan_id  1 : 0..N；RESTRICT
planning_profile_body_parts
| R15  body_parts →  | body_part_id  | 1 : 0..N；RESTRICT  |
| ------------------ | ------------- | ------------------ |
planning_profile_body_parts
R16  workout_plans → plan_days  workout_plan_id  1 : 0..N；RESTRICT
第 48 頁

Fitness Tracking Management System — SRS v1.1
編號 ⽗表 → ⼦表 ⼦表外鍵 ⽗端 : ⼦端／刪除
R17 plan_days → plan_exercises plan_day_id 1 : 0..N；RESTRICT
R18 exercise_versions → exercise_version_id 1 : 0..N；RESTRICT
plan_exercises
R19 users → workout_sessions user_id 1 : 0..N；CASCADE
R20 workout_sessions → workout_session_id 1 : 0..1；CASCADE
workout_session_plans
R21 plan_days → plan_day_id 1 : 0..N；RESTRICT
workout_session_plans
R22 workout_sessions → workout_session_id 1 : 0..N；CASCADE
workout_session_exercises
R23 plan_exercises → plan_exercise_id 1 : 0..N；RESTRICT
workout_session_exercises
R24 exercise_versions → exercise_version_id 1 : 0..N；RESTRICT
workout_session_exercises
R25 workout_session_exercises → workout_session_exercise_id 1 : 0..N；CASCADE
workout_sets
共 25 條 FK。workout_session_exercises 透過場次、來源課表項目與動作版本三組 FK 保留當場
快照；workout_sets 再指向該快照。completed 場次⾄少⼀組為跨表不變量，由 DEFERRABLE
CONSTRAINT TRIGGER 於 COMMIT 前檢查。
課表與版本不物理刪除：課表封存、動作停用，相關 RESTRICT 避免歷史斷鏈。帳號停用保留
資料。使用者明確刪除 completed/cancelled 整場時，場次及來源關聯、實際組數⼀併刪除；該操作不刪
課表。歷史保存承諾不包含已由使用者確認刪除的場次。正式資料保留／個資清除屬獨立維運流程，不
以停用或 CASCADE 冒充。
第 49 頁

Fitness Tracking Management System — SRS v1.1
唯⼀性或檢查 規則
帳號 UNIQUE(user_auth.user_id)、UNIQUE(email)。
偏好 PK(user_id,body_part_id)、UNIQUE(user_id,priority)；產課快照另有
相同的 plan 範圍鍵。
動作版本 UNIQUE(exercise_id,version_no)；Trigger 禁⽌ UPDATE／DELETE。
課表 UNIQUE(workout_plan_id,day_number)、
UNIQUE(plan_day_id,exercise_order)；Trigger 防⽌同日重複穩定
exercise_id。
場次 UNIQUE(user_id) WHERE status='in_progress'；status 與 ended_at 組
合 CHECK。
場次動作 UNIQUE(session_id,plan_exercise_id)、
UNIQUE(session_id,exercise_order)；Trigger 驗證來源日與版本。
每組 UNIQUE(workout_session_exercise_id,set_number)；完成場次⾄少⼀組
由延遲 Constraint Trigger 保護。
體重 UNIQUE(user_id,record_date)；Profile 完成後不得刪除最後⼀筆。
第 50 頁

Fitness Tracking Management System — SRS v1.1
4.4 隔離等級與併發交易協定
PostgreSQL 連線建立後明確執⾏ SET SESSION CHARACTERISTICS AS TRANSACTION
ISOLATION LEVEL READ COMMITTED，業務交易以此隔離層級執⾏；驗收以 SHOW
transaction_isolation 確認為 read committed。每⼀ SQL 指令取新的已提交快照；SELECT FOR
UPDATE 僅鎖既有資料列，不鎖「查不到的空集合」，也不等同 SERIALIZABLE。[1]
授權鎖先於業務鎖：需要持鎖驗證的寫⼊先取得 user_auth → user_sessions → admins（僅管理
操作），再進⼊ users → workout_plans（需要時）→ workout_sessions（需要時）→ exercises（需要
時，ID 升序）→ ⼦表。目前資料、偏好及體重寫⼊先鎖 users，使產課快照讀取⼀致。DB 觸發器補做
所需⽗列鎖並重新查詢；管理員修改動作不反向取得會員資源鎖。死結仍須處理，固定鎖序不是「永不
死結」的保證。
只在短交易內進⾏ DB 讀寫；圖片下載、外部 HTTP 呼叫、等待使用者操作與 password_hash()
不放在長時間持鎖區間。死結、鎖等待與連線中斷均必須回滾交易，不得回傳假成功。
4.4.1 開始訓練的交易步驟
BEGIN;
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
SELECT user_id FROM users
WHERE user_id = :authenticated_user_id FOR UPDATE;
-- 必須是鎖成功後的另⼀條 SQL，不能合併成同⼀個舊快照查詢。
SELECT workout_session_id FROM workout_sessions
WHERE user_id = :authenticated_user_id
AND status = 'in_progress';
-- 已有：相同來源日回既有 ID；不同日回 409。
-- 沒有：鎖來源課表，再驗證本⼈、已發布、未封存與動作啟用。
-- 同⼀交易建立場次與來源；COMMIT 前執⾏延遲完整性檢查。
COMMIT;
SQL 中的 :authenticated_user_id 由已驗證的登⼊狀態取得，不採用客⼾端任意 user_id。BEGIN 例示資
料庫交易；PHP 實作以 PDO beginTransaction() 啟動，不重複 BEGIN。
CREATE UNIQUE INDEX uq_workout_sessions_user_active
ON workout_sessions (user_id)
WHERE status = 'in_progress';
第 51 頁

Fitness Tracking Management System — SRS v1.1
| 時間                             | Request A               | Request B           |
| ------------------------------ | ----------------------- | ------------------- |
| T1  取得 users(U) 的 FOR UPDATE。  |                         | 嘗試鎖同⼀ users(U)，等待。  |
| T2  另查 active，為空；新增場次 S 與來源。   | 尚未取得鎖，不得依先前空結果 INSERT。  |                     |
| T3                             | COMMIT，釋放鎖。             | 取得鎖，另查看到已提交的 S。     |
同來源日回 200 與 S；不同日回 409，筆數不增
| T4  | 回 201 與 S。  |     |
| --- | ----------- | --- |
加。

若 A 回滾，B 取得鎖後可建立自⼰的場次。即使錯誤寫⼊路徑省略 users 鎖，部分唯⼀索引仍阻
⽌兩筆 active 同時提交：衝突 INSERT 可能等待對⽅結束，對⽅提交後失敗。[2] 只把 constraint/index
名稱為 uq_workout_sessions_user_active 的 SQLSTATE 23505 映射為續練衝突。
4.4.2 錯誤分類及重試界線
| 情況  |     | 處理要求  |
| --- | --- | ----- |
ROLLBACK 後新交易查 active；同日 200、不同日 409。若查無
23505 active 唯⼀性
（例如場次已完成），回 409 請重新載⼊，不盲目再建。
整筆回滾；本版不在控制器內自動無限重試，回 409
40P01 死結／40001 序列化失敗  TRANSACTION_RETRY_REQUIRED。若日後自動重試，必須重
跑整筆且有次數上限。
55P03 鎖逾時／57014 指令逾時  整筆回滾，回 503 RETRY_LATER；前端保留輸⼊。
不宣稱失敗亦不立即重建；先查 current 場次或該組唯⼀鍵。
提交結果不明  active 索引不是所有時間的 idempotency key，完成後的新開始是新
場次。
回滾，記錄不含機密的 request_id／SQLSTATE；回⼀般錯誤，不
其他 DB 錯誤
冒充已有場次。

第 52 頁

Fitness Tracking Management System — SRS v1.1
4.5 資料庫完整性與觸發器
「completed ⾄少⼀組」不是資料庫做不到，⽽是⼀般單列 CHECK 與 FK 無法表達⽗列必須有
⼦列。CHECK 不得以查詢其他表的函式假裝跨表約束；FK 只保證⼦列的⽗列存在。[2] 本版採後端預
檢加資料庫約束觸發器，正常應用／維運 DML 均受保護。
4.5.1 完成訓練與最後⼀組
workout_sets 的 BEFORE INSERT/UPDATE/DELETE 觸發器鎖定⽗ workout_sessions；取得鎖
後重新讀狀態。INSERT 只允許 in_progress；UPDATE 只許重量與次數，禁⽌換場次、換
plan_exercise_id、換組號；cancelled 不允許逐組改刪。completed 的 DELETE 最終是否違規由提交前檢
查決定。
⽗場次 INSERT／狀態 UPDATE，以及組數 INSERT／UPDATE／DELETE，各自登記 AFTER
ROW CONSTRAINT TRIGGER，設定 DEFERRABLE INITIALLY DEFERRED。檢查於交易結束時讀
取最終狀態：若⽗場次仍存在且 status=completed，必須 EXISTS ⾄少⼀筆 workout_sets；不符拋出命名
約束錯誤，COMMIT 失敗並回滾。[3]
-- 約束觸發器的檢查邏輯；需分別掛在⽗表與⼦表事件。
affected_session := NEW/OLD.workout_session_id;
SELECT status FROM workout_sessions
WHERE workout_session_id = affected_session FOR UPDATE;
IF parent_not_found THEN
RETURN; -- 僅允許已合法刪整場所導致的 CASCADE
END IF;
IF status = 'completed' AND NOT EXISTS (
SELECT 1 FROM workout_sets
WHERE workout_session_id = affected_session
) THEN
RAISE check_violation 'completed_session_requires_set';
END IF;
上述為規格偽碼，不是可直接執⾏的 migration。實作須區分 TG_OP 的 NEW/OLD，並測試
INSERT completed、改為 completed、刪最後⼀組及刪整場。BEFORE 觸發器序列化同⽗場次的改動；
延遲觸發器檢查提交後應成立的不變量，兩者不能互相取代。
兩個交易各刪⼀組時，即使原有兩組，也必先競爭同⼀⽗列鎖。第⼀筆刪除提交後剩⼀組，第
⼆筆取得鎖後刪除將在提交前被拒絕。完成與存組同時發⽣時，先存組者提交後完成可成功；先完成者
若無組則失敗，若已有組則後續新增因終態⽽被拒。
第 53 頁

Fitness Tracking Management System — SRS v1.1
整場刪除限定 completed/cancelled。⽗列刪除後 CASCADE 清除 sets 與來源，⼦表觸發器發現
⽗列在本交易已不存在時跳過非空檢查；禁⽌直接刪來源關聯。角⾊不得取得 TRUNCATE、停用
trigger 或改 session_replication_role 的權限。擁有者／超級使用者能繞過部分保護，屬受管制維運邊
界，不宣稱可防所有特權操作。
4.5.2 來源與不可變版本
觸發時機 保證內容
exercise_versions BEFORE 舊版本不可覆寫或刪除；修改動作必須 INSERT 新版本。
UPDATE/DELETE
plan_exercises BEFORE 同⼀課表日不得放⼊同⼀穩定 exercise_id 的不同版本。
INSERT/UPDATE
workout_session_exercises 快照 plan_exercise_id 必須屬於場次來源日，exercise_version_id 必
BEFORE INSERT/UPDATE 須與來源處⽅⼀致。
body_records BEFORE 以 advisory transaction lock 序列化同⼀使用者刪除；完整 Profile ⾄
DELETE 少保留⼀筆體重。
workout_sessions / workout_sets 於 COMMIT 前確認 completed 場次存在⾄少⼀組；刪除最後⼀組
/ workout_session_exercises 或刪除其場次動作快照都會使交易失敗。
CONSTRAINT TRIGGER
workout_plans / plan_days / 來源課表有 in_progress 場次時禁⽌修改或刪除；本場調整必須寫⼊
plan_exercises BEFORE 場次快照。
UPDATE/DELETE
資料庫觸發器保證結構及時間不變量；產課的選擇策略與預估時間由具版本的後端
規則驗證，不能把有 FK 等同於授權或健身合理性。所有測試須確認失敗交易的欄位與筆
數均不變。 copied_from_plan_id 只允許指向已發布且同會員的既有課表，來源在新課表之
前建立，因此不得形成自循環或修訂循環。
第 54 頁

Fitness Tracking Management System — SRS v1.1
4.5.3 基本資料完成與最低⼀筆體重
首次完成基本資料時，後端在同⼀交易鎖定 users、UPSERT 當日 body_records，最
後設定 users.profile_completed_at。只要 profile_completed_at 非 NULL，該會員就必須保
有⾄少⼀筆體重紀錄。這項規則避免刪除全部體重後，目前體重變成 NULL，造成產課與
介面欄位失去必要輸⼊。
body_records 的 BEFORE DELETE／user_id UPDATE 觸發器先以 FOR UPDATE 鎖
定⽗ users，使同⼀會員的並⾏刪除依序執⾏。users 的 profile_completed_at 變動，以及
body_records 的 DELETE 或 user_id UPDATE，另登記 DEFERRABLE INITIALLY
DEFERRED 約束觸發器。提交前若會員仍存在、profile_completed_at 非 NULL 且查無
body_records，交易以 23514 拒絕。刪除完整帳號時，⽗ users 已不存在，CASCADE 清理
不受此限制。
-- 提交前不變量偽碼
IF EXISTS (
SELECT 1 FROM users AS u
WHERE u.user_id = affected_user_id
AND u.profile_completed_at IS NOT NULL
) AND NOT EXISTS (
SELECT 1 FROM body_records AS br
WHERE br.user_id = affected_user_id
) THEN
RAISE check_violation 'completed_profile_requires_weight_record';
END IF;
刪除最後⼀筆體重時 API 回 409 LAST_BODY_RECORD_REQUIRED，介面改為提
供「修改體重」。產課交易仍會鎖 users 並讀取最新體重；資料庫觸發器負責最低⼀筆的結
構保障，後端負責把可理解的錯誤訊息回傳給使用者。
第 55 頁

Fitness Tracking Management System — SRS v1.1
4.6 正規化與完整歷史保存
4.6.1 保存範圍與時間語意
本版的「完整歷史」指能還原當次的產課輸⼊、來源課表日、動作版本、場次順
序、場次目標處⽅與現存實際組數。開始運動時把 plan_exercises 複製為
workout_session_exercises，因此後續編輯或封存課表模板，不會改變已建立場次的處⽅。
| 歷史項目  | 保存位置  | 後續修改的歷史⾏為  |     |
| ----- | ----- | ---------- | --- |
產課目標、年齡、身⾼、
存當時快照；不跟 users 或 body_records 同
| 體重與日期、程度、天 | planning_profiles  |     |     |
| ---------- | ------------------ | --- | --- |
步。
數、時間
每個部位⼀列，不用 VARCHAR 清單；不
| 偏好部位與順序  | planning_profile_body_parts  |     |     |
| -------- | ---------------------------- | --- | --- |
跟目前偏好同步。
| 動作名稱、難度、器材、 |     | 版本不可覆寫；穩定 exercise_id 可跨版本 |     |
| ----------- | --- | -------------------------- | --- |
exercise_versions
| 說明與圖片 URL   |     |                    | 彙總。  |
| ----------- | --- | ------------------ | ---- |
| 開始當下的動作順序、版 |     | 場次建立後獨立於來源模板；本場可調整 |      |
workout_session_exercises
| 本與目標處⽅      |                   |                    | 目標。    |
| ----------- | ----------------- | ------------------ | ------ |
| 場次時間、狀態與實際重 | workout_sessions、 | 實際紀錄與處⽅是不同事實；修正錯記後 |        |
| 量／次數        | workout_sets      |                    | 統計重算。  |

不保存：未提交的輸⼊、已確認刪除的場次、每次修改實際重量前的舊值、整個候
選目錄在當時的所有版本集合、瀏覽器像素畫面及登⼊憑證。因此本版可完整查閱處⽅與
現存訓練事實，但不是全面稽核日誌，也不宣稱僅憑 algorithm_version 就能重新執⾏得到
完全相同的候選搜尋結果。若課程要求數值修改稽核，須另增 append-only audit 表，不能
稱目前已具備。

第 56 頁

Fitness Tracking Management System — SRS v1.1
exercise_versions 保存每個版本當時的 image_url 與⽂字說明，使舊課表與訓練歷史
仍能指出當時引用的圖片網址；本系統不保存遠端圖片⼆進位內容，也不宣稱網址永久可
用。若網址失效，介面顯示動作名稱、說明與明確的缺圖替代內容。需要永久影像保存
時，應在未來加⼊具版本與備份政策的物件儲存服務。
三年前名稱為「槓鈴臥推」的版本 V1，改名後新增 V2「平板槓鈴臥推」。舊
plan_exercises 仍指向 V1，因此三年前歷史顯示 V1 的名稱、器材、說明與圖片；新課表才
指向 V2。exercise_id 不變，可彙總同⼀動作跨版本進步。
4.6.2 刻意重複與第三正規化
正規化的目標是排除錯誤的函數相依與更新異常，不是禁⽌不同時間事實出現相同
數值。本版不在每組重複保存名稱、圖片與部位，也不保存可計算的 volume、總組數、
session_date 或目前體重。名稱與圖片在 exercise_version_id 下只保存⼀次。
| 關係與候選鍵  | 主要函數相依  | 3NF 判定與刻意重複  |
| ------- | ------- | ------------ |
exercise_versions；PK version_id， 版本鍵 → 名稱、難度、器 穩定主部位放 exercises；歷史描述
| AK(exercise_id,version_no)  | 材、說明、圖片         | 不依賴目前版本。           |
| --------------------------- | --------------- | ------------------ |
| planning_profiles；PK        | 課表 ID → 當次所有排課輸 | 此為不同時點的業務事實，與      |
| workout_plan_id             | ⼊               | users 目前值不同是預期⾏為。  |
planning_profile_body_parts；複合  (plan_id,body_part_id) →  消除多值字串；非鍵不依賴部分
| PK                 | priority         | 主鍵。           |
| ------------------ | ---------------- | ------------- |
| plan_exercises；PK  | 處⽅ ID → 動作版本與目標  | 不重複名稱、器材或部位。  |
plan_exercise_id
workout_session_exercises；PK  場次動作 ID → 來源、版 與 plan_exercises 數值重複是刻意
| session_exercise_id  | 本、順序與當場目標  | 的時間快照；建立後獨立變動。  |
| -------------------- | ---------- | --------------- |
workout_sets；PK set_id， 組的鍵 → weight_kg、reps、 volume 由查詢計算；不保存可推
AK(session_exercise_id,set_number)  created_at  導的動作名稱或場次 user_id。

第 57 頁

Fitness Tracking Management System — SRS v1.1
本版的資料表以 3NF 為設計目標：exercise_id → body_part_id，因此固定主部位只
存 exercises，不在每個版本重複；exercise_versions 只保存會隨版本改變的描述。歷史分類
經固定 exercise_id 取得，不受目前名稱更動影響。場次 user_id 的跨表重複仍須明列用途與
DB ⼀致性檢查，不能宣稱完全沒有重複。
課表複製修訂會重用既有 exercise_versions，但複製該次的日與處⽅列；這是以不同
workout_plan_id 識別的兩個不可變處⽅事實。重複值增加儲存量，交換獨立可重建、無回
寫同步的歷史。此取捨與列內函數相依分開評估。
所有 immutable 表的 UPDATE/DELETE 權限應以最小權限及觸發器雙重限制；對
可變表只給必要欄位更新權。任何版本修訂都先建立新列再引用，禁⽌背景程序「同步修
正」舊版本。版本與圖片保留期間須涵蓋引用它們的所有課表與場次。
第 58 頁

Fitness Tracking Management System — SRS v1.1
4.7 JWT 身分與資料庫授權
Access JWT 僅攜帶 sub、jti、iat、exp，不存 role。JWT 簽章只能證明內容未被竄
改，不能證明管理員資格仍然有效。因此每次受保護請求都查 user_sessions 與 user_auth，
管理端點另即時查 admins。JWT 的用途是帶⼊簽名過的使用者與 Session 識別值，不是當
作永久權限快取。
每次受保護請求驗證 Token 與登⼊狀態；⼀般資源再驗所有權，管理端點再查
admins。GET /api/me 與 GET /api/auth/session 的 role 是當下查詢結果，僅供介面顯示。
admins 列被刪除後，下⼀個管理 API 即回 403；DB 不可用或查詢失敗時不放⾏。[4]
管理員資格在每⼀個 API Request 的驗證階段由 admins 即時查詢。若資格在該
Request 通過驗證後才被撤銷，已進⼊處理中的單⼀ Request 可能完成；撤銷不追溯取消已
通過的交易，但下⼀個管理 Request 必須回 403。⽂件不宣稱使用尚未實作的資格列鎖定流
程。
第 59 頁

Fitness Tracking Management System — SRS v1.1
4.8 SQL 查詢與索引
歷史查詢⼀定⾛處⽅固定版本，不使用目前目錄的 MAX(version_no)。下例保留
JOIN、GROUP BY 與 SUM；:user_id 來自伺服器認證。
SELECT
ws.workout_session_id,
ev.exercise_version_id,
ev.exercise_name,
SUM(s.weight_kg * s.reps) AS total_volume
FROM workout_sessions AS ws
JOIN workout_session_exercises AS wse
ON wse.workout_session_id = ws.workout_session_id
JOIN workout_sets AS s
ON s.workout_session_exercise_id = wse.workout_session_exercise_id
JOIN exercise_versions AS ev
ON ev.exercise_version_id = wse.exercise_version_id
WHERE ws.user_id = :user_id
AND ws.status = 'completed'
GROUP BY ws.workout_session_id,
ev.exercise_version_id, ev.exercise_name
ORDER BY ws.workout_session_id DESC;
每週次數由場次表直接 COUNT(*)，或組表 JOIN 後 COUNT(DISTINCT
workout_session_id)，避免⼀場多組被重複計數。每日／每週日期均從 started_at 換算
Asia/Taipei；日期篩選以 UTC 半開區間 [起日,迄日+1日) 套用到 started_at。
第 60 頁

Fitness Tracking Management System — SRS v1.1
索引 用途與邊界
UNIQUE(user_id) WHERE status='in_progress'；同⼀使用者最後
uq_workout_sessions_user_active
防重複。
idx_user_sessions_expires user_sessions(expires_at)；排程分批清理。
idx_login_failures_ip_time login_failures(ip_hash,failed_at DESC)；15 分鐘滑動視窗。
body_records(user_id,record_date DESC,body_record_id DESC)；取
idx_body_records_user_date
目前體重。
idx_exercises_body_active exercises(body_part_id,is_active)；候選動作篩選。
idx_exercise_versions_latest exercise_versions(exercise_id,version_no DESC)；目錄取最新版。
idx_workout_plans_user_created workout_plans(user_id,created_at DESC)；課表清單。
idx_plan_days_plan /
課表依天數與動作順序讀取。
idx_plan_exercises_day
idx_workout_sessions_user_started workout_sessions(user_id,started_at DESC)；訓練歷史。
workout_session_exercises(workout_session_id,exercise_order)；場
idx_session_exercises_session
次詳情。
workout_sets(workout_session_exercise_id,set_number)；逐組讀取
idx_workout_sets_session_exercise
與統計。
既有 PK／UNIQUE 已有索引，不重複建立相同前綴。以 EXPLAIN (ANALYZE,
BUFFERS) 驗證讀取計畫及資料量，不能由「已建索引」推論必然變快。Migration 與備份
帳號和應用帳號分離；版本化 SQL、schema_migrations 與 Seeder 必須可在隔離測試庫重
跑。
第 61 頁

Fitness Tracking Management System — SRS v1.1
4.9 登⼊限流與過期資料清理
登⼊限流使用 PostgreSQL login_failures 事件表。PHP 以 RATE_LIMIT_SECRET 對
來源 IP 做 HMAC-SHA-256，不儲存原始 IP。每次請求在交易內對 ip_hash 取得
pg_advisory_xact_lock，先刪除 15 分鐘視窗外的事件，再 COUNT 目前視窗。前 20 次錯誤
帳密回 401 並新增事件；第 21 次在驗密前回 429 與 Retry-After。成功登⼊會刪除該
ip_hash 的失敗事件。
BEGIN;
SELECT pg_advisory_xact_lock(hashtextextended(:ip_hash, 0));
DELETE FROM login_failures
WHERE ip_hash = :ip_hash
AND failed_at <= CURRENT_TIMESTAMP - INTERVAL '15 minutes';
SELECT COUNT(*), MIN(failed_at)
FROM login_failures WHERE ip_hash = :ip_hash;
-- COUNT >= 20：COMMIT 後回 429 + Retry-After，不驗密。
-- 密碼錯誤：INSERT ⼀筆 failed_at，COMMIT 後回 401。
-- 登⼊成功：DELETE 該 ip_hash 的失敗事件。
COMMIT;
Render Cron Service 以 UTC 19:00 排程，等於台北時間每日 03:00 執⾏ php
bin/cleanup-expired.php。腳本取得全局 advisory lock，以 500 筆為⼀批、FOR UPDATE
SKIP LOCKED 刪除 expires_at <= CURRENT_TIMESTAMP 的 user_sessions，並刪除超過
15 分鐘的 login_failures。每批獨立提交，避免長交易。Render 上排程服務需 Starter 或當
時支援 Cron 的⽅案；若未啟用，應由維運者以外部排程執⾏同⼀命令。
第 62 頁

Fitness Tracking Management System — SRS v1.1
WITH doomed AS (
SELECT user_session_id
FROM user_sessions
WHERE expires_at <= CURRENT_TIMESTAMP
ORDER BY expires_at
LIMIT 500
FOR UPDATE SKIP LOCKED
)
DELETE FROM user_sessions AS us
USING doomed
WHERE us.user_session_id = doomed.user_session_id;
DELETE FROM login_failures
排程輸出開始後的刪除筆數、執⾏毫秒與時區，但不記錄 Cookie、Token、雜湊或
原始 IP。排程失敗不得影響使用者既有資料；監控連續失敗並由維運⼈員重跑。TC-27 驗
證跨 Worker 限流，TC-31 驗證分批清理只刪除已到期 Session 與視窗外事件。
第 63 頁

Fitness Tracking Management System — SRS v1.1
5. 非功能性需求
5.1 效能需求
下列為驗收門檻，並非已完成的量測結果。測試使用預先喚醒的雲端服務、同區資
料庫，以及 1,000 位會員、10,000 場訓練與 100,000 組紀錄；測試報告需記錄實際 CPU、記
憶體、DB ⽅案、資料量與測試時間。
編號 量化門檻 驗證⽅式
⼀般讀取 API P95 ≤500 ms；每組儲存 P95 API 用⼾端量測完整 HTTP 回應，排除測
NFR-01
≤1,000 ms；產⽣課表 P95 ≤3,000 ms。 試前 60 秒暖機；依端點分別計算。
30 秒升⾄ 200 ⼈；每⼈請求後停 1 秒；讀
200 個並⾏虛擬使用者連續操作 5 分鐘；預期
NFR-02 取／存組／產課表比例 70/20/10，不得崩
成功請求的非預期失敗率 <1%。
潰或違反唯⼀鍵。
收到儲存成功回應後，重新載⼊可讀到相同紀 另⼀次 HTTP 查詢與 DB SELECT 交叉確
NFR-03
錄；不接受假成功。 認；故障注⼊不得留下部分資料。
5.2 安全性需求
• NFR-04：公開站點強制 HTTPS；應用程式連線雲端資料庫使用 TLS。HTTP ⼊⼝重新
導向 HTTPS。
• NFR-05：密碼以 PHP bcrypt（cost=10）雜湊儲存。Access JWT 固定 HS256、效期 2 小
時且不含 role，採 HttpOnly Cookie 機制，正式環境設定 Secure、SameSite=Strict，不存
⼊ localStorage 或 sessionStorage。有效期內重新整理可恢復登⼊，不延長效期。寫⼊請
求須驗證同源與 CSRF Token；每次受保護請求查驗 user_sessions 與 user_auth，確認
Session 有效且帳號啟用，管理端點另即時查詢 admins 判定權限。
• NFR-06：PHP PDO 使用 prepare() 與參數綁定，關閉模擬預備語句；排序欄位採允許清
單，個⼈資源檢查所有權。範本輸出以 htmlspecialchars() 編碼，JavaScript 以
textContent 顯示使用者⽂字。
第 64 頁

Fitness Tracking Management System — SRS v1.1
• NFR-07：DATABASE_URL、SECRET_KEY、API key 與部署密碼不得進
Git；.env.example 僅列空值或非機密範例。日誌不得輸出明⽂密碼、JWT 或完整連線字
串。
• NFR-08：登⼊限流以 PostgreSQL login_failures 與 pg_advisory_xact_lock 在多個 PHP
Worker 間實作共用滑動視窗。來源 IP 先用 RATE_LIMIT_SECRET 做 HMAC-SHA-
256；DB 不可用時登⼊ fail closed 回 503。X-Forwarded-For 只在 REMOTE_ADDR 屬
TRUSTED_PROXY_IPS 時採信，否則使用直接連線 IP。
第 65 頁

Fitness Tracking Management System — SRS v1.1
5.3 易用性與相容性
• NFR-09：驗收當日的 Chrome、Safari、Edge 各最新兩個主要版本均須完成註冊、產⽣
課表與逐組存檔；報告記錄實際版本。
• NFR-10：375×812、768×1024 與 1440×900 三種視窗下，不出現整頁⽔平捲動；主要按
鈕最小可點擊範圍為 44×44 CSS px。
• NFR-11：已具備訓練設定的使用者由課表頁⾄首組輸⼊最多 2 次主要按鈕操作；成功、
失敗與未存檔狀態必須以⽂字顯示。
• NFR-12：欄位具有可辨識標籤、錯誤提示與鍵盤焦點順序；圖片提供替代⽂字，圖片
故障不阻擋運動紀錄。
5.4 資料可靠性與可維護性
• NFR-13：database/postgres.sql 必須在空 PostgreSQL 建立 20 張應用資料表、25 條
FK、索引與觸發器。database/migrations/20261006_teacher_review_v1_1.sql 必須將舊版
15 表 Schema 原地升級，先做資料條件檢查、在單⼀交易內回填快照，失敗即全部回
滾。
• NFR-14：每日備份，保留最近 7 份；同時備份不可覆寫圖片資源及 SHA-256 清單，單
備份 URL 不算完成。⾄少⼀次還原到獨立測試庫，核對表數、筆數、FK、版本及圖片
雜湊；RPO≤24 小時、RTO 目標≤60 分鐘。
• NFR-15：README 包含 PHP、PDO_PGSQL、環境變數、啟動、Migration、Seed、
SQLite 煙霧測試、PostgreSQL 完整性／併發測試、Schema ⼀致性檢查、清理排程與部
署。公開目錄限 public/，伺服器重啟不影響雲端 PostgreSQL。
動作種⼦資料⾄少 16 筆：⼋部位各 2 個 Beginner 動作，另可增加其他難度。每筆含步
驟、注意事項及動作相符的自製或合法授權圖片，資源清單記錄來源、作者及授權；不可
把通用佔位圖當作該動作的教學圖片。
第 66 頁

Fitness Tracking Management System — SRS v1.1
6. 驗收測試案例
6.1 功能驗收
以隔離的測試資料庫執⾏，A、B 為⼀般會員，M 為管理員。每個案例記錄 HTTP 狀態、畫面結果及 SQL 查詢證據；破壞性與故障
注⼊操作不得對正式使用者資料執⾏。表格沿用老師要求的案例編號、測試功能、前置條件、操作步驟與預期結果五欄。
| 案例     | 功能        | 前置條件     |                             | 操作步驟         |                                                   |     | 預期結果  |
| ------ | --------- | -------- | --------------------------- | ------------ | ------------------------------------------------- | --- | ----- |
|        |           |          | 註冊，查 users/auth/sessions 與  |              | 201；三表各 +1；JWT 無 role、exp−iat=7200；Access Cookie  |     |       |
| TC-01  | FR-01 註冊  | 新 Email  |                             |              |                                                   |     |       |
|        |           |          |                             | Set-Cookie。  | 為 Secure／HttpOnly／SameSite=Strict；無 admins。       |     |       |
TC-02  FR-01 重複帳號  已有小寫 Email  以不同⼤小寫再註冊。  409 EMAIL_EXISTS；各表筆數不變。
存 4 天 60 分偏好胸背；再送 7 天
| TC-03  | FR-05／06 設定  | 會員已登⼊  |     |     |     | 合法 200；非法 422；舊設定保留。  |     |
| ------ | ------------ | ------ | --- | --- | --- | --------------------- | --- |
或重複部位。
|        |           | 初階增肌4天60分， | 產課後 JOIN 輸⼊、日、動作版 |     | 201；4天、每日3–6動作、全部位覆蓋且不超時；完整輸⼊ |     |                 |
| ------ | --------- | ---------- | ----------------- | --- | ----------------------------- | --- | --------------- |
| TC-04  | FR-10 產課  |            |                   |     |                               |     |                 |
|        |           | 各部位⾜夠候選    |                   | 本。  |                               |     | 與published_at。  |
FR-02 登⼊、重整 登⼊→F5→GET /auth/session→登 重整後不重輸帳密；登出撤銷 Session 並清 Cookie；舊
| TC-05  |      | 有效帳號  |                  |     |     |     |                |
| ------ | ---- | ----- | ---------------- | --- | --- | --- | -------------- |
|        | 與登出  |       | 出→用舊 Cookie 呼叫。  |     |     |     | Cookie 回 401。  |
改密碼驗舊 Token；重新登⼊後停
| TC-06  | FR-03 密碼與停用  | 兩個登⼊階段  |     |     | 所有舊 Token 401；停用後不能登⼊，訓練仍在 DB。  |     |     |
| ------ | ------------ | ------- | --- | --- | ------------------------------- | --- | --- |
用。
第 67 頁

Fitness Tracking Management System — SRS v1.1
| 案例  | 功能  | 前置條件  | 操作步驟  |     | 預期結果  |
| --- | --- | ----- | ----- | --- | ----- |
存身⾼ 100.00 及 250.00；送 99.99；
邊界可存，非法 422；同日體重僅 1 筆；完成時間與初始體重
| TC-07  FR-04 基本資料  |     | 已有會員  | 同日改體重；檢查  |     |     |
| ------------------ | --- | ----- | --------- | --- | --- |
同交易提交，users 無體重副本。
profile_completed_at。
TC-08  FR-07 動作搜尋  同動作有V1,V2  目錄搜尋與V1舊課表查詢。  目錄顯V2；舊課表顯V1；空搜尋items=[]。
|                    |     | 改名、說明、圖片建立V2；直接 | V2新增；舊值不變；UPDATE被DB拒絕；不改 |     |               |
| ------------------ | --- | --------------- | ------------------------ | --- | ------------- |
| TC-09  FR-08 版本修改  |     | 已引用V1           |                          |     |               |
|                    |     |                 | SQL UPDATE V1。           |     | exercise_id。  |
管理員改description；會員嘗試；
| TC-10  FR-09 參考資料  |     | 管理員／⼀般會員  |     | 200／403／422；固定身份與名稱不變。  |     |
| ------------------ | --- | --------- | --- | ----------------------- | --- |
嘗試改分類名。
FR-11 課表與本場 修改／封存 P；調整場次目標；取 來源模板操作回 409；本場目標 200 且不回寫 P；場次結束後
| TC-11              |     | 課表 P 有進⾏中場次         |          |                                     |     |
| ------------------ | --- | ------------------- | -------- | ----------------------------------- | --- |
|                    | 目標  |                     | 消後修改 P。  | 可修改，舊歷史不變。                          |     |
|                    |     | 使用者無 active；兩個      |          | 僅 1 場 in_progress；⼀個 201、⼀個 200；兩者  |     |
| TC-12  FR-12 同日併發  |     | 兩個 Request 同時開始同日。  |          |                                     |     |
|                    |     | 獨立 PostgreSQL 連線    |          | workout_session_id 相同。              |     |
同時POST異日；另以測試SQL
TC-13  FR-12 異日併發  同上，兩個不同來源日  API⼀201⼀409；直接SQL⾄多1筆提交，另⼀23505。
繞過users鎖競爭active索引。
同 session_exercise_id／set_number
| FR-13 組數重送與 |     | in_progress 且有場次快 |     |     |     |
| ----------- | --- | ----------------- | --- | --- | --- |
TC-14  同值送 2 次，再送不同值；直接  201／200／409；只 1 組。跨日快照被 DB Trigger 拒絕。
|     | 來源保護  | 照   |     |     |     |
| --- | ----- | --- | --- | --- | --- |
SQL 插⼊跨日快照。
第 68 頁

Fitness Tracking Management System — SRS v1.1
| 案例  | 功能  | 前置條件  | 操作步驟  |     | 預期結果  |
| --- | --- | ----- | ----- | --- | ----- |
改重量→刪該組→SQL換所屬場
| TC-15  | FR-14 組數修正  | completed恰1組  |     | 修改200且量改變；刪組409；換場次被DB拒絕。  |     |
| ------ | ----------- | ------------- | --- | -------------------------- | --- |
次。
空場次與已有⼀組的  直接 SQL 完成空場次、刪除
TC-16  FR-15 DB 非空約束  completed 場次；非  completed 最後⼀組、刪除其場次 三種繞過均回 23514 且交易回滾；無空 completed 場次留存。
|     |     | superuser 測試角⾊  | 動作快照。  |     |     |
| --- | --- | --------------- | ------ | --- | --- |
FR-15 並⾏刪最後 兩連線各刪不同⼀組，第⼀筆提交
| TC-17  |     | completed有2組  |     | ⾄多⼀筆刪除提交；另⼀約束失敗；最終≥1組。  |     |
| ------ | --- | ------------- | --- | ----------------------- | --- |
|        | 組   | 後第⼆筆再提交。      |     |                         |     |
刪除 admins 列後以原 Cookie 呼叫
TC-18  管理員撤權  有效 JWT 與 admins 列  立即 403；JWT 無 role；⼀般會員 API 仍依所有權執⾏。
管理 API。
開始後修改課表模板、會員設定與 歷史仍顯示場次快照的 V1 名稱、處⽅、順序，並查得當時排
| TC-19  | FR-16 完整歷史  | P1/V1 有已完成場次  |           |     |       |
| ------ | ----------- | ------------- | --------- | --- | ----- |
|        |             |               | 動作產⽣ V2。  |     | 課輸⼊。  |
完成組 60×12、
查 Dashboard 外加重量訓練量、總 external_load_volume=1890 kg·次；total_reps=45；
| TC-20  | FR-17 統計  | 65×10、65×8 及徒⼿  |     |                             |     |
| ------ | --------- | --------------- | --- | --------------------------- | --- |
|        |           | 次數與徒⼿次數。        |     | bodyweight_reps=15；取消場次排除。  |     |
0×15
重複409；改值成功；刪最新後目前體重回退；刪最後⼀筆回
兩日各1筆且 Profile  同日新增、改值、刪最新，再刪最
| TC-21  | FR-18 體重 CRUD  |      |       | 409 LAST_BODY_RECORD_REQUIRED；已發布輸⼊快照 |     |
| ------ | -------------- | ---- | ----- | ------------------------------------- | --- |
|        |                | 已完成  | 後⼀筆。  |                                       |     |
不變。
第 69 頁

Fitness Tracking Management System — SRS v1.1
| 案例     | 功能        | 前置條件   |                  | 操作步驟  |                                     | 預期結果  |
| ------ | --------- | ------ | ---------------- | ----- | ----------------------------------- | ----- |
|        |           |        | SHOW隔離；故意互鎖造死結，再 |       | read committed；回滾後409或503；不得部分寫⼊或假成 |       |
| TC-22  | 隔離／死結／逾時  | 兩測試連線  |                  |       |                                     |       |
持鎖超3秒。  功。
開始時來源INSERT前注⼊錯誤；
| TC-23  | 原⼦性／來源  | 無active  |     |     | 前者全回滾；後者DB拒絕，原來源仍在。  |     |
| ------ | ------- | -------- | --- | --- | -------------------- | --- |
直接刪既有來源後COMMIT。
按鎖順序：開始先成功則既有場次保留；封存先提交則開始
| TC-24  | 封存／開始競爭  | 已發布未封存P  | 兩連線同時封存P及開始P。  |     |     |     |
| ------ | -------- | -------- | -------------- | --- | --- | --- |
409；無斷鏈。
|        |          |                      | 並⾏完成及新增；重送完成或取   |     | 存組先則完成可見；完成先則新增409；同終態重送200時間       |             |
| ------ | -------- | -------------------- | ---------------- | --- | ----------------------------------- | ----------- |
| TC-25  | 完成／存組競爭  | 場次已有1組               |                  |     |                                     |             |
|        |          |                      |                  | 消。  |                                     | 不變，換終態409。  |
|        |          |                      | DELETE場次，查組、來源、課 |     | 204；場次/組/來源刪除，課表/版本保留；in_progress刪除 |             |
| TC-26  | 整場刪除     | completed或cancelled  |                  |     |                                     |             |
表、版本。  409。
兩個 PHP Worker；相 15 分鐘內連續 21 次失敗；換 IP； 前 20 次 401，第 21 次 429 + Retry-After；不同 IP 獨立；成功
| TC-27  | 安全與限流  |         |                  |     |     |                  |
| ------ | ------ | ------- | ---------------- | --- | --- | ---------------- |
|        |        | 同來源 IP  | 成功登⼊；模擬 DB 不可用。  |     |     | 後清除；DB 失敗回 503。  |
既有歷史引用 V1 圖片  管理員修改 image_url 建立 V2；查 V2 新增；舊場次仍引用 V1 的 image_url 與⽂字說明；缺圖時
| TC-28  | FR-08 圖片版本  |      |                  |     |                          |     |
| ------ | ----------- | ---- | ---------------- | --- | ------------------------ | --- |
|        |             | URL  | 詢舊場次；模擬舊圖片網址失效。  |     | 顯示⽂字替代內容，不宣稱系統備份圖片⼆進位檔。  |     |
200⼈5分鐘；另測3種視窗及指
| TC-29  | 效能／響應式  | 第5章資料量及環境  |     |     | 依NFR實測記錄P95、錯誤率及截圖；未達不得標示通過。  |     |
| ------ | ------- | ---------- | --- | --- | ----------------------------- | --- |
定瀏覽器。
第 70 頁

Fitness Tracking Management System — SRS v1.1
| 案例  | 功能  | 前置條件  | 操作步驟  |     | 預期結果  |
| --- | --- | ----- | ----- | --- | ----- |
建立新 Schema；套用 v1.1
| Schema／Migration  |      | 空測試庫與含代表資料 |               | 20 張應用表、25 條 FK；規劃快照與舊訓練歷史回填； |                    |
| ----------------- | ---- | ---------- | ------------- | ----------------------------- | ------------------ |
| TC-30             |      |            | Migration；執⾏  |                               |                    |
|                   | ⼀致性  | 的舊版庫       |               |                               | Manifest 比對 PASS。  |
schema_consistency.py。
同時有效、過期
執⾏ cleanup-expired.php；查詢剩 過期資料刪除，有效 Session 保留；每批≤500；日誌無
| TC-31  Session 與限流清理  |     | Session 與超過 15 分鐘 |     |     |                  |
| --------------------- | --- | ----------------- | --- | --- | ---------------- |
|                       |     | 餘資料與 JSON 日誌。     |     |     | Token、雜湊或原始 IP。  |
的失敗事件

第 71 頁

Fitness Tracking Management System — SRS v1.1
7. 參考資料
l 健身動作資料集：https://github.com/hasaneyldrm/exercises-dataset
l 協作：ChatGPT、Codex
[1] PostgreSQL 16 Transaction Isolation：https://www.PostgreSQL.org/docs/16/transaction-iso.html
[2] PostgreSQL 16 Constraints：https://www.PostgreSQL.org/docs/16/ddl-constraints.html
[3] PostgreSQL 16 CREATE TRIGGER：https://www.PostgreSQL.org/docs/16/sql-createtrigger.html
[4] OWASP Authorization Cheat Sheet：
https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html
第 72 頁
