"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/analytics/', include('apps.analytics.urls')),
    path('api/v1/bookings/', include('apps.bookings.urls')),
    path('api/v1/content/', include('apps.content.urls')),
    path('api/v1/listings/', include('apps.listings.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
    path('api/v1/pricing/', include('apps.pricing.urls')),
    path('api/v1/reviews/', include('apps.reviews.urls')),
    path('api/v1/users/', include('apps.users.urls')),
]
