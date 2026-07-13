from django.urls import path

from apps.content.controller import PhotoDetailView, PhotoListCreateView

app_name = "content"

urlpatterns = [
    path(
        "listings/<uuid:listing_id>/photos/",
        PhotoListCreateView.as_view(),
        name="listing-photos",
    ),
    path(
        "listings/<uuid:listing_id>/photos/<uuid:pk>/",
        PhotoDetailView.as_view(),
        name="listing-photo-detail",
    ),
]
