import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';
import { getAllDates, getDailyData } from '../lib/data';

export async function GET(context: any) {
  const dates = getAllDates().slice(0, 30);
  const items = dates.map(date => {
    const data = getDailyData(date);
    if (!data) return null;
    return {
      title: `AI 日报 · ${date}`,
      pubDate: new Date(date + 'T06:00:00+08:00'),
      description: data.summary,
      link: `/${date}`,
      categories: data.items.map(i => i.category),
    };
  }).filter(Boolean);

  return rss({
    title: 'AI Lens · AI 日报',
    description: '透过镜头看 AI 新闻 — 技术 / 应用 / 硬件 / 思想',
    site: context.site,
    items: items,
    customData: '<language>zh-CN</language>',
  });
}
