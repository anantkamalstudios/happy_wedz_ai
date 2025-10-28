from flask import Blueprint, request, jsonify, send_file, current_app
import requests
import io
from datetime import datetime
from PIL import Image

from apps.image_processing.core.makeup_image_core import is_real_photo_strict, contains_person, is_full_body_front_facing
from apps.image_processing.models.makeup_image_model import db, UserImage, ImageType
from ..core.helpers import ensure_min_size

tryon_bp = Blueprint("tryon", __name__)


@tryon_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Flask backend running"}), 200


@tryon_bp.route("/tryon", methods=["POST"])
def tryon():
    """Start a virtual try-on job using form-data upload."""
    if "person_images" not in request.files or "garment_images" not in request.files:
        return jsonify({"error": "Missing files: person_images and garment_images required"}), 400

    person_images = request.files.getlist("person_images")
    garment_images = request.files.getlist("garment_images")

    # Process and validate images
    try:
        person_data = []
        for img in person_images:
            img_bytes = img.read()
            
            # Validate person image using existing utilities
            image = Image.open(io.BytesIO(img_bytes))
            if not is_real_photo_strict(image):
                return jsonify({"error": "Invalid person image: Must be a real photograph"}), 400
            if not contains_person(image):
                return jsonify({"error": "Invalid person image: No person detected"}), 400
            if not is_full_body_front_facing(image):
                return jsonify({"error": "Invalid person image: Please provide a full-body, front-facing photo"}), 400
            
            # Save to database
            processed_img = ensure_min_size(img_bytes)
            user_image = UserImage(
                image_type=ImageType.TRYON_PERSON,
                image_data=processed_img,
                created_at=datetime.utcnow()
            )
            db.session.add(user_image)
            person_data.append(processed_img)

        garment_data = []
        for img in garment_images:
            img_bytes = img.read()
            processed_img = ensure_min_size(img_bytes)
            
            # Save to database
            user_image = UserImage(
                image_type=ImageType.TRYON_GARMENT,
                image_data=processed_img,
                created_at=datetime.utcnow()
            )
            db.session.add(user_image)
            garment_data.append(processed_img)
        
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

    # Call the virtual try-on service
    try:
        headers = {"Accept": "application/json"}
        tryon_url = current_app.config["TRYON_SERVICE_URL"]
        
        files = []
        for i, img_data in enumerate(person_data):
            files.append(("person", (f"person_{i}.jpg", img_data, "image/jpeg")))
        for i, img_data in enumerate(garment_data):
            files.append(("cloth", (f"garment_{i}.jpg", img_data, "image/jpeg")))

        response = requests.post(tryon_url, files=files, headers=headers)
        
        if response.status_code != 200:
            return jsonify({"error": f"Try-on service error: {response.text}"}), 500

        # Return the processed image
        img_data = response.content
        return send_file(
            io.BytesIO(img_data),
            mimetype="image/jpeg",
            as_attachment=True,
            download_name="tryon_result.jpg"
        )

    except Exception as e:
        return jsonify({"error": f"Try-on service error: {str(e)}"}), 500