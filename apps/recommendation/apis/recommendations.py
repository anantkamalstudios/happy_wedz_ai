from flask import Blueprint, jsonify
from ..services.recommendation_engine import HybridRecommendationEngine, CategorizedVendorRecommender

recommendation_bp = Blueprint('recommendations', __name__)

@recommendation_bp.route("/<int:user_id>", methods=["GET"])
def recommend(user_id):
    """Get personalized recommendations for a user"""
    recommendations = HybridRecommendationEngine.get_recommendations(user_id)
    return jsonify({"recommendations": recommendations})

@recommendation_bp.route("/categorized/<int:user_id>", methods=["GET"])
def get_categorized_recommendations(user_id):
    """Get categorized vendor recommendations for a user"""
    categorized_recs = CategorizedVendorRecommender.get_categorized_recommendations(user_id)
    return jsonify({"categories": categorized_recs})