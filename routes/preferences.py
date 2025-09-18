from flask import Blueprint, jsonify
from services.cache import user_interaction_cache
from services.recommendation_engine import UserPreferenceRecommender

preferences_bp = Blueprint("preferences", __name__)

@preferences_bp.route("/user/<int:user_id>/preferences", methods=["GET"])
def get_user_preferences(user_id):
    if user_id not in user_interaction_cache:
        return jsonify({"message": "No interaction data found."})

    interactions = user_interaction_cache[user_id]['interactions']
    if not interactions:
        return jsonify({"message": "No interactions yet."})

    preferences = UserPreferenceRecommender.calculate_weighted_preferences(interactions)

    formatted = {
        "favorite_cities": dict(preferences['cities']),
        "favorite_vendor_categories": dict(preferences['vendor_categories']),
        "favorite_types": dict(preferences['types']),
        "total_interactions": len(interactions)
    }
    return jsonify({"user_id": user_id, "preferences": formatted})
