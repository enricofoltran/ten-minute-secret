from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from django.utils.timezone import utc
from django.conf import settings
from django.db import models
from .managers import AvailableManager
from .utils import knuth_encode


class Secret(models.Model):
    data = models.TextField(
        verbose_name=_('data'))
    views = models.PositiveIntegerField(
        verbose_name=_('views'), default=0)
    created_at = models.DateTimeField(
        verbose_name=_("created at"), auto_now_add=True, editable=False, )
    updated_at = models.DateTimeField(
        verbose_name=_("updated at"), auto_now=True, editable=False)

    objects = models.Manager()
    available = AvailableManager()

    class Meta:
        ordering = ('-created_at', )

    @property
    def oid(self):
        return knuth_encode(self.pk)

    def __str__(self):
        return self.oid.__str__()

    def get_absolute_url(self):
        return reverse('secrets:secret-update', kwargs={'oid': self.oid})
