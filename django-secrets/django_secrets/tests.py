import datetime
import uuid
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from cryptography.fernet import InvalidToken
from .models import Secret
from .utils import encrypt, decrypt, generate_salt, encode_id, decode_id
from .forms import SecretCreateForm, SecretUpdateForm


class UtilsSecurityTests(TestCase):
    """Test cryptographic utilities for security"""

    def test_unique_salts_generate_different_keys(self):
        """Verify that unique salts prevent rainbow table attacks"""
        passphrase = "test_passphrase"
        salt1 = generate_salt()
        salt2 = generate_salt()

        # Same passphrase with different salts should produce different ciphertext
        data = "secret data"
        encrypted1 = encrypt(data, passphrase, salt1)
        encrypted2 = encrypt(data, passphrase, salt2)

        self.assertNotEqual(encrypted1, encrypted2,
                            "Same passphrase with different salts must produce different ciphertext")

    def test_decrypt_returns_string_not_bytes(self):
        """Verify that decrypt returns a string, not bytes (bug fix)"""
        passphrase = "test"
        salt = generate_salt()
        data = "hello world"

        encrypted = encrypt(data, passphrase, salt)
        decrypted = decrypt(encrypted, passphrase, salt)

        self.assertIsInstance(decrypted, str, "Decrypt must return string, not bytes")
        self.assertEqual(decrypted, data, "Decrypted data must match original")

    def test_wrong_salt_fails_decryption(self):
        """Verify that using wrong salt prevents decryption"""
        passphrase = "test"
        salt1 = generate_salt()
        salt2 = generate_salt()
        data = "secret"

        encrypted = encrypt(data, passphrase, salt1)

        with self.assertRaises(InvalidToken):
            decrypt(encrypted, passphrase, salt2)

    def test_uuid_encoding_decoding(self):
        """Verify UUID encoding/decoding works correctly"""
        original_uuid = uuid.uuid4()
        encoded = encode_id(original_uuid)
        decoded = decode_id(encoded)

        self.assertEqual(original_uuid, decoded, "UUID encoding/decoding must be reversible")

    def test_invalid_oid_returns_none(self):
        """Verify invalid OID returns None instead of crashing"""
        invalid_oid = "invalid!!!!"
        result = decode_id(invalid_oid)
        self.assertIsNone(result, "Invalid OID should return None")


class SecretModelTests(TestCase):
    """Test Secret model security features"""

    def test_secret_has_unique_salt(self):
        """Verify each secret gets a unique salt"""
        form1 = SecretCreateForm(data={'data': 'secret1', 'passphrase': 'pass1'})
        form2 = SecretCreateForm(data={'data': 'secret2', 'passphrase': 'pass2'})

        self.assertTrue(form1.is_valid())
        self.assertTrue(form2.is_valid())

        secret1 = form1.save()
        secret2 = form2.save()

        self.assertNotEqual(secret1.salt, secret2.salt,
                            "Each secret must have a unique salt")

    def test_secret_has_uuid_id(self):
        """Verify secrets use UUID instead of sequential integer IDs"""
        form = SecretCreateForm(data={'data': 'test', 'passphrase': 'pass'})
        self.assertTrue(form.is_valid())
        secret = form.save()

        self.assertIsInstance(secret.id, uuid.UUID,
                              "Secret ID must be UUID")

    def test_secret_expiration(self):
        """Verify secrets expire after 10 minutes"""
        form = SecretCreateForm(data={'data': 'test', 'passphrase': 'pass'})
        self.assertTrue(form.is_valid())
        secret = form.save()

        # Manually set created_at to 11 minutes ago
        old_time = timezone.now() - datetime.timedelta(minutes=11)
        Secret.objects.filter(pk=secret.pk).update(created_at=old_time)

        # Refresh and check if it's in available queryset
        available_secrets = Secret.available.filter(pk=secret.pk)
        self.assertEqual(available_secrets.count(), 0,
                         "Secrets older than 10 minutes should not be available")


class SecretViewTests(TestCase):
    """Test view security features"""

    def setUp(self):
        self.client = Client()

    def test_secret_deleted_after_view(self):
        """Verify secrets are deleted after being viewed once"""
        # Create a secret
        response = self.client.post(reverse('secrets:secret-create'), {
            'data': 'one-time secret',
            'passphrase': 'testpass'
        })

        # Get the created secret
        secret = Secret.objects.first()
        self.assertIsNotNone(secret)

        # View the secret
        oid = secret.oid
        response = self.client.post(reverse('secrets:secret-update', kwargs={'oid': oid}), {
            'passphrase': 'testpass'
        })

        self.assertEqual(response.status_code, 200)

        # Verify secret was deleted
        self.assertEqual(Secret.objects.filter(pk=secret.pk).count(), 0,
                         "Secret must be deleted after viewing")

    def test_wrong_passphrase_fails(self):
        """Verify wrong passphrase prevents decryption"""
        # Create a secret
        self.client.post(reverse('secrets:secret-create'), {
            'data': 'secret data',
            'passphrase': 'correctpass'
        })

        secret = Secret.objects.first()
        oid = secret.oid

        # Try with wrong passphrase
        response = self.client.post(reverse('secrets:secret-update', kwargs={'oid': oid}), {
            'passphrase': 'wrongpass'
        })

        # Should show form with error, not the secret
        self.assertContains(response, 'Oops')
        self.assertNotContains(response, 'secret data')

        # Secret should still exist (not deleted on failed attempt)
        self.assertEqual(Secret.objects.filter(pk=secret.pk).count(), 1,
                         "Secret should not be deleted on failed decryption")

    def test_expired_secret_not_viewable(self):
        """Verify expired secrets cannot be viewed"""
        # Create a secret
        self.client.post(reverse('secrets:secret-create'), {
            'data': 'expired secret',
            'passphrase': 'testpass'
        })

        secret = Secret.objects.first()
        oid = secret.oid

        # Manually expire it
        old_time = timezone.now() - datetime.timedelta(minutes=11)
        Secret.objects.filter(pk=secret.pk).update(created_at=old_time)

        # Try to view it
        response = self.client.post(reverse('secrets:secret-update', kwargs={'oid': oid}), {
            'passphrase': 'testpass'
        })

        self.assertEqual(response.status_code, 404,
                         "Expired secrets should return 404")


class SecurityRegressionTests(TestCase):
    """Tests for specific security vulnerabilities that were fixed"""

    def test_no_shared_salt_vulnerability(self):
        """Regression test: Verify salts are not shared between secrets"""
        secrets = []
        for i in range(5):
            form = SecretCreateForm(data={
                'data': f'secret{i}',
                'passphrase': 'same_passphrase'  # Same passphrase for all
            })
            self.assertTrue(form.is_valid())
            secrets.append(form.save())

        # All secrets should have unique salts
        salts = [s.salt for s in secrets]
        unique_salts = set(salts)

        self.assertEqual(len(unique_salts), len(secrets),
                         "All secrets must have unique salts, even with same passphrase")

        # All encrypted data should be different
        encrypted_data = [s.data for s in secrets]
        unique_encrypted = set(encrypted_data)

        self.assertEqual(len(unique_encrypted), len(secrets),
                         "Same passphrase should produce different ciphertext with unique salts")

    def test_uuid_prevents_enumeration(self):
        """Verify UUIDs make enumeration attacks infeasible"""
        secret1 = SecretCreateForm(data={'data': 'test1', 'passphrase': 'pass1'}).save()
        secret2 = SecretCreateForm(data={'data': 'test2', 'passphrase': 'pass2'}).save()

        # UUIDs should not be sequential
        self.assertNotEqual(secret1.id, secret2.id)

        # OIDs should be significantly different (not just incremented)
        oid1 = secret1.oid
        oid2 = secret2.oid

        self.assertNotEqual(oid1, oid2)
        # OIDs should be at least 20 characters (base64-encoded UUID)
        self.assertGreater(len(oid1), 20)
        self.assertGreater(len(oid2), 20)
