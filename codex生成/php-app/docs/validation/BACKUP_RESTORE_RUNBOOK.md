# FitTrack 備份與還原操作手冊

## 備份內容

每日排程產生一個 `fittrack-backup-<run-id>.tar.gz.enc`，保留 7 天，內含：

- `database.dump`：PostgreSQL custom-format 備份。
- `database-manifest.json`：Schema Migration 版本、20 張應用表、25 條外鍵與每表筆數。
- `media-sha256.txt`：2,648 個動作圖片與 GIF 的 SHA-256。

明文資料庫不會上傳 GitHub Artifact。加密金鑰僅儲存在 GitHub Repository Secret `FITTRACK_BACKUP_KEY`，不得寫入 Git、截圖或日誌。

## 下載與驗簽

```bash
gh run download <run-id> --repo Loisekoy/- --name fittrack-backup-<run-id>
shasum -a 256 -c fittrack-backup-<run-id>.sha256
```

## 解密

將密鑰放在當前 Shell 的 `FITTRACK_BACKUP_KEY`，不要寫在指令參數或 Shell History：

```bash
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 \
  -in fittrack-backup-<run-id>.tar.gz.enc \
  -out fittrack-backup.tar.gz \
  -pass env:FITTRACK_BACKUP_KEY
tar -xzf fittrack-backup.tar.gz
```

## 還原到獨立資料庫

不得先還原到正式庫。先建立名稱含 `fittrack_restore` 的空白 PostgreSQL 16 資料庫：

```bash
pg_restore --dbname="$RESTORE_DATABASE_URL" --no-owner --no-acl --exit-on-error database.dump
DATABASE_URL="$RESTORE_DATABASE_URL" APP_ENV=test \
  php bin/database-manifest.php --verify database-manifest.json
php bin/verify-media-manifest.php media-sha256.txt
```

只有 Manifest 與媒體雜湊全數通過後，才能進入正式還原的變更視窗。

## RPO / RTO

- RPO 門檻：24 小時；每日 03:17 Asia/Taipei 執行。
- RTO 目標：60 分鐘。
- 每次排程都自動還原到獨立 PostgreSQL 16 並比對筆數；排程失敗時不上傳未驗證的備份。
