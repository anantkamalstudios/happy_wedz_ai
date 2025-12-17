import os
import base64
from flask import Flask, request, jsonify, send_from_directory, Blueprint, current_app

from  apps.outfit_tryon.core import outfit_tryon_logic as logic

# Do NOT import application-level config at module import time to avoid
# circular imports with config.create_app. Access config values via
# current_app.config inside request handlers (request context available).

outfit_tryon_bp = Blueprint("outfit_tryon", __name__, url_prefix="/api/outfit_tryon")

@outfit_tryon_bp.route("/tryon", methods=["POST"])
def tryon():
    try:
        # Accept both legacy names for convenience
        person = request.files.get("person_image") or request.files.get("person_images")
        garment = request.files.get("garment_image") or request.files.get("garment_images")
        if not person or not garment:
            return jsonify({"error": "Please upload both images"}), 400

        # Convert and resize
        upload_folder = current_app.config.get("UPLOAD_FOLDER")
        # Ensure upload dir exists (current_app is available inside request)
        if upload_folder:
            os.makedirs(upload_folder, exist_ok=True)

        person_path = logic.prepare_image(person, upload_folder, "person")
        garment_path = logic.prepare_image(garment, upload_folder, "garment")

        resp = logic.submit_tryon(person_path, garment_path)
        if resp.status_code != 202:
            return jsonify({"error": f"API Error {resp.status_code}", "details": resp.text}), resp.status_code

        job_id = resp.json().get("jobId")
        return jsonify({"message": "Job submitted", "job_id": job_id})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@outfit_tryon_bp.route("/status/<job_id>")
def check_status(job_id):
    try:
        resp = logic.get_status(job_id)
        data = resp.json()

        if data.get("status") == "completed":
            image_url = data.get("imageUrl")
            if image_url:
                result_folder = current_app.config.get("RESULT_FOLDER")
                if result_folder:
                    os.makedirs(result_folder, exist_ok=True)

                output_path = os.path.join(result_folder, f"{job_id}.jpg")
                if not os.path.exists(output_path):
                    logic.download_image_from_url(image_url, output_path)
                data["local_result"] = f"/results/{job_id}.jpg"

                # Read the saved image and include a base64 payload in the
                # status response so clients (Postman or frontends) can
                # directly display the image without an extra request.
                try:
                    with open(output_path, "rb") as f:
                        img_bytes = f.read()
                    data["image_base64"] = base64.b64encode(img_bytes).decode("ascii")
                except Exception:
                    # If reading fails, skip embedding base64 but keep local_result
                    pass

        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@outfit_tryon_bp.route("/results/<filename>")
def serve_result(filename):
    result_folder = current_app.config.get("RESULT_FOLDER")
    return send_from_directory(result_folder, filename)

@outfit_tryon_bp.route("/download/<job_id>")
def download_result(job_id):
    filename = f"{job_id}.jpg"
    result_folder = current_app.config.get("RESULT_FOLDER")
    local_path = os.path.join(result_folder, filename)

    # If file missing locally, try to fetch from upstream
    if not os.path.exists(local_path):
        resp = logic.get_status(job_id)
        if resp.status_code != 200:
            return jsonify({"error": "job not found or upstream error"}), 404

        data = resp.json()
        image_url = data.get("imageUrl")
        if not image_url:
            return jsonify({"error": "no image available for this job yet"}), 404

        try:
            logic.download_image_from_url(image_url, local_path)
        except Exception as e:
            return jsonify({"error": f"failed to fetch image: {e}"}), 502

    return send_from_directory(result_folder, filename, as_attachment=True)
