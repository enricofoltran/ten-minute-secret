# Generated migration for security updates
# WARNING: This migration will delete all existing secrets for security reasons
# The old encryption scheme (shared salt) was fundamentally insecure

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('secrets', '0003_remove_secret_updated_at'),
    ]

    operations = [
        # Delete all existing secrets (they use the old insecure encryption)
        migrations.RunSQL(
            sql='DELETE FROM secrets_secret;',
            reverse_sql=migrations.RunSQL.noop,
        ),

        # Remove old integer ID
        migrations.RemoveField(
            model_name='secret',
            name='id',
        ),

        # Add UUID primary key
        migrations.AddField(
            model_name='secret',
            name='id',
            field=models.UUIDField(
                default=uuid.uuid4,
                primary_key=True,
                serialize=False,
                editable=False
            ),
        ),

        # Add salt field for secure encryption
        migrations.AddField(
            model_name='secret',
            name='salt',
            field=models.BinaryField(
                max_length=16,
                verbose_name='salt',
                help_text='Unique salt for key derivation',
                default=b''  # Temporary default for migration
            ),
            preserve_default=False,
        ),
    ]
