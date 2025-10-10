from flask import Blueprint
from apps.recommendation.apis.interactions import interactions_bp
from apps.recommendation.apis.preferences import preferences_bp
from apps.recommendation.apis.recommendations import recommendations_bp
from apps.recommendation.apis.trending import trending_bp

def register_recommendation_routes(app):
    app.register_blueprint(interactions_bp)
    app.register_blueprint(recommendations_bp)
    app.register_blueprint(trending_bp)
    app.register_blueprint(preferences_bp)
