export const SITE_TITLE = '潔米爸書房';
export const SITE_DESCRIPTION =
  '潔米爸的書房：向外，陪女兒語寶理解世界——育兒、語言、旅遊與各國文化；向內，用紫微斗數慢慢理解自己。';

export const CATEGORIES = {
  yubao: {
    name: '語寶',
    description: '向外的理解——育兒觀 · 語言自學 · 旅遊 · 各國地理文化歷史',
  },
  ziwei: {
    name: '紫微筆記',
    description: '向內的理解——紫微斗數自學 · 紫微斗數漫畫',
  },
} as const;

export type CategoryId = keyof typeof CATEGORIES;
