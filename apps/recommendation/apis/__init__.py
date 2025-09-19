from flask import Blueprint

def register_routes(app):
    from .interactions import interactions_bp
    from .recommendations import recommendations_bp
    from .trending import trending_bp
    from .preferences import preferences_bp

    app.register_blueprint(interactions_bp)
    app.register_blueprint(recommendations_bp)
    app.register_blueprint(trending_bp)
    app.register_blueprint(preferences_bp)
