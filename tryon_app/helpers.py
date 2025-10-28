import io
from PIL import Image


def ensure_min_size(file_storage, min_size=(512, 512)):
    """Ensure uploaded image meets minimum size for Try-on API.

    Returns a tuple suitable for requests' files parameter: (filename, fileobj, mimetype)
    """
    # Open from stream without consuming original stream permanently
    image = Image.open(file_storage.stream)
    if image.width < min_size[0] or image.height < min_size[1]:
        image = image.resize(min_size, Image.LANCZOS)
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        buf.seek(0)
        return ("resized.png", buf, "image/png")
    else:
        # Reset stream pointer for safe reuse
        try:
            file_storage.stream.seek(0)
        except Exception:
            pass
        return (file_storage.filename, file_storage.stream, file_storage.mimetype)
