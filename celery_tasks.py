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

EMAIL_TEMPLATES = {
    "welcome": "welcome_template.html",
    "wishlist": "wishlist_template.html",
    "todo": "todo_template.html",
    "vendor_recommendation": "vendor_template.html",
    "budget_update": "budget.html",
    "budget_planner": "budget_planner/feature_intro.html",
    "guestlist": "guestlist/reminder.html",
}


@celery.task(bind=True, max_retries=3)
def process_email_queue(self, batch_size: int = 50):
    """
    Process pending emails from the queue using SQLAlchemy ORM.
    """
    try:
        session: Session = SessionLocal()
        sender = EmailSender(session)

        # Fetch pending emails using ORM
        emails = (
            session.query(EmailQueue)
            .join(User, EmailQueue.user_id == User.id)
            .outerjoin(UserEmailPreferences, User.id == UserEmailPreferences.user_id)
            .filter(
                EmailQueue.status == 'pending',
                EmailQueue.scheduled_at <= func.now(),
                (UserEmailPreferences.unsubscribed == False) | (UserEmailPreferences.unsubscribed.is_(None))
            )
            .order_by(EmailQueue.priority.desc(), EmailQueue.scheduled_at.asc())
            .limit(batch_size)
            .all()
        )

        if not emails:
            logger.info("No pending emails found.")
            return

        for eq in emails:
            try:
                template_file = EMAIL_TEMPLATES.get(eq.feature or eq.email_type)
                if not template_file:
                    raise ValueError(f"No template found for feature/email_type: {eq.feature}/{eq.email_type}")

                context = {
                    "name": eq.user.name,
                    "city": getattr(eq, "city", None),
                    **(eq.personalization_data or {})
                }

                success = sender.send_email(
                    to_email=eq.user.email,
                    subject=f"{eq.feature.capitalize()} Update" if eq.feature else "Update",
                    template_name=template_file,
                    context=context
                )

                if not success:
                    raise Exception("Email sending failed")

                eq.status = "sent"
                session.commit()
                logger.info(f"Email sent successfully to {eq.user.email} (Queue ID: {eq.id})")

            except Exception as e:
                eq.status = "failed"
                session.commit()
                logger.error(f"Failed to send email to {eq.user.email} (Queue ID: {eq.id}): {e}")

    except Exception as e:
        logger.error(f"Error in process_email_queue task: {e}")
        session.rollback()
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    finally:
        session.close()
