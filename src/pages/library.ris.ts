import type { APIRoute } from 'astro';
import { getCollection } from 'astro:content';
import { toRIS } from '../lib/cite';

// 全站合併 RIS:一次匯出所有論文
export const GET: APIRoute = async () => {
  const articles = await getCollection('articles');
  const sorted = articles.sort(
    (a, b) => new Date(b.data.pubDate).valueOf() - new Date(a.data.pubDate).valueOf()
  );
  const ris = sorted.map((a) => toRIS(a.data)).join('\n');
  return new Response(ris, {
    headers: { 'Content-Type': 'application/x-research-info-systems; charset=utf-8' },
  });
};
