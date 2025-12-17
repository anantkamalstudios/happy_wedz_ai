"""
One-off script to pre-geocode vendor cities and persist vendor entries with `_geo` field.

Usage (run from repo root):

    python scripts/pre_geocode_vendors.py --batch 500

Notes:
- Uses `apps.recommendations.services.geolocation` which defaults to Nominatim.
- The geolocation cache will be written to `apps/recommendations/services/geo_cache.json`.
- The updated vendors cache will be written to `apps/recommendations/services/vendors_cache.json`.
- Respect API rate limits. This script will respect the provider pause set in the geolocation module.
"""
import argparse
import json
from pathlib import Path

from apps.recommendations.services import cache, geolocation

VENDORS_CACHE_FILE = Path(__file__).parent.parent / "apps" / "recommendations" / "services" / "vendors_cache.json"


def main(batch_limit: int = 500):
    print("Starting pre-geocode job")

    # Load current vendors from in-memory cache
    vendors_lookup = cache.vendors_cache
    vendors = list(vendors_lookup.values())
    print(f"Loaded {len(vendors)} vendors from in-memory cache")

    # Run pre-geocode (this will write geo cache progressively)
    print(f"Geocoding up to {batch_limit} new cities...")
    geo_cache = geolocation.pre_geocode_vendor_cities(vendors, batch_limit=batch_limit)
    print(f"Geo cache now has {len(geo_cache)} entries")

    # Attach geo to vendors where possible
    updated = 0
    for v in vendors:
        city = (v.get("city") or "").strip().lower()
        if not city:
            continue
        loc = geo_cache.get(city)
        if loc:
            v["_geo"] = {"lat": loc["lat"], "lon": loc["lon"]}
            updated += 1

    print(f"Attached geo to {updated} vendors")

    # Persist vendors to vendors_cache.json
    out_list = list(vendors)
    try:
        with VENDORS_CACHE_FILE.open("w", encoding="utf-8") as fh:
            json.dump(out_list, fh, ensure_ascii=False)
        print(f"Wrote vendors cache to {VENDORS_CACHE_FILE}")
    except Exception as e:
        print("Failed to write vendors cache:", e)

    print("Done")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch', type=int, default=500, help='Max new cities to geocode this run')
    args = parser.parse_args()
    main(batch_limit=args.batch)
