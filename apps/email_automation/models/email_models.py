from datetime import datetime
# from click import DateTime
from sqlalchemy import Column, Float, Integer, String, Text, TIMESTAMP, ForeignKey, JSON, Boolean, CheckConstraint, DateTime
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "userfetch"
    id = Column(Integer, primary_key=True)
    email = Column(Text, unique=True, nullable=False)
    name = Column(Text)
    activities = relationship("UserActivity", back_populates="user")
    email_queue = relationship("EmailQueue", back_populates="user")
    email_logs = relationship("EmailLog", back_populates="user")
    preferences = relationship("UserEmailPreferences", back_populates="user",uselist=False)


class EmailTemplate(Base):
    __tablename__ = "email_templates"
    id = Column(Integer, primary_key=True)
    subject = Column(Text, nullable=False)
    template_file = Column(Text, nullable=False)
    queued_emails = relationship("EmailQueue", back_populates="template")
    logs = relationship("EmailLog", back_populates="template")


class EmailQueue(Base):
    __tablename__ = "email_queue"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    template_id = Column(Integer, ForeignKey("email_templates.id"))
    context = Column(JSON)
    scheduled_at = Column(TIMESTAMP, default=datetime.utcnow)
    processed_at = Column(TIMESTAMP)
    status = Column(Text, default="pending")
    priority = Column(Integer, default=0)

    __table_args__ = (CheckConstraint("status IN ('pending','sent','failed')", name="email_queue_status_check"),)

    user = relationship("User", back_populates="email_queue")
    template = relationship("EmailTemplate", back_populates="queued_emails")


class EmailLog(Base):
    __tablename__ = "email_log"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    template_id = Column(Integer, ForeignKey("email_templates.id"))
    status = Column(Text, default="sent")
    sent_at = Column(TIMESTAMP, default=datetime.utcnow)

    __table_args__ = (CheckConstraint("status IN ('sent','opened','clicked','failed')", name="email_log_status_check"),)

    user = relationship("User", back_populates="email_logs")
    template = relationship("EmailTemplate", back_populates="logs")


class UserActivity(Base):
    __tablename__ = "user_activity"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    activity_type = Column(Text)
    activity_metadata = Column(JSON)
    timestamp = Column(TIMESTAMP, default=datetime.utcnow)
    user = relationship("User", back_populates="activities")


class UserEmailPreferences(Base):
    __tablename__ = "user_email_preferences"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    frequency = Column(Text, default="daily")
    unsubscribed = Column(Boolean, default=False)
    last_email_sent = Column(TIMESTAMP)
    __table_args__ = (CheckConstraint("frequency IN ('daily','weekly','monthly')", name="email_pref_freq_check"),)
    user = relationship("User", back_populates="preferences")