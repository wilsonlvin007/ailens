export const CATEGORIES = {
  technology: { label: '技术', icon: '⚡', color: '#6366f1' },
  application: { label: '应用', icon: '🚀', color: '#06b6d4' },
  hardware: { label: '硬件', icon: '🔧', color: '#f59e0b' },
  thought: { label: '思想', icon: '💡', color: '#8b5cf6' },
} as const;

export type Category = keyof typeof CATEGORIES;
