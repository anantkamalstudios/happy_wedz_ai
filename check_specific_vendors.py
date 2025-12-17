#!/usr/bin/env python
import sys
import os
os.chdir('apps/recommendations')
sys.path.insert(0, '.')

from apps.recommendations.app_back import create_app
from apps.recommendations.models.vendor import VendorSubcategoryData

app = create_app()
with app.app_context():
    from apps.recommendations.extensions import db
    
    # Check specific vendors from your recommendation response
    vendor_ids = [11395, 2551]  # Lustre Studio, Sukhdev Caterers
    
    for vid in vendor_ids:
        rows = db.session.query(VendorSubcategoryData).filter_by(vendor_id=vid).all()
        print(f"\nVendor ID {vid}: {len(rows)} rows")
        if rows:
            print(f"  First row - attributes keys: {list(rows[0].attributes.keys())[:5] if rows[0].attributes else 'None'}")
            print(f"  First row - media count: {len(rows[0].media) if rows[0].media else 0}")
        else:
            print(f"  ⚠️  NO RECORDS FOUND FOR THIS VENDOR!")
