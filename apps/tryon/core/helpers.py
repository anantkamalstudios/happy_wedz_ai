import io
from PIL import Image

def ensure_min_size(image_bytes, min_size=512):
    """Ensure image meets minimum size requirements."""
    img = Image.open(io.BytesIO(image_bytes))
    width, height = img.size
    
    if width < min_size or height < min_size:
        scale = max(min_size / width, min_size / height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        img = img.resize((new_width, new_height), Image.LANCZOS)
    
    # Convert to RGB if necessary
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Save to bytes
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=95)
    return output.getvalue()