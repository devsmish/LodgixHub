from django.contrib import admin
from django.urls import include, path

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
]
