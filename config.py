# config.py
import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

class Config:
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

    # Mail
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")

    # Redis / Celery
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL

    # Paths
    LOG_DIR = os.getenv("LOG_DIR", "logs")
    UPLOAD_FOLDER = str(BASE_DIR / "uploads")
    RESULT_FOLDER = str(BASE_DIR / "results")

    # Tryon keys (don't raise at import time)
    TRYON_API_KEY = os.getenv("TRYON_API_KEY")
    TRYON_API_URL = os.getenv("TRYON_API_URL", "https://tryon-api.com/api/v1")

    # TheNewBlack
    NEWBLACK_API_BASE = "https://thenewblack.ai/api/1.1/wf"
    NEWBLACK_EMAIL = os.getenv("NEW_BLACK_EMAIL")
    NEWBLACK_PASSWORD = os.getenv("NEW_BLACK_PASSWORD")

    # Cloudinary
    CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")


def create_app():
    app = Flask(__name__)
    CORS(app)

    # load config
    app.config.from_object(Config)
    os.makedirs(app.config["LOG_DIR"], exist_ok=True)

    # import single db instance and initializers (import inside factory to avoid circulars)
    from db import db                    # <-- single SQLAlchemy instance
    from apps.try_on.core.extensions import init_cloudinary

    # IMPORTANT: init the SQLAlchemy app binding before importing models/blueprints
    db.init_app(app)

    # initialize cloudinary (safe, uses app.config.get inside)
    init_cloudinary(app)

    # runtime check for required secrets (raise here — not at module import time)
    if not app.config.get("TRYON_API_KEY"):
        # fail fast when running create_app if the key is required in production
        raise RuntimeError("TRYON_API_KEY is not set. Add it to a .env file or set the environment variable.")

    # register blueprints AFTER db.init_app(app) to avoid 'not registered' errors
    from apps.image_processing.apis import register_image_processing_routes
    from apps.recommendations.routes import register_routes as register_recommendations_routes
    from apps.outfit_tryon.apis import register_outfit_tryon_routes
    from apps.try_on.apis import register_tryon_routes

    register_image_processing_routes(app)
    register_recommendations_routes(app)
    register_outfit_tryon_routes(app)
    register_tryon_routes(app)

    return app
