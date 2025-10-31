# from flask import Flask
# from apps.image_processing.apis import register_image_processing_routes
# from apps.recommendation.apis import register_recommendation_routes
# import os
# from db import db
# from flask_cors import CORS
# from dotenv import load_dotenv
# load_dotenv()


# class Config:
#     SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
#     SQLALCHEMY_TRACK_MODIFICATIONS = False

#     MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
#     MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
#     MAIL_USERNAME = os.getenv("MAIL_USERNAME")
#     MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
#     MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")

#     REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
#     CELERY_BROKER_URL = REDIS_URL
#     CELERY_RESULT_BACKEND = REDIS_URL

#     LOG_DIR = os.getenv("LOG_DIR", "logs")


# def create_app():
#     app = Flask(__name__)
#     CORS(app)

#     # Load config
#     from config import Config
#     app.config.from_object(Config)

#     os.makedirs(app.config["LOG_DIR"], exist_ok=True)

#     db.init_app(app)
#     register_image_processing_routes(app)
#     register_recommendation_routes(app)

#     return app



# config.py
from flask import Flask
import os
from db import db
from flask_cors import CORS
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")

    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL

    LOG_DIR = os.getenv("LOG_DIR", "logs")
    BASE_DIR = Path(__file__).resolve().parent
    load_dotenv(BASE_DIR / ".env")

    # Outfit Tryon Configuration
    TRYON_API_KEY = os.getenv("TRYON_API_KEY")
    TRYON_API_URL = os.getenv("TRYON_API_URL", "https://tryon-api.com/api/v1")

    UPLOAD_FOLDER = str(BASE_DIR / "uploads")
    RESULT_FOLDER = str(BASE_DIR / "results")

    if not TRYON_API_KEY:
        raise RuntimeError(
            "TRYON_API_KEY is not set. Add it to a .env file or set the environment variable."
        )


def create_app():
    app = Flask(__name__)
    CORS(app)

    app.config.from_object(Config)
    os.makedirs(app.config["LOG_DIR"], exist_ok=True)

    db.init_app(app)

    # Lazy import avoids circular dependency
    from apps.image_processing.apis import register_image_processing_routes
    from apps.recommendation.apis import register_recommendation_routes
    from apps.outfit_tryon.apis import register_outfit_tryon_routes

    register_image_processing_routes(app)
    register_recommendation_routes(app)
    register_outfit_tryon_routes(app)

    return app

