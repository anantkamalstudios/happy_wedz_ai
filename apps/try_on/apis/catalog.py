# apis/catalog.py
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import func
import cloudinary.uploader
from apps.try_on.core.extensions import db
from apps.try_on.models.models import Item, Category

catalog_bp = Blueprint("catalog", __name__,url_prefix="/api/catalog")

# ---------- Helper ----------
def upload_to_cloudinary(file, folder="tryon/catalog"):
    """Upload image to Cloudinary and return secure URL."""
    result = cloudinary.uploader.upload(
        file,
        folder=folder,
        resource_type="image",
        use_filename=True,
        unique_filename=False
    )
    return result["secure_url"]


# ---------- Get Items ----------
CATEGORY_SYNONYMS = {
    "clothes": "outfit",
    "clothing": "outfit",
    "outfits": "outfit",
    "dresses": "outfit",
    "one-pieces": "outfit",
    "makeup": "makeup",
    "cosmetics": "makeup",
    "jewelry": "jewelry",
    "jewellery": "jewelry"
}

@catalog_bp.route("/items", methods=["GET"])
def get_items():
    category_name = request.args.get("category", type=str)
    category_id = request.args.get("category_id", type=int)

    current_app.logger.debug("GET /catalog/items?category=%s category_id=%s", category_name, category_id)

    # require at least one
    if not category_name and not category_id:
        return jsonify({"ok": False, "error": "Provide category name or category_id"}), 400

    category = None

    # 1) if category_id provided, use it directly
    if category_id:
        category = Category.query.get(category_id)

    # 2) try case-insensitive lookup by provided name
    if not category and category_name:
        name_norm = category_name.strip().lower()
        category = Category.query.filter(func.lower(Category.name) == name_norm).first()

    # 3) if still not found, try synonyms map
    if not category and category_name:
        mapped = CATEGORY_SYNONYMS.get(category_name.strip().lower())
        if mapped:
            current_app.logger.debug("Mapped category '%s' -> '%s' via synonyms", category_name, mapped)
            category = Category.query.filter(func.lower(Category.name) == mapped).first()

    if not category:
        return jsonify({"ok": True, "category": None, "items": []}), 200

    items = Item.query.filter_by(category_id=category.id).all()
    item_list = [{
        "id": i.id,
        "name": i.name,
        "brand": i.brand,
        "color": i.color,
        "image_url": i.image_url,
        "price": float(i.price) if i.price else None,
        "description": i.description,
        "category_id": i.category_id,
        "category_name": category.name
    } for i in items]

    return jsonify({"ok": True, "category": category.name, "items": item_list}), 200


# ---------- Add Item ----------
@catalog_bp.route("/items", methods=["POST"])
def add_item():
    """
    Add a new product item to catalog.
    form-data:
      - name (required)
      - category (name) OR category_id (required)
      - brand, color, price, description (optional)
      - item_file (required): image file
    """
    name = request.form.get("name")
    category_name = request.form.get("category")
    category_id = request.form.get("category_id")
    brand = request.form.get("brand")
    color = request.form.get("color")
    price = request.form.get("price")
    description = request.form.get("description")
    file = request.files.get("item_file")

    if not name or (not category_name and not category_id) or not file:
        return jsonify({"ok": False, "error": "Missing required fields: name, category/category_id, and item_file"}), 400

    # Find or create category
    category = None
    if category_id:
        category = Category.query.get(category_id)
    elif category_name:
        category = Category.query.filter(func.lower(Category.name) == category_name.strip().lower()).first()
        if not category:
            category = Category(name=category_name.strip().lower())
            db.session.add(category)
            db.session.commit()

    if not category:
        return jsonify({"ok": False, "error": "Invalid category"}), 400

    # Upload to Cloudinary
    try:
        image_url = upload_to_cloudinary(file, folder=f"tryon/catalog/{category.name}")
    except Exception as e:
        current_app.logger.exception("Cloudinary upload failed")
        return jsonify({"ok": False, "error": f"Cloudinary upload failed: {str(e)}"}), 500

    # Insert item record
    try:
        item_type = category.name.lower()  # derive from category

        item = Item(
            category_id=category.id,
            item_type=item_type,
            name=name,
            brand=brand,
            color=color,
            image_url=image_url,
            price=float(price) if price else None,
            description=description,
         )
        db.session.add(item)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": f"Database insert failed: {str(e)}"}), 500

    return jsonify({
        "ok": True,
        "message": "Item added successfully",
        "item": {
            "id": item.id,
            "name": item.name,
            "brand": item.brand,
            "color": item.color,
            "image_url": item.image_url,
            "price": float(item.price) if item.price else None,
            "description": item.description,
            "category_id": category.id,
            "category_name": category.name,
            "item_type": item.item_type
        }
    }), 201

@catalog_bp.route("/all_items", methods=["GET"])
def get_all_items():
    """
    Get all items across all categories without any parameters.
    """
    items = Item.query.all()
    item_list = []
    for i in items:
        category = Category.query.get(i.category_id)
        item_list.append({
            "id": i.id,
            "name": i.name,
            "brand": i.brand,
            "color": i.color,
            "image_url": i.image_url,
            "price": float(i.price) if i.price else None,
            "description": i.description,
            "category_id": i.category_id,
            "category_name": category.name if category else None
        })

    return jsonify({"ok": True, "items": item_list}), 200

# ---------- Delete Item ----------
@catalog_bp.route("/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    """
    Delete an item by ID.
    """
    item = Item.query.get(item_id)
    if not item:
        return jsonify({"ok": False, "error": "Item not found"}), 404

    try:
        db.session.delete(item)
        db.session.commit()
        return jsonify({"ok": True, "message": f"Item {item_id} deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": f"Failed to delete item: {str(e)}"}), 500
