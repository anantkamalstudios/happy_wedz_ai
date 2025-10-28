from config import Config

broker_url = Config.CELERY_BROKER_URL
result_backend = Config.CELERY_RESULT_BACKEND

imports = ("celery_tasks",)
timezone = "Asia/Kolkata"
worker_hijack_root_logger = False
worker_pool = "solo"

beat_schedule = {
    "process-email-queue": {
        "task": "celery_tasks.process_email_queue",
        "schedule": 60.0,  # run every minute for testing (change to 86400 for 24h)
    },
}
