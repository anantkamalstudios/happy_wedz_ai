from flask import Blueprint, jsonify
from datetime import datetime
from collections import Counter, defaultdict

from apps.recommendation.models.user import UserFetch
from apps.recommendation.services.recommendation_engine import HybridRecommendationEngine, get_fallback_recommendations
from apps.recommendation.services.vendor_categories import VendorCategories
from apps.recommendation.services.cache import user_interaction_cache

recommendations_bp = Blueprint("recommendations", __name__)

@recommendations_bp.route("/recommendations/<int:user_id>", methods=["GET"])
def recommend(user_id):
    try:
        # Step 1: Get hybrid recommendations
        recommendations = HybridRecommendationEngine.get_recommendations(user_id, limit=50)

        # Step 2: Separate venues and vendors
        venues = [r for r in recommendations if r.get('type') == 'venue'][:20]
        top_venue_cities = list({v['city'] for v in venues})
        vendors = [r for r in recommendations if r.get('type') != 'venue' and r.get('city') in top_venue_cities]

        # Step 3: Categorize vendors
        vendor_categories = defaultdict(lambda: {"display_name": "Other Services", "icon": "⭐", "items": []})
        for cat, info in VendorCategories.CATEGORIES.items():
            vendor_categories[cat] = {**info, "items": []}
        for v in vendors:
            vtype = VendorCategories.TYPE_MAP.get(v.get('type', '').lower(), 'other')
            vendor_categories[vtype]["items"].append(v)
        for cat in vendor_categories:
            vendor_categories[cat]["items"] = sorted(
                vendor_categories[cat]["items"], key=lambda x: x.get('final_score', 0), reverse=True
            )[:10]

        # Step 4: User info
        user = UserFetch.query.get(user_id)
        days_since_registration = (datetime.utcnow() - user.created_at).days if user else 0
        user_interactions = user_interaction_cache.get(user_id, {}).get('interactions', [])
        is_new_user = days_since_registration <= 7 and len(user_interactions) < 5

        method = "new_user_city" if is_new_user else "hybrid_weighted"

        # Step 5: Return structured JSON
        return jsonify({
            "method": method,
            "venues": venues,
            "vendors": vendors,
            "vendor_categories": vendor_categories,
            "user_profile": {
                "is_new_user": is_new_user,
                "days_since_registration": days_since_registration,
                "total_interactions": len(user_interactions)
            },
            "recommendation_stats": {
                "total_venues": len(venues),
                "total_vendors": len(vendors),
                "sources": dict(Counter([r.get('source', 'unknown') for r in recommendations]))
            }
        })

    except Exception as e:
        print(f"Error in recommend endpoint: {e}")
        return get_fallback_recommendations(user_id)
