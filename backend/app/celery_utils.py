from celery import Celery
from celery.schedules import crontab


def create_celery(app):
    celery = Celery(
        app.import_name,
        broker=app.config["CELERY_BROKER_URL"],
        backend=app.config["CELERY_RESULT_BACKEND"],
    )

    celery.conf.update(
        broker_url=app.config["CELERY_BROKER_URL"],
        result_backend=app.config["CELERY_RESULT_BACKEND"],
    )
    celery.conf.imports = ("app.tasks",)
    celery.conf.beat_schedule = {
        "daily-student-reminders": {
            "task": "app.tasks.send_daily_student_reminders",
            "schedule": crontab(
                hour=app.config.get("DAILY_REMINDER_HOUR", 9),
                minute=app.config.get("DAILY_REMINDER_MINUTE", 0),
            ),
        },
        "monthly-admin-report": {
            "task": "app.tasks.send_monthly_admin_report",
            "schedule": crontab(
                day_of_month="1",
                hour=app.config.get("MONTHLY_REPORT_HOUR", 8),
                minute=app.config.get("MONTHLY_REPORT_MINUTE", 0),
            ),
        },
    }

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery
