from apps.users.models import User


class UserRepository:

    @staticmethod
    def get_active_queryset():
        return User.objects.all()

    @staticmethod
    def get_all_queryset():
        """For moderators/admins only — display all users, including soft-deleted ones."""
        return User.all_objects.all()

    @staticmethod
    def get_by_id(user_id):
        return User.objects.filter(id=user_id).first()

    @staticmethod
    def get_by_id_any(user_id):
        return User.all_objects.filter(id=user_id).first()
