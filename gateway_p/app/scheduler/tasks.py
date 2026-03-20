from app.scheduler.worker import celery_app

@celery_app.task
def process_payment_background(payment_id: str):
    print(f"Processing payment {payment_id} in background")
