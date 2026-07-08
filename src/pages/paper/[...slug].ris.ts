import type { APIRoute } from 'astro';
import { getCollection } from 'astro:content';
import { toRIS } from '../../lib/cite';

export async function getStaticPaths() {
  const articles = await getCollection('articles');
  return articles.map((a) => ({ params: { slug: a.slug }, props: { data: a.data } }));
}

export const GET: APIRoute = ({ props }) =>
  new Response(toRIS(props.data), {
    headers: { 'Content-Type': 'application/x-research-info-systems; charset=utf-8' },
  });
