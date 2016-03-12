"""inviare URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.utils.translation import ugettext_lazy as _
from django.conf.urls import include, url, patterns
from django.views.generic.base import TemplateView
from django.conf.urls.static import static
from django.contrib import admin
from django.conf import settings


admin.site.site_header = _('ten minute secret')
admin.site.site_title = _('ten minute secret')
admin.site.index_title = _('Dashboard')


urlpatterns = [
    url(r'', include('secrets.urls', 'secrets')),
    url(r'^about/$', TemplateView.as_view(template_name="about.html"), name="about"),
    url(r'^terms/$', TemplateView.as_view(template_name="terms.html"), name="terms"),
    url(r'^!/', include(admin.site.urls)),
]
