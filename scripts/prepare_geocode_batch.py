"""Prepare a batch of vendor entries missing geocoded city coordinates.

Usage:
    python scripts/prepare_geocode_batch.py --limit 200 --out scripts/geocode_batch_2.json

This script loads the in-memory vendor cache from `apps.recommendations.services.cache`,
loads the existing city geo cache from `apps.recommendations.services.geolocation`,
and writes up to `--limit` vendors whose city is not yet geocoded into the output JSON.
"""
import argparse
import json
import sys
from pathlib import Path

# allow importing app modules when script run from repo root
sys.path.insert(0, str(Path(__file__).parent))
# insert repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.recommendations.services import cache, geolocation


def prepare_batch(limit: int = 200, out_path: str = "scripts/geocode_batch_2.json"):
    # ensure caches are loaded from DB or file
    try:
        cache.reload_data()
    except Exception:
        # best-effort
        pass

    geo_cache = geolocation._load_cache()

    vendors = list(cache.vendors_cache.values())
    batch = []
    seen_cities = set()

    for v in vendors:
        if len(batch) >= limit:
            break
        city = (v.get("city") or "").strip()
        if not city:
            continue
        key = city.lower()
        # skip if already geocoded in cache or vendor already has _geo
        if key in geo_cache:
            continue
        if v.get("_geo"):
            continue
        # avoid adding multiple vendors for same city in the batch initially
        if key in seen_cities:
            # still add vendors for same city if desired, but we prefer diversity
            continue
        seen_cities.add(key)
        batch.append({
            "id": v.get("id"),
            "businessName": v.get("businessName"),
            "city": city,
            "vendor_type_name": v.get("vendor_type_name"),
            "type": v.get("type", "vendor")
        })

    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Prepared batch of {len(batch)} vendors to geocode -> {out_file}")


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--limit', type=int, default=200)
    p.add_argument('--out', type=str, default='scripts/geocode_batch_2.json')
    args = p.parse_args()
    prepare_batch(limit=args.limit, out_path=args.out)
