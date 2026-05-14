#!/usr/bin/env python3
"""
ailens streaming pipeline
用 streaming 模式调用 Dify API，获取每个节点的输出
"""

import json
import urllib.request
import ssl
import sys
import os
import re
from datetime import datetime
from pathlib import Path

# 配置
DIFY_API_URL = os.environ.get("DIFY_API_URL", "https://api.dify.ai/v1/workflows/run")
DIFY_API_KEY = os.environ.get("DIFY_API_KEY", "app-NP5NYyw7BUrw5O3EFGRGYbw1")

SITE_DIR = Path(__file__).parent.parent
DATA_DIR = SITE_DIR / "public" / "data"


def run_workflow_stream(raw_items: str, date: str) -> dict:
    """用 streaming 模式调用 Dify，收集所有节点的输出"""
    payload = json.dumps({
        "inputs": {
            "date": date,
            "raw_items": raw_items,
        },
        "response_mode": "streaming",
        "user": "ailens-pipeline",
    }).encode("utf-8")

    req = urllib.request.Request(
        DIFY_API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {DIFY_API_KEY}",
            "Content-Type": "application/json",
        },
    )

    node_outputs = {}      # node_id -> full text
    node_titles = {}        # node_id -> title
    node_types = {}         # node_id -> node_type
    workflow_status = None

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting Dify workflow (streaming)...")

    with urllib.request.urlopen(req, timeout=600) as resp:
        buffer = ""
        for chunk in iter(lambda: resp.read(1), b""):
            buffer += chunk.decode("utf-8", errors="replace")

            # Process complete SSE events
            while "\n\n" in buffer:
                event_str, buffer = buffer.split("\n\n", 1)
                for line in event_str.split("\n"):
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if not data_str.strip():
                        continue
                    try:
                        event = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    evt_type = event.get("event", "")
                    evt_data = event.get("data", {})

                    if evt_type == "workflow_started":
                        print(f"  Workflow started: {evt_data.get('workflow_run_id', '')[:12]}")

                    elif evt_type == "node_started":
                        node_id = evt_data.get("node_id", "")
                        title = evt_data.get("title", "")
                        ntype = evt_data.get("node_type", "")
                        node_titles[node_id] = title
                        node_types[node_id] = ntype
                        node_outputs[node_id] = ""
                        print(f"  ▶ {title} ({ntype})...")

                    elif evt_type == "node_finished":
                        node_id = evt_data.get("node_id", "")
                        title = node_titles.get(node_id, "")
                        status = evt_data.get("status", "")
                        elapsed = evt_data.get("elapsed_time", 0)
                        outputs = evt_data.get("outputs", {})
                        print(f"  ✓ {title} ({status}, {elapsed:.1f}s)")
                        # Use the final output from node_finished if available
                        if outputs:
                            for key, val in outputs.items():
                                if isinstance(val, str) and len(val) > len(node_outputs.get(node_id, "")):
                                    node_outputs[node_id] = val

                    elif evt_type == "text_chunk":
                        node_id_list = evt_data.get("from_variable_selector", [])
                        if node_id_list:
                            node_id = node_id_list[0]
                            text = evt_data.get("text", "")
                            if node_id in node_outputs:
                                node_outputs[node_id] += text

                    elif evt_type == "workflow_finished":
                        workflow_status = evt_data.get("status", "")

    print(f"  Workflow finished: {workflow_status}")
    return node_outputs, node_titles, workflow_status


def extract_node_by_title(node_outputs, node_titles, title_keyword):
    """根据节点标题关键字找到对应输出"""
    for node_id, title in node_titles.items():
        if title_keyword in title:
            return node_outputs.get(node_id, "")
    return ""


def generate_site_data(date, items_text, deep_dive_text):
    """从 Dify 输出生成网站数据文件"""
    # 解析 items
    try:
        items_data = json.loads(items_text)
        if isinstance(items_data, dict):
            items = items_data.get("items", [])
        elif isinstance(items_data, list):
            items = items_data
        else:
            items = []
    except json.JSONDecodeError:
        # 尝试提取 JSON 块
        match = re.search(r'\{[\s\S]*\}', items_text)
        if match:
            try:
                items_data = json.loads(match.group())
                items = items_data.get("items", [])
            except:
                items = []
        else:
            items = []

    # 解析 deep_dive
    try:
        deep_dive = json.loads(deep_dive_text) if deep_dive_text else None
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', deep_dive_text) if deep_dive_text else None
        if match:
            try:
                deep_dive = json.loads(match.group())
            except:
                deep_dive = None
        else:
            deep_dive = None

    # 为每条 item 生成 ID
    for i, item in enumerate(items):
        if "id" not in item:
            item["id"] = f"{date}-{i+1:03d}"
        if "collected_at" not in item:
            item["collected_at"] = f"{date}T06:00:00+08:00"

    site_data = {
        "date": date,
        "generated_at": datetime.now().isoformat(),
        "summary": "",
        "items": items,
    }

    if deep_dive:
        site_data["deep_dive"] = deep_dive

    # 生成总摘要
    summaries = [item.get("summary", item.get("summary_cn", "")) for item in items[:3] if item.get("summary") or item.get("summary_cn")]
    if summaries:
        site_data["summary"] = "；".join(summaries)

    # 写入文件
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    date_file = DATA_DIR / f"{date}.json"
    with open(date_file, "w", encoding="utf-8") as f:
        json.dump(site_data, f, ensure_ascii=False, indent=2)
    print(f"  Written: {date_file}")

    latest_file = DATA_DIR / "latest.json"
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(site_data, f, ensure_ascii=False, indent=2)
    print(f"  Written: {latest_file}")

    # 更新 index
    index_file = DATA_DIR / "index.json"
    dates = []
    if index_file.exists():
        try:
            with open(index_file, "r") as f:
                dates = json.load(f).get("dates", [])
        except:
            pass
    if date not in dates:
        dates.insert(0, date)
    dates = sorted(set(dates), reverse=True)
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump({"dates": dates, "latest": dates[0] if dates else None}, f, ensure_ascii=False, indent=2)
    print(f"  Written: {index_file}")

    return site_data


def main():
    sys.path.insert(0, str(Path(__file__).parent))
    from collect import main as collect_main

    date = datetime.now().strftime("%Y-%m-%d")
    print(f"=== ailens pipeline ===")
    print(f"Date: {date}")

    # Step 1: Collect
    print("\n[1/3] Collecting...")
    raw = collect_main()
    items = json.loads(raw)[:10]  # 限制10条避免超时
    raw_items = json.dumps(items, ensure_ascii=False)
    print(f"  Collected {len(items)} items")

    if len(items) == 0:
        print("No items, aborting.")
        return

    # Step 2: Call Dify
    print(f"\n[2/3] Processing with Dify...")
    node_outputs, node_titles, status = run_workflow_stream(raw_items, date)

    if status != "succeeded":
        print(f"ERROR: Workflow status = {status}")
        # 保存调试信息
        debug_file = Path("/tmp/ailens_debug.json")
        with open(debug_file, "w") as f:
            json.dump({"status": status, "outputs": node_outputs, "titles": node_titles}, f, ensure_ascii=False, indent=2)
        print(f"Debug info saved to {debug_file}")
        return

    # Step 3: Generate site data
    print(f"\n[3/3] Generating site data...")
    items_text = extract_node_by_title(node_outputs, node_titles, "重构")
    deep_dive_text = extract_node_by_title(node_outputs, node_titles, "快评")
    summary_text = extract_node_by_title(node_outputs, node_titles, "分类")

    site_data = generate_site_data(date, items_text, deep_dive_text)

    print(f"\n=== Done ===")
    print(f"Items: {len(site_data.get('items', []))}")
    print(f"Deep dive: {bool(site_data.get('deep_dive'))}")
    print(f"Data dir: {DATA_DIR}")


if __name__ == "__main__":
    main()
