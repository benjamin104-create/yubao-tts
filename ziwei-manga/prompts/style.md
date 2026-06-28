# style.md — 全域風格（每次生圖都會自動前置）

> 【給你看的中文說明，不會送進 API】
> 這份是全系列共用的「風格 + 硬規則」。只有 PROMPT 標記區塊（下方圍欄）之間的英文，
> 會被腳本擷取送進 gpt-image-2。要調全系列風格，改這裡即可。
> （注意：中文說明區請勿寫出 PROMPT 的起訖標記字串，以免擷取錯位。）
>
> 已內含：港漫武俠電影感（馬榮成《風雲》、黃玉郎《天子傳奇／龍虎門》）、深藍夜色 + 金色命盤、
> 古卷紙感、華麗金框、台北101、紫微堂、情緒濃但不恐怖、以及最關鍵的
> 「**不要生成任何文字／中文，所有字留白後製**」與「命盤十二宮硬規則」。

===PROMPT START===
SERIES ART STYLE — apply to every image:

Medium & influence: a premium Hong Kong wuxia manhua splash page, in the cinematic, heroic
ink style of Ma Wing-shing (Fung Wan / Storm Riders) and Tony Wong Yuk-long
(Dragon Tiger Gate / Son of Heaven). Highly detailed, dramatic chiaroscuro, dynamic
wind-blown robes, flowing hair, powerful anatomy, epic depth, motion energy, painterly
yet sharp linework. Movie-poster composition and lighting.

Palette & mood: deep midnight-blue night sky with a luminous starfield; rich GOLD accents —
glowing golden astrolabe / destiny-chart light, gilded ornate art-nouveau border frame
around the whole image; aged parchment-scroll textures; warm lantern glow. Emotionally
intense and heartfelt, awe-inspiring — but NEVER horror, NEVER gore, NEVER scary.
Colors must be vivid and high-contrast between elements (do not let the whole image collapse
into one similar hue — keep clear separation of blue night, gold chart, warm skin/lantern,
and parchment cream so the page feels rich, not flat).

Recurring world elements (use when relevant): the Taipei 101 tower glowing in a distant night
cityscape; "Zi Wei Tang" study hall — an old hall with walls of ancient books, an armillary
sphere, oil lamps, hanging lanterns, and a long unrolled destiny-chart scroll; swirling golden
star-constellation lines; an optional majestic golden/azure dragon coiling through the starry sky.

ABSOLUTE TEXT RULE (critical): Render NO text of any kind. No Chinese characters, no letters,
no numbers, no glyphs, no calligraphy, no captions, no signatures, no UI. Any area that would
hold a title, dialogue balloon, or chart label must be left as CLEAN EMPTY SPACE — an empty
speech bubble, an empty banner, or a blank aged-paper cell — reserved for later typesetting.
If a destiny chart appears, its cells must be EMPTY blank parchment panels (no writing inside).

DESTINY-CHART (Zi Wei / Purple Star) HARD RULES — obey whenever a chart is shown:
- The chart is a SQUARE grid: a 4x4 layout whose 12 OUTER cells form a ring of palaces, with a
  larger empty 2x2 center panel. Exactly 12 outer palace cells. Keep the grid geometrically clean.
- All 12 cells and the center are EMPTY blank parchment (no text — labels are added in post).
- Do not invent fake symbols or pseudo-Chinese inside cells. Keep them clean for typesetting.
- When constellation lines connect palaces (san-fang-si-zheng), draw a clear structural pattern
  (one home cell, its opposite cell, and two trine cells linked) — not random decorative lines.
- Prioritize a correct, clean, readable chart structure first; decorative starlight/dragon/gold
  effects must NOT bury or distort the chart's grid logic.

Format: vertical portrait orientation, suitable for an Instagram 4:5 / comic page. Full-bleed
illustration inside the ornate golden border. No watermark.
===PROMPT END===
