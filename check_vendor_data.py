#!/usr/bin/env python
import sys
import os
os.chdir('apps/recommendations')
sys.path.insert(0, '.')

from app_back import create_app
from models.vendor import VendorSubcategoryData

app = create_app()
with app.app_context():
    from extensions import db
    
    total = db.session.query(VendorSubcategoryData).count()
    print(f"Total VendorSubcategoryData rows: {total}")
    
    if total > 0:
        # Check first 5 rows
        rows = db.session.query(VendorSubcategoryData).limit(5).all()
        for row in rows:
            print(f"\nRow ID: {row.id}")
            print(f"  vendor_id: {row.vendor_id}")
            print(f"  vendor_subcategory_id: {row.vendor_subcategory_id}")
            print(f"  attributes keys: {list(row.attributes.keys()) if row.attributes else 'None'}")
            print(f"  media count: {len(row.media) if row.media else 0}")
    else:
        print("No rows found in VendorSubcategoryData table!")

