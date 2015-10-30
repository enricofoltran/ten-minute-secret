# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('secrets', '0002_remove_secret_views'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='secret',
            name='updated_at',
        ),
    ]
