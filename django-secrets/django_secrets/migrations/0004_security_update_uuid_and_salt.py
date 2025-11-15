# Generated migration for security updates
# WARNING: This migration will delete all existing secrets for security reasons
# The old encryption scheme (shared salt) was fundamentally insecure

import uuid
from django.db import migrations, models


def delete_old_secrets(apps, schema_editor):
    """
    Safely delete all existing secrets from either old or new table name.
    This handles the app rename from 'secrets' to 'django_secrets'.
    """
    db_alias = schema_editor.connection.alias
    with schema_editor.connection.cursor() as cursor:
        # Try to delete from old table name (for existing installations)
        try:
            cursor.execute("DELETE FROM secrets_secret;")
        except Exception:
            # Table might not exist, that's fine
            pass

        # Try to delete from new table name
        try:
            cursor.execute("DELETE FROM django_secrets_secret;")
        except Exception:
            # Table might not exist, that's fine
            pass


class Migration(migrations.Migration):

    dependencies = [
        ('django_secrets', '0003_remove_secret_updated_at'),
    ]

    operations = [
        # Delete all existing secrets using Python function for better error handling
        migrations.RunPython(delete_old_secrets, reverse_code=migrations.RunPython.noop),

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
