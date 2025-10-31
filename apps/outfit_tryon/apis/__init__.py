from apps.outfit_tryon.apis.outfit_trypon_apis import (
    outfit_tryon_bp
    )

def register_outfit_tryon_routes(app):
    app.register_blueprint(outfit_tryon_bp)