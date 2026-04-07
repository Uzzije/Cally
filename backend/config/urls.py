from django.contrib import admin
from django.urls import include, path

from config.api import api
from config.inngest import inngest_endpoint

urlpatterns = [
    path("admin/", admin.site.urls),
    path("_allauth/", include("allauth.headless.urls")),
    path("accounts/", include("allauth.urls")),
    path("api/v1/", api.urls),
    inngest_endpoint,
]
