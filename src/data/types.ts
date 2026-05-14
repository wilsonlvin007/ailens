export interface NewsItem {
  id: string;
  title: string;
  category: string;
  importance: number;
  source: string;
  source_name: string;
  summary: string;
  analysis: string;
  tags: string[];
  collected_at: string;
}

export interface DailyData {
  date: string;
  generated_at: string;
  summary: string;
  items: NewsItem[];
  deep_dive?: {
    topic: string;
    content: string;
  };
}

export interface Subscriber {
  webhook_url: string;
  filter?: {
    categories?: string[];
    min_importance?: number;
  };
  format?: 'json';
  subscribed_at: string;
  subscriber_id: string;
}

export interface SubscribersData {
  subscribers: Subscriber[];
}
