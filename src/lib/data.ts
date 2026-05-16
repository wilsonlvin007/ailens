import fs from 'node:fs';
import path from 'node:path';
import type { DailyData } from '../data/types';

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
