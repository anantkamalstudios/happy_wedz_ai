from db import db
from datetime import datetime

class UserInteraction(db.Model):
    __tablename__ = 'user_interactions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    item_type = db.Column(db.String(50))
    item_id = db.Column(db.Integer)
    interaction_type = db.Column(db.String(20))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)