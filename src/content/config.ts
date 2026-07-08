import { z, defineCollection } from 'astro:content';

// 第二層萃取用的「AI 草稿 + 人工確認」成對欄位
// ai_draft 由 AI 產生;confirmed 由你本人審閱後填入(空字串代表尚未確認)
const draftPair = z
  .object({
    ai_draft: z.string().optional().default(''),
    confirmed: z.string().optional().default(''),
  })
  .optional()
  .default({ ai_draft: '', confirmed: '' });

const articlesCollection = defineCollection({
  type: 'content',
  schema: z.object({
    // ── 既有欄位(維持不變,舊文章照常運作)──
    title: z.string(),
    journal: z.string(),
    category: z.string().default('未分類'),
    pubDate: z.string(),
    link: z.string(),
    doi: z.string().optional().default(''),
    tags: z.array(z.string()).default([]),

    // ── 狀態機:區分「快速道(摘要)」與「深讀道(全文)」──
    depth: z.enum(['triage', 'reading', 'done']).optional().default('triage'),
    fulltext_source: z
      .enum(['pmc', 'upload', 'unpaywall', 'none', ''])
      .optional()
      .default(''),
    pmid: z.string().optional().default(''),

    // ── 第一層:高信賴,全文自動填入 ──
    study_design: z.string().optional().default(''),
    sample_size: z.string().optional().default(''),
    inclusion: z.string().optional().default(''),
    exclusion: z.string().optional().default(''),
    instruments: z.array(z.string()).optional().default([]),
    statistics: z.array(z.string()).optional().default([]),
    limitations_stated: z.string().optional().default(''),
    funding: z.string().optional().default(''),
    coi: z.string().optional().default(''),

    // ── 第二層:AI 草稿 + 你確認 ──
    pico: draftPair,
    rob: z
      .object({
        tool: z.string().optional().default(''), // 如 Cochrane-RoB2 / Newcastle-Ottawa
        ai_draft: z.string().optional().default(''),
        confirmed: z.string().optional().default(''),
      })
      .optional()
      .default({ tool: '', ai_draft: '', confirmed: '' }),
    key_findings: draftPair,
    gap: draftPair,

    // ── 關聯與個人筆記 ──
    related: z.array(z.string()).optional().default([]), // 以 pmid 互連
    my_notes: z.string().optional().default(''),
  }),
});

export const collections = {
  articles: articlesCollection,
};
