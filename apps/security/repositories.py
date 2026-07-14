from apps.users.models import User


class UserRepository:

    @staticmethod
    def create_user(
        *, email: str, password: str, first_name: str, last_name: str
    ) -> User:
        return User.objects.create_user(
            email=email, password=password, first_name=first_name, last_name=last_name
        )
