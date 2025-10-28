from flask import Flask
from apps.image_processing.apis import register_image_processing_routes
from apps.recommendation.apis import register_recommendation_routes
from apps.tryon.apis import register_tryon_routes
import os
from db import db
from flask_cors import CORS
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
    
    # Virtual Try-on service configuration
    TRYON_SERVICE_URL = os.getenv("TRYON_SERVICE_URL", "https://api.happywedz.com/api/tryon/process")


def create_app():
    app = Flask(__name__)
    CORS(app)

    # Load config
    from config import Config
    app.config.from_object(Config)

    os.makedirs(app.config["LOG_DIR"], exist_ok=True)

    db.init_app(app)
    register_image_processing_routes(app)
    register_recommendation_routes(app)
    register_tryon_routes(app)

    return app
