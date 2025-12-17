import json
from pathlib import Path

VENDORS = Path('apps') / 'recommendations' / 'services' / 'vendors_cache.json'
GEO = Path('apps') / 'recommendations' / 'services' / 'geo_cache.json'

vendors = []
geo = {}

if VENDORS.exists():
    try:
        vendors = json.loads(VENDORS.read_text(encoding='utf-8') or '[]')
    except Exception as e:
        print('ERR: failed to read vendors cache', e)
        raise
else:
    print('ERR: vendors cache not found:', VENDORS)
    raise SystemExit(2)

if GEO.exists():
    try:
        geo = json.loads(GEO.read_text(encoding='utf-8') or '{}')
    except Exception as e:
        print('ERR: failed to read geo cache', e)
        raise
else:
    geo = {}

total = len(vendors)
with_geo_field = 0
with_geo_city_cached = 0
missing_city = 0
missing_geo = 0

for v in vendors:
    city = (v.get('city') or '').strip()
    if v.get('_geo'):
        with_geo_field += 1
    if city and city.lower() in geo:
        with_geo_city_cached += 1
    if not city:
        missing_city += 1
    if not v.get('_geo'):
        missing_geo += 1

# write a small summary
summary = {
    'total_vendors': total,
    'vendors_with__geo_field': with_geo_field,
    'vendors_with_city_in_geo_cache': with_geo_city_cached,
    'vendors_missing_city': missing_city,
    'vendors_missing__geo_field': missing_geo,
    'vendors_potentially_geocodable': total - with_geo_field - missing_city
}
print(json.dumps(summary, indent=2))
