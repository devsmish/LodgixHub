from celery import shared_task
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)

@shared_task
def run_update_listing_current_price():
    logger.info("Starting a scheduled task: update_listing_current_price")
    try:
        call_command('update_listing_current_price')
        logger.info("The update_listing_current_price task has completed successfully.")
    except Exception as e:
        logger.error(f"Runtime error update_listing_current_price: {e}")
