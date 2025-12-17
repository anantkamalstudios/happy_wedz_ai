from flask import Blueprint, request, jsonify, current_app
import cloudinary.uploader
import requests, time, io
from apps.try_on.core.extensions import db
from apps.try_on.models.models import Item, TryOnSession

clothes_bp = Blueprint("clothes", __name__, url_prefix="/api/tryon")

def multipart_fields_dict(d: dict):
    return {k: (None, str(v)) for k, v in d.items()}

def upload_result_to_cloudinary(image_url):
    """Download image from URL and upload to Cloudinary, return Cloudinary URL."""
    try:
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        image_data = io.BytesIO(response.content)
        up = cloudinary.uploader.upload(image_data, folder="tryon/results")
        return up["secure_url"]
    except Exception as e:
        current_app.logger.error(f"Failed to upload result image to Cloudinary: {e}")
        raise e

@clothes_bp.route("/clothes", methods=["POST"])
def tryon_clothes_start():
    cfg = current_app.config
    model_file = request.files.get("model_photo")
    item_id = request.form.get("item_id")
    item_url = request.form.get("item_url")
    clothing_type = request.form.get("clothing_type", "one-pieces").strip().lower()

    if not model_file:
        return jsonify({"error": "model_photo required"}), 400

    # Resolve item URL from DB if item_id is provided
    item = None
    if item_id:
        item = Item.query.get(item_id)
        if not item:
            return jsonify({"error": "item not found"}), 404
        item_url = item.image_url

    if not item_url:
        return jsonify({"error": "item_url or item_id required"}), 400

    # Upload model to Cloudinary
    try:
        up = cloudinary.uploader.upload(model_file, folder="tryon/models")
        model_url = up["secure_url"]
    except Exception as e:
        return jsonify({"error": f"Cloudinary upload failed: {e}"}), 500

    # Create DB session record
    session = TryOnSession(
        item_id=item.id if item else None,
        input_image_url=model_url,
        status="submitted"
    )
    db.session.add(session)
    db.session.commit()

    # Validate clothing_type
    valid_types = ["tops", "bottom", "one-pieces"]
    if clothing_type not in valid_types:
        clothing_type = "one-pieces"

    current_app.logger.info(f"Sending request to provider: model_photo={model_url}, clothing_photo={item_url}, clothing_type={clothing_type}")

    # Call provider
    fields = {
        "email": cfg.get("NEWBLACK_EMAIL"),
        "password": cfg.get("NEWBLACK_PASSWORD"),
        "model_photo": model_url,
        "clothing_photo": item_url,
        "clothing_type": clothing_type,
    }

    try:
        resp = requests.post(f"{cfg.get('NEWBLACK_API_BASE')}/vto", files=multipart_fields_dict(fields), timeout=30)
    except requests.RequestException as e:
        session.status = "failed"
        session.error_message = f"Provider request failed: {e}"
        db.session.commit()
        return jsonify({"error": "Failed contacting provider", "details": str(e)}), 502

    job_id = resp.text.strip()
    session.job_id = job_id
    session.status = "processing"
    db.session.commit()

    # Quick rejection check
    if not job_id or "inputs needed" in job_id.lower() or resp.status_code >= 400:
        session.status = "failed"
        session.error_message = job_id
        db.session.commit()
        return jsonify({"error": "API rejected input", "api_response": job_id}), 400

    # If provider returned direct URL immediately
    if job_id.startswith("http"):
        try:
            cloudinary_url = upload_result_to_cloudinary(job_id)
            session.result_image_url = cloudinary_url
        except Exception as e:
            session.status = "failed"
            session.error_message = f"Cloudinary upload failed: {e}"
            db.session.commit()
            return jsonify({"error": "Failed to upload result to Cloudinary", "details": str(e)}), 500
        session.status = "completed"
        db.session.commit()
        return jsonify({"ok": True, "status": "completed", "result": cloudinary_url, "session_id": str(session.id)}), 200

    # Poll results synchronously
    poll_interval = 5
    max_attempts = 36
    for attempt in range(max_attempts):
        time.sleep(poll_interval)
        try:
            r = requests.post(
                f"{cfg.get('NEWBLACK_API_BASE')}/results",
                files=multipart_fields_dict({
                    "email": cfg.get("NEWBLACK_EMAIL"),
                    "password": cfg.get("NEWBLACK_PASSWORD"),
                    "id": job_id
                }),
                timeout=15
            )
        except requests.RequestException as e:
            session.error_message = f"results request error: {e}"
            db.session.commit()
            continue

        txt = r.text.strip()
        current_app.logger.debug("Poll attempt %d: provider response: %s", attempt+1, txt[:300])

        if txt.startswith("http"):
            try:
                cloudinary_url = upload_result_to_cloudinary(txt)
                session.result_image_url = cloudinary_url
            except Exception as e:
                session.status = "failed"
                session.error_message = f"Cloudinary upload failed: {e}"
                db.session.commit()
                return jsonify({"error": "Failed to upload result to Cloudinary", "details": str(e)}), 500
            session.status = "completed"
            session.error_message = None
            db.session.commit()
            return jsonify({"ok": True, "status": "completed", "result": cloudinary_url, "session_id": str(session.id)}), 200

        lowered = txt.lower()
        if "inputs needed" in lowered or "insufficient" in lowered or "error" in lowered or "failed" in lowered:
            session.status = "failed"
            session.error_message = txt
            db.session.commit()
            return jsonify({"ok": False, "status": "failed", "provider_response": txt}), 400

    session.status = "timeout"
    session.error_message = f"timed out after {poll_interval * max_attempts} seconds"
    db.session.commit()
    return jsonify({"ok": False, "status": "timeout", "message": "Generation timed out"}), 504
