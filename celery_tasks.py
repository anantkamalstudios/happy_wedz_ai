from celery import Celery
import logging
from email_sender import EmailSender
from db import get_db
from config import Config
from psycopg2.extras import RealDictCursor

celery = Celery("wedding_email_system")
celery.config_from_object("celeryconfig")

logger = logging.getLogger(__name__)

# Map email types/features to template files (HTML or text)
EMAIL_TEMPLATES = {
    "welcome": "welcome_template.html",
    "wishlist": "wishlist_template.html",
    "todo": "todo_template.html",
    "vendor_recommendation": "vendor_template.html",
    "budget_update": "budget.html",
    "budget_planner": "budget_planner/feature_intro.html",
    "guestlist": "guestlist/reminder.html",
    # Add more feature-specific templates here
}


@celery.task(bind=True, max_retries=3)
def process_email_queue(self, batch_size: int = 50):
    """
    Process pending emails from the queue with dynamic template rendering.
    """
    try:
        with get_db() as db:
            sender = EmailSender(db)
            with db.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT eq.id, eq.user_id, eq.email_type, eq.feature, eq.city, eq.personalization_data, 
                           u.email, u.name as first_name
                    FROM email_queue eq
                    JOIN users u ON eq.user_id = u.id
                    LEFT JOIN user_email_preferences ep ON eq.user_id = ep.user_id
                    WHERE eq.status = 'pending'
                      AND eq.scheduled_at <= NOW()
                      AND (ep.unsubscribed IS NULL OR ep.unsubscribed = FALSE)
                    ORDER BY eq.priority DESC, eq.scheduled_at ASC
                    LIMIT %s
                """, (batch_size,))

                emails = cursor.fetchall()

            if not emails:
                logger.info("No pending emails found.")
                return

            for email_data in emails:
                try:
                    # Determine template based on email_type or feature
                    template_file = EMAIL_TEMPLATES.get(
                        email_data['feature'] or email_data['email_type']
                    )
                    if not template_file:
                        raise ValueError(f"No template found for feature/email_type: {email_data['feature']}/{email_data['email_type']}")

                    # Prepare context for template rendering
                    context = {
                        "name": email_data["first_name"],
                        "city": email_data["city"],
                        **(email_data["personalization_data"] or {})
                    }

                    # Send the email
                    success = sender.send_email(
                        to_email=email_data["email"],
                        subject=f"{email_data['feature'].capitalize()} Update",
                        template_name=template_file,
                        context=context
                    )
                    if not success:
                        raise Exception("Email sending failed")

                    # Mark as sent
                    sender._mark_as_sent(email_data['id'])
                    logger.info(f"Email sent successfully to {email_data['email']} (Queue ID: {email_data['id']})")

                except Exception as e:
                    # Mark as failed and log error
                    sender._mark_as_failed(email_data['id'], str(e))
                    logger.error(f"Failed to send email to {email_data['email']} (Queue ID: {email_data['id']}): {e}")

    except Exception as e:
        logger.error(f"Error in process_email_queue task: {e}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
