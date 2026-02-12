from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.catalog.urls")),
    path("", include("apps.materials.urls")),
    path("", include("apps.accounts.urls")),
    path("", include("apps.ui.urls")),
    path("", include("apps.production.urls")),
]
