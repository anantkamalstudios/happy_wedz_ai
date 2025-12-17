"""Apply geocode results to vendors cache file.

Usage:
    python scripts/apply_geocode_results.py --results results/geocode_batch_2_retry_results.json

This loads `apps/recommendations/services/vendors_cache.json`, updates any vendor entries whose id appears in the results with lat/lon, writing `_geo` field, and writes the cache file back.
"""
import argparse
import json
import sys
from pathlib import Path

VENDORS_CACHE_FILE = Path('apps') / 'recommendations' / 'services' / 'vendors_cache.json'


def apply_results(results_path: Path):
    if not results_path.exists():
        print('Results file not found:', results_path)
        return 2
    if not VENDORS_CACHE_FILE.exists():
        print('Vendors cache file not found:', VENDORS_CACHE_FILE)
        return 3

    results = json.loads(results_path.read_text(encoding='utf-8'))
    # build map of id -> (lat, lon)
    coords = {}
    for r in results:
        if r.get('status') in ('ok', 'cached') and r.get('lat') is not None and r.get('lon') is not None:
            coords[int(r['id'])] = {'lat': r['lat'], 'lon': r['lon']}

    if not coords:
        print('No coordinates to apply')
        return 0

    vendors = json.loads(VENDORS_CACHE_FILE.read_text(encoding='utf-8') or '[]')
    updated = 0
    for v in vendors:
        vid = v.get('id')
        if vid is None:
            continue
        if int(vid) in coords:
            v['_geo'] = coords[int(vid)]
            updated += 1

    VENDORS_CACHE_FILE.write_text(json.dumps(vendors, ensure_ascii=False), encoding='utf-8')
    print(f'Updated {updated} vendor entries in {VENDORS_CACHE_FILE}')
    return 0


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--results', required=True)
    args = p.parse_args()
    rc = apply_results(Path(args.results))
    sys.exit(rc)
