# config.py
import os
from dotenv import load_dotenv

load_dotenv()  # Load from .env

DB_URL="postgresql+psycopg2://postgres:root@localhost:5432/happywedzdb"
SECRET_KEY="my_super_secret_key"
class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DB_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret")
