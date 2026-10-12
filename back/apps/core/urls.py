from django.urls import path

from apps.core.api import ShopLogoView, ShopSettingsView

app_name = 'core'

urlpatterns = [
    path('settings/', ShopSettingsView.as_view(), name='settings'),
    path('settings/logo/', ShopLogoView.as_view(), name='settings-logo'),
]
