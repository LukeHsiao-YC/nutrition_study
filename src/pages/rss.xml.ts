import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';
import type { APIContext } from 'astro';

// RSS 訂閱:用任何 RSS 閱讀器追蹤新文獻(呼應「期刊 RSS 追蹤」工作流)
export async function GET(context: APIContext) {
  const articles = await getCollection('articles');
  const base = import.meta.env.BASE_URL;
  const items = articles
    .map((a) => {
      const t = new Date(a.data.pubDate);
      return { a, date: isNaN(t.valueOf()) ? new Date() : t };
    })
    .sort((x, y) => y.date.valueOf() - x.date.valueOf())
    .slice(0, 60)
    .map(({ a, date }) => ({
      title: a.data.title,
      pubDate: date,
      description: `${a.data.journal} · ${a.data.category}${
        a.data.depth && a.data.depth !== 'triage' ? ' · 深讀' : ''
      }`,
      categories: a.data.tags || [],
      link: `${base}paper/${a.slug}`,
    }));

  return rss({
    title: '營養與兒童醫學文獻追蹤',
    description: '從各期刊定期抓取並整理的最新文獻',
    site: context.site ?? 'https://lukehsiao-yc.github.io',
    items,
  });
}
