"""Clean noisy city strings from previous geocode results and retry geocoding.

Usage:
    python scripts/clean_and_retry_geocode.py --results results/geocode_batch_2_results.json \
        --out_batch scripts/geocode_batch_2_retry.json \
        --out_results results/geocode_batch_2_retry_results.json

This script:
 - Loads previous results file and extracts entries with status 'not_found'
 - Applies conservative cleaning heuristics to `city` strings
 - Writes a cleaned batch file suitable for geocoding
 - Calls `scripts/run_geocode_batch.py` to attempt geocoding the cleaned cities

Cleaning heuristics (conservative):
 - Remove text inside parentheses
 - If a period appears (".") assume trailing descriptive sentence; keep text before the first period
 - If there is a comma, prefer the last token after the last comma (commonly city)
 - Strip common distance tokens like "0.22 km" or ".22 km)"
 - Trim and collapse whitespace

"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def clean_city(raw: str) -> str:
    if not raw:
        return ''
    s = raw.strip()

    # remove content in parentheses
    s = re.sub(r"\([^)]*\)", "", s)
    # remove km/distance tokens
    s = re.sub(r"\d+(?:\.\d+)?\s*(?:km|mi)\b", "", s, flags=re.IGNORECASE)
    # if there's a dot followed by a space, keep only before first dot (to chop long descriptions)
    if '.' in s:
        parts = s.split('.')
        if len(parts[0]) >= 2:
            s = parts[0]
    # if comma exists, prefer last token (often city or region)
    if ',' in s:
        parts = [p.strip() for p in s.split(',') if p.strip()]
        if parts:
            s = parts[-1]
    # common prefixes like "in " or short descriptors remove
    s = re.sub(r'^(in\s+|at\s+|near\s+)', '', s, flags=re.IGNORECASE)
    # remove trailing punctuation
    s = s.strip(" .,-_")
    # collapse whitespace
    s = re.sub(r"\s+", " ", s)
    return s


def build_clean_batch(results_path: Path, out_batch: Path, limit: int = 200):
    data = json.loads(results_path.read_text(encoding='utf-8'))
    batch = []
    seen = set()
    for item in data:
        if item.get('status') != 'not_found':
            continue
        if len(batch) >= limit:
            break
        cid = item.get('id')
        raw_city = item.get('city') or ''
        cleaned = clean_city(raw_city)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        batch.append({
            'id': cid,
            'businessName': item.get('businessName'),
            'city': cleaned,
            'original_city': raw_city,
            'type': item.get('type', 'vendor')
        })
    out_batch.parent.mkdir(parents=True, exist_ok=True)
    out_batch.write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding='utf-8')
    return batch


def retry_geocode(batch_path: Path, results_out: Path):
    # call existing run_geocode_batch.py
    cmd = [sys.executable, 'scripts/run_geocode_batch.py', '--in', str(batch_path), '--out', str(results_out)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    print(proc.stdout)
    if proc.returncode != 0:
        print('Geocode run failed:', proc.stderr)
    return proc.returncode


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--results', required=True)
    p.add_argument('--out_batch', required=True)
    p.add_argument('--out_results', required=True)
    p.add_argument('--limit', type=int, default=200)
    args = p.parse_args()

    results_path = Path(args.results)
    out_batch = Path(args.out_batch)
    out_results = Path(args.out_results)

    if not results_path.exists():
        print('Results file not found:', results_path)
        sys.exit(2)

    batch = build_clean_batch(results_path, out_batch, limit=args.limit)
    print(f'Prepared cleaned batch of {len(batch)} entries -> {out_batch}')

    rc = retry_geocode(out_batch, out_results)
    sys.exit(rc)
