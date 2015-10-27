from django.utils.translation import ugettext_lazy as _
from django.template.defaultfilters import filesizeformat
from django.utils.html import format_html
from django.contrib import admin
from .models import Secret


class SecretAdmin(admin.ModelAdmin):
    actions = ('delete', )
    list_display_links = None
    list_display = ('on_site', 'pretty_size', 'views', 'updated_at', 'created_at', )
    list_filter = ('updated_at', 'created_at', )
    date_hierarchy = 'created_at'
    ordering = ('-created_at', '-updated_at', )

    def has_add_permission(self, request):
        return False

    def pretty_size(self, obj):
        return filesizeformat(obj.size)
    pretty_size.short_description = _('size')

    def on_site(self, obj):
        return format_html(
            '<a href="{url}" target="_blank">{oid}</a>',
            url=obj.get_absolute_url(), oid=obj.oid
        )
    on_site.short_description = _('View on site')
    on_site.allow_tags = True


admin.site.register(Secret, SecretAdmin)
