import datetime
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils.timezone import utc
from django.conf import settings
from django.db import models
from .managers import AvailableManager
from .utils import encode_id


class Secret(models.Model):
    # Use UUIDField for secure, unguessable IDs
    id = models.UUIDField(primary_key=True, default=None, editable=False)
    data = models.TextField(
        verbose_name=_('data'))
    # Store unique salt for each secret (CRITICAL for security)
    salt = models.BinaryField(
        max_length=16,
        verbose_name=_('salt'),
        help_text=_('Unique salt for key derivation'))
    created_at = models.DateTimeField(
        verbose_name=_("created at"), auto_now_add=True, editable=False)

    objects = models.Manager()
    available = AvailableManager()

    class Meta:
        ordering = ('-created_at', )

    @property
    def oid(self):
        """Obfuscated ID for URLs - uses UUID encoding"""
        return encode_id(self.pk)

    @property
    def size(self):
        return len(self.data.encode('utf-8'))

    @property
    def expire_at(self):
        created_at = self.created_at.replace(tzinfo=utc)
        expire_at = created_at + datetime.timedelta(minutes=10)
        return expire_at

    def __str__(self):
        return str(self.oid)

    def get_absolute_url(self):
        return reverse('secrets:secret-update', kwargs={'oid': self.oid})
