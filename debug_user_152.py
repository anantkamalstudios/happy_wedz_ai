#!/usr/bin/env python
import sys
sys.path.insert(0, '.')

from run import app
from apps.recommendations.models.user import User
from apps.recommendations.services.cache import vendors_cache
import json

output = []

with app.app_context():
    # Check user 152
    user = User.query.get(152)
    if user:
        output.append(f"✓ User 152 found: city={user.city}, wedding_venue={user.wedding_venue}")
    else:
        output.append("✗ User 152 not found in DB")
    
    # Check nashik vendors in cache
    nashik_vendors = [v for v in vendors_cache.values() if (v.get('city') or '').lower() == 'nashik']
    delhi_vendors = [v for v in vendors_cache.values() if (v.get('city') or '').lower() == 'delhi']
    
    output.append(f"\nVendors in cache:")
    output.append(f"  Nashik vendors: {len(nashik_vendors)}")
    output.append(f"  Delhi vendors: {len(delhi_vendors)}")
    
    # Show top 5 vendor cities
    city_counts = {}
    for v in vendors_cache.values():
        c = (v.get('city') or 'unknown').lower().strip()
        city_counts[c] = city_counts.get(c, 0) + 1
    
    output.append(f"\nTop cities in vendors_cache:")
    for city, count in sorted(city_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        output.append(f"  {city}: {count} vendors")

with open("debug_output.txt", "w") as f:
    f.write("\n".join(output))

print("Output written to debug_output.txt")
