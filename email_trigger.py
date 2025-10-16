import random
import json
from datetime import datetime, timedelta
from db import get_db
import logging

logger = logging.getLogger(__name__)

class EmailTriggerEngine:
    def __init__(self):
        pass

    def schedule_email(self, user_id, template_id, context, delay_minutes=0):
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO email_queue (user_id, template_id, context, scheduled_at, status)
                        VALUES (%s, %s, %s, NOW() + INTERVAL '%s minutes', 'pending')
                    """, (user_id, template_id, json.dumps(context), delay_minutes))
                conn.commit()
            logger.info(f"📬 Email queued for user {user_id}, template {template_id}")
        except Exception as e:
            logger.exception(f" Failed to queue email: {e}")

    def schedule_daily_email(self, user_id):
        """
        Selects a random email template and schedules one email per day.
        """
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM email_templates")
                    templates = [row[0] for row in cur.fetchall()]
                    if not templates:
                        logger.warning(" No templates found.")
                        return

                    chosen = random.choice(templates)
                    scheduled_time = datetime.now() + timedelta(days=1)

                    cur.execute("""
                        INSERT INTO email_queue (user_id, template_id, context, scheduled_at, status)
                        VALUES (%s, %s, %s, %s, 'pending')
                    """, (user_id, chosen, json.dumps({"type": "daily_random"}), scheduled_time))
                conn.commit()
            logger.info(f" Daily random email scheduled for user {user_id}")
        except Exception as e:
            logger.exception(f" Failed to schedule daily email: {e}")
