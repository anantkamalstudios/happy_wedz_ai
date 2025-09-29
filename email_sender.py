# email_sender.py (production-ready)

import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader
from db import get_db
from config import Config

logger = logging.getLogger(__name__)

# Setup Jinja2 environment for email templates
env = Environment(loader=FileSystemLoader("templates"))

class EmailSender:
    def __init__(self, db):
        self.db = db
        self.smtp_server = Config.MAIL_SERVER
        self.smtp_port = Config.MAIL_PORT
        self.username = Config.MAIL_USERNAME
        self.password = Config.MAIL_PASSWORD
        self.from_email = Config.MAIL_DEFAULT_SENDER

    def send_email(self, to_email, subject, template_name, context):
        """
        Send email using SMTP with HTML template.
        """
        try:
            # Load Jinja2 template
            template = env.get_template(template_name)
            html_body = template.render(**context)

            # Build email
            msg = MIMEMultipart("alternative")
            msg["From"] = self.from_email
            msg["To"] = to_email
            msg["Subject"] = subject

            msg.attach(MIMEText(html_body, "html"))

            # Send via Gmail SMTP
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.from_email, to_email, msg.as_string())

            logger.info(f"✅ Email sent to {to_email} with subject '{subject}'")
            return True

        except Exception as e:
            logger.exception(f"❌ Failed to send email to {to_email}: {e}")
            return False

    def process_queue(self):
        """
        Process all pending emails from queue.
        """
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT eq.id, u.email, et.subject, et.template_file, eq.context
                    FROM email_queue eq
                    JOIN users u ON eq.user_id = u.id
                    JOIN email_templates et ON eq.template_id = et.id
                    WHERE eq.status = 'pending'
                    ORDER BY eq.scheduled_at ASC
                    LIMIT 20
                """)
                emails = cur.fetchall()

                for email in emails:
                    eq_id, to_email, subject, template_file, context = email

                    success = self.send_email(
                        to_email=to_email,
                        subject=subject,
                        template_name=template_file,
                        context=context
                    )

                    status = "sent" if success else "failed"
                    cur.execute(
                        "UPDATE email_queue SET status=%s, processed_at=NOW() WHERE id=%s",
                        (status, eq_id)
                    )
                    cur.execute(
                        "INSERT INTO email_log (user_id, template_id, status, sent_at) "
                        "VALUES ((SELECT user_id FROM email_queue WHERE id=%s), "
                        "(SELECT template_id FROM email_queue WHERE id=%s), %s, NOW())",
                        (eq_id, eq_id, status)
                    )

                conn.commit()

    def _send_email(self, email_data):
        """
        Send email based on email_data.
        """
        # For now, assume a default template and subject
        subject = f"Email for {email_data['email_type']}"
        template_name = "default.html"  # assume a template exists
        context = {
            'first_name': email_data['first_name'],
            'feature': email_data['feature'],
            'city': email_data['city'],
            **email_data['personalization_data']
        }
        return self.send_email(email_data['email'], subject, template_name, context)

    def _mark_as_sent(self, email_id):
        """
        Mark email as sent.
        """
        with self.db.cursor() as cur:
            cur.execute("UPDATE email_queue SET status='sent', processed_at=NOW() WHERE id=%s", (email_id,))
            self.db.commit()

    def _mark_as_failed(self, email_id, error):
        """
        Mark email as failed.
        """
        with self.db.cursor() as cur:
            cur.execute("UPDATE email_queue SET status='failed', error_message=%s, processed_at=NOW() WHERE id=%s", (error, email_id))
            self.db.commit()
