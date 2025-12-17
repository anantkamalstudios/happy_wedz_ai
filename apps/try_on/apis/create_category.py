from flask import request, jsonify,current_app, Blueprint
from apps.try_on.core.extensions import db
from apps.try_on.models.models import Item, TryOnSession,Category

create_category_bp = Blueprint("create_category",__name__, url_prefix="/api/create_category")
get_categories_bp = Blueprint("get_categories",__name__,url_prefix="/api/get_categories")

@get_categories_bp.route("/categories", methods=["GET"])
def get_categories():
    """
    Get all categories
    """
    try:
        categories = Category.query.all()
        category_list = [{"id": cat.id, "name": cat.name} for cat in categories]
        return jsonify({"categories": category_list}), 200
    except Exception as e:
        current_app.logger.exception("Failed to fetch categories")
        return jsonify({"error": f"Failed to fetch categories: {str(e)}"}), 500

@create_category_bp.route("/categories",methods=["POST"])
def create_category():
    """
    Create new Category for tryon
    """
    name = (request.json and request.json.get("name") or request.form.get("name"))
    if not name:
        return jsonify({"error":"Please give category name"}), 400
    
    name = name.strip().lower()
    existing = Category.query.filter_by(name=name).first()
    if existing:
        return jsonify({"error":"Category already exists","category_id":existing.id}), 400

    try:
        cat = Category(name=name)
        db.session.add(cat)
        db.session.commit()
        return jsonify({"message":"Category created","category_id":cat.id,"name":cat.name}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Failed to create category")
        return jsonify({"error": f"Failed to create category: {str(e)}"}), 500
    
@create_category_bp.route("/categories/<int:category_id>", methods=["DELETE"])
def delete_category(category_id):
    """
    Delete a category.
    Query params:
      - force=true  -> delete category and cascade delete items (if DB supports ON DELETE CASCADE)
    By default, deletion is blocked if items exist.
    """
    # if not require_token():
    #     return jsonify({"error": "unauthorized"}), 401

    cat = Category.query.get(category_id)
    if not cat:
        return jsonify({"error": "category not found"}), 404

    # check for items
    item_count = Item.query.filter_by(category_id=cat.id).count()
    force = request.args.get("force", "false").lower() in ("1", "true", "yes")

    if item_count > 0 and not force:
        return jsonify({
            "error": "category has items",
            "item_count": item_count,
            "message": "Pass ?force=true to delete the category and its items (if DB cascades)"
        }), 400

    try:
        # If DB has ON DELETE CASCADE, deleting category will remove items.
        db.session.delete(cat)
        db.session.commit()
        return jsonify({"ok": True, "message": f"Category {category_id} deleted", "deleted_items": item_count}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Failed to delete category")
        return jsonify({"error": f"Failed to delete category: {str(e)}"}), 500