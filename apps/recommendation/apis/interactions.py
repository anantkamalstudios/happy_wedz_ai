from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from db import db
from apps.recommendation.models.interaction import UserInteraction

interactions_bp = Blueprint("interactions", __name__)

# In-memory cache (imported from services later)
from apps.recommendation.services.cache import user_interaction_cache

@interactions_bp.route("/interact", methods=["POST"])
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

    # Add new interaction
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
