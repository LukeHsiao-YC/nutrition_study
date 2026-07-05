import { z, defineCollection } from 'astro:content';

const articlesCollection = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    journal: z.string(),
    category: z.string().default('未分類'),
    pubDate: z.string(),
    link: z.string(),
    doi: z.string().optional().default(''),
    tags: z.array(z.string()).default([]),
  })
});

export const collections = {
  'articles': articlesCollection,
};
