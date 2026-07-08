from django.contrib.auth.models import Group

from apps.security.constants import SYSTEM_ROLES


def create_system_groups(sender, **kwargs):
    """
    Automatically creates system groups after migrations are executed.
    """
    for role in SYSTEM_ROLES:
        Group.objects.get_or_create(name=role)
