from celery import shared_task
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)

@shared_task
def run_process_bookings():
    logger.info("Starting a scheduled task: process_bookings")
    try:
        call_command('process_bookings')
        logger.info("The process_bookings task completed successfully.")
    except Exception as e:
        logger.error(f"Runtime error process_bookings: {e}")
        