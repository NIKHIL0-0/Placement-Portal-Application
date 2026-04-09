from app import create_app
from app.celery_utils import create_celery


flask_app = create_app()
celery = create_celery(flask_app)


if __name__ == "__main__":
    celery.worker_main()
