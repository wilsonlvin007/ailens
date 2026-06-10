#!/usr/bin/env python3
"""
ailens 新闻采集脚本 v2
数据源架构：
  - 主干聚合：AINews (smol.ai) — 覆盖 12 个 AI subreddits + 544 Twitter 账号 + AI Discords
  - 官方一手：OpenAI Blog, Google AI Blog, Anthropic News
  - AI 生产力应用：Product Hunt AI, Hacker News Show HN, GitHub Trending AI
  - 技术实践：Towards Data Science
"""

import json
import urllib.request
import re
import xml.etree.ElementTree as ET
from datetime import datetime


def fetch_json(url, headers=None, timeout=15):
    """通用 JSON 请求"""
    if headers is None:
        headers = {"User-Agent": "ailens-bot/2.0"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def fetch_text(url, headers=None, timeout=15):
    """通用文本请求"""
    if headers is None:
        headers = {"User-Agent": "ailens-bot/2.0"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def collect_rss(feed_url, source_name, limit=5):
    """采集 RSS Feed（兼容 RSS 2.0 和 Atom）"""
    items = []
    try:
        xml_text = fetch_text(feed_url)
        root = ET.fromstring(xml_text)

        ns_atom = "http://www.w3.org/2005/Atom"
        is_atom = root.tag.endswith("feed") or bool(root.findall(f"{{{ns_atom}}}entry"))

        if is_atom:
            entries = root.findall(f"{{{ns_atom}}}entry")[:limit]
            for entry in entries:
                title_el = entry.find(f"{{{ns_atom}}}title")
                link_el = entry.find(f"{{{ns_atom}}}link")
                summary_el = entry.find(f"{{{ns_atom}}}summary")
                title = title_el.text if title_el is not None else ""
                url = link_el.get("href", "") if link_el is not None else ""
                snippet = ""
                if summary_el is not None and summary_el.text:
                    snippet = re.sub(r"<[^>]+>", "", summary_el.text)[:300]
                elif title:
                    snippet = title
                items.append({
                    "title": title,
                    "url": url,
                    "source_name": source_name,
                    "snippet": snippet,
                })
        else:
            # RSS 2.0
            rss_items = root.findall(".//item")[:limit]
            for entry in rss_items:
                title_el = entry.find("title")
                link_el = entry.find("link")
                desc_el = entry.find("description")
                title = title_el.text if title_el is not None else ""
                url = link_el.text if link_el is not None else ""
                snippet = ""
                if desc_el is not None and desc_el.text:
                    snippet = re.sub(r"<[^>]+>", "", desc_el.text)[:300]
                elif title:
                    snippet = title
                items.append({
                    "title": title,
                    "url": url,
                    "source_name": source_name,
                    "snippet": snippet,
                })
    except Exception as e:
        print(f"[RSS {source_name}] Error: {e}")
    return items


def collect_smol_ai(limit=5):
    """采集 AINews (smol.ai) — 主干聚合源"""
    return collect_rss("https://news.smol.ai/rss.xml", "AINews (smol.ai)", limit=limit)


def collect_hn_show(limit=10):
    """采集 Hacker News Show HN（AI 产品发布）"""
    items = []
    try:
        show_ids = fetch_json(
            "https://hacker-news.firebaseio.com/v0/showstories.json"
        )

        ai_keywords = [
            "ai", "artificial intelligence", "machine learning", "deep learning",
            "llm", "gpt", "claude", "gemini", "llama", "openai", "anthropic",
            "neural", "transformer", "diffusion", "language model", "chatbot",
            "robot", "autonomous", "nlp", "computer vision", "reinforcement",
            "generative", "alignment", "safety", "fine-tune", "rag",
            "agent", "coding", "copilot", "codex", "cursor", "windsurf",
            "productivity", "workflow", "automation", "tool",
        ]

        count = 0
        for sid in show_ids:
            if count >= limit:
                break
            try:
                story = fetch_json(
                    f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                    timeout=5
                )
                if story.get("type") != "story" or not story.get("url"):
                    continue
                title = story.get("title", "")
                title_lower = title.lower()
                if any(kw in title_lower for kw in ai_keywords):
                    items.append({
                        "title": title,
                        "url": story.get("url", ""),
                        "source_name": "HN Show HN",
                        "snippet": title,
                    })
                    count += 1
            except Exception:
                continue
    except Exception as e:
        print(f"[HN Show] Error: {e}")

    return items


def collect_github_ai(limit=5):
    """采集 GitHub Trending AI 开源项目"""
    items = []
    try:
        from datetime import timedelta
        week_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
        url = (
            "https://api.github.com/search/repositories"
            f"?q=topic:artificial-intelligence+created:>{week_ago}"
            "&sort=stars&order=desc&per_page=" + str(limit)
        )
        headers = {
            "User-Agent": "ailens-bot/2.0",
            "Accept": "application/vnd.github.v3+json",
        }
        data = fetch_json(url, headers=headers)

        for repo in data.get("items", [])[:limit]:
            desc = repo.get("description") or ""
            items.append({
                "title": f"{repo.get('full_name', '')} — {desc}"[:200],
                "url": repo.get("html_url", ""),
                "source_name": "GitHub Trending AI",
                "snippet": (
                    f"⭐ {repo.get('stargazers_count', 0)} | "
                    f"{repo.get('language', 'N/A')} | "
                    f"{desc[:150]}"
                ),
            })
    except Exception as e:
        print(f"[GitHub AI] Error: {e}")

    return items


def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting collection v2...")

    all_items = []

    # === 主干聚合 ===
    print("  Collecting AINews (smol.ai) — 主干源...")
    all_items.extend(collect_smol_ai(limit=5))

    # === 官方一手 ===
    official_feeds = [
        ("https://openai.com/news/rss.xml", "OpenAI Blog"),
        ("https://blog.google/technology/ai/rss/", "Google AI Blog"),
        ("https://hnrss.org/frontpage?q=claude+OR+gpt+OR+llm+OR+openai+OR+gemini+OR+anthropic", "HN AI"),
        ("https://feeds.feedburner.com/TheHackersNews", "Hacker News"),
        ("https://www.artificialintelligence-news.com/feed/", "AI News"),
        ("https://syncedreview.com/feed/", "Synced Review"),
        ("https://www.marktechpost.com/feed/", "MarkTechPost"),
    ]
    for feed_url, source_name in official_feeds:
        print(f"  Collecting {source_name}...")
        all_items.extend(collect_rss(feed_url, source_name, limit=3))


    # === Anthropic News (via HN API — no reliable RSS) ===
    print("  Collecting Anthropic News (HN search)...")
    try:
        hn_url = "https://hn.algolia.com/api/v1/search?query=anthropic+OR+claude&tags=story&hitsPerPage=5&numericFilters=points>5"
        hn_data = fetch_json(hn_url, timeout=10)
        for hit in hn_data.get("hits", [])[:5]:
            title = hit.get("title", "")
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
            if len(title) > 5 and "anthropic" in title.lower() or "claude" in title.lower():
                all_items.append({
                    "title": title,
                    "url": url,
                    "source_name": "Anthropic (via HN)",
                    "snippet": title,
                })
        print(f"    Got {len([i for i in all_items if 'Anthropic (via HN)' in i.get('source_name','')])} items from Anthropic")
    except Exception as e:
        print(f"    Anthropic HN error: {e}")

    # === AI 硬件 ===
    hardware_feeds = [
        ("https://hnrss.org/frontpage?q=nvidia+OR+gpu+OR+chip+OR+semiconductor+OR+hardware+OR+tpu", "HN Hardware"),
        ("https://blogs.nvidia.com/feed/", "NVIDIA Blog"),
        ("https://semiengineering.com/feed/", "Semiconductor Engineering"),
    ]
    for feed_url, source_name in hardware_feeds:
        print(f"  Collecting {source_name}...")
        all_items.extend(collect_rss(feed_url, source_name, limit=3))

    # === AI 生产力应用 ===

    print("  Collecting Product Hunt AI...")
    all_items.extend(collect_rss(
        "https://www.producthunt.com/feed?topic=ai",
        "Product Hunt AI",
        limit=5
    ))

    print("  Collecting HN Show HN (AI products)...")
    all_items.extend(collect_hn_show(limit=10))

    print("  Collecting GitHub Trending AI...")
    all_items.extend(collect_github_ai(limit=5))

    # === 技术实践 ===
    print("  Collecting Towards Data Science...")
    all_items.extend(collect_rss(
        "https://towardsdatascience.com/feed",
        "Towards Data Science",
        limit=3
    ))

    # === 去重（按标题相似度） ===
    seen = set()
    unique_items = []
    for item in all_items:
        title_key = item["title"].lower().strip()[:80]
        if title_key not in seen:
            seen.add(title_key)
            unique_items.append(item)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Collected {len(unique_items)} unique items "
          f"(from {len(all_items)} raw)")

    return json.dumps(unique_items, ensure_ascii=False)


if __name__ == "__main__":
    result = main()
    print(json.dumps(
        {"raw_items": result, "count": len(json.loads(result))},
        ensure_ascii=False
    ))
