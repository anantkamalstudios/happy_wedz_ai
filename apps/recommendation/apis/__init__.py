from flask import Blueprint
from .interactions import interactions_bp
from .recommendations import recommendation_bp

api_bp = Blueprint('api', __name__)

api_bp.register_blueprint(interactions_bp, url_prefix='/interactions')
api_bp.register_blueprint(recommendation_bp, url_prefix='/recommendations')


def register_recommendation_routes(app):
	"""Register recommendation API blueprint on the Flask app.

	This mirrors the pattern used by `apps.image_processing.apis.register_image_processing_routes`.
	"""
	app.register_blueprint(api_bp, url_prefix='/api/recommendation')