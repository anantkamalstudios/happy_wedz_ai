"""Initialize the tryon apis module."""
from apps.tryon.apis.tryon_apis import tryon_bp

def register_tryon_routes(app):
    app.register_blueprint(tryon_bp, url_prefix="/api/tryon")