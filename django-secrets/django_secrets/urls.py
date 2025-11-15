from django.urls import path, re_path
from .views import SecretCreateView, SecretUpdateView

app_name = 'secrets'

urlpatterns = [
    path('', SecretCreateView.as_view(), name='secret-create'),
    re_path(r'^(?P<oid>[a-zA-Z0-9\-_]+)/$', SecretUpdateView.as_view(), name='secret-update'),
]
