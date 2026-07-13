from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.content.models import Photo


@receiver(post_delete, sender=Photo)
def delete_photo_file_from_storage(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(save=False)
