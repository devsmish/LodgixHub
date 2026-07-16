from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from config import settings

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.security.urls")),
    path("api/v1/", include("apps.users.urls")),
    path("api/v1/", include("apps.listings.urls")),
    path("api/v1/", include("apps.content.urls")),
    path("api/v1/", include("apps.bookings.urls")),
    path("api/v1/", include("apps.pricing.urls")),
    path("api/v1/", include("apps.reviews.urls")),
    path("api/v1/", include("apps.analytics.urls")),
    path("api/v1/", include("apps.notifications.urls")),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]
