from flask import Flask


def create_app():
    """Application factory. Configure app and register blueprints."""
    app = Flask(__name__)

    # apply configuration
    from .config import init_config
    init_config(app)

    # register blueprints
    from .blueprints.tryon import tryon_bp
    app.register_blueprint(tryon_bp)

    return app
