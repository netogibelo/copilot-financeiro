from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "copilot_financeiro",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Sao_Paulo",
    enable_utc=True,
    beat_schedule={
        # Run subscription detection every day at 2am
        "detect-subscriptions-daily": {
            "task": "app.tasks.tasks.detect_subscriptions_all_users",
            "schedule": crontab(hour=2, minute=0),
        },
        # Run cashflow predictions every day at 3am
        "predict-cashflow-daily": {
            "task": "app.tasks.tasks.predict_cashflow_all_users",
            "schedule": crontab(hour=3, minute=0),
        },
        # Weekly AI report every Sunday at 8am
        "weekly-ai-report": {
            "task": "app.tasks.tasks.generate_weekly_reports",
            "schedule": crontab(hour=8, minute=0, day_of_week=0),
        },
    },
)
