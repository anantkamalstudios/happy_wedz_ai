from flask import Flask
from apps.image_processing.models.makeup_image_model import db
from apps.image_processing.apis.makeup_image_apis import (
    images_bp,
    products_bp
    )
import os
from dotenv import load_dotenv

load_dotenv()


def create_app():
    app = Flask(__name__)
    # ---- CONFIG ----
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # limit upload size (e.g., 16 MB)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

    db.init_app(app)

    # Register blueprints
    app.register_blueprint(images_bp)
    app.register_blueprint(products_bp)

    return app
