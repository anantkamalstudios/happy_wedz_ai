import logging
from db import get_db

logger = logging.getLogger(__name__)

class EmailTriggerEngine:
    def __init__(self):
        pass

    def schedule_email(self, user_id, template_id, context):
        """
        Schedule an email by inserting into queue.
        """
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO email_queue (user_id, template_id, context, scheduled_at, status)
                        VALUES (%s, %s, %s, NOW(), 'pending')
                    """, (user_id, template_id, context))
                conn.commit()
            logger.info(f"📬 Email queued for user {user_id}, template {template_id}")
        except Exception as e:
            logger.exception(f"❌ Failed to queue email: {e}")
