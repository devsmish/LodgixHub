from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from apps.security.repositories import UserRepository
from apps.users.models import User


def register_user(
    *, email: str, password: str, first_name: str, last_name: str, role: str
) -> User:
    user = UserRepository.create_user(
        email=email, password=password, first_name=first_name, last_name=last_name
    )

    group = Group.objects.get(name=role)
    user.groups.add(group)

    user.terms_accepted_at = timezone.now()
    user.save(update_fields=["terms_accepted_at"])

    return user


def mint_token_pair(user: User) -> RefreshToken:
    refresh = RefreshToken.for_user(user)
    refresh["token_version"] = user.token_version
    return refresh
