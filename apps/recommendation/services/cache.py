import pandas as pd
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from apps.recommendation.services.vendor_categories import VendorCategories
from dotenv import load_dotenv
import os

load_dotenv()

# --- DB connection & ORM reflection ---
engine = create_engine(os.getenv("DATABASE_URL"))
Base = automap_base()
Base.prepare(engine, reflect=True)

# ORM classes for tables
Venue = Base.classes.venues_fetch
Vendor = Base.classes.vendors_fetch
UserInteraction = Base.classes.user_interactions

# Session
Session = sessionmaker(bind=engine)
session = Session()

# --- Global caches ---
venues_cache = {}
vendors_cache = {}
vendor_categories_cache = defaultdict(list)
user_interaction_cache = defaultdict(lambda: defaultdict(list))

def reload_data():
    """Load and cache data for recommendations"""
    global venues_cache, vendors_cache, vendor_categories_cache, user_interaction_cache

    print("🔄 Reloading data from database...")

    # --- Load venues ---
    venues_cache = {}
    venues = session.query(Venue).all()
    for venue in venues:
        venues_cache[venue.id] = {
            'id': venue.id,
            'name': getattr(venue, 'name', ''),
            'city': getattr(venue, 'city', ''),
            'capacity': getattr(venue, 'capacity', 0) or 0,
            'price': getattr(venue, 'price', 0) or 0,
            'rating': getattr(venue, 'rating', 0) or 0,
            'type': 'venue'
        }

    # --- Load vendors ---
    vendors_cache = {}
    vendor_categories_cache = defaultdict(list)
    vendors = session.query(Vendor).all()
    for vendor in vendors:
        normalized = VendorCategories.normalize_vendor_type(getattr(vendor, 'type', ''))
        category_info = VendorCategories.get_category_display_info(normalized)

        vendor_data = {
            'id': vendor.id,
            'name': getattr(vendor, 'name', ''),
            'city': getattr(vendor, 'city', ''),
            'type': normalized,
            'original_type': getattr(vendor, 'type', ''),
            'category': normalized,
            'category_display': category_info['display_name'],
            'rating': getattr(vendor, 'rating', 0) or 0,
            'item_type': 'vendor'
        }
        vendors_cache[vendor.id] = vendor_data
        vendor_categories_cache[normalized].append(vendor_data)

    # --- Load recent interactions (last 90 days) ---
    cutoff_date = datetime.utcnow() - timedelta(days=90)
    interactions = (
        session.query(UserInteraction)
        .filter(UserInteraction.timestamp >= cutoff_date)
        .order_by(UserInteraction.timestamp.desc())
        .all()
    )

    user_interaction_cache = defaultdict(lambda: defaultdict(list))
    for i in interactions:
        user_interaction_cache[i.user_id]['interactions'].append({
            'item_id': i.item_id,
            'item_type': i.item_type,
            'interaction_type': i.interaction_type,
            'timestamp': i.timestamp,
            'days_ago': (datetime.now(timezone.utc) - i.timestamp).days
        })

    # print(f"✅ Loaded {len(venues_cache)} venues, {len(vendors_cache)} vendors")
    # print(f"✅ Vendor categories: {list(vendor_categories_cache.keys())}")
    # print(f"✅ Cached {len(interactions)} interactions")

# --- Initialize at startup ---
reload_data()
