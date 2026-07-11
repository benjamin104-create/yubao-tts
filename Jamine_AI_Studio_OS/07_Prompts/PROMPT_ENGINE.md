# 07 — Prompt 引擎 (Prompt Engine)

> **不用再手寫 Prompt。** 你只填六格，AI 自己輸出三千字 Prompt。
> 引擎的原料 = Brand Bible + World Bible + Character Bible + 三大電影語言庫。

---

## 一、六格輸入 (The Six-Slot Input)

```
角色：   （填 character slug，如 ah-zhe）
情緒：   （填 emotion 代號，如 loneliness）
場景：   （填 scene，如 台北捷運）
時間：   （如 晚上）
運鏡：   （填 camera 代號，如 slow-push）
光線：   （選填；留空則自動推導）
```

範例：

```
角色：阿哲
情緒：孤獨
場景：台北捷運
時間：晚上
運鏡：slow-push
光線：（留空 → 自動 neon）
```

---

## 二、引擎怎麼展開（給 AI 的組裝指令）

> 你是 Jamine Studio 的 Prompt Engineer。依下列六格輸入，產出一段可直接餵給 Kling / Seedance 的完整影片 Prompt。
> 組裝時**必須**：
> 1. 先讀 `01_Brand`、`02_World`，確保 Tone 與世界觀一致（暖=理解、冷=壓力、神秘不玄幻、不恐怖不浮誇）。
> 2. 用 `03_Characters/{slug}` 的**定裝錨句**鎖定角色外型，確保跨鏡頭一致。
> 3. 用 `emotion_library` 展開表演，`camera_language` 展開運鏡，`lighting_library` 展開光線（未指定則自動推導）。
> 4. 若場景／道具已在 `04_Assets` 登記，沿用既有風格描述，不另創。
>
> 輸出結構固定為：
> `[Character anchor] + [Action & emotion] + [Scene & world] + [Camera] + [Lighting & color] + [Mood & sound cue] + [Technical: cinematic, aspect ratio, quality]`

---

## 三、輸出範例（三千字 Prompt 的縮影）

輸入上面的阿哲案例，引擎輸出（節錄）：

> A tired 28-year-old Taiwanese man, 176cm, slim, messy black fringe, grey hoodie over a plain tee, headphones around his neck — sitting alone in a near-empty Taipei MRT carriage at night. His shoulders are slightly hunched, eyes unfocused, breathing shallow, a subtle sense of loneliness and inner exhaustion. **Slow, deliberate push-in** toward his face, gradually tightening the frame to pull the viewer into his inner state. **Cool neon light** from the passing platform reflects on the wet windows, cyan and blue tones dominating the cold, pressured urban mood. The carriage sways gently; muffled train ambience, distant announcement. Cinematic, shallow depth of field, 2.39:1, film grain, high detail, moody realism, no horror, no exaggeration.

（正式使用時引擎會展開更完整的動作、環境、鏡頭運動曲線與時間軸描述。）

---

## 四、為什麼這樣做

- **一致性**：外型、世界觀、色彩由 Bible 鎖死，季季不走鐘。
- **速度**：六格 → 秒出 Prompt，一集 40 鏡頭不再是 40 次從零手寫。
- **可交棒**：DeepSeek / Production Worker 可以照這份規格批次跑（見 Phase 2）。

---

## 五、單鏡頭 Prompt 存檔

每個生成出來的鏡頭 Prompt，用 [`_TEMPLATE_shot_prompt.md`](_TEMPLATE_shot_prompt.md) 存檔，命名 `{PROJECT}_S01_E01_shot_012_v01.md`，方便重生與版本比對。
