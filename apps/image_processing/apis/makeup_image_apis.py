from flask import Blueprint, request, jsonify, send_file, url_for
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw, ImageFilter, ImageChops
import io
from apps.image_processing.models.makeup_image_model import (
    db, UserImage, ImageType, CategoryEnum, Product, UserMakeupResultImage, ProductDetailedCategory
)
from apps.image_processing.core.makeup_image_core import (
    allowed_file, count_people, is_real_photo_strict, is_blurry, contains_person, is_full_body_front_facing, apply_lipstick, apply_blush, apply_eyeshadow, apply_contact_lenses, apply_foundation, apply_mascara, apply_kajal, apply_concealer, apply_contour
)
from apps.image_processing.core.jwellery_image_core import (
    apply_bindi, apply_mangtika
)
from ultralytics import YOLO
import mediapipe as mp
import cv2
import numpy as np
import face_recognition
import base64
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from datetime import datetime
from reportlab.lib.utils import ImageReader
from torch import nn
import torch
from transformers import SegformerImageProcessor, SegformerForSemanticSegmentation
import tempfile
import os
from PIL import Image, ImageDraw, ImageFilter, ImageChops
import json
import logging
from io import BytesIO



images_bp = Blueprint("images", __name__, url_prefix="/api/images")
products_bp = Blueprint("products", __name__, url_prefix="/api/products")
product_categories_bp = Blueprint("product_categories", __name__, url_prefix="/api/product_categories")

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=True,
    model_complexity=2,
    enable_segmentation=False,
    min_detection_confidence=0.7
)
mp_face_mesh = mp.solutions.face_mesh

MAX_FILE_SIZE = 5 * 1024 * 1024


def resize_image_bytes(image_bytes, max_size=300, quality=40):
    try:
        image = Image.open(BytesIO(image_bytes))

        # Convert to RGB (to remove alpha/transparency and unify format)
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Resize keeping aspect ratio
        image.thumbnail((max_size, max_size))

        # Save to in-memory buffer
        output = BytesIO()
        image.save(output, format="JPEG", quality=quality, optimize=True)
        return output.getvalue()

    except Exception as e:
        print("⚠️ Image normalization failed:", e)
        return image_bytes  # fallback (send original)



# POST /api/images  -> upload & store in DB
@images_bp.route("", methods=["POST"])
def upload_image():
    if "image" not in request.files:
        return jsonify({"error": "image file is required"}), 400

    file = request.files["image"]
    if not file or file.filename == "":
        return jsonify({"error": "empty filename"}), 400

    if not allowed_file(file.filename):
        return jsonify(
            {
                "error": (
                    "unsupported file format. "
                    "Allowed formats are jpg, jpeg, png, gif, webp"
                )
            }
        ), 400

    filename = secure_filename(file.filename)
    content = file.read()

    if len(content) > MAX_FILE_SIZE:
        return jsonify(
            {
                "error": (
                    f"file too large. Max allowed size is "
                    f"{MAX_FILE_SIZE // (1024*1024)} MB"
                )
            }
        ), 400

    # Step 1: Is it a real photo?
    if not is_real_photo_strict(content):
        return jsonify({"error": "Only real photographs are accepted. Please upload a genuine photo, not an illustration, drawing, or AI-generated image."}), 400

    # Step 2: Is it blurry?
    if is_blurry(content):
        return jsonify({"error": "Image is too blurry. Please upload a clear, sharp photo for better results."}), 400

    # Step 3: Does it contain a person?
    if not contains_person(content):
        return jsonify({"error": "Image must contain a human"}), 400

    # Step 4: Does it contain more than one person?
    people_count = count_people(content)
    if people_count > 1:
        return jsonify({"error": f"Multiple people detected ({people_count}). Please upload image with only one person"}), 400

    # Step 5: Does it contain full body and is it front facing
    # is_valid, message = is_full_body_front_facing(content)
    # if not is_valid:
    #     return jsonify({"error": message}), 400
    
    image_type = request.form.get("image_type")

    img = UserImage(
        filename=filename,
        content_type=file.mimetype or "application/octet-stream",
        size_bytes=len(content),
        data=content,
        image_type=image_type
    )
    db.session.add(img)
    db.session.commit()

    return jsonify({
        "id": img.id,
        "filename": img.filename,
        "size_bytes": img.size_bytes,
        "content_type": img.content_type
    }), 201


# GET /api/images/<id>  -> fetch the stored image
@images_bp.route("/<int:image_id>", methods=["GET"])
def get_image(image_id):
    img = UserImage.query.get_or_404(image_id)

    buf = io.BytesIO(img.data)

    return send_file(
        buf,
        mimetype=img.content_type,
        as_attachment=False,
        download_name=img.filename
    )


@images_bp.route("/apply-makeup", methods=["POST"])
def apply_makeup_api():
    try:
        payload = request.get_json(silent=True) or {}
        image_id = payload.get("image_id")
        product_ids = payload.get("product_ids", [])
        
    
        if not image_id or not product_ids:
            return jsonify({"error": "image_id and product_ids are required"}), 400
    
        img_row = UserImage.query.get(image_id)
        if not img_row:
            return jsonify({"error": "image not found"}), 404
    
        nparr = np.frombuffer(img_row.data, np.uint8)
        original_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if original_img is None:
            return jsonify({"error": "failed to decode image"}), 400
    
        rgb_img = cv2.cvtColor(original_img, cv2.COLOR_BGR2RGB)
        face_landmarks_list = face_recognition.face_landmarks(rgb_img)
        if not face_landmarks_list:
            return jsonify({"error": "no face detected"}), 400
    
        landmarks = face_landmarks_list[0]
        result = original_img.copy()
        stored_products = []
    
        for product_id in product_ids:
            product = Product.query.get(product_id)
            if not product:
                return jsonify({"error": f"Product not found: {product_id}"}), 404
    
            feature = product.detailed_category.name.lower()
    
            intensity = float(payload.get(f"{feature}_intensity", 0.5))
            radius = int(payload.get(f"{feature}_radius", 50))
            thickness = int(payload.get(f"{feature}_thickness", 25))
            radius_scale = float(payload.get(f"{feature}_radius_scale", 1.0))
            hex_color = payload.get(f"{feature}_color")
            bindi_size = int(payload.get("bindi_size", 6))
            # hex_color = product.product_colors
    
            if feature == "lipstick":
                result = apply_lipstick(result, landmarks, hex_color, intensity)
            elif feature == "blush":
                result = apply_blush(result, landmarks, hex_color, intensity, radius)
            elif feature == "eyeshadow":
                result = apply_eyeshadow(result, landmarks, hex_color, intensity, thickness)
            elif feature in ["lenses", "contactlenses"]:
                result = apply_contact_lenses(result, lens_color=hex_color, lens_intensity=intensity, lens_radius_scale=radius_scale)
            # elif feature == "primer":
            #     result = apply_primer(result, landmarks, hex_color, intensity)
            elif feature == "foundation":
                result = apply_foundation(result, landmarks, hex_color, intensity)
            elif feature == "mascara":
                result = apply_mascara(result, landmarks, intensity=1.0)
            elif feature == "kajal":
                result = apply_kajal(result, kajal_color_hex=hex_color, intensity=intensity)
            elif feature == "concealer":
                result = apply_concealer(result, intensity=intensity, color_hex=hex_color)
            elif feature == "contour":
                result = apply_contour(result, intensity=intensity, color_hex=hex_color)
            elif feature == "bindi":
                result = apply_bindi(result, size=bindi_size, color_hex=hex_color)
            elif feature == "mangtika":
                result = apply_mangtika(result, product.product_real_image, scale_factor=0.8)
    
            user_makeup_entry = UserMakeupResultImage(
                result_image_id=image_id,
                result_product_id=product.id
            )
            db.session.add(user_makeup_entry)
            db.session.flush()
    
            stored_products.append({
                    "product_id": product.id,
                    "processed_image_id": user_makeup_entry.id,
                    "hex_color": hex_color,
                    "detailed_category": product.detailed_category.name
                })
    
        ok, buf = cv2.imencode(".png", result)
        if not ok:
            return jsonify({"error": "failed to encode result"}), 500
    
        new_data = buf.tobytes()
        new_img = UserImage(
            filename=f"{image_id}_makeup.png",
            content_type="image/png",
            size_bytes=len(new_data),
            data=new_data,
            image_type=ImageType.RESULT
        )
        db.session.add(new_img)
        db.session.commit()
    
        fetch_url = f"https://www.happywedz.com/ai/api/images/{new_img.id}"
    
        return jsonify({
            "processed_image_id": new_img.id,
            "url": fetch_url,
            "applied_products": stored_products
        }), 201
    except Exception as e:
        # Logs request payload + full stack trace
        logging.error(
            "Error in /apply-makeup API. Payload=%s",
            payload,
            exc_info=True
        )
        return jsonify({"error": "Internal server error"}), 500


@products_bp.route("/filter_products", methods=["GET"])
def get_products():
    category = request.args.get("category")
    detailed_category = request.args.get("detailed_category")
    user = request.args.get("user")  # 'bride' or 'groom'

    query = ProductDetailedCategory.query

    # ---- Filter by main category (MAKEUP / JWELLERY) ----
    if category:
        try:
            category_enum = next(c for c in CategoryEnum if c.value.lower() == category.lower())
            query = query.join(Product).filter(Product.product_category == category_enum)
        except StopIteration:
            return jsonify({"error": "Invalid category"}), 400

    # ---- Filter by detailed category ----
    if detailed_category:
        query = query.filter(ProductDetailedCategory.name.ilike(detailed_category))

    # ---- User-specific product filtering ----
    if user:
        user = user.lower()
        if user not in ["bride", "groom"]:
            return jsonify({"error": "Invalid user type. Must be 'bride' or 'groom'."}), 400

        if user == "groom":
            allowed_groom_categories = [
                "foundation",
                "concealer",
                "contactlenses",
                "lipbalm"
            ]
            query = query.filter(
                db.func.lower(ProductDetailedCategory.name).in_(allowed_groom_categories)
            )

    detailed_categories = query.all()
    result = []

    # ---- Build response ----
    for dc in detailed_categories:
        products_list = []
        for p in dc.products:
            compressed_image = resize_image_bytes(p.product_real_image)

            products_list.append({
                "id": p.id,
                "product_name": p.product_name,
                "brand_name": p.brand_name,
                "price": str(p.price),
                "product_colors": p.product_colors,
                "description": p.description,
                "product_real_image": (
                    f"data:{p.product_real_image_type};base64,"
                    + base64.b64encode(compressed_image).decode("utf-8")
                ),
            })

        if dc.image:
            compressed_dc_image = resize_image_bytes(dc.image)
            dc_image_base64 = (
                f"data:image/jpeg;base64,"
                + base64.b64encode(compressed_dc_image).decode("utf-8")
            )
        else:
            dc_image_base64 = None

        result.append({
            "product_detailed_category_name": dc.name,
            "product_detailed_image": dc_image_base64,
            "products": products_list
        })

    return jsonify(result), 200


@products_bp.route("/store_products", methods=["POST"])
def create_product():
    if "product_real_image" not in request.files:
        return jsonify({"error": "Product real image is required"}), 400

    file = request.files["product_real_image"]
    if not file or file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Unsupported file format"}), 400

    filename = secure_filename(file.filename)
    content = file.read()

    if len(content) > MAX_FILE_SIZE:
        return jsonify({"error": f"File too large. Max {MAX_FILE_SIZE//(1024*1024)} MB"}), 400
    colors_str = request.form.get("product_colors")
    product_colors = json.loads(colors_str) if colors_str else []

    category_id = int(request.form.get("product_detailed_category_id"))  # frontend sends id
    detailed_category = ProductDetailedCategory.query.get(category_id)
    if not detailed_category:
        return jsonify({"error": "Invalid detailed category ID"}), 400
    # print(request.form.get("product_category"))
    product = Product(
        product_category=request.form.get("product_category"),
        detailed_category=detailed_category,   # link to new model
        product_name=request.form.get("product_name"),
        brand_name=request.form.get("brand_name"),
        price=request.form.get("price"),
        product_real_image=content,
        product_real_image_type=file.mimetype or "application/octet-stream",
        product_colors=product_colors,
        description=request.form.get("description"),
    )

    db.session.add(product)
    db.session.commit()

    return jsonify({"id": product.id, "message": "Product created successfully"}), 201


@product_categories_bp.route("/create_category", methods=["POST"])
def create_product_detailed_category():
    name = request.form.get("name")
    if not name:
        return jsonify({"error": "Category name is required"}), 400

    # Check if name already exists
    existing = ProductDetailedCategory.query.filter_by(name=name).first()
    if existing:
        return jsonify({"error": "Category with this name already exists"}), 400

    image_data = None
    image_type = None

    if "image" in request.files:
        file = request.files["image"]
        if file.filename != "":
            if not allowed_file(file.filename):
                return jsonify({"error": "Unsupported file format"}), 400
            content = file.read()
            if len(content) > MAX_FILE_SIZE:
                return jsonify({"error": f"File too large. Max {MAX_FILE_SIZE // (1024*1024)} MB"}), 400
            image_data = content
            image_type = file.mimetype or "application/octet-stream"

    category = ProductDetailedCategory(
        name=name,
        image=image_data,
        image_type=image_type
    )

    db.session.add(category)
    db.session.commit()

    return jsonify({
        "id": category.id,
        "name": category.name,
        "message": "Product detailed category created successfully"
    }), 201