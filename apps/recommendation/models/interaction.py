from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from db import db


class UserInteraction(db.Model):
    __tablename__ = "user_interactions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    item_type = db.Column(db.String(50))   # venue or vendor
    item_id = db.Column(db.Integer)
    interaction_type = db.Column(db.String(20))  # like, view, wishlist
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
