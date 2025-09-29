from flask import Flask, request, jsonify
from activity_tracker import ActivityTracker
from email_trigger import EmailTriggerEngine
from db import get_db

app = Flask(__name__)
tracker = ActivityTracker()
trigger = EmailTriggerEngine()

@app.route("/api/activity", methods=["POST"])
def track_activity():
    data = request.json
    user_id = data["user_id"]
    activity_type = data["activity_type"]
    metadata = data.get("metadata", {})
    tracker.log_activity(user_id, activity_type, metadata)
    return jsonify({"status": "ok"})

@app.route("/api/trigger-email", methods=["POST"])
def trigger_email():
    data = request.json
    user_id = data["user_id"]
    template_id = data["template_id"]
    context = data.get("context", {})
    trigger.schedule_email(user_id, template_id, context)
    return jsonify({"status": "queued"})

if __name__ == "__main__":
    app.run(debug=True)
