from config import Config

broker_url = Config.CELERY_BROKER_URL
result_backend = Config.CELERY_RESULT_BACKEND

imports = ("celery_tasks",)
timezone = "Asia/Kolkata"
worker_hijack_root_logger = False
hostname = 'localhost'
worker_pool = 'solo'

beat_schedule = {
    "process-email-queue": {
        "task": "celery_tasks.process_email_queue",
        "schedule": 10.0,  # every 24 hours (1 day)
        # OR use crontab for a specific time
        # "schedule": crontab(hour=9, minute=0),
    },
    "cleanup-old-data": {
        "task": "celery_tasks.cleanup_old_data",
        "schedule": 86400.0,  # every day
    },
}
