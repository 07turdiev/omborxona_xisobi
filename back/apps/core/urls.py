from django.urls import path

from apps.core.api import ShopSettingsView

app_name = 'core'

urlpatterns = [
    path('settings/', ShopSettingsView.as_view(), name='settings'),
]
