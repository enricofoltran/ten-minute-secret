import datetime
from django.utils import timezone
from django.db import models


class AvailableManager(models.Manager):
    def get_queryset(self):
        qs = super(AvailableManager, self).get_queryset()
        now = datetime.datetime.utcnow().replace(tzinfo=timezone.utc)
        threshold = now - datetime.timedelta(minutes=10)
        return qs.filter(created_at__gt=threshold)
