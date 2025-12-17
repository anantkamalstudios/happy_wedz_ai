# models/tryon_models.py
from apps.try_on.core.extensions import db
import uuid
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

class Category(db.Model):
    __tablename__ = "product_category"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

class Item(db.Model):
    __tablename__ = "items"
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("product_category.id", ondelete="CASCADE"), nullable=False)
    item_type = db.Column(db.String(50), nullable=False,index = True)
    name = db.Column(db.String(100), nullable=False)
    brand = db.Column(db.String(100))
    color = db.Column(db.String(50))
    image_url = db.Column(db.Text, nullable=False)
    price = db.Column(db.Numeric(10,2))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    category = db.relationship("Category", backref=db.backref("items", lazy="dynamic"))

class TryOnSession(db.Model):
    __tablename__ = "tryon_sessions"
    id = db.Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(db.Integer, nullable=True)
    item_id = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=True)
    input_image_url = db.Column(db.Text, nullable=False)
    result_image_url = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default="pending")
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    completed_at = db.Column(db.DateTime, nullable=True)

    item = db.relationship("Item", backref=db.backref("tryon_sessions", lazy="dynamic"))


