#!/usr/bin/env python3
"""
ailens 新闻采集脚本
从 Hacker News、Reddit、Google AI Blog RSS 等源采集 AI 相关新闻
"""

import json
import urllib.request
import re
import xml.etree.ElementTree as ET
from datetime import datetime


def fetch_json(url, headers=None, timeout=10):
    """通用 JSON 请求"""
    if headers is None:
        headers = {"User-Agent": "ailens-bot/1.0"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def fetch_text(url, headers=None, timeout=10):
    """通用文本请求"""
    if headers is None:
        headers = {"User-Agent": "ailens-bot/1.0"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def collect_hacker_news(limit=30):
    """采集 Hacker News Top Stories"""
    items = []
    try:
        top_ids = fetch_json(
            "https://hacker-news.firebaseio.com/v0/topstories.json"
        )[:limit]

        ai_keywords = [
            "ai", "artificial intelligence", "machine learning", "deep learning",
            "llm", "gpt", "claude", "gemini", "llama", "openai", "anthropic",
            "neural", "transformer", "diffusion", "language model", "chatbot",
            "robot", "autonomous", "nlp", "computer vision", "reinforcement",
            "generative", "alignment", "safety", "mlops", "fine-tune", "rag",
        ]

        for sid in top_ids:
            try:
                story = fetch_json(
                    f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                    timeout=5
                )
                if story.get("type") != "story" or not story.get("url"):
                    continue
                title = story.get("title", "")
                # 简单 AI 相关过滤
                title_lower = title.lower()
                if any(kw in title_lower for kw in ai_keywords):
                    items.append({
                        "title": title,
                        "url": story.get("url", ""),
                        "source_name": "Hacker News",
                        "snippet": title,
                    })
            except:
                continue
    except Exception as e:
        print(f"[HN] Error: {e}")

    return items


def collect_reddit(subreddit, limit=15):
    """采集 Reddit 子版块"""
    items = []
    try:
        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
        data = fetch_json(url)
        for child in data["data"]["children"]:
            post = child["data"]
            text = post.get("selftext", "") or post.get("title", "")
            items.append({
                "title": post.get("title", ""),
                "url": f"https://reddit.com{post.get('permalink', '')}",
                "source_name": f"Reddit r/{subreddit}",
                "snippet": text[:300],
            })
    except Exception as e:
        print(f"[Reddit r/{subreddit}] Error: {e}")
    return items


def collect_rss(feed_url, source_name, limit=10):
    """采集 RSS Feed"""
    items = []
    try:
        xml_text = fetch_text(feed_url)
        root = ET.fromstring(xml_text)

        # Atom or RSS
        if "atom" in feed_url or root.tag.endswith("feed"):
            entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")[:limit]
            for entry in entries:
                title_el = entry.find("{http://www.w3.org/2005/Atom}title")
                link_el = entry.find("{http://www.w3.org/2005/Atom}link")
                items.append({
                    "title": title_el.text if title_el is not None else "",
                    "url": link_el.get("href", "") if link_el is not None else "",
                    "source_name": source_name,
                    "snippet": title_el.text if title_el is not None else "",
                })
        else:
            entries = root.findall(".//item")[:limit]
            for entry in entries:
                title_el = entry.find("title")
                link_el = entry.find("link")
                items.append({
                    "title": title_el.text if title_el is not None else "",
                    "url": link_el.text if link_el is not None else "",
                    "source_name": source_name,
                    "snippet": title_el.text if title_el is not None else "",
                })
    except Exception as e:
        print(f"[RSS {source_name}] Error: {e}")
    return items


def collect_techcrunch_ai(limit=10):
    """采集 TechCrunch AI 标签页"""
    items = []
    try:
        data = fetch_json(
            "https://techcrunch.com/wp-json/wp/v2/posts?tags=587429&per_page="
            + str(limit)
        )
        for post in data:
            items.append({
                "title": post.get("title", {}).get("rendered", ""),
                "url": post.get("link", ""),
                "source_name": "TechCrunch AI",
                "snippet": re.sub("<[^>]+>", "", post.get("excerpt", {}).get("rendered", ""))[:300],
            })
    except Exception as e:
        print(f"[TechCrunch] Error: {e}")
    return items


def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting collection...")

    all_items = []

    # Hacker News
    print("  Collecting Hacker News...")
    all_items.extend(collect_hacker_news(limit=30))

    # Reddit
    for subreddit in ["artificial", "MachineLearning", "LocalLLaMA"]:
        print(f"  Collecting Reddit r/{subreddit}...")
        all_items.extend(collect_reddit(subreddit, limit=10))

    # RSS Feeds
    feeds = [
        ("https://news.smol.ai/rss.xml", "AINews (smol.ai)"),
        ("https://blog.google/technology/ai/rss/", "Google AI Blog"),
        ("https://openai.com/blog/rss.xml", "OpenAI Blog"),
        ("https://www.anthropic.com/news/rss", "Anthropic News"),
        ("https://mistral.ai/news/rss/", "Mistral AI"),
    ]
    for feed_url, source_name in feeds:
        print(f"  Collecting {source_name}...")
        all_items.extend(collect_rss(feed_url, source_name, limit=5))

    # TechCrunch
    print("  Collecting TechCrunch AI...")
    all_items.extend(collect_techcrunch_ai(limit=5))

    # 去重（按标题相似度）
    seen = set()
    unique_items = []
    for item in all_items:
        title_key = item["title"].lower().strip()[:80]
        if title_key not in seen:
            seen.add(title_key)
            unique_items.append(item)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Collected {len(unique_items)} unique items")

    return json.dumps(unique_items, ensure_ascii=False)


if __name__ == "__main__":
    result = main()
    print(json.dumps({"raw_items": result, "count": len(json.loads(result))}, ensure_ascii=False))
