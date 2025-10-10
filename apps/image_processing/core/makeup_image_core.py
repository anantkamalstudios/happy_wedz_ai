from flask import Blueprint, request, jsonify, send_file, url_for
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw, ImageFilter, ImageChops
import io
from apps.image_processing.models.makeup_image_model import (
    db, UserImage, ImageType, CategoryEnum, Product, UserMakeupResultImage
)
from ultralytics import YOLO
import mediapipe as mp
import cv2
import numpy as np
import face_recognition
import base64
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from datetime import datetime
from reportlab.lib.utils import ImageReader
from torch import nn
import torch
from transformers import SegformerImageProcessor, SegformerForSemanticSegmentation
import tempfile
import os
from PIL import Image, ImageDraw, ImageFilter, ImageChops
import math


# --------------------------Upload Image Validation Functions-----------------------

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
yolo_model = YOLO("yolov8n.pt")

def allowed_file(filename):
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def count_people(image_data: bytes) -> int:
    try:
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        results = yolo_model(img)
        person_count = 0

        for r in results:
            for cls in r.boxes.cls:
                if int(cls) == 0:
                    person_count += 1

        return person_count
    except Exception:
        return 0


def is_real_photo_strict(image_content: bytes) -> bool:
    try:
        pil_image = Image.open(io.BytesIO(image_content)).convert("RGB")
        img = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        pixel_std = np.std(gray.astype(np.float32))
        edge_density = np.mean(cv2.Canny(gray, 50, 150) > 0)

        if pixel_std < 5:
            return False
        if edge_density < 0.002:  
            return False

        return True
    except Exception:
        return False


def is_blurry(image_content: bytes,
              lap_thresh: float = 15.0,
              tenengrad_thresh: float = 400.0) -> bool:

    pil = Image.open(io.BytesIO(image_content)).convert("RGB")
    gray = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2GRAY)

    lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()

    gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    tenengrad = float(np.mean(gx*gx + gy*gy))

    return lap_var < lap_thresh or tenengrad < tenengrad_thresh


def contains_person(image_content: bytes) -> bool:
    try:
        nparr = np.frombuffer(image_content, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        results = yolo_model(img)
        for r in results:
            for c in r.boxes.cls:
                if int(c) == 0:
                    return True
        return False
    except Exception:
        return False


FRONT_FACE_ERR = "human in the image is not front facing. Please upload image in proper format"


def is_full_body_front_facing(
    image_data: bytes,
    min_visibility: float = 0.60,
    shoulder_center_tolerance: float = 0.35,
    min_eye_dist_abs: float = 0.035,
    min_eye_dist_rel_to_shoulders: float = 0.12,
    max_yaw_visibility_imbalance: float = 0.35
) -> tuple[bool, str]:
    try:
        mp_pose = mp.solutions.pose
        with mp_pose.Pose(
            static_image_mode=True,
            model_complexity=2,
            enable_segmentation=False,
            min_detection_confidence=0.7
        ) as pose:
            image = Image.open(io.BytesIO(image_data)).convert("RGB")
            img_np = np.array(image)

            if img_np.shape[1] > 1280:
                new_w = 1280
                new_h = int(img_np.shape[0] * 1280 / img_np.shape[1])
                img_np = cv2.resize(img_np, (new_w, new_h))

            results = pose.process(img_np)

            if not results.pose_landmarks:
                return False, FRONT_FACE_ERR

            landmarks = results.pose_landmarks.landmark
            # Required landmarks with clear names
            req = {
                "nose": mp_pose.PoseLandmark.NOSE,
                "left_eye": mp_pose.PoseLandmark.LEFT_EYE,
                "right_eye": mp_pose.PoseLandmark.RIGHT_EYE,
                "left_ear": mp_pose.PoseLandmark.LEFT_EAR,
                "right_ear": mp_pose.PoseLandmark.RIGHT_EAR,
                "mouth_left": mp_pose.PoseLandmark.MOUTH_LEFT,
                "mouth_right": mp_pose.PoseLandmark.MOUTH_RIGHT,
                "left_shoulder": mp_pose.PoseLandmark.LEFT_SHOULDER,
                "right_shoulder": mp_pose.PoseLandmark.RIGHT_SHOULDER,
                "left_wrist": mp_pose.PoseLandmark.LEFT_WRIST,
                "right_wrist": mp_pose.PoseLandmark.RIGHT_WRIST,
                "left_hip": mp_pose.PoseLandmark.LEFT_HIP,
                "right_hip": mp_pose.PoseLandmark.RIGHT_HIP,
                "left_ankle": mp_pose.PoseLandmark.LEFT_ANKLE,
                "right_ankle": mp_pose.PoseLandmark.RIGHT_ANKLE,
            }
            # Check visibility of all required landmarks
            for name, idx in req.items():
                if landmarks[idx].visibility < min_visibility:
                    return False, FRONT_FACE_ERR

            def X(idx): return landmarks[idx].x
            def Y(idx): return landmarks[idx].y

            left_shoulder, right_shoulder = req["left_shoulder"], req["right_shoulder"]
            left_eye, right_eye = req["left_eye"], req["right_eye"]
            left_ear, right_ear = req["left_ear"], req["right_ear"]
            nose = req["nose"]

            shoulder_width = abs(X(left_shoulder) - X(right_shoulder))
            if shoulder_width < 0.05:
                return False, FRONT_FACE_ERR

            # 1) Nose centered between shoulders
            nose_to_left = abs(X(nose) - X(left_shoulder))
            nose_to_right = abs(X(nose) - X(right_shoulder))
            center_ratio = abs(nose_to_left - nose_to_right) / shoulder_width
            if center_ratio > shoulder_center_tolerance:
                return False, FRONT_FACE_ERR

            # 2) Inter-eye distance checks
            eye_dist_abs = abs(X(left_eye) - X(right_eye))
            eye_dist_rel = eye_dist_abs / shoulder_width
            if eye_dist_abs < min_eye_dist_abs or eye_dist_rel < min_eye_dist_rel_to_shoulders:
                return False, FRONT_FACE_ERR

            # 3) Face visibility balance
            left_vis = (landmarks[left_eye].visibility + landmarks[left_ear].visibility)
            right_vis = (landmarks[right_eye].visibility + landmarks[right_ear].visibility)
            if (abs(left_vis - right_vis) / max(left_vis + right_vis, 1e-6)) > max_yaw_visibility_imbalance:
                return False, FRONT_FACE_ERR

            # 4) Ankles should be well below hips
            avg_ankle_y = (Y(req["left_ankle"]) + Y(req["right_ankle"])) / 2.0
            avg_hip_y = (Y(req["left_hip"]) + Y(req["right_hip"])) / 2.0
            if (avg_ankle_y - avg_hip_y) < 0.20:
                return False, FRONT_FACE_ERR

            # 5) Shoulder and hip alignment
            shoulder_center_x = (X(left_shoulder) + X(right_shoulder)) / 2.0
            hip_center_x = (X(req["left_hip"]) + X(req["right_hip"])) / 2.0
            if abs(shoulder_center_x - hip_center_x) > 0.12:
                return False, FRONT_FACE_ERR

            return True, "ok"
    except Exception:
        return False, FRONT_FACE_ERR



# ----------------Apply Makeup Functions--------------------------

mp_face_mesh = mp.solutions.face_mesh


def hex_to_bgr(hex_color: str):
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join([c*2 for c in hex_color])
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return (b, g, r)


def apply_lipstick(original_img, landmarks, color="#ff0000", intensity=0.7):
    glossiness = 0.2
    def hex_to_bgr(hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (4, 2, 0))
    
    def create_precise_lip_mask(landmarks, img_shape):
        h, w = img_shape[:2]
        
        top_lip = np.array(landmarks["top_lip"], dtype=np.int32)
        bottom_lip = np.array(landmarks["bottom_lip"], dtype=np.int32)
        
        full_mask = np.zeros((h, w), dtype=np.uint8)
        
        if len(top_lip) > 2:
            cv2.fillPoly(full_mask, [top_lip], 255)
            
        if len(bottom_lip) > 2:
            cv2.fillPoly(full_mask, [bottom_lip], 255) 
            
        top_only_mask = np.zeros((h, w), dtype=np.uint8)
        bottom_only_mask = np.zeros((h, w), dtype=np.uint8)
        
        if len(top_lip) > 2:
            cv2.fillPoly(top_only_mask, [top_lip], 255)
        if len(bottom_lip) > 2:
            cv2.fillPoly(bottom_only_mask, [bottom_lip], 255)
            
        teeth_mask = np.zeros((h, w), dtype=np.uint8)
        
        if len(top_lip) > 6 and len(bottom_lip) > 6:
            top_inner = top_lip[1:6] if len(top_lip) > 6 else top_lip[1:-1] 
            bottom_inner = bottom_lip[1:6] if len(bottom_lip) > 6 else bottom_lip[1:-1]
            
            if len(top_inner) > 2 and len(bottom_inner) > 2:
                inner_mouth_points = np.vstack([
                    top_inner,
                    bottom_inner[::-1]
                ])
                
                cv2.fillPoly(teeth_mask, [inner_mouth_points], 255)
                
                teeth_mask = cv2.erode(teeth_mask, np.ones((2, 2), np.uint8), iterations=1)
        
        final_mask = cv2.bitwise_and(full_mask, cv2.bitwise_not(teeth_mask))
        
        if np.sum(final_mask) < np.sum(full_mask) * 0.6:
            top_mask = np.zeros((h, w), dtype=np.uint8)
            bottom_mask = np.zeros((h, w), dtype=np.uint8)
            
            if len(top_lip) > 2:
                cv2.fillPoly(top_mask, [top_lip], 255)
            if len(bottom_lip) > 2:
                cv2.fillPoly(bottom_mask, [bottom_lip], 255)
                bottom_mask = cv2.erode(bottom_mask, np.ones((2, 2), np.uint8), iterations=1)
            
            final_mask = cv2.bitwise_or(top_mask, bottom_mask)
            
        
        return final_mask
    
    def detect_lip_color_regions(roi, mask):
        hsv = cv2.cvtColor(roi.astype(np.uint8), cv2.COLOR_BGR2HSV)
        
        lip_pixels = hsv[mask > 0]
        
        if len(lip_pixels) == 0:
            return np.ones_like(mask, dtype=np.float32)
        
        red_hue1 = (lip_pixels[:, 0] >= 0) & (lip_pixels[:, 0] <= 15)
        red_hue2 = (lip_pixels[:, 0] >= 160) & (lip_pixels[:, 0] <= 179)
        pink_hue = (lip_pixels[:, 0] >= 140) & (lip_pixels[:, 0] <= 179)
        
        natural_lip_mask = red_hue1 | red_hue2 | pink_hue
        
        color_confidence = np.zeros_like(mask, dtype=np.float32)
        lip_coords = np.where(mask > 0)
        
        for i, (y, x) in enumerate(zip(lip_coords[0], lip_coords[1])):
            if i < len(natural_lip_mask):
                if natural_lip_mask[i]:
                    color_confidence[y, x] = 1.0
                else:
                    color_confidence[y, x] = 0.3
        
        return color_confidence
    
    def create_natural_blend_mask(mask, landmarks):
        h, w = mask.shape
        
        distance_map = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
        max_distance = np.max(distance_map)
        
        if max_distance > 0:
            normalized_distance = distance_map / max_distance
            
            blend_mask = np.power(normalized_distance, 0.7)  
            blend_mask = cv2.GaussianBlur(blend_mask, (5, 5), 0)
        else:
            blend_mask = mask.astype(np.float32) / 255.0
        
        return blend_mask
    
    lip_points = np.array(landmarks["top_lip"] + landmarks["bottom_lip"], np.int32)
    if len(lip_points) == 0:
        return original_img
        
    x, y, w, h = cv2.boundingRect(lip_points)
    
    padding = 10
    x = max(0, x - padding)
    y = max(0, y - padding)
    w = min(original_img.shape[1] - x, w + 2 * padding)
    h = min(original_img.shape[0] - y, h + 2 * padding)
    
    full_mask = create_precise_lip_mask(landmarks, original_img.shape)
    lip_mask = full_mask[y:y+h, x:x+w]
    
    if np.sum(lip_mask) == 0:
        return original_img
    
    roi = original_img[y:y+h, x:x+w].copy()
    
    color_confidence = detect_lip_color_regions(roi, lip_mask)
    
    blend_mask = create_natural_blend_mask(lip_mask, landmarks)
    
    lipstick_bgr = np.array(hex_to_bgr(color), dtype=np.float32)
    
    roi_lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB).astype(np.float32)
    lipstick_rgb = np.array([lipstick_bgr[2], lipstick_bgr[1], lipstick_bgr[0]])
    lipstick_lab = cv2.cvtColor(np.uint8([[lipstick_rgb]]), cv2.COLOR_RGB2LAB)[0, 0].astype(np.float32)
    
    result_roi = roi.astype(np.float32)
    
    mask_float = lip_mask.astype(np.float32) / 255.0
    
    for i in range(h):
        for j in range(w):
            if mask_float[i, j] > 0:
                orig_pixel = roi_lab[i, j]
                
                base_alpha = intensity * mask_float[i, j] * blend_mask[i, j]
                color_alpha = base_alpha * (0.7 + 0.3 * color_confidence[i, j])

                new_l = orig_pixel[0] * (1 - color_alpha * 0.3) + lipstick_lab[0] * (color_alpha * 0.3)
                
                new_a = orig_pixel[1] * (1 - color_alpha) + lipstick_lab[1] * color_alpha
                new_b = orig_pixel[2] * (1 - color_alpha) + lipstick_lab[2] * color_alpha
                
                roi_lab[i, j] = [new_l, new_a, new_b]

    result_roi = cv2.cvtColor(np.clip(roi_lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)
    
    if glossiness > 0:
        result_roi = result_roi.astype(np.float32)
        
        highlight_mask = cv2.GaussianBlur(blend_mask, (15, 15), 0)
        highlight_mask = np.power(highlight_mask, 2)
        
        gloss_boost = 1 + glossiness * 0.15 * highlight_mask[:, :, np.newaxis]
        result_roi = result_roi * gloss_boost
        
        result_roi = np.clip(result_roi, 0, 255).astype(np.uint8)
    
    result = original_img.copy()
    result[y:y+h, x:x+w] = result_roi
    
    return result


def apply_blush(original_img, landmarks, color="#ff6666", intensity=0.5, radius=40):
    blush_mask = np.zeros(original_img.shape[:2], dtype=np.uint8)

    chin = landmarks["chin"]
    left_eye = landmarks["left_eye"]
    right_eye = landmarks["right_eye"]

    left_cheek_x = int((chin[3][0] + left_eye[0][0]) / 2)
    left_cheek_y = int((chin[3][1] + left_eye[0][1]) / 2)
    left_cheek = (left_cheek_x, left_cheek_y)

    right_cheek_x = int((chin[13][0] + right_eye[3][0]) / 2)
    right_cheek_y = int((chin[13][1] + right_eye[3][1]) / 2)
    right_cheek = (right_cheek_x, right_cheek_y)

    cv2.circle(blush_mask, left_cheek, radius, 255, -1)
    cv2.circle(blush_mask, right_cheek, radius, 255, -1)

    mask_blur = cv2.GaussianBlur(blush_mask, (101, 101), 0).astype(np.float32) / 255.0
    mask_3 = cv2.merge([mask_blur] * 3)

    color_bgr = np.array(hex_to_bgr(color), dtype=np.uint8)
    overlay = np.full_like(original_img, color_bgr, dtype=np.uint8)
    alpha = np.clip(intensity, 0.0, 1.0)

    return cv2.convertScaleAbs(original_img * (1 - mask_3 * alpha) + overlay * (mask_3 * alpha))


def hex_to_bgrs(hex_color: str):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (4, 2, 0))  # BGR


def apply_professional_eyeshadow(image, landmarks, color="#9370DB", intensity=0.4):
    result = image.copy().astype(np.float32)
    bgr_color = np.array(hex_to_bgrs(color), dtype=np.float32)


    deep_color = bgr_color * 0.6

    for eye_key, brow_key in [("left_eye", "left_eyebrow"), ("right_eye", "right_eyebrow")]:
        if eye_key not in landmarks or brow_key not in landmarks:
            continue

        eye_points = np.array(landmarks[eye_key], dtype=np.int32)
        brow_points = np.array(landmarks[brow_key], dtype=np.int32)

        if len(eye_points) < 6 or len(brow_points) < 3:
            continue

        inner_corner = eye_points[0]
        outer_corner = eye_points[3]
        eye_top = np.mean(eye_points[1:3], axis=0).astype(int)
        eye_bottom = np.mean(eye_points[4:6], axis=0).astype(int)
        eye_width = abs(outer_corner[0] - inner_corner[0])
        eye_height = abs(eye_top[1] - eye_bottom[1])

        brow_inner = brow_points[0]
        brow_outer = brow_points[-1]
        brow_top = np.min(brow_points[:, 1])
        brow_bottom = np.max(brow_points[:, 1])

        shadow_inner_x = min(inner_corner[0], brow_inner[0]) - int(eye_width * 0.1)
        shadow_outer_x = max(outer_corner[0], brow_outer[0]) + int(eye_width * 0.2)

        shadow_bottom_y = eye_top[1]
        shadow_top_y = brow_bottom - int((brow_bottom - brow_top) * 0.3)

        main_shadow_points = np.array([
            [shadow_inner_x, shadow_bottom_y],
            [shadow_inner_x + int(eye_width * 0.1), shadow_top_y],
            [inner_corner[0] + int(eye_width * 0.3), shadow_top_y - int(eye_height * 0.2)],
            [outer_corner[0] - int(eye_width * 0.1), shadow_top_y - int(eye_height * 0.3)],
            [shadow_outer_x - int(eye_width * 0.1), shadow_top_y],
            [shadow_outer_x, shadow_bottom_y],
            [shadow_outer_x - int(eye_width * 0.05), shadow_bottom_y - int(eye_height * 0.1)],
            [outer_corner[0], eye_top[1]],
            [inner_corner[0] + int(eye_width * 0.1), eye_top[1]],
            [shadow_inner_x + int(eye_width * 0.05), shadow_bottom_y - int(eye_height * 0.1)]
        ], dtype=np.int32)

        outer_v_width = int(eye_width * 0.4)
        outer_v_points = np.array([
            [outer_corner[0] - int(outer_v_width * 0.3), eye_top[1]],
            [outer_corner[0] - int(outer_v_width * 0.1), shadow_top_y - int(eye_height * 0.2)],
            [shadow_outer_x - int(eye_width * 0.05), shadow_top_y],
            [shadow_outer_x, shadow_bottom_y],
            [shadow_outer_x - int(eye_width * 0.1), shadow_bottom_y + int(eye_height * 0.2)],
            outer_corner
        ], dtype=np.int32)

        main_mask = np.zeros(image.shape[:2], dtype=np.float32)
        cv2.fillPoly(main_mask, [main_shadow_points], 1.0)

        h, w = main_mask.shape
        y_coords, x_coords = np.ogrid[:h, :w]

        eye_center_x = (inner_corner[0] + outer_corner[0]) // 2
        horizontal_gradient = np.exp(-((x_coords - eye_center_x) ** 2) / (eye_width ** 2))

        vertical_gradient = np.exp(-((y_coords - shadow_bottom_y) ** 2) / ((shadow_top_y - shadow_bottom_y) ** 2))

        combined_gradient = horizontal_gradient * vertical_gradient
        main_mask *= combined_gradient

        main_mask = cv2.GaussianBlur(main_mask, (0, 0), 12)

        outer_mask = np.zeros(image.shape[:2], dtype=np.float32)
        cv2.fillPoly(outer_mask, [outer_v_points], 1.0)
        outer_mask = cv2.GaussianBlur(outer_mask, (0, 0), 8)

        base_intensity = intensity * 0.7
        outer_intensity = intensity * 0.9

        for i in range(3):
            color_layer = main_mask * base_intensity * bgr_color[i]
            result[:, :, i] = (1 - main_mask * base_intensity) * result[:, :, i] + color_layer

        for i in range(3):
            outer_layer = outer_mask * outer_intensity * deep_color[i]
            result[:, :, i] = (1 - outer_mask * outer_intensity) * result[:, :, i] + outer_layer

        highlight_color = np.minimum(bgr_color * 1.4, 255)
        highlight_radius = int(eye_width * 0.12)
        highlight_center = (inner_corner[0] - int(eye_width * 0.05), inner_corner[1] - int(eye_height * 0.3))

        highlight_mask = np.zeros(image.shape[:2], dtype=np.float32)
        cv2.circle(highlight_mask, highlight_center, highlight_radius, 1.0, -1)
        highlight_mask = cv2.GaussianBlur(highlight_mask, (0, 0), highlight_radius//2)

        highlight_intensity = intensity * 0.4
        for i in range(3):
            highlight_layer = highlight_mask * highlight_intensity * highlight_color[i]
            result[:, :, i] = np.minimum(result[:, :, i] + highlight_layer, 255)

    return np.clip(result, 0, 255).astype(np.uint8)


def apply_wide_coverage_eyeshadow(image, landmarks, color="#9370DB", intensity=0.4):
    result = image.copy().astype(np.float32)
    bgr_color = np.array(hex_to_bgrs(color), dtype=np.float32)

    for eye_key, brow_key in [("left_eye", "left_eyebrow"), ("right_eye", "right_eyebrow")]:
        if eye_key not in landmarks or brow_key not in landmarks:
            continue

        eye_points = np.array(landmarks[eye_key], dtype=np.int32)
        brow_points = np.array(landmarks[brow_key], dtype=np.int32)

        if len(eye_points) < 6 or len(brow_points) < 3:
            continue

        inner_corner = eye_points[0]
        outer_corner = eye_points[3]
        eye_center = np.mean(eye_points, axis=0).astype(int)

        brow_start = brow_points[0]
        brow_end = brow_points[-1]
        brow_top = np.min(brow_points[:, 1])

        eye_width = abs(outer_corner[0] - inner_corner[0])

        left_bound = min(inner_corner[0], brow_start[0]) - int(eye_width * 0.1)
        right_bound = max(outer_corner[0], brow_end[0]) + int(eye_width * 0.3)

        eye_top_line = min(eye_points[1][1], eye_points[2][1]) 
        bottom_bound = eye_top_line - int(eye_width * 0.1) 
        top_bound = brow_top + int((eye_top_line - brow_top) * 0.4)  

        center_x = (left_bound + right_bound) // 2
        center_y = (top_bound + bottom_bound) // 2
        width_radius = (right_bound - left_bound) // 2
        height_radius = (bottom_bound - top_bound) // 2

        mask = np.zeros(image.shape[:2], dtype=np.float32)

        y_coords, x_coords = np.ogrid[:mask.shape[0], :mask.shape[1]]
        ellipse_mask = ((x_coords - center_x) / width_radius) ** 2 + ((y_coords - center_y) / height_radius) ** 2 <= 1
        mask[ellipse_mask] = 1.0

        gradient = 1.0 - np.abs(y_coords - (bottom_bound + int((top_bound - bottom_bound) * 0.3))) / ((top_bound - bottom_bound) * 0.7)
        gradient = np.maximum(0, gradient)
        gradient = np.power(gradient, 0.8)

        final_mask = mask * gradient

        final_mask = cv2.GaussianBlur(final_mask, (0, 0), 15)

        for i in range(3):
            color_layer = final_mask * intensity * bgr_color[i]
            result[:, :, i] = (1 - final_mask * intensity) * result[:, :, i] + color_layer

    return np.clip(result, 0, 255).astype(np.uint8)


def apply_eyeshadow(image, landmarks, color="#9370DB", intensity=0.4, thickness=25):
    return apply_wide_coverage_eyeshadow(image, landmarks, color, intensity)


mp_face_mesh = mp.solutions.face_mesh


def hex_to_bgr_new(hex_color):
    hex_color = hex_color.lstrip('#')
    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return rgb[::-1]  # Convert RGB to BGR


def create_corner_exclusion_mask(image_shape, eye_points, exclusion_radius=8):
    exclusion_mask = np.zeros(image_shape[:2], dtype="uint8")
    eye_array = np.array(eye_points)

    outer_corner = eye_array[0]
    inner_corner = eye_array[3] 

    cv2.circle(exclusion_mask, tuple(outer_corner.astype(int)), exclusion_radius, 255, -1)
    cv2.circle(exclusion_mask, tuple(inner_corner.astype(int)), exclusion_radius, 255, -1)

    return exclusion_mask


def create_iris_only_mask(image, eye_points, safety_margin=0.25):
    eye_array = np.array(eye_points)

    middle_points = np.concatenate([eye_array[1:3], eye_array[4:6]])
    center_x = int(np.mean(middle_points[:, 0]))
    center_y = int(np.mean(middle_points[:, 1]))

    outer_corner = eye_array[0]
    inner_corner = eye_array[3]

    dist_to_outer = np.sqrt((center_x - outer_corner[0])**2 + (center_y - outer_corner[1])**2)
    dist_to_inner = np.sqrt((center_x - inner_corner[0])**2 + (center_y - inner_corner[1])**2)

    max_safe_radius = min(dist_to_outer, dist_to_inner) * (1 - safety_margin)

    eye_width = np.max(eye_array[:, 0]) - np.min(eye_array[:, 0])
    eye_height = np.max(eye_array[:, 1]) - np.min(eye_array[:, 1])

    estimated_iris_radius = min(eye_width, eye_height) * 0.45

    final_radius = int(min(max_safe_radius, estimated_iris_radius))

    final_radius = max(8, min(final_radius, 35))

    iris_mask = np.zeros(image.shape[:2], dtype="uint8")
    cv2.circle(iris_mask, (center_x, center_y), final_radius, 255, -1)

    corner_exclusion = create_corner_exclusion_mask(image.shape, eye_points, exclusion_radius=12)

    iris_mask = cv2.bitwise_and(iris_mask, cv2.bitwise_not(corner_exclusion))

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    eye_region_mask = np.zeros(image.shape[:2], dtype="uint8")
    cv2.fillPoly(eye_region_mask, [eye_array], 255)
    eye_pixels = gray[eye_region_mask > 0]

    if len(eye_pixels) > 0:
 
        bright_threshold = np.percentile(eye_pixels, 80)
        bright_areas = (gray > bright_threshold).astype(np.uint8) * 255

        iris_mask = cv2.bitwise_and(iris_mask, cv2.bitwise_not(bright_areas))

    if np.sum(iris_mask) < 30:
        iris_mask = np.zeros(image.shape[:2], dtype="uint8")
        minimal_radius = max(3, final_radius // 2)
        cv2.circle(iris_mask, (center_x, center_y), minimal_radius, 255, -1)
        iris_mask = cv2.bitwise_and(iris_mask, cv2.bitwise_not(corner_exclusion))

    return iris_mask


def apply_lenses_improved(image, lens_color="#1E90FF", lens_intensity=0.7, lens_radius_scale=1.0):
    face_landmarks_list = face_recognition.face_landmarks(image)

    if not face_landmarks_list:
        return image

    result_image = image.copy()

    for landmarks in face_landmarks_list:
        for eye_key in ["left_eye", "right_eye"]:
            if eye_key not in landmarks:
                continue

            eye_points = landmarks[eye_key]

            if len(eye_points) < 6:
                continue

            iris_mask = create_iris_only_mask(image, eye_points)

            if lens_radius_scale != 1.0:
                moments = cv2.moments(iris_mask)
                if moments['m00'] != 0:
                    cx = int(moments['m10'] / moments['m00'])
                    cy = int(moments['m01'] / moments['m00'])

                    scaled_mask = np.zeros(iris_mask.shape, dtype="uint8")

                    contours, _ = cv2.findContours(iris_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    if contours:
                        largest_contour = max(contours, key=cv2.contourArea)
                        (x, y), radius = cv2.minEnclosingCircle(largest_contour)
                        new_radius = int(radius * lens_radius_scale)
                        cv2.circle(scaled_mask, (cx, cy), new_radius, 255, -1)

                        corner_exclusion = create_corner_exclusion_mask(image.shape, eye_points)
                        scaled_mask = cv2.bitwise_and(scaled_mask, cv2.bitwise_not(corner_exclusion))
                        iris_mask = scaled_mask

            overlay = np.full(image.shape, hex_to_bgr_new(lens_color), dtype="uint8")

            smooth_mask = cv2.GaussianBlur(iris_mask.astype(np.float32), (3, 3), 0)
            smooth_mask = smooth_mask / 255.0 

            for c in range(3):
                result_image[:, :, c] = (
                    result_image[:, :, c] * (1 - smooth_mask * lens_intensity) +
                    overlay[:, :, c] * smooth_mask * lens_intensity
                ).astype(np.uint8)

    return result_image


def apply_lenses_advanced_fixed(image, lens_color="#1E90FF", lens_intensity=0.7, lens_radius_scale=1.2, add_reflection=True, exclude_very_bright=True):

    # Use the improved lens application as base
    result = apply_lenses_improved(image, lens_color, lens_intensity, lens_radius_scale)

    if not add_reflection:
        return result

    # Add subtle reflection effect
    face_landmarks_list = face_recognition.face_landmarks(result)

    if not face_landmarks_list:
        return result

    for landmarks in face_landmarks_list:
        for eye_key in ["left_eye", "right_eye"]:
            if eye_key not in landmarks:
                continue

            eye_points = landmarks[eye_key]

            if len(eye_points) < 6:
                continue

            iris_mask = create_iris_only_mask(result, eye_points)

            if np.sum(iris_mask) < 20:
                continue

            eye_array = np.array(eye_points)
            middle_points = np.concatenate([eye_array[1:3], eye_array[4:6]])
            center_x = int(np.mean(middle_points[:, 0]))
            center_y = int(np.mean(middle_points[:, 1]))

            reflection_mask = np.zeros(result.shape[:2], dtype="uint8")

            contours, _ = cv2.findContours(iris_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                largest_contour = max(contours, key=cv2.contourArea)
                (x, y), radius = cv2.minEnclosingCircle(largest_contour)

                reflection_x = int(center_x - radius * 0.3)
                reflection_y = int(center_y - radius * 0.3)
                reflection_radius = max(2, int(radius * 0.3))

                cv2.circle(reflection_mask, (reflection_x, reflection_y), reflection_radius, 255, -1)

                reflection_mask = cv2.bitwise_and(reflection_mask, iris_mask)

                reflection_smooth = cv2.GaussianBlur(reflection_mask.astype(np.float32), (3, 3), 0) / 255.0
                reflection_intensity = 0.3

                for c in range(3):
                    result[:, :, c] = (
                        result[:, :, c] * (1 - reflection_smooth * reflection_intensity) +
                        255 * reflection_smooth * reflection_intensity
                    ).astype(np.uint8)

    return result


def apply_contact_lenses(image, lens_color="#1E90FF", lens_intensity=0.7, lens_radius_scale=1.2, add_reflection=True):
    return apply_lenses_advanced_fixed(
        image,
        lens_color=lens_color,
        lens_intensity=lens_intensity,
        lens_radius_scale=lens_radius_scale,
        add_reflection=add_reflection
    )

processor = SegformerImageProcessor.from_pretrained("jonathandinu/face-parsing")
model = SegformerForSemanticSegmentation.from_pretrained("jonathandinu/face-parsing")

def get_face_mask(image_bgr, close_kernel=15, debug=False):
    model_id = "jonathandinu/face-parsing"

    if not hasattr(get_face_mask, "processor"):
        get_face_mask.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        get_face_mask.processor = SegformerImageProcessor.from_pretrained(model_id)
        get_face_mask.model = SegformerForSemanticSegmentation.from_pretrained(model_id).to(get_face_mask.device).eval()

    device = get_face_mask.device
    processor = get_face_mask.processor
    model = get_face_mask.model

    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(image_rgb)

    inputs = processor(images=pil_img, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model(**inputs)
    logits = outputs.logits

    upsampled = nn.functional.interpolate(
        logits,
        size=pil_img.size[::-1],
        mode="bilinear",
        align_corners=False,
    )
    seg = upsampled.argmax(dim=1)[0].cpu().numpy().astype(np.int32)

    face_label_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

    raw_mask = np.isin(seg, face_label_ids).astype(np.uint8) * 255

    if raw_mask.sum() == 0:
        raw_mask = (seg == 1).astype(np.uint8) * 255

    h, w = raw_mask.shape

    k = max(3, (close_kernel // 2) * 2 + 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    closed = cv2.morphologyEx(raw_mask, cv2.MORPH_CLOSE, kernel, iterations=1)

    inv = cv2.bitwise_not(closed)
    flood = inv.copy()
    mask_ff = np.zeros((h + 2, w + 2), np.uint8)
    cv2.floodFill(flood, mask_ff, (0, 0), 255)
    flood_inv = cv2.bitwise_not(flood)
    filled = cv2.bitwise_or(closed, flood_inv)

    contours, _ = cv2.findContours(filled, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    hull_mask = np.zeros_like(filled)
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 50:
            continue
        hull = cv2.convexHull(cnt)
        cv2.fillConvexPoly(hull_mask, hull, 255)
    if hull_mask.sum() == 0:
        hull_mask = filled.copy()

    final = cv2.GaussianBlur(hull_mask, (7, 7), 0)
    final = (final > 128).astype(np.uint8) * 255

    kernel_ear = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 15))
    final = cv2.dilate(final, kernel_ear, iterations=1)

    neck_mask = (seg == 17).astype(np.uint8) * 255


    final = cv2.bitwise_or(final, neck_mask)

    return final


# def apply_primer(image, landmarks, hex_color=None, intensity=0.5):
#     result = image.copy()

#     mask = get_face_mask(image)
#     if mask is None or mask.sum() == 0:
#         return result

#     smooth = cv2.bilateralFilter(result, d=15, sigmaColor=80, sigmaSpace=80)

#     alpha = np.clip(intensity, 0.0, 1.0)
#     primer_applied = cv2.addWeighted(smooth, alpha, result, 1 - alpha, 0)
#     result[mask == 255] = primer_applied[mask == 255]

#     if intensity > 0:
#         glow = cv2.convertScaleAbs(result, alpha=1.02, beta=int(10 * intensity))
#         result[mask == 255] = glow[mask == 255]

#     return result


# def apply_foundation(image, landmarks, hex_color="#f5d6c6", intensity=0.6):
    # result = image.copy()
    # mask = get_face_mask(image)
    # if mask is None or mask.sum() == 0:
    #     return result

    # mask = cv2.GaussianBlur(mask, (25, 25), 15)

    # smooth = cv2.bilateralFilter(result, d=20, sigmaColor=90, sigmaSpace=90)

    # hex_color = hex_color.lstrip("#")
    # r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    # foundation_color = np.full_like(result, (b, g, r))

    # alpha = np.clip(intensity, 0.0, 1.0)
    # toned = cv2.addWeighted(smooth, 1 - alpha, foundation_color, alpha, 0)

    # details = cv2.subtract(result, cv2.GaussianBlur(result, (21, 21), 10))
    # toned = cv2.addWeighted(toned, 1.0, details, 0.3, 0)

    # mask_norm = mask.astype(float) / 255.0
    # for c in range(3):
    #     result[..., c] = (result[..., c] * (1 - mask_norm) +
    #                       toned[..., c] * mask_norm)

    # return result

def apply_foundation(image, landmarks, hex_color="#f5d6c6", intensity=0.6):
    result = image.copy()

    mask = get_face_mask(image)
    if mask is None or mask.sum() == 0:
        return result

    smooth = cv2.bilateralFilter(result, d=15, sigmaColor=80, sigmaSpace=80)

    alpha = np.clip(intensity, 0.0, 1.0)
    primer_applied = cv2.addWeighted(smooth, alpha, result, 1 - alpha, 0)
    result[mask == 255] = primer_applied[mask == 255]

    if intensity > 0:
        glow = cv2.convertScaleAbs(result, alpha=1.02, beta=int(10 * intensity))
        result[mask == 255] = glow[mask == 255]

    return result


def apply_mascara(image, landmarks, intensity=0.65, density=0.7,
                  max_len_px=13, band_px=2, roots_target=34, micro_lashes=1, rng_seed=1234):
    img = image.copy()
    h, w = img.shape[:2]
    rng = np.random.default_rng(rng_seed)

    def bezier(p0, p1, p2, t):
        return (1-t)**2 * p0 + 2*(1-t)*t * p1 + t**2 * p2

    def curve_normals(curve):
        c = np.asarray(curve, dtype=np.float32)
        prev = np.roll(c, 1, axis=0)
        nxt  = np.roll(c, -1, axis=0)
        tang = nxt - prev
        tang /= (np.linalg.norm(tang, axis=1, keepdims=True) + 1e-6)
        nrms = np.stack([-tang[:,1], tang[:,0]], axis=1).astype(np.float32)
        centroid = c.mean(axis=0, keepdims=True)
        sign = np.sign(((c - centroid) * nrms).sum(axis=1, keepdims=True) + 1e-6)
        nrms *= sign
        return c.astype(np.float32), nrms

    def resample_by_arclength(poly, m):
        p = np.asarray(poly, dtype=np.float32)
        seg = np.linalg.norm(p[1:] - p[:-1], axis=1)
        s = np.concatenate([[0.0], np.cumsum(seg)])
        total = s[-1] if len(s) else 1.0
        if total < 1e-3:
            return p
        t = np.linspace(0, total, m)
        res = []
        j = 0
        for ti in t:
            while j+1 < len(s) and s[j+1] < ti:
                j += 1
            if j+1 >= len(p):
                res.append(p[-1])
            else:
                u = (ti - s[j]) / max(1e-6, s[j+1]-s[j])
                res.append(p[j]*(1-u) + p[j+1]*u)
        return np.vstack(res).astype(np.float32)

    def select_upper_lid(eye_pts):
        pts = np.asarray(eye_pts, dtype=np.float32)
        cy = np.median(pts[:,1])
        upper = pts[pts[:,1] < cy]
        if len(upper) < 3:
            upper = pts
        upper = upper[np.argsort(upper[:,0])]
        return upper

    def render_eye(eye_pts):
        upper = select_upper_lid(eye_pts)
        upper_rs = resample_by_arclength(upper, roots_target)
        roots, normals = curve_normals(upper_rs)

        lashA = np.zeros((h, w), dtype=np.float32)

        for i, p in enumerate(roots):
            if rng.random() > density:
                continue

            base_n = normals[i].astype(np.float32).reshape(2,)
            base_t = np.array([base_n[1], -base_n[0]], dtype=np.float32)

            edge_factor = 0.85 + 0.15*np.sin(np.pi * i / max(1, len(roots)-1))
            L0 = max_len_px * edge_factor

            count = 1 + max(0, int(micro_lashes))
            for k in range(count):
                ang = (rng.random()*2-1) * np.deg2rad(8.0) * (0.6 if k==0 else 1.0)
                n = (np.cos(ang)*base_n + np.sin(ang)*base_t)
                n /= (np.linalg.norm(n) + 1e-6)
                tvec = np.array([n[1], -n[0]], dtype=np.float32)

                L = L0 * (0.8 + 0.35*rng.random()) * (0.75 if k>0 else 1.0)

                skew = (rng.random()*2-1) * 0.28
                p0 = p.astype(np.float32) + base_t * rng.normal(0, 0.2)
                p2 = p0 + n * L
                p1 = p0 + n * (0.55*L) + tvec * (skew*0.35*L)

                steps = max(10, int(L))
                for s in range(steps):
                    tt = s/(steps-1)
                    q = bezier(p0, p1, p2, tt)
                    x, y = int(round(q[0])), int(round(q[1]))
                    if 0 <= x < w and 0 <= y < h:
                        r = max(0.6, 1.8 - 1.5*tt)
                        a = (1.0 - tt)**0.7 * (0.6 + 0.4*intensity) * (0.9 if k==0 else 0.6)
                        cv2.circle(lashA, (x, y), int(round(r)), a, -1, lineType=cv2.LINE_AA)

        band = np.zeros((h, w), dtype=np.uint8)
        cv2.polylines(band, [upper_rs.astype(np.int32)], False, 255, band_px, lineType=cv2.LINE_AA)
        dark = img.astype(np.float32) * (1.0 - 0.35*intensity)
        img[band==255] = dark[band==255].astype(np.uint8)

        a = np.clip(lashA, 0, 1.0)
        for c in range(3):
            img[:,:,c] = (img[:,:,c]*(1-a)).astype(np.uint8)

    render_eye(landmarks["left_eye"])
    render_eye(landmarks["right_eye"])
    return img


LEFT_EYE = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
RIGHT_EYE = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]

def apply_kajal(image, kajal_color_hex="#000000", intensity=3):
    hex_color = kajal_color_hex.lstrip("#")
    try:
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    except:
        rgb = (0, 0, 0)
    kajal_color_bgr = rgb[::-1]

    h, w = image.shape[:2]
    result_image = image.copy()

    # Use MediaPipe FaceMesh
    with mp_face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5
    ) as face_mesh:
        image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        results = face_mesh.process(image_bgr)

        if not results.multi_face_landmarks:
            # print("No face detected")
            return image

        face_landmarks = results.multi_face_landmarks[0]
        landmarks = []
        for lm in face_landmarks.landmark:
            x = int(lm.x * w)
            y = int(lm.y * h)
            landmarks.append([x, y])

        # Draw kajal on both eyes
        for eye_indices in [LEFT_EYE, RIGHT_EYE]:
            eye_points = np.array([landmarks[i] for i in eye_indices], dtype=np.int32)
            thickness = max(1, int(round(intensity * 2)))
            cv2.polylines(result_image, [eye_points], True, kajal_color_bgr, thickness, lineType=cv2.LINE_AA)

            # Optional subtle fill
            if thickness > 2:
                mask = np.zeros((h, w), dtype=np.uint8)
                cv2.polylines(mask, [eye_points], True, 255, max(1, thickness-1), lineType=cv2.LINE_AA)
                alpha = 0.1
                for c in range(3):
                    ch = result_image[:, :, c].astype(np.float32)
                    ch = ch * (1 - mask.astype(np.float32)/255.0 * alpha) + mask.astype(np.float32)/255.0 * alpha * kajal_color_bgr[c]
                    result_image[:, :, c] = np.clip(ch, 0, 255).astype(np.uint8)

    return result_image
    

def alpha_blend(base_bgr, overlay_bgr, mask_uint8):
    mask = (mask_uint8.astype(np.float32) / 255.0)[..., None]
    blended = overlay_bgr.astype(np.float32) * mask + base_bgr.astype(np.float32) * (1.0 - mask)
    return blended.astype(np.uint8)


def soft_mask_from_binary(bin_mask, sigma=7.0, normalize=True):
    soft = cv2.GaussianBlur(bin_mask, (0, 0), sigmaX=sigma, sigmaY=sigma, borderType=cv2.BORDER_DEFAULT)
    if normalize:
        m = soft.max()
        if m > 0:
            soft = (soft.astype(np.float32) * (255.0 / m)).clip(0, 255).astype(np.uint8)
    return soft


def apply_concealer_patch(img, center, radius=40, intensity=0.30, color=(160,180,220), feather_sigma=8.0):
    h, w = img.shape[:2]
    mask_bin = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(mask_bin, center, radius, 255, -1)

    mask_soft = soft_mask_from_binary(mask_bin, sigma=feather_sigma, normalize=True)
    mask_soft = (mask_soft.astype(np.float32) * float(intensity)).clip(0, 255).astype(np.uint8)

    overlay = img.copy()
    overlay[mask_bin > 0] = color
    return alpha_blend(img, overlay, mask_soft)

def apply_under_eye_crescent(img, lm, left_idx_inner, left_idx_outer,
                             right_idx_inner, right_idx_outer, hw,
                             width_ratio=0.18, height_ratio=0.10, intensity=0.30,
                             color=(160,180,220), feather_sigma=8.0):
    h, w = hw
    mask_bin = np.zeros(img.shape[:2], dtype=np.uint8)

    def safe_get(idx):
        if isinstance(lm, dict):
            return lm.get(idx, None)
        elif isinstance(lm, (list, tuple)) and 0 <= idx < len(lm):
            return lm[idx]
        return None

    def draw_crescent(inner, outer):
        if inner is None or outer is None:
            return
        x_inner = int(inner.x * w); y_inner = int(inner.y * h)
        x_outer = int(outer.x * w); y_outer = int(outer.y * h)
        cx = (x_inner + x_outer) // 2
        cy = max(y_inner, y_outer) + int(height_ratio * h) - int(0.09 * h)
        half_width = int(abs(x_outer - x_inner) * 0.6 + width_ratio * w * 0.5)
        half_height = int(height_ratio * h)
        cv2.ellipse(mask_bin, (cx, cy), (half_width, half_height),
                    angle=0, startAngle=0, endAngle=180, color=255, thickness=-1)
        offset_h = int(half_height * 0.6)
        cv2.ellipse(mask_bin, (cx, cy - offset_h), (half_width, half_height),
                    angle=0, startAngle=0, endAngle=180, color=0, thickness=-1)

    draw_crescent(safe_get(left_idx_inner), safe_get(left_idx_outer))

    draw_crescent(safe_get(right_idx_inner), safe_get(right_idx_outer))

    mask_soft = soft_mask_from_binary(mask_bin, sigma=feather_sigma, normalize=True)
    mask_soft = (mask_soft.astype(np.float32) * float(intensity)).clip(0, 255).astype(np.uint8)

    overlay = img.copy()
    overlay[mask_bin > 0] = color
    return alpha_blend(img, overlay, mask_soft)


# def safe_lm(lm, idx):
#     if isinstance(lm, dict):
#         return lm.get(idx, None)
#     elif isinstance(lm, (list, tuple)):
#         if 0 <= idx < len(lm):
#             return lm[idx]
#     return None


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def apply_concealer(img_bgr, intensity=0.8, color_hex="#FFDBAC"):
    blur_radius=16

    # ✅ Convert HEX → RGB for PIL
    color = tuple(int(color_hex.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))

    # ✅ Get image dimensions
    h, w = img_bgr.shape[:2]

    # ✅ Mediapipe face landmarks
    mp_face = mp.solutions.face_mesh
    with mp_face.FaceMesh(static_image_mode=True, max_num_faces=1,
                          refine_landmarks=True, min_detection_confidence=0.5) as face_mesh:
        rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)
        if not results.multi_face_landmarks:
            return img_bgr  # no face detected
        lm = results.multi_face_landmarks[0].landmark

    # --- Convert to PIL for drawing ---
    img_pil = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))

    # ✅ Helper: soft round patch
    def apply_patch(img, center, radius=20):
        mask = Image.new("L", img.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse([center[0]-radius, center[1]-radius,
              center[0]+radius, center[1]+radius], fill=255)

        # ✅ Blur only the mask, NOT the full image
        if blur_radius > 0:
            mask = mask.filter(ImageFilter.GaussianBlur(blur_radius))

        patch = Image.new("RGB", img.size, color)
        patch = Image.blend(img, patch, alpha=intensity)
        return Image.composite(patch, img, mask)

    # ✅ Helper: under-eye crescent
    def apply_under_eye(img, h, w):
        mask = Image.new("L", img.size, 0)
        draw = ImageDraw.Draw(mask)

        def draw_crescent(inner, outer):
            x_inner = int(inner.x * w); y_inner = int(inner.y * h)
            x_outer = int(outer.x * w); y_outer = int(outer.y * h)
            cx = (x_inner + x_outer) // 2
            cy = max(y_inner, y_outer) + int(0.085 * h) - int(0.18 * h)
            half_width = int(abs(x_outer - x_inner) * 0.6 + 0.05 * w * 0.5)
            half_height = int(0.085 * h)
            draw.ellipse([cx-half_width, cy,
                          cx+half_width, cy+half_height*2], fill=255)
            offset_h = int(half_height * 0.6)
            draw.ellipse([cx-half_width, cy-offset_h,
                          cx+half_width, cy+half_height*2-offset_h], fill=0)

        draw_crescent(lm[133], lm[33])     # left eye
        draw_crescent(lm[362], lm[263])    # right eye

        # ✅ Blur only the crescent mask
        if blur_radius > 0:
            mask = mask.filter(ImageFilter.GaussianBlur(blur_radius))

        patch = Image.new("RGB", img.size, color)
        patch = Image.blend(img, patch, alpha=intensity)
        return Image.composite(patch, img, mask)

    # ✅ Apply patches (you can adjust positions/radii as needed)
    img_pil = apply_patch(img_pil, (int(w*0.5), int(h*0.27)), radius=22)             # forehead
    img_pil = apply_under_eye(img_pil, h, w)                                        # under eyes
    img_pil = apply_patch(img_pil, (int(lm[1].x*w),  int(lm[1].y*h)-int(0.035*h)), radius=16)  # nose bridge
    img_pil = apply_patch(img_pil, (int(lm[152].x*w), int(lm[152].y*h)-int(0.03*h)), radius=20) # chin


    # ✅ Back to BGR for OpenCV
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

def safe_lm(lm, idx):
    if isinstance(lm, dict):
        return lm.get(idx, None)
    elif isinstance(lm, (list, tuple)):
        if 0 <= idx < len(lm):
            return lm[idx]
    return None


def apply_contour(img_bgr, intensity=0.2, color_hex="#644632"):
    blur_radius=12
    # Convert HEX → RGB
    base_color = tuple(int(color_hex.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    
    # Convert to PIL
    img = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
    img_rgba = img.convert("RGBA")
    
    # Face landmarks
    mp_face_mesh = mp.solutions.face_mesh
    with mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1) as face_mesh:
        rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)
        if not results.multi_face_landmarks:
            return img_bgr
        lm = results.multi_face_landmarks[0].landmark
    
    h, w = img_bgr.shape[:2]
    
    # --- Nose contour + forehead bands ---
    eyebrow_center = lm[9]
    nose_tip = lm[1]
    nose_left = lm[98]
    nose_right = lm[327]
    
    y_top = int(eyebrow_center.y * h)
    y_bottom = int(nose_tip.y * h)
    x_center = int(nose_tip.x * w)
    x_left = int(nose_left.x * w)
    x_right = int(nose_right.x * w)
    
    nose_width = x_right - x_left
    line_offset = max(3, int(nose_width * 0.2))
    line_width = max(5, int(nose_width * 0.25))
    
    # Adjust height
    height_scale = 0.6
    mid = (y_top + y_bottom) // 2
    y_top_new = int(mid - (y_bottom - y_top) * height_scale / 2)
    y_bottom_new = int(mid + (y_bottom - y_top) * height_scale / 2)
    y_bottom_new += int((y_bottom - y_top) * 0.15)
    
    mask = Image.new("L", img.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    
    # Nose lines
    mask_draw.line([(x_center - line_offset, y_top_new), (x_center - line_offset, y_bottom_new)],
                   fill=255, width=line_width)
    mask_draw.line([(x_center + line_offset, y_top_new), (x_center + line_offset, y_bottom_new)],
                   fill=255, width=line_width)
    radius = int(line_offset * 1.4)
    bbox = [x_center - radius, y_bottom_new - radius, x_center + radius, y_bottom_new + radius]
    mask_draw.arc(bbox, start=0, end=180, fill=255, width=line_width)
    
    # Forehead bands
    forehead_y = int(eyebrow_center.y * h) - int(h * 0.10)
    forehead_band_width = int(nose_width * 0.9)
    forehead_band_height = int(nose_width * 0.7)
    gap_between_bands = int(nose_width * 0.6)
    tilt_angle = -30
    
    def draw_band(x_start, tilt):
        band_mask = Image.new("L", img.size, 0)
        band_draw = ImageDraw.Draw(band_mask)
        band_box = [(x_start, forehead_y),
                    (x_start + forehead_band_width, forehead_y + forehead_band_height)]
        band_draw.rounded_rectangle(band_box, radius=forehead_band_height//2, fill=255)
        return band_mask.rotate(tilt, center=(x_start + forehead_band_width//2, forehead_y), fillcolor=0)
    
    left_band = draw_band(x_center - gap_between_bands - forehead_band_width, -tilt_angle)
    right_band = draw_band(x_center + gap_between_bands, tilt_angle)
    mask = ImageChops.add(mask, left_band)
    mask = ImageChops.add(mask, right_band)
    
    # --- Jawline contour ---
    left_jaw_indices = [234, 93, 132, 58, 172, 136, 150, 149, 176, 148]
    right_jaw_indices = [454, 397, 288, 379, 378, 400, 377]
    
    def jaw_points(indices, shift=0):
        points = [(int(lm[i].x * w) + shift, int(lm[i].y * h)) for i in indices]
        lip_upper_y = int(lm[13].y * h)
        return [(x, y) for x, y in points if y > lip_upper_y]
    
    shift_x = int(nose_width * 0.05)
    left_jaw_pts = jaw_points(left_jaw_indices, -shift_x)
    right_jaw_pts = jaw_points(right_jaw_indices, shift_x)
    
    jaw_mask = Image.new("L", img.size, 0)
    jaw_draw = ImageDraw.Draw(jaw_mask)
    jaw_line_width = max(6, int(nose_width * 0.2))
    
    for pts in [left_jaw_pts, right_jaw_pts]:
        if len(pts) > 1:
            jaw_draw.line(pts, fill=255, width=jaw_line_width, joint="curve")
            jaw_draw.ellipse([pts[0][0]-jaw_line_width//2, pts[0][1]-jaw_line_width//2,
                              pts[0][0]+jaw_line_width//2, pts[0][1]+jaw_line_width//2], fill=255)
            jaw_draw.ellipse([pts[-1][0]-jaw_line_width//2, pts[-1][1]-jaw_line_width//2,
                              pts[-1][0]+jaw_line_width//2, pts[-1][1]+jaw_line_width//2], fill=255)
    
    mask = ImageChops.add(mask, jaw_mask)
    
    # --- Cheekbone tilted lines ---
    def rotate_point(x, y, cx, cy, angle_deg):
        angle = math.radians(angle_deg)
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        dx, dy = x - cx, y - cy
        qx = cx + cos_a*dx - sin_a*dy
        qy = cy + cos_a*dy + sin_a*dx
        return int(qx), int(qy)
    
    def shorten_line(x1, y1, x2, y2, factor):
        cx, cy = (x1 + x2)/2, (y1 + y2)/2
        return int(cx + (x1-cx)*factor), int(cy + (y1-cy)*factor), int(cx + (x2-cx)*factor), int(cy + (y2-cy)*factor)
    
    tilt_angle_cheek = -15
    cheek_len_factor = 0.5
    
    left_cheek_pts = shorten_line(int(lm[234].x*w), int(lm[234].y*h),
                                  int(lm[61].x*w), int(lm[61].y*h), cheek_len_factor)
    right_cheek_pts = shorten_line(int(lm[454].x*w), int(lm[454].y*h),
                                   int(lm[291].x*w), int(lm[291].y*h), cheek_len_factor)
    
    cheek_mask = Image.new("L", img.size, 0)
    cheek_draw = ImageDraw.Draw(cheek_mask)
    cheek_line_width = max(6, int(nose_width*0.25))
    
    cheek_draw.line([left_cheek_pts[:2], left_cheek_pts[2:]], fill=255, width=cheek_line_width)
    cheek_draw.line([right_cheek_pts[:2], right_cheek_pts[2:]], fill=255, width=cheek_line_width)
    
    for x, y in [left_cheek_pts[:2], left_cheek_pts[2:], right_cheek_pts[:2], right_cheek_pts[2:]]:
        cheek_draw.ellipse([x-cheek_line_width//2, y-cheek_line_width//2, x+cheek_line_width//2, y+cheek_line_width//2], fill=255)
    
    mask = ImageChops.add(mask, cheek_mask)
    
    # --- Blur & intensity ---
    mask_blur = mask.filter(ImageFilter.GaussianBlur(blur_radius))
    mask_array = np.array(mask_blur).astype(np.float32) * intensity
    mask_array = np.clip(mask_array, 0, 255).astype(np.uint8)
    
    overlay = Image.new("RGBA", img.size, base_color + (255,))
    overlay.putalpha(Image.fromarray(mask_array))
    
    img_final = Image.alpha_composite(img_rgba, overlay).convert("RGB")
    return cv2.cvtColor(np.array(img_final), cv2.COLOR_RGB2BGR)