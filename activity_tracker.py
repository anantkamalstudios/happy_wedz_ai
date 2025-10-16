import json
import logging
from datetime import datetime, timedelta
from db import get_db
from email_trigger import EmailTriggerEngine

logger = logging.getLogger(__name__)

class ActivityTracker:
    def _send_welcome_email_on_first_visit(self, user_id):
        """Send welcome email only if this is the user's first page view."""
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    # Check if user has any previous page_view activities
                    cur.execute("""
                        SELECT COUNT(*) FROM user_activity
                        WHERE user_id = %s AND activity_type = 'page_view'
                    """, (user_id,))
                    count = cur.fetchone()[0]
                    if count == 1:  # This is the first page view
                        EmailTriggerEngine().schedule_email(user_id, 1, {"type": "welcome"})  # Assuming template_id 1 is welcome template
        except Exception as e:
            logger.exception(f" Failed to send welcome email: {e}")

    def log_activity(self, user_id, activity_type, metadata=None):
        metadata = metadata or {}
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO user_activity (user_id, activity_type, activity_metadata, timestamp)
                        VALUES (%s, %s, %s, NOW())
                    """, (user_id, activity_type, json.dumps(metadata)))
                conn.commit()
            logger.info(f" Activity logged: {activity_type} for user {user_id}")

            if activity_type == "login":
                EmailTriggerEngine().schedule_daily_email(user_id)
            elif activity_type == "page_view":
                # Send welcome email on first page view
                self._send_welcome_email_on_first_visit(user_id)
            elif activity_type == "budget_created":
                # Send budget planning email
                EmailTriggerEngine().schedule_email(user_id, 2, {"type": "budget_created"})  # Assuming template_id 2 is budget template
            elif activity_type == "vendor_contacted":
                # Send vendor reminder email
                EmailTriggerEngine().schedule_email(user_id, 3, {"type": "vendor_contacted"})  # Assuming template_id 3 is vendor template
            elif activity_type == "todo_created":
                # Send todo reminder email
                EmailTriggerEngine().schedule_email(user_id, 4, {"type": "todo_created"})  # Assuming template_id 4 is todo template
            elif activity_type == "wishlist_added":
                # Send wishlist email
                EmailTriggerEngine().schedule_email(user_id, 5, {"type": "wishlist_added"})  # Assuming template_id 5 is wishlist template

        except Exception as e:
            logger.exception(f" Failed to log activity: {e}")
