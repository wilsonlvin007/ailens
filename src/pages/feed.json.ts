import type { APIRoute } from 'astro';
import { getAllDates, getDailyData } from '../lib/data';

export const GET: APIRoute = async ({ site }) => {
  const dates = getAllDates().slice(0, 30);
  const items = dates.map(date => {
    const data = getDailyData(date);
    if (!data) return null;
    return {
      id: `${site}/${date}`,
      url: `${site}/${date}`,
      title: `AI 日报 · ${date}`,
      content_text: data.summary,
      date_published: new Date(date + 'T06:00:00+08:00').toISOString(),
      authors: [{ name: 'AI Lens' }],
      tags: data.items.flatMap(i => i.tags || []),
    };
  }).filter(Boolean);

  const feed = {
    version: 'https://jsonfeed.org/version/1.1',
    title: 'AI Lens · AI 日报',
    description: '透过镜头看 AI 新闻 — 技术 / 应用 / 硬件 / 思想',
    home_page_url: site?.toString() || 'https://ailens.news',
    feed_url: `${site}/feed.json`,
    language: 'zh-CN',
    authors: [{ name: 'AI Lens' }],
    items,
  };

  return new Response(JSON.stringify(feed, null, 2), {
    headers: {
      'Content-Type': 'application/feed+json',
      'Cache-Control': 'public, max-age=600',
    },
  });
};
