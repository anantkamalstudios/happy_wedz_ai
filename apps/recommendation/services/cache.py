import pandas as pd
from collections import defaultdict
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from apps.recommendation.services.vendor_categories import VendorCategories

# DB connection
from config import DB_URL
engine = create_engine(DB_URL)

# Global caches
venues_cache = {}
vendors_cache = {}
vendor_categories_cache = defaultdict(list)
user_interaction_cache = defaultdict(lambda: defaultdict(list))

def reload_data():
    """Load and cache data for recommendations"""
    global venues_cache, vendors_cache, vendor_categories_cache, user_interaction_cache

    print("🔄 Reloading data from database...")

    # --- Load venues ---
    venues_df = pd.read_sql("SELECT * FROM sub_venues", engine)
    venues_cache = {}
    for _, venue in venues_df.iterrows():
        venues_cache[venue['id']] = {
            'id': venue['id'],
            'name': venue['name'],
            'city': venue['city'],
            'capacity': venue['capacity'] or 0,
            'price': venue['price'] or 0,
            'rating': venue['rating'] or 0,
            'image': venue.get('image', ''),
            'type': 'venue'
        }

    # --- Load vendors ---
    vendors_df = pd.read_sql("SELECT * FROM sub_vendors", engine)
    vendors_cache = {}
    vendor_categories_cache = defaultdict(list)
    for _, vendor in vendors_df.iterrows():
        vendor_id = vendor.get('id')
        if not vendor_id:
            continue  # Skip vendors without id
        vendor_type = vendor.get('type')
        normalized = VendorCategories.normalize_vendor_type(vendor_type)
        category_info = VendorCategories.get_category_display_info(normalized)

        vendor_data = {
            'id': vendor_id,
            'name': vendor.get('name', 'Unknown'),
            'city': vendor.get('city', 'Unknown'),
            'type': normalized,
            'original_type': vendor_type,
            'category': normalized,
            'category_display': category_info.get('display_name', 'Other'),
            'rating': vendor.get('rating', 0) or 0,
            'image': vendor.get('image', ''),
            'item_type': 'vendor'
        }
        vendors_cache[vendor_id] = vendor_data
        vendor_categories_cache[normalized].append(vendor_data)

    # --- Load recent interactions (last 90 days) ---
    cutoff_date = (datetime.utcnow() - timedelta(days=90)).strftime('%Y-%m-%d')
    interactions_df = pd.read_sql(
        f"SELECT * FROM user_interactions_test WHERE timestamp >= '{cutoff_date}' ORDER BY timestamp DESC",
        engine
    )

    user_interaction_cache = defaultdict(lambda: defaultdict(list))
    for _, i in interactions_df.iterrows():
        user_interaction_cache[i['user_id']]['interactions'].append({
            'item_id': i['item_id'],
            'item_type': i['item_type'],
            'interaction_type': i['interaction_type'],
            'timestamp': i['timestamp'],
            'days_ago': (datetime.utcnow() - i['timestamp']).days
        })

    print(f"✅ Loaded {len(venues_cache)} venues, {len(vendors_cache)} vendors")
    print(f"✅ Vendor categories: {list(vendor_categories_cache.keys())}")
    print(f"✅ Cached {len(interactions_df)} interactions")

# Initialize at startup
reload_data()
