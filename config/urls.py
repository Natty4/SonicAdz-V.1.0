"""
URL configuration for sonicadz.

"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from miniapp.admin import admin_site


urlpatterns = [
    # path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path('sys/admin/963/', admin_site.urls),
    path("", include("miniapp.urls")),
    path("api/", include("api.urls")),
    path("advertiser/", include("advertisers.urls")),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)