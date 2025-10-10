import cv2
import mediapipe as mp
from rembg import remove
import numpy as np
from PIL import Image
import io


def apply_bindi(image, color_hex="#FF0000", size=6):
    # Convert hex color to BGR
    color_hex = color_hex.lstrip("#")
    r, g, b = tuple(int(color_hex[i:i+2], 16) for i in (0, 2, 4))
    bindi_color = (b, g, r)  # OpenCV uses BGR

    # Prepare Mediapipe face mesh
    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=True
    )

    # Mediapipe expects RGB
    rgb_img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_img)
    output = image.copy()

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            h, w, _ = rgb_img.shape

            # Eyebrow landmarks
            left_eyebrow = face_landmarks.landmark[65]
            right_eyebrow = face_landmarks.landmark[295]

            # Pixel coordinates
            lx, ly = int(left_eyebrow.x * w), int(left_eyebrow.y * h)
            rx, ry = int(right_eyebrow.x * w), int(right_eyebrow.y * h)

            # Midpoint between eyebrows
            cx, cy = (lx + rx) // 2, (ly + ry) // 2

            # Draw the bindi
            cv2.circle(output, (cx, cy), size, bindi_color, -1)

    face_mesh.close()
    return output



# def apply_mangtika(user_img: np.ndarray, mangtika_img_bytes: bytes, scale_factor: float = 0.8) -> np.ndarray:
#     jewelry_img = Image.open(io.BytesIO(mangtika_img_bytes)).convert("RGBA")
#     jewelry_np = np.array(jewelry_img)  # RGBA
#     # -------------------------

#     # -------------------------
#     # Optional: remove very dark inner pixels without changing color
#     alpha = jewelry_np[:, :, 3].copy()
#     black_mask = np.all(jewelry_np[:, :, :3] < 20, axis=2)
#     alpha[black_mask] = 0
#     jewelry_np[:, :, 3] = alpha
#     # -------------------------

#     # -------------------------
#     # Convert RGB → BGR to match user image
#     jewelry_np[:, :, :3] = jewelry_np[:, :, :3][:, :, ::-1]
#     # -------------------------

#     # -------------------------
#     # Detect forehead center using Mediapipe
#     mp_face_mesh = mp.solutions.face_mesh
#     with mp_face_mesh.FaceMesh(static_image_mode=True) as face_mesh:
#         rgb_user = cv2.cvtColor(user_img, cv2.COLOR_BGR2RGB)
#         results = face_mesh.process(rgb_user)
#         if not results.multi_face_landmarks:
#             raise ValueError("No face detected in user image!")

#         face_landmarks = results.multi_face_landmarks[0]
#         h, w, _ = user_img.shape
#         left_eye_inner = face_landmarks.landmark[33]
#         right_eye_inner = face_landmarks.landmark[263]

#         # Forehead center (slightly above eyes)
#         center_x = int((left_eye_inner.x + right_eye_inner.x) / 2 * w) + 10
#         center_y = int((left_eye_inner.y + right_eye_inner.y) / 2 * h) - int(0.15 * h)
#     # -------------------------

#     # -------------------------
#     # Resize jewelry relative to face width
#     jewelry_h, jewelry_w = jewelry_np.shape[:2]
#     face_width = int(abs(right_eye_inner.x - left_eye_inner.x) * w)
#     new_w = int(jewelry_w * scale_factor * face_width / jewelry_w)
#     new_h = int(jewelry_h * scale_factor * face_width / jewelry_w)
#     jewelry_resized = cv2.resize(jewelry_np, (new_w, new_h), interpolation=cv2.INTER_AREA)
#     # -------------------------

#     # -------------------------
#     # Overlay jewelry on user image
#     overlay = user_img.copy()
#     x1 = center_x - new_w // 2
#     y1 = center_y - new_h // 2
#     x2 = x1 + new_w
#     y2 = y1 + new_h

#     # Ensure coordinates within bounds
#     x1, y1 = max(0, x1), max(0, y1)
#     x2, y2 = min(w, x2), min(h, y2)

#     alpha_j = jewelry_resized[:, :, 3] / 255.0
#     for c in range(3):
#         overlay[y1:y2, x1:x2, c] = (
#             alpha_j[:y2 - y1, :x2 - x1] * jewelry_resized[:y2 - y1, :x2 - x1, c]
#             + (1 - alpha_j[:y2 - y1, :x2 - x1]) * overlay[y1:y2, x1:x2, c]
#         )
#     # -------------------------

#     return overlay



# import io
# import cv2
# import numpy as np
# from PIL import Image
# from rembg import remove
# import mediapipe as mp



# def apply_mangtika(user_img: np.ndarray, mangtika_img_bytes: bytes, scale_factor: float = 0.8) -> np.ndarray:
#     """
#     Places a mangtika (forehead jewelry) on the user's image after removing its background.

#     Args:
#         user_img: BGR numpy image (OpenCV format).
#         mangtika_img_bytes: Raw image bytes of the jewelry (any background) or PIL Image bytes.
#         scale_factor: Relative scale of the jewelry compared to face width.

#     Returns:
#         overlayed image as a BGR numpy array.
#     """

#     # -------------------------
#     # ✅ 1️⃣ Ensure valid image bytes
#     try:
#         # Try opening directly
#         Image.open(io.BytesIO(mangtika_img_bytes))
#         valid_bytes = mangtika_img_bytes
#     except (OSError, ValueError):
#         # If mangtika_img_bytes is raw pixel data or PIL image, convert to PNG bytes
#         if isinstance(mangtika_img_bytes, Image.Image):
#             buf = io.BytesIO()
#             mangtika_img_bytes.save(buf, format="PNG")
#             valid_bytes = buf.getvalue()
#         else:
#             raise ValueError("Invalid jewelry image bytes provided!")
#     # -------------------------

#     # -------------------------
#     # ✅ 2️⃣ Remove background from mangtika
#     clean_bytes = remove(valid_bytes)  # returns PNG bytes with transparent background
#     jewelry_img = Image.open(io.BytesIO(clean_bytes)).convert("RGBA")
#     jewelry_np = np.array(jewelry_img)  # RGBA
#     # -------------------------

#     # -------------------------
#     # ✅ 3️⃣ Convert RGB → BGR to match OpenCV user image
#     jewelry_np[:, :, :3] = jewelry_np[:, :, :3][:, :, ::-1]
#     # -------------------------

#     # -------------------------
#     # ✅ 4️⃣ Detect forehead center using Mediapipe
#     mp_face_mesh = mp.solutions.face_mesh
#     with mp_face_mesh.FaceMesh(static_image_mode=True) as face_mesh:
#         rgb_user = cv2.cvtColor(user_img, cv2.COLOR_BGR2RGB)
#         results = face_mesh.process(rgb_user)
#         if not results.multi_face_landmarks:
#             raise ValueError("No face detected in user image!")

#         face_landmarks = results.multi_face_landmarks[0]
#         h, w, _ = user_img.shape
#         left_eye_inner = face_landmarks.landmark[33]
#         right_eye_inner = face_landmarks.landmark[263]

#         # Forehead center (slightly above eyes)
#         center_x = int((left_eye_inner.x + right_eye_inner.x) / 2 * w) + 10
#         center_y = int((left_eye_inner.y + right_eye_inner.y) / 2 * h) - int(0.15 * h)
#     # -------------------------

#     # -------------------------
#     # ✅ 5️⃣ Resize jewelry relative to face width
#     jewelry_h, jewelry_w = jewelry_np.shape[:2]
#     face_width = int(abs(right_eye_inner.x - left_eye_inner.x) * w)
#     new_w = int(scale_factor * face_width)
#     new_h = int(jewelry_h * (new_w / jewelry_w))
#     jewelry_resized = cv2.resize(jewelry_np, (new_w, new_h), interpolation=cv2.INTER_AREA)
#     # -------------------------

#     # -------------------------
#     # ✅ 6️⃣ Overlay jewelry on user image
#     overlay = user_img.copy()
#     x1 = center_x - new_w // 2
#     y1 = center_y - new_h // 2
#     x2 = x1 + new_w
#     y2 = y1 + new_h

#     # Ensure coordinates within bounds
#     x1, y1 = max(0, x1), max(0, y1)
#     x2, y2 = min(w, x2), min(h, y2)

#     alpha_j = jewelry_resized[:, :, 3] / 255.0
#     for c in range(3):
#         overlay[y1:y2, x1:x2, c] = (
#             alpha_j[:y2 - y1, :x2 - x1] * jewelry_resized[:y2 - y1, :x2 - x1, c] +
#             (1 - alpha_j[:y2 - y1, :x2 - x1]) * overlay[y1:y2, x1:x2, c]
#         )
#     # -------------------------

#     return overlay


import logging
import io
from PIL import Image
import cv2
import numpy as np
import mediapipe as mp
from rembg import remove

def apply_mangtika(user_img: np.ndarray, mangtika_img_bytes: bytes, scale_factor: float = 0.8) -> np.ndarray:
    """
    Places a mangtika (forehead jewelry) on the user's image after removing its background.
    Returns: overlayed BGR numpy array.
    """
    try:
        # ✅ 1️⃣ Ensure valid image bytes
        try:
            Image.open(io.BytesIO(mangtika_img_bytes))
            valid_bytes = mangtika_img_bytes
        except (OSError, ValueError):
            if isinstance(mangtika_img_bytes, Image.Image):
                buf = io.BytesIO()
                mangtika_img_bytes.save(buf, format="PNG")
                valid_bytes = buf.getvalue()
            else:
                raise ValueError("Invalid jewelry image bytes provided!")

        # ✅ 2️⃣ Remove background
        clean_bytes = remove(valid_bytes)
        jewelry_img = Image.open(io.BytesIO(clean_bytes)).convert("RGBA")
        jewelry_np = np.array(jewelry_img)

        # ✅ 3️⃣ Convert RGB → BGR
        jewelry_np[:, :, :3] = jewelry_np[:, :, :3][:, :, ::-1]

        # ✅ 4️⃣ Detect forehead center
        mp_face_mesh = mp.solutions.face_mesh
        with mp_face_mesh.FaceMesh(static_image_mode=True) as face_mesh:
            rgb_user = cv2.cvtColor(user_img, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb_user)
            if not results.multi_face_landmarks:
                raise ValueError("No face detected in user image!")

            face_landmarks = results.multi_face_landmarks[0]
            h, w, _ = user_img.shape
            left_eye_inner = face_landmarks.landmark[33]
            right_eye_inner = face_landmarks.landmark[263]

            center_x = int((left_eye_inner.x + right_eye_inner.x) / 2 * w) + 10
            center_y = int((left_eye_inner.y + right_eye_inner.y) / 2 * h) - int(0.15 * h)

        # ✅ 5️⃣ Resize jewelry
        jewelry_h, jewelry_w = jewelry_np.shape[:2]
        face_width = int(abs(right_eye_inner.x - left_eye_inner.x) * w)
        new_w = int(scale_factor * face_width)
        new_h = int(jewelry_h * (new_w / jewelry_w))
        jewelry_resized = cv2.resize(jewelry_np, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # ✅ 6️⃣ Overlay
        overlay = user_img.copy()
        x1 = max(0, center_x - new_w // 2)
        y1 = max(0, center_y - new_h // 2)
        x2 = min(w, x1 + new_w)
        y2 = min(h, y1 + new_h)

        alpha_j = jewelry_resized[:, :, 3] / 255.0
        for c in range(3):
            overlay[y1:y2, x1:x2, c] = (
                alpha_j[:y2 - y1, :x2 - x1] * jewelry_resized[:y2 - y1, :x2 - x1, c] +
                (1 - alpha_j[:y2 - y1, :x2 - x1]) * overlay[y1:y2, x1:x2, c]
            )

        return overlay

    except Exception as e:
        # 🔥 Logs full stack trace to logs/error.log
        logging.error("Error inside apply_mangtika", exc_info=True)
        raise   # Re-raise so API can handle it



# import io
# import cv2
# import numpy as np
# from PIL import Image
# import mediapipe as mp

# def apply_mangtika(user_img: np.ndarray, mangtika_img_bytes: bytes, scale_factor: float = 0.8) -> np.ndarray:
#     """
#     Places a mangtika (forehead jewelry) on the user's image after removing its background
#     using simple alpha masking (no rembg dependency).

#     Args:
#         user_img: BGR numpy image (OpenCV format).
#         mangtika_img_bytes: Raw image bytes of the jewelry (PNG/JPG with alpha or solid background).
#         scale_factor: Relative scale of the jewelry compared to face width.

#     Returns:
#         Overlayed image as a BGR numpy array.
#     """

#     # -------------------------
#     # ✅ 1️⃣ Load jewelry image
#     jewelry_img = Image.open(io.BytesIO(mangtika_img_bytes)).convert("RGBA")
#     jewelry_np = np.array(jewelry_img)  # RGBA
#     # -------------------------

#     # -------------------------
#     # ✅ 2️⃣ Remove background if solid (white) background
#     if jewelry_np.shape[2] == 4:  # already has alpha
#         alpha = jewelry_np[:, :, 3]
#         # If alpha is fully opaque, try thresholding white background
#         if np.all(alpha == 255):
#             gray = cv2.cvtColor(jewelry_np[:, :, :3], cv2.COLOR_RGB2GRAY)
#             _, mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
#             jewelry_np[:, :, 3] = mask
#     else:  # no alpha channel, add one
#         gray = cv2.cvtColor(jewelry_np[:, :, :3], cv2.COLOR_RGB2GRAY)
#         _, mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
#         jewelry_np = cv2.cvtColor(jewelry_np, cv2.COLOR_RGB2BGRA)
#         jewelry_np[:, :, 3] = mask
#     # -------------------------

#     # -------------------------
#     # ✅ 3️⃣ Convert RGB → BGR to match OpenCV user image
#     jewelry_np[:, :, :3] = jewelry_np[:, :, :3][:, :, ::-1]
#     # -------------------------

#     # -------------------------
#     # ✅ 4️⃣ Detect forehead center using Mediapipe
#     mp_face_mesh = mp.solutions.face_mesh
#     with mp_face_mesh.FaceMesh(static_image_mode=True) as face_mesh:
#         rgb_user = cv2.cvtColor(user_img, cv2.COLOR_BGR2RGB)
#         results = face_mesh.process(rgb_user)
#         if not results.multi_face_landmarks:
#             raise ValueError("No face detected in user image!")

#         face_landmarks = results.multi_face_landmarks[0]
#         h, w, _ = user_img.shape
#         left_eye_inner = face_landmarks.landmark[33]
#         right_eye_inner = face_landmarks.landmark[263]

#         # Forehead center (slightly above eyes)
#         center_x = int((left_eye_inner.x + right_eye_inner.x) / 2 * w) + 10
#         center_y = int((left_eye_inner.y + right_eye_inner.y) / 2 * h) - int(0.15 * h)
#     # -------------------------

#     # -------------------------
#     # ✅ 5️⃣ Resize jewelry relative to face width
#     jewelry_h, jewelry_w = jewelry_np.shape[:2]
#     face_width = int(abs(right_eye_inner.x - left_eye_inner.x) * w)
#     new_w = int(scale_factor * face_width)
#     new_h = int(jewelry_h * (new_w / jewelry_w))
#     jewelry_resized = cv2.resize(jewelry_np, (new_w, new_h), interpolation=cv2.INTER_AREA)
#     # -------------------------

#     # -------------------------
#     # ✅ 6️⃣ Overlay jewelry on user image
#     overlay = user_img.copy()
#     x1 = center_x - new_w // 2
#     y1 = center_y - new_h // 2
#     x2 = x1 + new_w
#     y2 = y1 + new_h

#     # Ensure coordinates within bounds
#     x1, y1 = max(0, x1), max(0, y1)
#     x2, y2 = min(w, x2), min(h, y2)

#     alpha_j = jewelry_resized[:, :, 3] / 255.0
#     for c in range(3):
#         overlay[y1:y2, x1:x2, c] = (
#             alpha_j[:y2 - y1, :x2 - x1] * jewelry_resized[:y2 - y1, :x2 - x1, c] +
#             (1 - alpha_j[:y2 - y1, :x2 - x1]) * overlay[y1:y2, x1:x2, c]
#         )
#     # -------------------------

#     return overlay

