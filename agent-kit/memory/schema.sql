-- 本機素材/檔案索引 DB（SQLite）
-- 由 tools/scan_assets.py 自動建立與維護。
-- 目的：把散落本機(+ 之後 Google Drive)的檔案登錄起來,Agent 用查詢取代每次重掃硬碟。

CREATE TABLE IF NOT EXISTS assets (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  path        TEXT UNIQUE NOT NULL,   -- 絕對路徑
  filename    TEXT NOT NULL,
  ext         TEXT,                   -- 副檔名(小寫,不含點)
  kind        TEXT,                   -- image / video / audio / doc / other
  size_bytes  INTEGER,
  mtime       TEXT,                   -- 最後修改時間 (ISO)
  sha1        TEXT,                   -- 內容雜湊(找重複檔用;大檔可略過)
  source      TEXT DEFAULT 'local',   -- local / gdrive
  tags        TEXT,                   -- 逗號分隔,人工或 AI 標註
  note        TEXT,                   -- 備註
  indexed_at  TEXT NOT NULL           -- 這筆登錄時間
);

CREATE INDEX IF NOT EXISTS idx_assets_kind ON assets(kind);
CREATE INDEX IF NOT EXISTS idx_assets_ext  ON assets(ext);
CREATE INDEX IF NOT EXISTS idx_assets_sha1 ON assets(sha1);

-- 全文搜尋(用檔名 + tags + note 找素材)
CREATE VIRTUAL TABLE IF NOT EXISTS assets_fts USING fts5(
  filename, tags, note, content='assets', content_rowid='id'
);
