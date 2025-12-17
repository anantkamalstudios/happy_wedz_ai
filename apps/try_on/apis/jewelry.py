# apis/jewelry.py
from flask import Blueprint, request, jsonify, current_app
import cloudinary.uploader
import requests, time, io
from apps.try_on.core.extensions import db
from apps.try_on.models.models import Item, TryOnSession

jewelry_bp = Blueprint("jewelry", __name__, url_prefix="/api/tryon")

def multipart_fields_dict(d: dict):
    return {k: (None, str(v)) for k, v in d.items()}

def upload_result_to_cloudinary(image_url):
    """Download image from URL and upload to Cloudinary, return Cloudinary URL."""
    try:
        # Download the image
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        image_data = io.BytesIO(response.content)

        # Upload to Cloudinary
        up = cloudinary.uploader.upload(image_data, folder="tryon/results")
        return up["secure_url"]
    except Exception as e:
        current_app.logger.error(f"Failed to upload result image to Cloudinary: {e}")
        raise e

@jewelry_bp.route("/jewelry", methods=["POST"])
def tryon_jewelry_start():
    cfg = current_app.config
    model_file = request.files.get("model_photo")
    item_id = request.form.get("item_id")
    item_url = request.form.get("item_url")
    description = request.form.get("description", "Stylish jewelry")

    if not model_file:
        return jsonify({"error": "model_photo required"}), 400

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

    # create DB session record (status submitted)
    session = TryOnSession(item_id=item.id if item else None, input_image_url=model_url, status="submitted")
    db.session.add(session)
    db.session.commit()

    # call provider to start job
    fields = {
        "email": cfg.get("NEWBLACK_EMAIL"),
        "password": cfg.get("NEWBLACK_PASSWORD"),
        "model_photo": model_url,
        "jewelry_photo": item_url,
        "description": description,
    }

    try:
        resp = requests.post(f"{cfg.get('NEWBLACK_API_BASE')}/vto-jewelry", files=multipart_fields_dict(fields), timeout=30)
    except requests.RequestException as e:
        session.status = "failed"
        session.error_message = f"Provider request failed: {e}"
        db.session.commit()
        return jsonify({"error": "Failed contacting provider", "details": str(e)}), 502

    text = (resp.text or "").strip()
    current_app.logger.debug("vto-jewelry response: status=%s body=%s", resp.status_code, text[:400])

    # quick rejection check / immediate image
    lowered = text.lower()
    if text.startswith("http"):
        try:
            cloudinary_url = upload_result_to_cloudinary(text)
            session.result_image_url = cloudinary_url
        except Exception as e:
            session.status = "failed"
            session.error_message = f"Cloudinary upload failed: {e}"
            db.session.commit()
            return jsonify({"error": "Failed to upload result to Cloudinary", "details": str(e)}), 500
        session.status = "completed"
        session.job_id = None
        session.error_message = None
        db.session.commit()
        current_app.logger.info(f"Session {session.id} committed with result {session.result_image_url}")
        return jsonify({"ok": True, "status": "completed", "result": cloudinary_url, "session_id": str(session.id)}), 200

    if resp.status_code >= 400 or "inputs needed" in lowered or "insufficient" in lowered or "please provide a valid id" in lowered or "error" in lowered:
        session.status = "failed"
        session.job_id = None
        session.error_message = text
        db.session.commit()
        return jsonify({"ok": False, "status": "failed", "provider_response": text}), 400

    # otherwise treat text as job id (store and poll). If it's malformed later, results call will surface it.
    job_id = text
    session.job_id = job_id
    session.status = "processing"
    db.session.commit()

    # --- Poll results synchronously every 5 seconds ---
    poll_interval = 5       # seconds
    max_attempts = 36       # 36*5 = 180s (3 minutes)
    for attempt in range(max_attempts):
        time.sleep(poll_interval)
        try:
            r = requests.post(
                f"{cfg.get('NEWBLACK_API_BASE')}/results",
                files=multipart_fields_dict({
                    "email": cfg.get("NEWBLACK_EMAIL"),
                    "password": cfg.get("NEWBLACK_PASSWORD"),
                    "id": session.job_id
                }),
                timeout=15
            )
        except requests.RequestException as e:
            # log error into session and continue (network hiccup)
            session.error_message = f"results request error: {e}"
            db.session.commit()
            current_app.logger.warning("Results request exception on attempt %d: %s", attempt+1, e)
            continue

        txt = (r.text or "").strip()
        current_app.logger.debug("Jewelry poll attempt %d: status=%s body=%s", attempt+1, r.status_code, txt[:400])

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
            current_app.logger.info(f"Session {session.id} committed with result {session.result_image_url}")
            return jsonify({"ok": True, "status": "completed", "result": cloudinary_url, "session_id": str(session.id)}), 200

        lowered = txt.lower()
        # provider returned explicit rejection or error -> fail early
        if "inputs needed" in lowered or "please provide a valid id" in lowered or "invalid" in lowered or "insufficient" in lowered or "error" in lowered or "failed" in lowered:
            session.status = "failed"
            session.error_message = txt
            db.session.commit()
            return jsonify({"ok": False, "status": "failed", "provider_response": txt}), 400

        # otherwise keep looping until attempts exhausted

    # final timeout
    session.status = "timeout"
    session.error_message = f"timed out after {poll_interval * max_attempts} seconds"
    db.session.commit()
    return jsonify({"ok": False, "status": "timeout", "message": "Generation timed out"}), 504
