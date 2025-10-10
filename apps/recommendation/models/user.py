from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from db import db


class UserFetch(db.Model):
    __tablename__ = "usersfetch"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100))
    overall_budget = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
