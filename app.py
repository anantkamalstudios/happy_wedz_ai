from flask import Flask, request, jsonify, send_file
import requests
import io
from PIL import Image
import os

# ---------------- Configuration ----------------
TRYON_API_KEY = os.getenv("TRYON_API_KEY", "ta_48b22e1d630f45cd8f492718fbe1b96d")
TRYON_API_URL = os.getenv("TRYON_API_URL", "https://tryon-api.com/api/v1")

app = Flask(__name__)

# ---------------- Helper: Ensure minimum size ----------------
def ensure_min_size(file_storage, min_size=(512, 512)):
    """Ensure uploaded image meets minimum size for Try-on API."""
    image = Image.open(file_storage.stream)
    if image.width < min_size[0] or image.height < min_size[1]:
        image = image.resize(min_size, Image.LANCZOS)
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        buf.seek(0)
        return ("resized.png", buf, "image/png")
    else:
        file_storage.stream.seek(0)
        return (file_storage.filename, file_storage.stream, file_storage.mimetype)


# ---------------- ROUTES ----------------

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Flask backend running"}), 200


@app.route("/tryon", methods=["POST"])
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
            f"{TRYON_API_URL}/tryon",
            headers={"Authorization": f"Bearer {TRYON_API_KEY}"},
            files=files,
            data=data,
        )

        if res.status_code not in [200, 202]:
            return jsonify({"error": res.text, "status": res.status_code}), res.status_code

        return jsonify(res.json()), res.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/status/<job_id>", methods=["GET"])
def get_status(job_id):
    """Poll Try-on API for job status."""
    try:
        res = requests.get(
            f"{TRYON_API_URL}/tryon/status/{job_id}",
            headers={"Authorization": f"Bearer {TRYON_API_KEY}"},
        )
        return jsonify(res.json()), res.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/view/<job_id>", methods=["GET"])
def view_result(job_id):
    """
    Return the current state of the job as JSON.
    If completed, includes the imageUrl and download link.
    """
    try:
        res = requests.get(
            f"{TRYON_API_URL}/tryon/status/{job_id}",
            headers={"Authorization": f"Bearer {TRYON_API_KEY}"}
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


@app.route("/download/<job_id>", methods=["GET"])
def download_result(job_id):
    """Download the result image from Try-on API once completed."""
    try:
        res = requests.get(
            f"{TRYON_API_URL}/tryon/status/{job_id}",
            headers={"Authorization": f"Bearer {TRYON_API_KEY}"},
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


# ---------------- MAIN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
