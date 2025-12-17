"""Run raw geocoding for a prepared batch using GeoNames.

Usage:
    python scripts/run_geocode_batch.py --in scripts/geocode_batch_2.json --out results/geocode_batch_2_results.json

This script will:
 - load the prepared batch JSON
 - for each vendor, attempt to geocode the `city` string via GeoNames
 - update the geolocation cache (`apps/recommendations/services/geo_cache.json`)
 - write a results file listing vendor id, original city string and geocode result

Requirements:
 - `GEONAMES_USERNAME` environment variable must be set (register at geonames.org)
 - network access to api.geonames.org

Note: This performs live API calls and respects the pause configured in the geolocation module.
"""
import argparse
import json
import sys
from pathlib import Path

# allow importing app modules when script run from repo root
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.recommendations.services import geolocation
import os


def run(in_path: str, out_path: str):
    in_file = Path(in_path)
    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    if not in_file.exists():
        print(f"Input batch file not found: {in_file}")
        return 2

    username = os.getenv('GEONAMES_USERNAME')
    if not username:
        print("GEONAMES_USERNAME is not set in environment. Set it and retry.")
        return 3

    # load batch
    batch = json.loads(in_file.read_text(encoding='utf-8'))
    cache = geolocation._load_cache()

    results = []
    for i, item in enumerate(batch, start=1):
        vid = item.get('id')
        city = (item.get('city') or '').strip()
        key = city.lower()
        # If already in cache, use it
        if key in cache:
            loc = cache[key]
            results.append({'id': vid, 'businessName': item.get('businessName'), 'city': city, 'lat': loc.get('lat'), 'lon': loc.get('lon'), 'status': 'cached'})
            continue

        # Attempt raw geocode using GeoNames
        try:
            loc = geolocation._geonames_geocode(city)
        except Exception as e:
            loc = None
        if loc:
            cache[key] = loc
            # persist cache after each successful hit to avoid redoing
            try:
                geolocation._save_cache(cache)
            except Exception:
                pass
            results.append({'id': vid, 'businessName': item.get('businessName'), 'city': city, 'lat': loc.get('lat'), 'lon': loc.get('lon'), 'status': 'ok'})
        else:
            results.append({'id': vid, 'businessName': item.get('businessName'), 'city': city, 'lat': None, 'lon': None, 'status': 'not_found'})

    # write results
    out_file.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Wrote {len(results)} results to {out_file}")
    return 0


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--in', dest='in_path', required=True)
    p.add_argument('--out', dest='out_path', required=True)
    args = p.parse_args()
    rc = run(args.in_path, args.out_path)
    sys.exit(rc)
