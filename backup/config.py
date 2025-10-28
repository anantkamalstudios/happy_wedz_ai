from flask import Flask
from apps.image_processing.apis import register_image_processing_routes
from apps.recommendation.apis import register_recommendation_routes
import os
from db import db
from flask_cors import CORS
from dotenv import load_dotenv
load_dotenv()


def create_app():
    app = Flask(__name__)
    CORS(app)
    # ---- CONFIG ----
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # limit upload size (e.g., 16 MB)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

    db.init_app(app)

    # Register routes
    register_image_processing_routes(app)
    register_recommendation_routes(app)
    return app
