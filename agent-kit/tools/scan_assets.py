#!/usr/bin/env python3
"""
掃描本機資料夾,把所有檔案登錄進 memory/assets.db。
對應需求：「本機電腦協助讓我去找尋資料夾並存取,並把資訊存進本機資料庫」。

用法：
    python3 tools/scan_assets.py <資料夾1> [資料夾2] ...
    python3 tools/scan_assets.py ~/Movies ~/Pictures
    python3 tools/scan_assets.py --find 貓          # 用關鍵字查已索引的素材
    python3 tools/scan_assets.py --stats            # 看統計

只用 Python 標準庫,免裝任何套件。
"""
import hashlib
import os
import sqlite3
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "..", "memory", "assets.db")
SCHEMA = os.path.join(HERE, "..", "memory", "schema.sql")
HASH_MAX_BYTES = 64 * 1024 * 1024  # 超過 64MB 的檔不算 sha1(太慢),欄位留空

KIND = {
    "image": {"jpg", "jpeg", "png", "gif", "webp", "heic", "bmp", "tiff", "svg"},
    "video": {"mp4", "mov", "m4v", "avi", "mkv", "webm", "flv"},
    "audio": {"mp3", "wav", "m4a", "aac", "flac", "ogg"},
    "doc":   {"pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "txt", "md", "csv"},
}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".cache", ".Trash", "renders"}


def kind_of(ext):
    for k, exts in KIND.items():
        if ext in exts:
            return k
    return "other"


def sha1_of(path, size):
    if size > HASH_MAX_BYTES:
        return None
    h = hashlib.sha1()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def connect():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    con = sqlite3.connect(DB)
    with open(SCHEMA, encoding="utf-8") as f:
        con.executescript(f.read())
    return con


def scan(roots):
    con = connect()
    cur = con.cursor()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    added = updated = 0
    for root in roots:
        root = os.path.abspath(os.path.expanduser(root))
        if not os.path.isdir(root):
            print(f"  ⚠ 跳過(不是資料夾)：{root}")
            continue
        print(f"  掃描：{root}")
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
            for name in filenames:
                if name.startswith("."):
                    continue
                path = os.path.join(dirpath, name)
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
                mtime = datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(timespec="seconds")
                row = cur.execute("SELECT id, mtime FROM assets WHERE path=?", (path,)).fetchone()
                if row and row[1] == mtime:
                    continue  # 沒變,略過
                vals = (path, name, ext, kind_of(ext), st.st_size, mtime,
                        sha1_of(path, st.st_size), "local", now)
                if row:
                    cur.execute(
                        "UPDATE assets SET filename=?,ext=?,kind=?,size_bytes=?,mtime=?,"
                        "sha1=?,source=?,indexed_at=? WHERE path=?",
                        (name, ext, kind_of(ext), st.st_size, mtime,
                         sha1_of(path, st.st_size), "local", now, path))
                    cur.execute("UPDATE assets_fts SET filename=? WHERE rowid=?", (name, row[0]))
                    updated += 1
                else:
                    cur.execute(
                        "INSERT INTO assets(path,filename,ext,kind,size_bytes,mtime,sha1,source,indexed_at)"
                        " VALUES (?,?,?,?,?,?,?,?,?)", vals)
                    cur.execute("INSERT INTO assets_fts(rowid,filename,tags,note) VALUES (?,?,'','')",
                                (cur.lastrowid, name))
                    added += 1
    con.commit()
    print(f"\n✅ 完成：新增 {added}、更新 {updated}。DB：{os.path.abspath(DB)}")
    con.close()


def find(keyword):
    con = connect()
    rows = con.execute(
        "SELECT a.kind,a.path,a.size_bytes FROM assets_fts f JOIN assets a ON a.id=f.rowid "
        "WHERE assets_fts MATCH ? ORDER BY a.mtime DESC LIMIT 50", (keyword + "*",)).fetchall()
    if not rows:
        print(f"找不到含「{keyword}」的素材。")
    for kind, path, size in rows:
        print(f"  [{kind:5}] {size/1e6:7.1f}MB  {path}")
    con.close()


def stats():
    con = connect()
    print("各類型數量：")
    for kind, n, mb in con.execute(
        "SELECT kind, COUNT(*), SUM(size_bytes)/1e6 FROM assets GROUP BY kind ORDER BY 2 DESC"):
        print(f"  {kind:6} {n:6} 個   {mb:10.1f} MB")
    con.close()


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
    elif args[0] == "--find" and len(args) > 1:
        find(args[1])
    elif args[0] == "--stats":
        stats()
    else:
        scan(args)
