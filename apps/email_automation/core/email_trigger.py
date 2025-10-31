import random
import json
from datetime import datetime, timedelta
from db import SessionLocal
from apps.email_automation.models.email_models import EmailTemplate, EmailQueue
import logging

logger = logging.getLogger(__name__)

class EmailTriggerEngine:
    def __init__(self):
        pass

    def schedule_email(self, user_id, template_id, context, delay_minutes=0):
        try:
            session = SessionLocal()
            scheduled_at = datetime.utcnow() + timedelta(minutes=delay_minutes)
            email_queue = EmailQueue(
                user_id=user_id,
                template_id=template_id,
                context=json.dumps(context),
                scheduled_at=scheduled_at,
                status='pending'
            )
            session.add(email_queue)
            session.commit()
            logger.info(f"📬 Email queued for user {user_id}, template {template_id}")
        except Exception as e:
            session.rollback()
            logger.exception(f" Failed to queue email: {e}")
        finally:
            session.close()

    def schedule_daily_email(self, user_id):
        """
        Selects a random email template and schedules one email per day.
        """
        try:
            session = SessionLocal()
            templates = session.query(EmailTemplate.id).all()
            if not templates:
                logger.warning(" No templates found.")
                return

            template_ids = [t[0] for t in templates]
            chosen = random.choice(template_ids)
            scheduled_time = datetime.utcnow() + timedelta(days=1)

            email_queue = EmailQueue(
                user_id=user_id,
                template_id=chosen,
                context=json.dumps({"type": "daily_random"}),
                scheduled_at=scheduled_time,
                status='pending'
            )
            session.add(email_queue)
            session.commit()
            logger.info(f" Daily random email scheduled for user {user_id}")
        except Exception as e:
            session.rollback()
            logger.exception(f" Failed to schedule daily email: {e}")
        finally:
            session.close()
