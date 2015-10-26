from django.utils.translation import ugettext_lazy as _
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.utils.html import format_html
from django.contrib import admin
from .models import Secret


class SecretAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {
            'fields': ('data', )
        }),
        ('Advanced info', {
            'classes': ('collapse',),
            'fields': ('age', 'views', 'updated_at', 'created_at', )
        }),
    )
    readonly_fields = ('data', 'age', 'views', 'updated_at', 'created_at', )
    list_display_links = ('oid', )
    list_display = ('oid', 'on_site', 'age', 'views', 'updated_at', 'created_at', )
    list_filter = ('updated_at', 'created_at', )
    date_hierarchy = 'created_at'
    ordering = ('-created_at', '-updated_at', )

    def has_add_permission(self, request):
        return False

    def age(self, obj):
        return naturaltime(obj.created_at)
    age.short_description = _('Age')

    def on_site(self, obj):
        return format_html(
            '<a href="{}" target="_blank">View on site</a>',
            obj.get_absolute_url()
        )
    on_site.short_description = _('View on site')
    on_site.allow_tags = True


admin.site.register(Secret, SecretAdmin)
