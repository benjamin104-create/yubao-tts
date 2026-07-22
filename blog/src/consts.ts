export const SITE_TITLE = '潔米爸・腦內革命記';
export const SITE_DESCRIPTION =
  '潔米爸把命盤畫成一張心的地圖：從六種顏色人格、語寶與紫微筆記，慢慢理解自己。';

export const CATEGORIES = {
  yubao: {
    name: '語寶',
    description: '向外的理解——育兒陪伴 · 語言自學 · 旅遊 · 世界文化',
  },
  ziwei: {
    name: '紫微筆記',
    description: '灰色定盤者的入口——紫微斗數自學 · 漫畫 · 理性拆解',
  },
} as const;

export type CategoryId = keyof typeof CATEGORIES;

export const NINE_GRID = [
  {
    id: 'white',
    theme: 'white',
    eyebrow: '白 · 純潔完美',
    name: '畫師',
    description: '空白畫布，替你的心情找到顏色',
    href: '/quiz/',
    index: '01',
  },
  {
    id: 'blue',
    theme: 'blue',
    eyebrow: '藍 · 冷靜專業',
    name: '推理者',
    description: '把焦慮拆成可以理解的問題',
    href: '/personas/blue/',
    index: '02',
  },
  {
    id: 'black',
    theme: 'black',
    eyebrow: '黑 · 權威神秘',
    name: '進化者',
    description: '看見野心，也看見選擇的代價',
    href: '/personas/black/',
    index: '03',
  },
  {
    id: 'green',
    theme: 'green',
    eyebrow: '綠 · 療癒平衡',
    name: '歌者',
    description: '替疲憊留一段可以呼吸的拍子',
    href: '/personas/green/',
    index: '04',
  },
  {
    id: 'core',
    theme: 'core',
    eyebrow: '本體我 · I',
    name: '潔米爸',
    description: '容器我 × 感受我，發現意識 E 的存在',
    href: '/self/',
    index: 'I',
  },
  {
    id: 'gray',
    theme: 'gray',
    eyebrow: '灰 · 中立穩重',
    name: '定盤者',
    description: '紫微筆記本家，把命盤讀成理解',
    href: '/ziwei/',
    index: '05',
  },
  {
    id: 'yubao',
    theme: 'yubao',
    eyebrow: '向外的理解',
    name: '語寶',
    description: '育兒、語言、旅遊與世界文化',
    href: '/yubao/',
    index: '☀',
  },
  {
    id: 'red',
    theme: 'red',
    eyebrow: '紅 · 熱情自信',
    name: '行動者',
    description: '把在乎變成跨出去的勇氣',
    href: '/personas/red/',
    index: '06',
  },
  {
    id: 'cards',
    theme: 'cards',
    eyebrow: '互動入口',
    name: '卡牌遊戲',
    description: '每日一卡，練習一種心理能力',
    href: '/cards/',
    index: '◇',
  },
] as const;

export const PERSONA_PAGES = {
  blue: {
    theme: 'blue',
    eyebrow: '藍 · 冷靜專業',
    title: '推理者',
    description: '不急著猜答案，先把問題看清楚。',
    promise: '用洞察與分析降低焦慮，讓複雜的感受有一個可以理解的結構。',
    topics: ['心理分析', '命盤邏輯', '焦慮拆解'],
  },
  black: {
    theme: 'black',
    eyebrow: '黑 · 權威神秘',
    title: '進化者',
    description: '承認企圖心，也保留選擇與界線。',
    promise: '神秘感來自內心深處，不來自魔法；蛻變不是命令，而是一場誠實的自我對話。',
    topics: ['深度命理', '突破慣性', '野心與界線'],
  },
  green: {
    theme: 'green',
    eyebrow: '綠 · 療癒平衡',
    title: '歌者',
    description: '先讓呼吸慢下來，再一起往前。',
    promise: '把育兒、陪伴、旅行與日常休息，整理成能接住疲憊的內容。',
    topics: ['育兒陪伴', '旅行日常', '身心平衡'],
  },
  red: {
    theme: 'red',
    eyebrow: '紅 · 熱情自信',
    title: '行動者',
    description: '勇氣不是不怕，而是仍願意跨一步。',
    promise: '把熱情放回生活選擇，為在乎的人與重要的事採取正向行動。',
    topics: ['行動練習', '突破舒適圈', '正向勇氣'],
  },
} as const;

export type PersonaSlug = keyof typeof PERSONA_PAGES;
