from collections import defaultdict, Counter
from datetime import datetime, timedelta
from ..models.interaction import Venue, Vendor
from .weights import RecommendationWeights
from .vendor_categories import VendorCategories

venues_cache = {}
vendors_cache = {}
vendor_categories_cache = defaultdict(list)
user_interaction_cache = defaultdict(lambda: defaultdict(list))

def reload_data(db):
    """Load and cache data for fast recommendations"""
    global venues_cache, vendors_cache, vendor_categories_cache, user_interaction_cache

    try:
        # Test database connection
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        

        # Load venues (all columns)
        venues_query = Venue.query.all()
        venues_cache.clear()
        for venue in venues_query:
            venues_cache[venue.id] = venue.to_dict()

        # Load vendors (only required columns to save memory)
        from sqlalchemy.orm import load_only
        vendors_query = Vendor.query.options(
            load_only(Vendor.id, Vendor.name, Vendor.city, Vendor.type, Vendor.rating, Vendor.image_type)
        ).all()
        vendors_cache.clear()
        vendor_categories_cache.clear()

        unmapped_types = set()
        for vendor in vendors_query:
            vendor_data = vendor.to_dict()
            vendors_cache[vendor.id] = vendor_data
            vendor_categories_cache[vendor_data['category']].append(vendor_data)

            if vendor_data['category'] == 'other':
                unmapped_types.add(vendor.type)

        if unmapped_types:
            print(f"⚠️ Unmapped vendor types (mapped to 'other'): {sorted(unmapped_types)}")

        # Sort vendors in each category by rating
        for category in vendor_categories_cache:
            vendor_categories_cache[category].sort(key=lambda x: x['rating'], reverse=True)

        # Load recent interactions (last 90 days)
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        from ..models import UserInteraction
        interactions_query = UserInteraction.query.filter(
            UserInteraction.timestamp >= cutoff_date
        ).order_by(UserInteraction.timestamp.desc()).all()

        # Build user interaction profiles
        user_interaction_cache.clear()
        for interaction in interactions_query:
            user_id = interaction.user_id
            user_interaction_cache[user_id]['interactions'].append({
                'item_id': interaction.item_id,
                'item_type': interaction.item_type,
                'interaction_type': interaction.interaction_type,
                'timestamp': interaction.timestamp,
                'days_ago': (datetime.utcnow() - interaction.timestamp).days
            })

        print(f"✅ Loaded {len(venues_cache)} venues, {len(vendors_cache)} vendors")
        print(f"✅ Vendor categories: {list(vendor_categories_cache.keys())}")
        print(f"✅ Processed {len(interactions_query)} recent interactions for {len(user_interaction_cache)} users")

    except Exception as e:
        import traceback
        print(f"⚠️ Database connection error: {e}")
        traceback.print_exc()
        print("Using empty caches for now...")