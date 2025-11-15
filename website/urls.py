"""inviare URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
"""
from django.utils.translation import gettext_lazy as _
from django.urls import include, path, re_path
from django.views.generic.base import TemplateView
from django.contrib import admin
from django.conf import settings


admin.site.site_header = _('ten minute secret')
admin.site.site_title = _('ten minute secret')
admin.site.index_title = _('Dashboard')


urlpatterns = [
    path('', include('django_secrets.urls')),
    path('about/', TemplateView.as_view(template_name="about.html"), name="about"),
    path('terms/', TemplateView.as_view(template_name="terms.html"), name="terms"),
    path('!/', admin.site.urls),
]
