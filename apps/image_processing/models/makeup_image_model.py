
from datetime import datetime
import enum
from sqlalchemy.dialects.postgresql import ARRAY

from db import db

class ImageType(enum.Enum):
    ORIGINAL = "ORIGINAL"
    RESULT = "RESULT"
    TRYON_PERSON = "TRYON_PERSON"
    TRYON_GARMENT = "TRYON_GARMENT"
    TRYON_RESULT = "TRYON_RESULT"


class UserImage(db.Model):
    __tablename__ = "user_images"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(100), nullable=False)
    size_bytes = db.Column(db.Integer, nullable=False)
    data = db.Column(db.LargeBinary, nullable=False)  # <-- BYTEA in Postgres
    image_type = db.Column(db.Enum(ImageType), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)


class CategoryEnum(enum.Enum):
    MAKEUP = "MAKEUP"
    JWELLERY = "JWELLERY"



# class ProductDetailedEnum(enum.Enum):
#     LIPSTICK = "LipStick"   
#     BLUSH = "Blush" 
#     EYESHADOW = "EyeShadow" 
#     CONTACTLENSES = "ContactLenses" 
#     # PRIMER = "Primer"  
#     FOUNDATION = "Foundation" 
#     CONCEALER = "concealer" 
#     CONTOUR = "Contour" 
#     MASCARA = "Mascara" 
#     KAJAL = "Kajal" 
#     BINDI = "Bindi"
#     MANGTIKA = "MangTika"


class ProductDetailedCategory(db.Model):
    __tablename__ = "product_detailed_categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)  # Lipstick, Blush, etc.
    image = db.Column(db.LargeBinary, nullable=True)               # optional representative image
    image_type = db.Column(db.String(50), nullable=True)           # e.g., "image/png"

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship: One ProductDetailedCategory -> Many Products
    products = db.relationship("Product", back_populates="detailed_category")

                                                                                                         
class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    product_category = db.Column(db.Enum(CategoryEnum), nullable=False)
    
    # Link to ProductDetailedCategory
    product_detailed_category_id = db.Column(
        db.Integer, db.ForeignKey("product_detailed_categories.id"), nullable=False
    )
    
    product_name = db.Column(db.Text, nullable=False)
    brand_name = db.Column(db.Text, nullable=False)
    price = db.Column(db.Numeric(10, 2))	
    product_real_image = db.Column(db.LargeBinary, nullable=False)   # store image binary
    product_real_image_type = db.Column(db.Text, nullable=False)  # keep mimetype
    product_colors = db.Column(ARRAY(db.String(7)), nullable=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    detailed_category = db.relationship(
        "ProductDetailedCategory", back_populates="products"
    )



class UserMakeupResultImage(db.Model):      # need to add user_id foreign key
    __tablename__ = "user_makeup_result_image"

    id = db.Column(db.Integer, primary_key=True)
    result_image_id = db.Column(db.Integer, db.ForeignKey("user_images.id"), nullable=False)
    result_product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # relation
    result_image = db.relationship("UserImage", backref="applied_products")
    product = db.relationship("Product", backref="used_in_results")
