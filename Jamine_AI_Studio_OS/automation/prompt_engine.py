"""prompt_engine.py — 六格輸入 → 完整影片 Prompt。

實作 07_Prompts/PROMPT_ENGINE.md 的組裝規格：
[角色錨句] + [情緒表演] + [場景世界] + [運鏡] + [光線色彩] + [聲音] + [技術]

已內建 Phase 1.1 修補：
  缺口 #4 —— 光線優先序：明確指定 > 場景預設 > （最後才）情緒隱含。
             場景先定調，情緒不會覆蓋場景的冷暖。

用法（CLI）：
  python prompt_engine.py --char ah-zhe --emotion anxiety \
      --scene 台北捷運 --time 晚上 --camera slow-push [--lighting neon]
"""
from __future__ import annotations

import argparse

import studio


def _match_key(mapping: dict, scene: str) -> str | None:
    """場景字串以子字串比對 mapping 的鍵，回傳命中的鍵。"""
    for key in mapping:
        if key in scene:
            return key
    return None


def match_scene_key(scene: str, libs: dict) -> str | None:
    """回傳分鏡場景字串對應的地點鍵（無則 None）。"""
    return _match_key(libs["scenes"], scene)


def resolve_lighting(shot_lighting: str, scene: str, libs: dict) -> tuple[str, str]:
    """缺口 #4 修補：決定光線代號與展開文字。

    優先序：明確指定的光線 > 場景預設光 > dawn 保底。
    情緒「不」參與光線決定——場景先定調冷暖。
    """
    code = (shot_lighting or "").strip().strip("（）()")
    # 去掉「neon（自動推導：城市場景）」這類註記
    code = code.split("（")[0].split("(")[0].strip()
    if code and code in libs["lighting"]:
        return code, libs["lighting"][code]
    key = _match_key(libs["lighting_scene_default"], scene)
    if key:
        code = libs["lighting_scene_default"][key]
        return code, libs["lighting"][code]
    return "dawn", libs["lighting"]["dawn"]


def resolve_scene(scene: str, libs: dict, fallback_key: str | None = None) -> dict:
    """回傳場景 desc/sound。分鏡場景欄常是「取景標籤」而非地點，
    比對不到時沿用 fallback_key（上一個鏡頭的地點，carry-forward）。"""
    key = match_scene_key(scene, libs)
    if key:
        return libs["scenes"][key]
    if fallback_key and fallback_key in libs["scenes"]:
        return libs["scenes"][fallback_key]
    return {"desc": scene, "sound": "ambient sound of the scene"}


def build_prompt(char_slugs, emotion, scene, time, camera, lighting,
                 dialogue="", libs=None, chars=None, fallback_key=None) -> str:
    libs = libs or studio.load_libraries()
    chars = chars or studio.load_characters()

    parts = []

    # 1. 角色錨句（鎖外型一致性）；命盤空間等無角色鏡頭略過
    anchors = [chars[s]["anchor"] for s in char_slugs if s in chars and chars[s]["anchor"]]
    if anchors:
        parts.append(" ".join(anchors))

    # 2. 情緒表演
    emo = libs["emotion"].get(emotion, "")
    if emo:
        parts.append(f"Performance and mood: {emo}.")

    # 3. 場景與世界觀（比對不到地點時 carry-forward）
    sc = resolve_scene(scene, libs, fallback_key)
    parts.append(f"Setting: {sc['desc']}.")

    # 4. 運鏡
    cam = libs["camera"].get(camera, "")
    if cam:
        parts.append(cam)

    # 5. 光線與色彩（缺口 #4）
    _, light_text = resolve_lighting(lighting, scene, libs)
    parts.append(f"Lighting: {light_text}.")

    # 6. 聲音
    parts.append(f"Sound: {sc['sound']}.")

    # 7. 技術 + 品牌護欄
    parts.append(libs["technical"])
    parts.append(libs["brand_guardrail"])

    return " ".join(p.strip() for p in parts if p.strip())


def build_from_shot(row: dict, chars: dict, libs: dict, fallback_key=None) -> str:
    """從一列分鏡 dict 產出 Prompt；fallback_key 為上一鏡地點，供 carry-forward。"""
    name_to_slug = chars["_name_to_slug"]
    char_slugs = studio.split_characters(row.get("角色", ""), name_to_slug)
    return build_prompt(
        char_slugs=char_slugs,
        emotion=row.get("情緒", "").strip(),
        scene=row.get("場景", "").strip(),
        time="",
        camera=row.get("運鏡", "").strip(),
        lighting=row.get("光線", "").strip(),
        dialogue=row.get("對白/旁白", ""),
        libs=libs,
        chars=chars,
        fallback_key=fallback_key,
    )


def _cli():
    ap = argparse.ArgumentParser(description="六格 → 完整 Prompt")
    ap.add_argument("--char", default="", help="角色 slug，多個用逗號")
    ap.add_argument("--emotion", required=True)
    ap.add_argument("--scene", required=True)
    ap.add_argument("--time", default="")
    ap.add_argument("--camera", required=True)
    ap.add_argument("--lighting", default="")
    args = ap.parse_args()
    slugs = [s for s in args.char.split(",") if s.strip()]
    print(build_prompt(slugs, args.emotion, args.scene, args.time,
                       args.camera, args.lighting))


if __name__ == "__main__":
    _cli()
