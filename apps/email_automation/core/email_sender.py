import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader
from config import create_app

logger = logging.getLogger(__name__)
env = Environment(loader=FileSystemLoader("templates"))

class EmailSender:
    def __init__(self, session):
        self.session = session
        self.smtp_server = create_app.MAIL_SERVER
        self.smtp_port = create_app.MAIL_PORT
        self.username = create_app.MAIL_USERNAME
        self.password = create_app.MAIL_PASSWORD
        self.from_email = create_app.MAIL_DEFAULT_SENDER

    def send_email(self, to_email, subject, template_name, context):
        try:
            template = env.get_template(template_name)
            html_body = template.render(**context)

            msg = MIMEMultipart("alternative")
            msg["From"] = self.from_email
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.from_email, to_email, msg.as_string())

            logger.info(f" Email sent to {to_email} - {subject}")
            return True
        except Exception as e:
            logger.exception(f" Failed to send email to {to_email}: {e}")
            return False
