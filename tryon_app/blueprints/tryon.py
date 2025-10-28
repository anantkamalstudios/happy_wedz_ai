from flask import Blueprint, request, jsonify, send_file, current_app
import requests
import io

from ..helpers import ensure_min_size

tryon_bp = Blueprint("tryon", __name__)


@tryon_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Flask backend running"}), 200


@tryon_bp.route("/tryon", methods=["POST"])
def tryon():
    """Start a virtual try-on job using form-data upload."""
    if "person_images" not in request.files or "garment_images" not in request.files:
        return jsonify({"error": "Missing files: person_images and garment_images required"}), 400

    person_f = request.files["person_images"]
    garment_f = request.files["garment_images"]
    fast_mode = request.form.get("fast_mode", "true")

    # Resize if needed
    person_file = ensure_min_size(person_f)
    garment_file = ensure_min_size(garment_f)

    files = {
        "person_images": person_file,
        "garment_images": garment_file,
    }

    data = {"fast_mode": fast_mode}

    try:
        # POST to Try-on API
        res = requests.post(
            f"{current_app.config['TRYON_API_URL']}/tryon",
            headers={"Authorization": f"Bearer {current_app.config['TRYON_API_KEY']}"},
            files=files,
            data=data,
        )

        if res.status_code not in [200, 202]:
            return jsonify({"error": res.text, "status": res.status_code}), res.status_code

        return jsonify(res.json()), res.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tryon_bp.route("/status/<job_id>", methods=["GET"])
def get_status(job_id):
    """Poll Try-on API for job status."""
    try:
        res = requests.get(
            f"{current_app.config['TRYON_API_URL']}/tryon/status/{job_id}",
            headers={"Authorization": f"Bearer {current_app.config['TRYON_API_KEY']}"},
        )
        return jsonify(res.json()), res.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tryon_bp.route("/view/<job_id>", methods=["GET"])
def view_result(job_id):
    """Return the current state of the job as JSON."""
    try:
        res = requests.get(
            f"{current_app.config['TRYON_API_URL']}/tryon/status/{job_id}",
            headers={"Authorization": f"Bearer {current_app.config['TRYON_API_KEY']}"}
        )

        if res.status_code != 200:
            return jsonify({"error": res.text, "status": res.status_code}), res.status_code

        data = res.json()
        response = {
            "job_id": job_id,
            "status": data.get("status"),
            "image_url": data.get("imageUrl"),
            "download_url": f"/download/{job_id}" if data.get("status") == "completed" else None,
            "message": data.get("message", ""),
        }

        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tryon_bp.route("/download/<job_id>", methods=["GET"])
def download_result(job_id):
    """Download the result image from Try-on API once completed."""
    try:
        res = requests.get(
            f"{current_app.config['TRYON_API_URL']}/tryon/status/{job_id}",
            headers={"Authorization": f"Bearer {current_app.config['TRYON_API_KEY']}"},
        )

        if res.status_code != 200:
            return jsonify({"error": res.text, "status": res.status_code}), res.status_code

        data = res.json()
        if data.get("status") != "completed" or not data.get("imageUrl"):
            return jsonify({"message": f"Job {job_id} not completed yet", "status": data.get('status')}), 200

        # Download image
        img_res = requests.get(data["imageUrl"])
        if img_res.status_code != 200:
            return jsonify({"error": "Failed to fetch result image"}), 500

        # Serve as downloadable file
        return send_file(
            io.BytesIO(img_res.content),
            mimetype="image/png",
            as_attachment=True,
            download_name=f"tryon_result_{job_id}.png",
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500
