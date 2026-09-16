from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.core.urls")),
    path("api/", include("apps.catalog.urls")),
    path("api/", include("apps.inventory.urls")),
    path("api/", include("apps.purchases.urls")),
    path("api/", include("apps.sales.urls")),
    path("api/", include("apps.expenses.urls")),
    path("api/", include("apps.reports.urls")),
]

# API hujjatlari va sxemasi faqat ishlab chiqishda ochiq: ishlab
# chiqarishda ular tizim tuzilishini begonaga ko'rsatib qo'yadi.
if settings.DEBUG:
    from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    ]

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
