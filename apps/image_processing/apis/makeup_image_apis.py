from flask import Blueprint, request, jsonify, send_file, url_for
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw, ImageFilter, ImageChops
import io
from apps.image_processing.models.makeup_image_model import (
    db, UserImage, ImageType, CategoryEnum, Product, UserMakeupResultImage, ProductDetailedEnum
)
from apps.image_processing.core.makeup_image_core import (
    allowed_file, count_people, is_real_photo_strict, is_blurry, contains_person, is_full_body_front_facing, apply_lipstick, apply_blush, apply_eyeshadow, apply_contact_lenses, apply_primer, apply_foundation, apply_mascara, apply_eyeliner, apply_kajal, apply_concealer, apply_contour
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



images_bp = Blueprint("images", __name__, url_prefix="/api/images")
products_bp = Blueprint("products", __name__, url_prefix="/api/products")

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=True,
    model_complexity=2,
    enable_segmentation=False,
    min_detection_confidence=0.7
)
mp_face_mesh = mp.solutions.face_mesh

MAX_FILE_SIZE = 15 * 1024 * 1024


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

        feature = product.product_detailed_category.value.lower()

        intensity = float(payload.get(f"{feature}_intensity", 0.5))
        radius = int(payload.get(f"{feature}_radius", 50))
        thickness = int(payload.get(f"{feature}_thickness", 25))
        radius_scale = float(payload.get(f"{feature}_radius_scale", 1.0))

        hex_color = product.product_color_hex

        if feature == "lipstick":
            result = apply_lipstick(result, landmarks, hex_color, intensity)
        elif feature == "blush":
            result = apply_blush(result, landmarks, hex_color, intensity, radius)
        elif feature == "eyeshadow":
            result = apply_eyeshadow(result, landmarks, hex_color, intensity, thickness)
        elif feature in ["lenses", "contactlenses"]:
            result = apply_contact_lenses(result, lens_color=hex_color, lens_intensity=intensity, lens_radius_scale=radius_scale)
        elif feature == "primer":
            result = apply_primer(result, landmarks, hex_color, intensity)
        elif feature == "foundation":
            result = apply_foundation(result, landmarks, hex_color, intensity)
        elif feature == "mascara":
            result = apply_mascara(result, landmarks, intensity=1.0)
        elif feature == "eyeliner":
            result = apply_eyeliner(result, landmarks, intensity=1.0)
        elif feature == "kajal":
            result == apply_kajal(result, landmarks, intensity=1.0)
        elif feature == "concealer":
            h, w = result.shape[:2]
            result = apply_concealer(result, lm=landmarks, hw=(h, w))
        elif feature == "contour":
            h, w = result.shape[:2]
            result = apply_contour(result, lm=landmarks, hw=(h, w))

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
            "detailed_category": product.product_detailed_category.value
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

    fetch_url = url_for("images.get_image", image_id=new_img.id, _external=True)

    return jsonify({
        "processed_image_id": new_img.id,
        "url": fetch_url,
        "applied_products": stored_products
    }), 201


@products_bp.route("/filter_products", methods=["GET"])
def get_products():
    category = request.args.get("category")
    detailed_category = request.args.get("detailed_category")

    query = Product.query

    if category:
        try:
            category_enum = next(c for c in CategoryEnum if c.value.lower() == category.lower())
            query = query.filter_by(product_category=category_enum)
        except StopIteration:
            return jsonify({"error": "Invalid category"}), 400


    if detailed_category:
        try:
            detailed_enum = next(d for d in ProductDetailedEnum if d.value.lower() == detailed_category.lower())
            query = query.filter_by(product_detailed_category=detailed_enum)
        except StopIteration:
            return jsonify({"error": "Invalid detailed category"}), 400

    products = query.all()

    result = [
        {
            "id": p.id,
            "category": p.product_category.value,
            "detailed_category": p.product_detailed_category.value,
            "product_name": p.product_name,
            "brand_name": p.brand_name,
            "price": str(p.price),
            "product_real_image": f"data:{p.product_real_image_type};base64," + base64.b64encode(p.product_real_image).decode("utf-8"),
            "product_color_hex": p.product_color_hex,
            "description": p.description,
        }
        for p in products
    ]
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

    product = Product(
        product_category=request.form.get("product_category"),
        product_detailed_category=request.form.get("product_detailed_category"),
        product_name=request.form.get("product_name"),
        brand_name=request.form.get("brand_name"),
        price=request.form.get("price"),
        product_real_image=content,
        product_real_image_type=file.mimetype or "application/octet-stream",
        product_color_hex=request.form.get("product_color_hex"),
        description=request.form.get("description"),
    )

    db.session.add(product)
    db.session.commit()

    return jsonify({"id": product.id, "message": "Product created successfully"}), 201

