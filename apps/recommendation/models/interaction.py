from db import db
from datetime import datetime

class UserInteraction(db.Model):
    __tablename__ = "user_interactions_test"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    item_type = db.Column(db.String(50))   # venue or vendor
    item_id = db.Column(db.Integer)
    interaction_type = db.Column(db.String(20))  # like, view, wishlist
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
