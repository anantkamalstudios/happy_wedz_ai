# core/__init__.py
from flask import Flask
import config
from apps.try_on.core.extensions import db, init_cloudinary
from apps.try_on.apis.clothes import clothes_bp
from apps.try_on.apis.catalog import catalog_bp
from apps.try_on.apis.jewelry import jewelry_bp
from apps.try_on.apis.create_category import create_category_bp,get_categories_bp

# def create_app():
#     app = Flask(__name__)
#     app.config.from_object(config.Config)

#     # init extensions
#     db.init_app(app)
#     init_cloudinary(app)

def register_tryon_routes(app):
    # register blueprints
    app.register_blueprint(clothes_bp)
    app.register_blueprint(jewelry_bp)
    app.register_blueprint(catalog_bp)
    app.register_blueprint(create_category_bp)
    app.register_blueprint(get_categories_bp)

    return app
