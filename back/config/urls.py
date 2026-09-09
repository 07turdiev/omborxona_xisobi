from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.users.urls")),
    path("api/", include("apps.units.urls")),
    path("api/", include("apps.catalog.urls")),
    path("api/", include("apps.stock.urls")),
    path("api/", include("apps.documents.urls")),
    path("api/", include("apps.partners.urls")),
    path("api/", include("apps.reports.urls")),
    path("api/", include("apps.tenants.urls")),
    path("api/", include("apps.pricing.urls")),
    path("api/", include("apps.warehouse.urls")),
    # API hujjatlari
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
