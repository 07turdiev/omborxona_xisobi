from django.urls import path

from apps.dataimport.api import ImportCommitView, ImportPreviewView, ImportTemplateView

app_name = 'dataimport'

urlpatterns = [
    path('import/<slug:kind>/template/', ImportTemplateView.as_view(), name='template'),
    path('import/<slug:kind>/preview/', ImportPreviewView.as_view(), name='preview'),
    path('import/<slug:kind>/commit/', ImportCommitView.as_view(), name='commit'),
]
