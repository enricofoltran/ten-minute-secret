from django.conf.urls import url
from .views import SecretCreateView, SecretUpdateView


urlpatterns = [
    url(r'^$', SecretCreateView.as_view(), name='secret-create'),
    url(r'^(?P<oid>[0-9]+)/$', SecretUpdateView.as_view(), name='secret-update'),
]
