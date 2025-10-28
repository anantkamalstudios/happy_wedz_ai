from flask import Flask
from .apis.tryon_apis import tryon_bp

def create_tryon_app():
    app = Flask(__name__)
    
    # Register blueprints
    app.register_blueprint(tryon_bp, url_prefix="/api/tryon")
    
    return app