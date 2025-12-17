import os
import io
import requests
from PIL import Image, ImageOps, ImageFilter, ImageEnhance

from config import Config

TRYON_API_KEY = Config.TRYON_API_KEY
TRYON_API_URL = Config.TRYON_API_URL


def _enhance_image(img: Image.Image) -> Image.Image:
    """Apply small, safe enhancements to improve perceived detail.

    - Autocontrast (small amount)
    - Slight sharpening (UnsharpMask)
    - Mild increase in color/contrast if image is very flat
    """
    try:
        img = ImageOps.autocontrast(img, cutoff=1)
    except Exception:
        pass

    # Gentle unsharp mask to bring out edges
    try:
        img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=120, threshold=3))
    except Exception:
        pass

    # Slightly boost sharpness and color for perceived detail
    try:
        sharp = ImageEnhance.Sharpness(img)
        img = sharp.enhance(1.15)

        color = ImageEnhance.Color(img)
        img = color.enhance(1.05)
    except Exception:
        pass

    return img


def prepare_image(upload_file, folder, name_prefix, min_dim=512, max_dim=4000):
    """
    Prepare image for try-on: accept any input size, normalize orientation and
    mode, upscale small images to meet minimum dimension requirements using
    high-quality resampling, and apply light enhancement to improve perceived
    detail. Returns path to a saved JPEG suitable for the upstream API.
    """
    os.makedirs(folder, exist_ok=True)
    temp_path = os.path.join(folder, upload_file.filename)
    upload_file.save(temp_path)

    img = Image.open(temp_path)
    img = ImageOps.exif_transpose(img)

    # Normalize to RGB (handle transparency by compositing on white)
    if img.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    else:
        img = img.convert("RGB")

    w, h = img.size

    # Compute scale so that both width and height meet min_dim and do not
    # exceed max_dim.
    scale_up = 1.0
    if w < min_dim or h < min_dim:
        scale_up = max(min_dim / w, min_dim / h)

    scale_down = 1.0
    if w > max_dim or h > max_dim:
        scale_down = min(max_dim / w, max_dim / h)

    # Choose the overall scale (either upscale small images or downscale large ones)
    scale = scale_up if scale_up > 1.0 else scale_down

    if scale != 1.0:
        new_size = (max(1, int(round(w * scale))), max(1, int(round(h * scale))))
        # If upscaling by a large factor, perform in one high-quality step using LANCZOS.
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    # Apply gentle enhancement to improve sharpness and color
    img = _enhance_image(img)

    jpg_path = os.path.join(folder, f"{name_prefix}.jpg")

    # Save with high JPEG quality and no chroma subsampling to preserve detail.
    img.save(
        jpg_path,
        format="JPEG",
        quality=95,          # higher quality for better detail
        subsampling=0,       # keep chroma detail
        optimize=True,
        progressive=True,
    )

    try:
        os.remove(temp_path)
    except Exception:
        pass

    return jpg_path


def submit_tryon(person_path, garment_path, mode="standard"):
    """Submit person and garment images to the upstream Try-on API.

    Returns the requests.Response object so callers can inspect status/code/body.
    """
    headers = {"Authorization": f"Bearer {TRYON_API_KEY}"}
    with open(person_path, "rb") as p, open(garment_path, "rb") as g:
        files = {
            "person_images": p,
            "garment_images": g,
        }
        resp = requests.post(f"{TRYON_API_URL}/tryon", headers=headers, files=files, data={"mode": mode})
    return resp


def get_status(job_id):
    headers = {"Authorization": f"Bearer {TRYON_API_KEY}"}
    resp = requests.get(f"{TRYON_API_URL}/tryon/status/{job_id}", headers=headers)
    return resp


def download_image_from_url(image_url, save_path):
    r = requests.get(image_url, timeout=15)
    r.raise_for_status()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(r.content)
    return save_path
