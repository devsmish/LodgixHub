from rest_framework.routers import SimpleRouter

from apps.reviews.controller import ReviewViewSet

app_name = "reviews"

router = SimpleRouter()
router.register("reviews", ReviewViewSet, basename="review")

urlpatterns = router.urls
