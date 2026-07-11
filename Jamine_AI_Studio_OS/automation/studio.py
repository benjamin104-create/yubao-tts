"""studio.py — Jamine AI Studio OS 共用工具。

負責：讀 Bible / 語言庫、解析分鏡表、讀素材庫索引。
純標準庫，不需安裝任何套件。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# automation/ 的上一層就是 Jamine_AI_Studio_OS/
OS_ROOT = Path(__file__).resolve().parent.parent
DATA = Path(__file__).resolve().parent / "data"


def load_libraries() -> dict:
    """讀電影語言庫（運鏡 / 情緒 / 光線 / 場景）機器版。"""
    return json.loads((DATA / "libraries.json").read_text(encoding="utf-8"))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_characters() -> dict:
    """掃 03_Characters/*.md，回傳 {slug: {name, anchor}} 與名稱對照。

    回傳 dict 具備兩把鑰匙查法：以 slug 或以中文名皆可取到角色。
    """
    chars: dict[str, dict] = {}
    name_to_slug: dict[str, str] = {}
    cdir = OS_ROOT / "03_Characters"
    for f in sorted(cdir.glob("*.md")):
        if f.name.startswith("_TEMPLATE"):
            continue
        text = _read(f)
        name = _table_value(text, "中文名")
        slug = _strip_code(_table_value(text, "slug"))
        anchor = _anchor(text)
        if not slug:
            continue
        chars[slug] = {"name": name, "anchor": anchor}
        if name:
            name_to_slug[name] = slug
    chars["_name_to_slug"] = name_to_slug
    return chars


def _table_value(text: str, key: str) -> str:
    """從 markdown 表格取 `| key | value |` 的 value。"""
    m = re.search(rf"^\|\s*{re.escape(key)}\s*\|\s*(.*?)\s*\|", text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _strip_code(s: str) -> str:
    return s.strip().strip("`").strip()


def _anchor(text: str) -> str:
    """取「## Prompt 定裝錨句」後第一段 > 引用的英文錨句。"""
    m = re.search(r"##\s*Prompt\s*定裝錨句.*?\n+>\s*(.+?)\n", text, re.DOTALL)
    return m.group(1).strip() if m else ""


def load_asset_slugs() -> set[str]:
    """從 04_Assets/ASSET_LIBRARY_INDEX.md 收集所有已登記素材 slug。"""
    text = _read(OS_ROOT / "04_Assets" / "ASSET_LIBRARY_INDEX.md")
    slugs = set()
    for line in text.splitlines():
        # 素材表格列：| 名稱 | `slug` | ... |
        m = re.match(r"^\|[^|]*\|\s*`([a-z0-9\-]+)`\s*\|", line)
        if m:
            slugs.add(m.group(1))
    return slugs


def parse_storyboard(path: Path) -> list[dict]:
    """解析分鏡 markdown 表格，回傳每個鏡頭一個 dict。"""
    lines = _read(path).splitlines()
    header = None
    rows = []
    for line in lines:
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            if "運鏡" in cells and "Shot Prompt" in cells:
                header = cells
            continue
        if set("".join(cells)) <= set("-: "):  # 分隔列
            continue
        if len(cells) != len(header):
            continue
        row = dict(zip(header, cells))
        if not re.match(r"^\d+$", row.get("#", "")):
            continue
        rows.append(row)
    return rows


def split_assets(cell: str) -> list[str]:
    """把「需用素材」欄拆成 token 清單。"""
    cell = cell.strip()
    if not cell or cell in {"—", "-"}:
        return []
    return [t.strip() for t in re.split(r"[,\s、]+", cell) if t.strip()]


def split_characters(cell: str, name_to_slug: dict) -> list[str]:
    """把「角色」欄（可能是 潔米爸/阿哲）轉成 slug 清單。"""
    cell = cell.strip()
    if not cell or cell in {"—", "-"}:
        return []
    out = []
    for name in re.split(r"[/／]", cell):
        name = name.strip()
        slug = name_to_slug.get(name)
        if slug:
            out.append(slug)
    return out
