from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.users.controller import GroupListView, UserViewSet

app_name = "users"

router = SimpleRouter()
router.register("users", UserViewSet, basename="user")

urlpatterns = [
    path("users/roles/", GroupListView.as_view(), name="roles"),
] + router.urls
