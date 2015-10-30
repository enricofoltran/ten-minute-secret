import datetime
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
    created_at = models.DateTimeField(
        verbose_name=_("created at"), auto_now_add=True, editable=False, )

    objects = models.Manager()
    available = AvailableManager()

    class Meta:
        ordering = ('-created_at', )

    @property
    def oid(self):
        return knuth_encode(self.pk)

    @property
    def size(self):
        return len(self.data.encode('utf-8'))

    @property
    def expire_at(self):
        created_at = self.created_at.replace(tzinfo=utc)
        expire_at = created_at + datetime.timedelta(minutes=10)
        return expire_at

    def __str__(self):
        return self.oid.__str__()

    def get_absolute_url(self):
        return reverse('secrets:secret-update', kwargs={'oid': self.oid})
