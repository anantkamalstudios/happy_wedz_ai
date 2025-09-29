import json
from datetime import datetime, timedelta
import logging
import os

from db import get_db  # Use relative import if 'db.py' is in the same package

logger = logging.getLogger(__name__)

class ActivityTracker:
    def log_activity(self, user_id, activity_type, metadata=None):
        """
        Track user activity and queue emails if needed.
        """
        metadata = metadata or {}
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    # 1️⃣ Log the activity
                    cur.execute("""
                        INSERT INTO user_activity (user_id, activity_type, metadata, timestamp)
                        VALUES (%s, %s, %s, NOW())
                    """, (user_id, activity_type, json.dumps(metadata)))

                    # 2️⃣ Decide if an email should be queued
                    self._queue_email_if_needed(conn, user_id, activity_type, metadata)

                conn.commit()
            logger.info(f"📝 Activity logged: {activity_type} for user {user_id}")
        except Exception as e:
            logger.exception(f"❌ Failed to log activity: {e}")

    def _queue_email_if_needed(self, conn, user_id, activity_type, metadata):
        """
        Example rules for queuing emails based on activity.
        """
        with conn.cursor() as cur:
            # Example: If user views wishlist but hasn't added anything in 1 hour
            if activity_type == "wishlist_viewed":
                cur.execute("""
                    SELECT timestamp
                    FROM user_activity
                    WHERE user_id=%s AND activity_type='wishlist_added'
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (user_id,))
                last_added = cur.fetchone()
                now = datetime.now()
                if not last_added or (now - last_added[0]) > timedelta(hours=1):
                    personalization = {"user_name": self._get_user_name(conn, user_id)}
                    cur.execute("""
                        INSERT INTO email_queue (user_id, email_type, feature, personalization_data, scheduled_at, status)
                        VALUES (%s, %s, %s, %s, NOW() + INTERVAL '5 minutes', 'pending')
                    """, (user_id, "reminder", "wishlist", json.dumps(personalization)))
                    logger.info(f"📧 Queued reminder email for user {user_id}")

    def _get_user_name(self, conn, user_id):
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM users WHERE id=%s", (user_id,))
            result = cur.fetchone()
            return result[0] if result else "User"
