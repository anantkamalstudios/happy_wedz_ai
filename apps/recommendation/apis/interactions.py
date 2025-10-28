from flask import Blueprint, jsonify, request, send_file, abort
from ..models import UserInteraction
from db import db
from datetime import datetime, timedelta
from ..services.cache import user_interaction_cache
from ..models.interaction import Venue, Vendor
import io

interactions_bp = Blueprint('interactions', __name__)

# Serve vendor image as base64 by ID
import base64

@interactions_bp.route("/vendor_image_base64/<int:vendor_id>", methods=["GET"])
def get_vendor_image_base64(vendor_id):
    vendor = Vendor.query.get(vendor_id)
    if not vendor or not vendor.image or not vendor.image_type:
        abort(404)
    image_base64 = base64.b64encode(vendor.image).decode('utf-8')
    return jsonify({
        "image_base64": image_base64,
        "image_type": vendor.image_type
    })

# Serve venue image as base64 by ID
@interactions_bp.route("/venue_image_base64/<int:venue_id>", methods=["GET"])
def get_venue_image_base64(venue_id):
    venue = Venue.query.get(venue_id)
    if not venue or not venue.image or not venue.image_type:
        abort(404)
    image_base64 = base64.b64encode(venue.image).decode('utf-8')
    return jsonify({
        "image_base64": image_base64,
        "image_type": venue.image_type
    })

@interactions_bp.route("/", methods=["POST"])
def interact():
    data = request.json
    required_fields = ['user_id', 'item_type', 'item_id', 'interaction_type']
    
    if not all(field in data for field in required_fields):
        return jsonify({"success": False, "message": "All fields required"}), 400
    
    # Prevent spam interactions
    recent_interaction = UserInteraction.query.filter(
        UserInteraction.user_id == data['user_id'],
        UserInteraction.item_id == data['item_id'],
        UserInteraction.interaction_type == data['interaction_type'],
        UserInteraction.timestamp >= datetime.utcnow() - timedelta(minutes=5)
    ).first()
    
    if recent_interaction:
        return jsonify({"success": True, "message": "Interaction already recorded"})
    
    # Add interaction to database
    interaction = UserInteraction(
        user_id=data['user_id'],
        item_type=data['item_type'],
        item_id=data['item_id'],
        interaction_type=data['interaction_type']
    )
    db.session.add(interaction)
    db.session.commit()
    
    # Update cache
    user_id = data['user_id']
    user_interaction_cache[user_id]['interactions'].append({
        'item_id': data['item_id'],
        'item_type': data['item_type'],
        'interaction_type': data['interaction_type'],
        'timestamp': datetime.utcnow(),
        'days_ago': 0
    })
    
    return jsonify({"success": True, "message": "Interaction logged successfully"})