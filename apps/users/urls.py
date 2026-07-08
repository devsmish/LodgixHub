from django.urls import path

from apps.users.views import LoginView, LogoutView

app_name = "users"

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
]
