"""Merge multiple geocode results JSON files into one combined results file.

Usage:
    python scripts/merge_results.py --out results/geocode_batch_2_combined.json results/geocode_batch_2_results.json results/geocode_batch_2_retry_results.json
"""
import argparse
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--out', required=True)
p.add_argument('inputs', nargs='+')
args = p.parse_args()

combined = []
seen = set()
for inp in args.inputs:
    pth = Path(inp)
    if not pth.exists():
        continue
    data = json.loads(pth.read_text(encoding='utf-8'))
    for item in data:
        # keep first occurrence of an id
        iid = item.get('id')
        if iid in seen:
            continue
        seen.add(iid)
        combined.append(item)

outp = Path(args.out)
outp.parent.mkdir(parents=True, exist_ok=True)
outp.write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Wrote {len(combined)} combined results -> {outp}')
