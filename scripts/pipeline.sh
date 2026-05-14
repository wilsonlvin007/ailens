#!/bin/bash
# ailens pipeline via curl (avoids Python SSL issues)
# Usage: bash scripts/pipeline.sh

set -e

DATE=$(date +%Y-%m-%d)
echo "=== ailens pipeline ==="
echo "Date: $DATE"

SITE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATA_DIR="$SITE_DIR/public/data"
DIFY_API_KEY="${DIFY_API_KEY:-app-NP5NYyw7BUrw5O3EFGRGYbw1}"
DIFY_API_URL="${DIFY_API_URL:-https://api.dify.ai/v1/workflows/run}"
TMPDIR="${TMPDIR:-/tmp}"
RAW_FILE="$TMPDIR/ailens_raw.json"
RESULT_FILE="$TMPDIR/ailens_stream_result.txt"

# Step 1: Collect
echo ""
echo "[1/3] Collecting..."
python3 -c "
import json, sys
sys.path.insert(0, '$SITE_DIR/scripts')
from collect import main
raw = main()
items = json.loads(raw)[:10]
with open('$RAW_FILE', 'w') as f:
    json.dump({'date': '$DATE', 'raw_items': json.dumps(items, ensure_ascii=False)}, f)
print(f'  Collected {len(items)} items')
"

if [ ! -s "$RAW_FILE" ]; then
    echo "ERROR: No items collected"
    exit 1
fi

# Step 2: Call Dify (streaming)
echo ""
echo "[2/3] Processing with Dify (streaming)..."
curl -s -m 600 -N -X POST "$DIFY_API_URL" \
    -H "Authorization: Bearer $DIFY_API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"inputs\": $(cat "$RAW_FILE"), \"response_mode\": \"streaming\", \"user\": \"ailens-pipeline\"}" \
    > "$RESULT_FILE" 2>&1

echo "  Stream received, $(wc -c < "$RESULT_FILE") bytes"

# Step 3: Parse and generate site data
echo ""
echo "[3/3] Generating site data..."
python3 -c "
import json, re
from pathlib import Path
from datetime import datetime

RESULT_FILE = '$RESULT_FILE'
DATA_DIR = Path('$DATA_DIR')
DATE = '$DATE'

# Parse SSE stream
node_outputs = {}
node_titles = {}
with open(RESULT_FILE, 'r') as f:
    buffer = f.read()

for line in buffer.split('\n'):
    if not line.startswith('data: '):
        continue
    try:
        event = json.loads(line[6:])
    except:
        continue

    evt_type = event.get('event', '')
    data = event.get('data', {})

    if evt_type == 'node_finished':
        node_id = data.get('node_id', '')
        title = data.get('title', '')
        status = data.get('status', '')
        outputs = data.get('outputs', {})
        print(f'  {title}: {status}')
        node_titles[node_id] = title
        if outputs:
            # Save the largest output
            best = max(outputs.values(), key=len) if outputs else ''
            if len(best) > len(node_outputs.get(node_id, '')):
                node_outputs[node_id] = best
    elif evt_type == 'text_chunk':
        selectors = data.get('from_variable_selector', [])
        if selectors:
            nid = selectors[0]
            node_outputs[nid] = node_outputs.get(nid, '') + data.get('text', '')

# Find outputs by title
def find_output(keyword):
    for nid, title in node_titles.items():
        if keyword in title:
            return node_outputs.get(nid, '')
    return ''

items_text = find_output('重构')
deep_dive_text = find_output('快评')

# Parse items
try:
    items_data = json.loads(items_text)
    items = items_data.get('items', []) if isinstance(items_data, dict) else items_data if isinstance(items_data, list) else []
except:
    items = []

for i, item in enumerate(items):
    if 'id' not in item:
        item['id'] = f'{DATE}-{i+1:03d}'
    if 'collected_at' not in item:
        item['collected_at'] = f'{DATE}T06:00:00+08:00'

# Parse deep dive
deep_dive = None
if deep_dive_text:
    try:
        deep_dive = json.loads(deep_dive_text)
    except:
        m = re.search(r'\{[\s\S]*\}', deep_dive_text)
        if m:
            try: deep_dive = json.loads(m.group())
            except: pass

site_data = {
    'date': DATE,
    'generated_at': datetime.now().isoformat(),
    'summary': '',
    'items': items,
}
if deep_dive:
    site_data['deep_dive'] = deep_dive

summaries = [it.get('summary','') or it.get('summary_cn','') for it in items[:3] if it.get('summary') or it.get('summary_cn')]
if summaries:
    site_data['summary'] = '；'.join(summaries)

DATA_DIR.mkdir(parents=True, exist_ok=True)

# Write date file
with open(DATA_DIR / f'{DATE}.json', 'w') as f:
    json.dump(site_data, f, ensure_ascii=False, indent=2)
print(f'  Written: {DATA_DIR}/{DATE}.json')

# Write latest
with open(DATA_DIR / 'latest.json', 'w') as f:
    json.dump(site_data, f, ensure_ascii=False, indent=2)
print(f'  Written: {DATA_DIR}/latest.json')

# Update index
index_file = DATA_DIR / 'index.json'
dates = []
if index_file.exists():
    try:
        dates = json.loads(open(index_file).read()).get('dates', [])
    except: pass
if DATE not in dates:
    dates.insert(0, DATE)
dates = sorted(set(dates), reverse=True)
with open(index_file, 'w') as f:
    json.dump({'dates': dates, 'latest': dates[0] if dates else None}, f, ensure_ascii=False, indent=2)
print(f'  Written: {DATA_DIR}/index.json')

print(f'\nItems: {len(items)}')
print(f'Deep dive: {bool(deep_dive)}')
print('=== Done ===')
"

echo ""
echo "Files are ready in $DATA_DIR"
echo "Run 'npm run build' in $SITE_DIR to rebuild the site"
