from celery import Celery
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func
from db import SessionLocal
from email_sender import EmailSender
from models import User, EmailQueue, UserEmailPreferences
from config import Config

celery = Celery("wedding_email_system")
celery.config_from_object("celeryconfig")

logger = logging.getLogger(__name__)

@celery.task(bind=True, max_retries=3)
def process_email_queue(self, batch_size: int = 50):
    try:
        session: Session = SessionLocal()
        sender = EmailSender(session)

        emails = (
            session.query(EmailQueue)
            .join(User, EmailQueue.user_id == User.id)
            .outerjoin(UserEmailPreferences, User.id == UserEmailPreferences.user_id)
            .filter(
                EmailQueue.status == 'pending',
                EmailQueue.scheduled_at <= func.now(),
                (UserEmailPreferences.unsubscribed == False) | (UserEmailPreferences.unsubscribed.is_(None))
            )
            .order_by(EmailQueue.scheduled_at.asc())
            .limit(batch_size)
            .all()
        )

        if not emails:
            logger.info("No pending emails found.")
            return

        for eq in emails:
            try:
                template_name = eq.template.template_file
                context = eq.context or {}

                success = sender.send_email(
                    to_email=eq.user.email,
                    subject=eq.template.subject,
                    template_name=template_name,
                    context=context
                )

                eq.status = "sent" if success else "failed"
                session.commit()
            except Exception as e:
                eq.status = "failed"
                session.commit()
                logger.error(f"Failed to send email (Queue ID {eq.id}): {e}")
    except Exception as e:
        session.rollback()
        logger.error(f"Error in process_email_queue task: {e}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    finally:
        session.close()
