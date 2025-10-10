from flask import Blueprint, jsonify
from datetime import datetime, timedelta
from collections import defaultdict
from apps.recommendation.models.interaction import UserInteraction
from apps.recommendation.services.cache import venues_cache, vendors_cache
from apps.recommendation.services.weights import RecommendationWeights

trending_bp = Blueprint("trending", __name__)

@trending_bp.route("/trending", methods=["GET"])
def get_trending():
    recent_cutoff = datetime.utcnow() - timedelta(days=7)
    recent_interactions = UserInteraction.query.filter(
        UserInteraction.timestamp >= recent_cutoff
    ).all()

    item_popularity = defaultdict(int)
    for interaction in recent_interactions:
        weight = RecommendationWeights.INTERACTION_WEIGHTS.get(interaction.interaction_type, 1)
        if weight > 0:
            item_popularity[f"{interaction.item_type}_{interaction.item_id}"] += weight

    trending_venues = []
    trending_vendors_by_category = defaultdict(list)

    for item_key, score in sorted(item_popularity.items(), key=lambda x: x[1], reverse=True):
        item_type, item_id = item_key.split('_')
        item_id = int(item_id)
        if item_type == 'venue' and item_id in venues_cache:
            venue = venues_cache[item_id].copy()
            venue['trending_score'] = score
            trending_venues.append(venue)
        elif item_type == 'vendor' and item_id in vendors_cache:
            vendor = vendors_cache[item_id].copy()
            vendor['trending_score'] = score
            trending_vendors_by_category[vendor['category']].append(vendor)

    return jsonify({
        "trending_venues": trending_venues[:20],
        "trending_vendor_categories": dict(trending_vendors_by_category),
        "time_period": "last_7_days"
    })
