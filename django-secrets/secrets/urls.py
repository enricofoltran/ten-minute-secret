from django.conf.urls import url
from .views import SecretCreateView, SecretUpdateView


urlpatterns = [
    url(r'^$', SecretCreateView.as_view(), name='secret-create'),
    url(r'^(?P<oid>[a-zA-Z0-9\-_]{6})/$', SecretUpdateView.as_view(), name='secret-update'),
]
