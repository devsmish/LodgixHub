from django.db import transaction

from apps.bookings.booking_user_guard import (
    user_has_active_bookings,
    user_has_completed_booking_with_listing_owner,
)
from apps.users.errors import (
    PublicProfileNotAccessibleError,
    UserAlreadyBlockedError,
    UserHasActiveBookingsError,
    UserNotBlockedError,
)
from apps.users.filters import UserFilter
from apps.users.repositories import UserRepository


class UserService:

    def __init__(self, repository: UserRepository = None):
        self.repository = repository or UserRepository()

    # Profile

    def update_me(self, user, validated_data):
        for field, value in validated_data.items():
            setattr(user, field, value)
        user.full_clean(exclude=["password"])
        user.save()
        return user

    def get_public_profile(self, requesting_user, target_user_id):
        target = self.repository.get_by_id(target_user_id)
        if target is None:
            return None
        if not user_has_completed_booking_with_listing_owner(
            requesting_user, target_user_id
        ):
            raise PublicProfileNotAccessibleError()
        return target

    # delete

    @transaction.atomic
    def delete_self(self, user):
        if user_has_active_bookings(user):
            raise UserHasActiveBookingsError()
        user.delete()
        return user

    @transaction.atomic
    def delete_by_admin(self, target_user):
        if user_has_active_bookings(target_user):
            raise UserHasActiveBookingsError()
        target_user.delete()
        return target_user

    # block

    @transaction.atomic
    def block(self, target_user, blocked_reason, blocked_by):
        if target_user.blocked_at is not None:
            raise UserAlreadyBlockedError()
        if user_has_active_bookings(target_user):
            raise UserHasActiveBookingsError()
        target_user.block(reason=blocked_reason, blocked_by=blocked_by)
        return target_user

    @transaction.atomic
    def unblock(self, target_user):
        if target_user.blocked_at is None:
            raise UserNotBlockedError()
        target_user.unblock()
        return target_user

    # roles

    @transaction.atomic
    def update_groups(self, target_user, groups):
        target_user.groups.set(groups)
        return target_user

    # --- list (moderator/admin) ---

    def list_users(self, query_params):
        queryset = self.repository.get_all_queryset()
        return UserFilter(query_params).apply(queryset)
