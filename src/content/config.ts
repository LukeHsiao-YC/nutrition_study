import { z, defineCollection } from 'astro:content';

const articlesCollection = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    journal: z.string(),
    category: z.string().default('未分類'), // 新增這一行
    pubDate: z.string(),
    link: z.string(),
    tags: z.array(z.string()).default([]),
  })
});

export const collections = {
  'articles': articlesCollection,
};
