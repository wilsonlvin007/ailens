import fs from 'node:fs';
import path from 'node:path';
import type { DailyData, NewsItem } from '../data/types';

export interface RelatedArticle {
  date: string;
  item: NewsItem;
  score: number;
}

const DATA_DIR = path.join(process.cwd(), 'public', 'data');

function getDates(): string[] {
  if (!fs.existsSync(DATA_DIR)) return [];
  return fs.readdirSync(DATA_DIR)
    .filter(f => f.endsWith('.json') && f !== 'index.json' && f !== 'latest.json' && f !== 'hero-state.json')
    .map(f => f.replace('.json', ''))
    .filter(f => /^\d{4}-\d{2}-\d{2}$/.test(f))
    .sort()
    .reverse();
}

export function getLatestDate(): string | null {
  const dates = getDates();
  return dates[0] || null;
}

export function getDailyData(date: string): DailyData | null {
  const filePath = path.join(DATA_DIR, `${date}.json`);
  if (!fs.existsSync(filePath)) return null;
  const raw = fs.readFileSync(filePath, 'utf-8');
  return JSON.parse(raw) as DailyData;
}

export function getRecentDates(count: number = 7): string[] {
  return getDates().slice(0, count);
}

export function getAllDates(): string[] {
  return getDates();
}

export function getIndexData(): { dates: string[]; latest: string | null } {
  const dates = getAllDates();
  return { dates, latest: dates[0] || null };
}

/** Find related articles from other dates matching current categories */
export function getRelatedArticles(currentDate: string, limit: number = 4): RelatedArticle[] {
  const current = getDailyData(currentDate);
  if (!current) return [];

  // Categories present in today's articles
  const currentCategories = new Set(current.items.map(i => i.category));
  const currentIds = new Set(current.items.map(i => i.id));

  const allDates = getDates();
  const candidates: RelatedArticle[] = [];

  for (const date of allDates) {
    if (date === currentDate) continue;
    const daily = getDailyData(date);
    if (!daily) continue;

    for (const item of daily.items) {
      if (currentIds.has(item.id)) continue; // dedup by id

      let score = 0;
      // Category match: +3 (strong signal)
      if (currentCategories.has(item.category)) score += 3;
      // Recency bonus: +0..2 based on how close the date is
      const daysDiff = Math.abs(
        (new Date(date).getTime() - new Date(currentDate).getTime()) / 86400000
      );
      score += Math.max(0, 2 - daysDiff * 0.05); // decays slowly

      if (score > 0) {
        candidates.push({ date, item, score });
      }
    }
  }

  // Sort by score desc, then date desc
  candidates.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    return b.date.localeCompare(a.date);
  });

  return candidates.slice(0, limit);
}
