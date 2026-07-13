export const SITE_TITLE = '潔米爸書房';
export const SITE_DESCRIPTION =
  '潔米爸的長文分享空間：育兒觀、語言自學、旅遊與世界文化（語寶），以及紫微斗數自學筆記與漫畫（紫微筆記）。';

export const CATEGORIES = {
  yubao: {
    name: '語寶',
    description: '育兒觀 · 語言自學 · 旅遊分享 · 各國地理文化歷史',
  },
  ziwei: {
    name: '紫微筆記',
    description: '紫微斗數自學 · 紫微斗數漫畫',
  },
} as const;

export type CategoryId = keyof typeof CATEGORIES;
