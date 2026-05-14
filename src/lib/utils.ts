import { getCollection } from 'astro:content';
import type { DailyData } from '../data/types';

export async function getDailyData(date: string): Promise<DailyData | null> {
  try {
    const response = await fetch(`/data/${date}.json`);
    if (!response.ok) return null;
    return await response.json();
  } catch {
    return null;
  }
}

export function groupByCategory(items: DailyData['items']): Record<string, DailyData['items']> {
  return items.reduce((acc, item) => {
    const cat = item.category || 'other';
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(item);
    return acc;
  }, {} as Record<string, DailyData['items']>);
}

export function importanceLabel(level: number): string {
  if (level >= 5) return '突破';
  if (level >= 4) return '重大';
  if (level >= 3) return '关注';
  if (level >= 2) return '一般';
  return '次要';
}

export function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  const months = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月'];
  return `${d.getFullYear()}年${months[d.getMonth()]}${d.getDate()}日`;
}

export function formatWeekday(dateStr: string): string {
  const d = new Date(dateStr);
  const days = ['周日','周一','周二','周三','周四','周五','周六'];
  return days[d.getDay()];
}
