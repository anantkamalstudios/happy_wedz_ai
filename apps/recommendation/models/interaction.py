from db import db
from datetime import datetime
from ..services.vendor_categories import VendorCategories

class Venue(db.Model):
    __tablename__ = 'venues_fetch'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    city = db.Column(db.String(100))
    capacity = db.Column(db.Integer)
    rating = db.Column(db.Float)
    price = db.Column(db.Float)
    image = db.Column(db.String)
    image_type = db.Column(db.String)
    type = db.Column(db.String)
    description = db.Column(db.String)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'city': self.city,
            'capacity': self.capacity,
            'price': self.price,
            'rating': self.rating,
            'type': 'venue',
            'item_type': 'venue',
            'has_image': bool(self.image_type),
            'image_type': self.image_type,
            'description': self.description,
            'venue_type': self.type
        }

class Vendor(db.Model):
    __tablename__ = 'vendors_fetch'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    city = db.Column(db.String(100))
    type = db.Column(db.String(100))
    rating = db.Column(db.Float)
    image = db.Column(db.String)
    image_type = db.Column(db.String)

    def to_dict(self):
        normalized_category = VendorCategories.normalize_vendor_type(self.type)
        category_info = VendorCategories.get_category_display_info(normalized_category)
        return {
            'id': self.id,
            'name': self.name,
            'city': self.city,
            'type': normalized_category,
            'original_type': self.type,
            'category': normalized_category,
            'category_display': category_info['display_name'],
            'category_description': category_info['description'],
            'category_priority': category_info['priority'],
            'rating': self.rating,
            'item_type': 'vendor',
            'has_image': bool(self.image_type),
            'image_type': self.image_type
        }