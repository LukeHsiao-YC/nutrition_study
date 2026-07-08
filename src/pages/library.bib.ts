import type { APIRoute } from 'astro';
import { getCollection } from 'astro:content';
import { toBibTeX } from '../lib/cite';

// 全站合併 BibTeX:一次匯出所有論文,直接匯入 Zotero / LaTeX
export const GET: APIRoute = async () => {
  const articles = await getCollection('articles');
  const sorted = articles.sort(
    (a, b) => new Date(b.data.pubDate).valueOf() - new Date(a.data.pubDate).valueOf()
  );
  const bib = sorted.map((a) => toBibTeX(a.data)).join('\n');
  return new Response(bib, {
    headers: { 'Content-Type': 'application/x-bibtex; charset=utf-8' },
  });
};
