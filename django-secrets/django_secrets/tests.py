import datetime
import uuid
from unittest.mock import Mock, patch
from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.utils import timezone
from django.contrib.admin.sites import AdminSite
from django.http import Http404
from cryptography.fernet import InvalidToken
from .models import Secret
from .utils import encrypt, decrypt, generate_salt, encode_id, decode_id, passphrase_to_key
from .forms import SecretCreateForm, SecretUpdateForm
from .admin import SecretAdmin
from .mixins import KnuthIdMixin
from .views import SecretUpdateView


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
        form1 = SecretCreateForm(data={'data': 'test1', 'passphrase': 'pass1'})
        form2 = SecretCreateForm(data={'data': 'test2', 'passphrase': 'pass2'})
        self.assertTrue(form1.is_valid())
        self.assertTrue(form2.is_valid())
        secret1 = form1.save()
        secret2 = form2.save()

        # UUIDs should not be sequential
        self.assertNotEqual(secret1.id, secret2.id)

        # OIDs should be significantly different (not just incremented)
        oid1 = secret1.oid
        oid2 = secret2.oid

        self.assertNotEqual(oid1, oid2)
        # OIDs should be at least 20 characters (base64-encoded UUID)
        self.assertGreater(len(oid1), 20)
        self.assertGreater(len(oid2), 20)


class FormValidationTests(TestCase):
    """Test form validation and edge cases"""

    def test_create_form_empty_data_validation(self):
        """Test that empty data is rejected"""
        form = SecretCreateForm(data={'data': '', 'passphrase': 'test'})
        self.assertFalse(form.is_valid())
        self.assertIn('data', form.errors)

    def test_create_form_empty_passphrase_validation(self):
        """Test that empty passphrase is rejected"""
        form = SecretCreateForm(data={'data': 'test secret', 'passphrase': ''})
        self.assertFalse(form.is_valid())
        self.assertIn('passphrase', form.errors)

    def test_create_form_max_size_validation(self):
        """Test that data exceeding 50KB is rejected"""
        # Create data larger than 50KB
        large_data = 'a' * (50 * 1024 + 1)
        form = SecretCreateForm(data={'data': large_data, 'passphrase': 'test'})
        self.assertFalse(form.is_valid())
        self.assertIn('data', form.errors)
        self.assertIn('maximum', form.errors['data'][0].lower())

    def test_create_form_exactly_max_size(self):
        """Test that data at exactly 50KB is accepted"""
        # Create data at exactly 50KB
        max_data = 'a' * (50 * 1024)
        form = SecretCreateForm(data={'data': max_data, 'passphrase': 'test'})
        self.assertTrue(form.is_valid())

    def test_create_form_unicode_characters(self):
        """Test that unicode characters are handled correctly"""
        unicode_data = '你好世界 こんにちは мир 🔒🔑'
        form = SecretCreateForm(data={'data': unicode_data, 'passphrase': 'test'})
        self.assertTrue(form.is_valid())
        secret = form.save()

        # Verify it can be decrypted
        decrypted = decrypt(secret.data, 'test', secret.salt)
        self.assertEqual(decrypted, unicode_data)

    def test_create_form_special_characters(self):
        """Test that special characters in data are handled"""
        special_data = 'Test!@#$%^&*(){}[]|\\:";\'<>?,./~`'
        form = SecretCreateForm(data={'data': special_data, 'passphrase': 'test'})
        self.assertTrue(form.is_valid())
        secret = form.save()

        # Verify it can be decrypted
        decrypted = decrypt(secret.data, 'test', secret.salt)
        self.assertEqual(decrypted, special_data)

    def test_create_form_multiline_data(self):
        """Test that multiline data is handled correctly"""
        multiline_data = "Line 1\nLine 2\nLine 3\n\nLine 5"
        form = SecretCreateForm(data={'data': multiline_data, 'passphrase': 'test'})
        self.assertTrue(form.is_valid())
        secret = form.save()

        # Verify it can be decrypted
        decrypted = decrypt(secret.data, 'test', secret.salt)
        self.assertEqual(decrypted, multiline_data)

    def test_update_form_wrong_passphrase(self):
        """Test SecretUpdateForm rejects wrong passphrase"""
        # Create a secret first
        create_form = SecretCreateForm(data={'data': 'test secret', 'passphrase': 'correct'})
        self.assertTrue(create_form.is_valid())
        secret = create_form.save()

        # Try to update with wrong passphrase
        update_form = SecretUpdateForm(data={'passphrase': 'wrong'}, instance=secret)
        self.assertFalse(update_form.is_valid())
        self.assertIn('passphrase', update_form.errors)

    def test_update_form_correct_passphrase(self):
        """Test SecretUpdateForm accepts correct passphrase"""
        # Create a secret first
        create_form = SecretCreateForm(data={'data': 'test secret', 'passphrase': 'correct'})
        self.assertTrue(create_form.is_valid())
        secret = create_form.save()

        # Update with correct passphrase
        update_form = SecretUpdateForm(data={'passphrase': 'correct'}, instance=secret)
        self.assertTrue(update_form.is_valid())
        self.assertEqual(secret.decrypted_data, 'test secret')

    def test_update_form_sets_decrypted_data_attribute(self):
        """Test that update form sets decrypted_data on instance"""
        create_form = SecretCreateForm(data={'data': 'my secret', 'passphrase': 'pass'})
        self.assertTrue(create_form.is_valid())
        secret = create_form.save()

        update_form = SecretUpdateForm(data={'passphrase': 'pass'}, instance=secret)
        self.assertTrue(update_form.is_valid())

        # Check that decrypted_data attribute is set
        self.assertTrue(hasattr(secret, 'decrypted_data'))
        self.assertEqual(secret.decrypted_data, 'my secret')


class ModelPropertyTests(TestCase):
    """Test Secret model properties and methods"""

    def test_oid_property(self):
        """Test that oid property returns encoded UUID"""
        form = SecretCreateForm(data={'data': 'test', 'passphrase': 'pass'})
        self.assertTrue(form.is_valid())
        secret = form.save()

        oid = secret.oid
        self.assertIsInstance(oid, str)
        self.assertGreater(len(oid), 20)

        # Verify it can be decoded back to UUID
        decoded = decode_id(oid)
        self.assertEqual(decoded, secret.id)

    def test_size_property(self):
        """Test that size property returns correct byte count"""
        form = SecretCreateForm(data={'data': 'hello', 'passphrase': 'pass'})
        self.assertTrue(form.is_valid())
        secret = form.save()

        # The size property returns the size of encrypted data
        self.assertGreater(secret.size, 0)
        self.assertIsInstance(secret.size, int)

    def test_size_property_with_unicode(self):
        """Test size calculation with unicode characters"""
        unicode_data = '你好'  # 2 characters, 6 bytes in UTF-8
        form = SecretCreateForm(data={'data': unicode_data, 'passphrase': 'pass'})
        self.assertTrue(form.is_valid())
        secret = form.save()

        # Size should account for UTF-8 encoding
        self.assertGreater(secret.size, 0)

    def test_expire_at_property(self):
        """Test that expire_at is 10 minutes after creation"""
        form = SecretCreateForm(data={'data': 'test', 'passphrase': 'pass'})
        self.assertTrue(form.is_valid())
        secret = form.save()

        expected_expiry = secret.created_at + datetime.timedelta(minutes=10)

        # Allow small time difference (within 1 second)
        time_diff = abs((secret.expire_at - expected_expiry).total_seconds())
        self.assertLess(time_diff, 1)

    def test_str_method(self):
        """Test __str__ returns OID"""
        form = SecretCreateForm(data={'data': 'test', 'passphrase': 'pass'})
        self.assertTrue(form.is_valid())
        secret = form.save()

        self.assertEqual(str(secret), secret.oid)

    def test_get_absolute_url(self):
        """Test get_absolute_url returns correct URL"""
        form = SecretCreateForm(data={'data': 'test', 'passphrase': 'pass'})
        self.assertTrue(form.is_valid())
        secret = form.save()

        url = secret.get_absolute_url()
        expected_url = reverse('secrets:secret-update', kwargs={'oid': secret.oid})
        self.assertEqual(url, expected_url)

    def test_model_ordering(self):
        """Test that secrets are ordered by created_at descending"""
        # Create multiple secrets with small delays
        secrets = []
        for i in range(3):
            form = SecretCreateForm(data={'data': f'secret{i}', 'passphrase': 'pass'})
            self.assertTrue(form.is_valid())
            secrets.append(form.save())

        # Get all secrets
        all_secrets = list(Secret.objects.all())

        # Should be in reverse chronological order
        self.assertEqual(all_secrets[0].id, secrets[2].id)
        self.assertEqual(all_secrets[-1].id, secrets[0].id)


class ManagerTests(TestCase):
    """Test custom managers"""

    def test_available_manager_filters_expired(self):
        """Test that AvailableManager excludes expired secrets"""
        # Create a secret
        form = SecretCreateForm(data={'data': 'test', 'passphrase': 'pass'})
        self.assertTrue(form.is_valid())
        secret = form.save()

        # Should be available initially
        self.assertEqual(Secret.available.filter(pk=secret.pk).count(), 1)

        # Expire it
        old_time = timezone.now() - datetime.timedelta(minutes=11)
        Secret.objects.filter(pk=secret.pk).update(created_at=old_time)

        # Should no longer be available
        self.assertEqual(Secret.available.filter(pk=secret.pk).count(), 0)

        # But should still exist in objects manager
        self.assertEqual(Secret.objects.filter(pk=secret.pk).count(), 1)

    def test_available_manager_boundary_condition(self):
        """Test AvailableManager at exact 10-minute boundary"""
        # Create a secret
        form = SecretCreateForm(data={'data': 'test', 'passphrase': 'pass'})
        self.assertTrue(form.is_valid())
        secret = form.save()

        # Set to exactly 10 minutes ago (should be expired)
        boundary_time = timezone.now() - datetime.timedelta(minutes=10, seconds=1)
        Secret.objects.filter(pk=secret.pk).update(created_at=boundary_time)

        # Should be expired
        self.assertEqual(Secret.available.filter(pk=secret.pk).count(), 0)

    def test_available_manager_with_multiple_secrets(self):
        """Test AvailableManager with mix of valid and expired secrets"""
        # Create multiple secrets
        valid_secrets = []
        for i in range(3):
            form = SecretCreateForm(data={'data': f'valid{i}', 'passphrase': 'pass'})
            self.assertTrue(form.is_valid())
            valid_secrets.append(form.save())

        # Create and expire some secrets
        expired_secrets = []
        for i in range(2):
            form = SecretCreateForm(data={'data': f'expired{i}', 'passphrase': 'pass'})
            self.assertTrue(form.is_valid())
            secret = form.save()
            old_time = timezone.now() - datetime.timedelta(minutes=11)
            Secret.objects.filter(pk=secret.pk).update(created_at=old_time)
            expired_secrets.append(secret)

        # Available should only return valid ones
        available_count = Secret.available.count()
        self.assertEqual(available_count, 3)

        # Objects should return all
        total_count = Secret.objects.count()
        self.assertEqual(total_count, 5)


class UtilsEdgeCaseTests(TestCase):
    """Test utility functions with edge cases"""

    def test_passphrase_to_key_consistency(self):
        """Test that same passphrase and salt produce same key"""
        passphrase = "test_pass"
        salt = generate_salt()

        key1 = passphrase_to_key(passphrase, salt)
        key2 = passphrase_to_key(passphrase, salt)

        self.assertEqual(key1, key2)

    def test_passphrase_to_key_different_salts(self):
        """Test that different salts produce different keys"""
        passphrase = "test_pass"
        salt1 = generate_salt()
        salt2 = generate_salt()

        key1 = passphrase_to_key(passphrase, salt1)
        key2 = passphrase_to_key(passphrase, salt2)

        self.assertNotEqual(key1, key2)

    def test_encrypt_empty_string(self):
        """Test encrypting empty string"""
        passphrase = "test"
        salt = generate_salt()

        encrypted = encrypt("", passphrase, salt)
        self.assertIsInstance(encrypted, str)
        self.assertGreater(len(encrypted), 0)

        # Should be able to decrypt
        decrypted = decrypt(encrypted, passphrase, salt)
        self.assertEqual(decrypted, "")

    def test_encrypt_very_long_data(self):
        """Test encrypting very long data"""
        passphrase = "test"
        salt = generate_salt()
        long_data = "a" * 10000

        encrypted = encrypt(long_data, passphrase, salt)
        decrypted = decrypt(encrypted, passphrase, salt)

        self.assertEqual(decrypted, long_data)

    def test_encrypt_unicode_data(self):
        """Test encrypting unicode data"""
        passphrase = "test"
        salt = generate_salt()
        unicode_data = "Hello 世界 🌍"

        encrypted = encrypt(unicode_data, passphrase, salt)
        decrypted = decrypt(encrypted, passphrase, salt)

        self.assertEqual(decrypted, unicode_data)

    def test_decrypt_wrong_passphrase_raises_error(self):
        """Test that wrong passphrase raises InvalidToken"""
        salt = generate_salt()
        encrypted = encrypt("secret", "correct", salt)

        with self.assertRaises(InvalidToken):
            decrypt(encrypted, "wrong", salt)

    def test_generate_salt_uniqueness(self):
        """Test that generate_salt produces unique salts"""
        salts = [generate_salt() for _ in range(100)]
        unique_salts = set(salts)

        # All salts should be unique
        self.assertEqual(len(unique_salts), 100)

    def test_generate_salt_length(self):
        """Test that salt is 16 bytes"""
        salt = generate_salt()
        self.assertEqual(len(salt), 16)

    def test_encode_decode_string_uuid(self):
        """Test encoding/decoding with string UUID"""
        uuid_str = str(uuid.uuid4())
        encoded = encode_id(uuid_str)
        decoded = decode_id(encoded)

        self.assertEqual(decoded, uuid.UUID(uuid_str))

    def test_decode_invalid_base64(self):
        """Test decoding invalid base64 returns None"""
        result = decode_id("not-valid-base64!")
        self.assertIsNone(result)

    def test_decode_empty_string(self):
        """Test decoding empty string returns None"""
        result = decode_id("")
        self.assertIsNone(result)


class MixinTests(TestCase):
    """Test KnuthIdMixin"""

    def setUp(self):
        self.factory = RequestFactory()

    def test_knuth_id_mixin_with_valid_oid(self):
        """Test KnuthIdMixin decodes valid OID correctly"""
        # Create a secret
        form = SecretCreateForm(data={'data': 'test', 'passphrase': 'pass'})
        self.assertTrue(form.is_valid())
        secret = form.save()

        # Create a mock view with the mixin
        view = SecretUpdateView()
        view.kwargs = {'oid': secret.oid}

        # Get object should work
        obj = view.get_object()
        self.assertEqual(obj.id, secret.id)

    def test_knuth_id_mixin_with_invalid_oid(self):
        """Test KnuthIdMixin raises 404 for invalid OID"""
        view = SecretUpdateView()
        view.kwargs = {'oid': 'invalid-oid!!!'}

        with self.assertRaises(Http404):
            view.get_object()

    def test_knuth_id_mixin_with_nonexistent_oid(self):
        """Test KnuthIdMixin raises 404 for valid but non-existent OID"""
        # Create a valid OID for a UUID that doesn't exist
        fake_uuid = uuid.uuid4()
        fake_oid = encode_id(fake_uuid)

        view = SecretUpdateView()
        view.kwargs = {'oid': fake_oid}

        with self.assertRaises(Http404):
            view.get_object()

    def test_knuth_id_mixin_without_oid(self):
        """Test KnuthIdMixin raises error when OID is missing"""
        view = SecretUpdateView()
        view.kwargs = {}

        with self.assertRaises(AttributeError):
            view.get_object()


class AdminTests(TestCase):
    """Test admin interface"""

    def setUp(self):
        self.site = AdminSite()
        self.admin = SecretAdmin(Secret, self.site)

    def test_admin_has_no_add_permission(self):
        """Test that add permission is disabled"""
        request = Mock()
        self.assertFalse(self.admin.has_add_permission(request))

    def test_admin_pretty_size(self):
        """Test pretty_size display method"""
        form = SecretCreateForm(data={'data': 'test', 'passphrase': 'pass'})
        self.assertTrue(form.is_valid())
        secret = form.save()

        pretty_size = self.admin.pretty_size(secret)
        self.assertIsInstance(pretty_size, str)
        self.assertIn('bytes', pretty_size.lower())

    def test_admin_pretty_expire_at(self):
        """Test pretty_expire_at display method"""
        form = SecretCreateForm(data={'data': 'test', 'passphrase': 'pass'})
        self.assertTrue(form.is_valid())
        secret = form.save()

        pretty_expire = self.admin.pretty_expire_at(secret)
        self.assertIsInstance(pretty_expire, str)

    def test_admin_on_site_link(self):
        """Test on_site display method returns HTML link"""
        form = SecretCreateForm(data={'data': 'test', 'passphrase': 'pass'})
        self.assertTrue(form.is_valid())
        secret = form.save()

        on_site_html = self.admin.on_site(secret)
        self.assertIsInstance(on_site_html, str)
        self.assertIn('<a href=', on_site_html)
        self.assertIn(secret.oid, on_site_html)

    def test_admin_list_display(self):
        """Test admin list_display configuration"""
        self.assertIn('id', self.admin.list_display)
        self.assertIn('on_site', self.admin.list_display)
        self.assertIn('pretty_size', self.admin.list_display)
        self.assertIn('pretty_expire_at', self.admin.list_display)

    def test_admin_ordering(self):
        """Test admin default ordering"""
        self.assertEqual(self.admin.ordering, ('-created_at',))


class IntegrationTests(TestCase):
    """Integration tests for complete workflows"""

    def setUp(self):
        self.client = Client()

    def test_complete_workflow_create_view_delete(self):
        """Test complete workflow: create secret, view it, verify deletion"""
        # Step 1: Create a secret
        secret_data = "This is my secret message!"
        passphrase = "super_secret_passphrase"

        response = self.client.post(reverse('secrets:secret-create'), {
            'data': secret_data,
            'passphrase': passphrase
        })

        # Should redirect after creation
        self.assertEqual(response.status_code, 302)

        # Get the created secret
        secret = Secret.objects.first()
        self.assertIsNotNone(secret)

        # Step 2: View the secret with correct passphrase
        oid = secret.oid
        response = self.client.post(
            reverse('secrets:secret-update', kwargs={'oid': oid}),
            {'passphrase': passphrase}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, secret_data)

        # Step 3: Verify secret was deleted
        self.assertEqual(Secret.objects.filter(pk=secret.pk).count(), 0)

    def test_get_request_to_create_view(self):
        """Test GET request to create view shows form"""
        response = self.client.get(reverse('secrets:secret-create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data')
        self.assertContains(response, 'passphrase')

    def test_get_request_to_update_view(self):
        """Test GET request to update view shows passphrase form"""
        # Create a secret first
        form = SecretCreateForm(data={'data': 'test', 'passphrase': 'pass'})
        self.assertTrue(form.is_valid())
        secret = form.save()

        response = self.client.get(
            reverse('secrets:secret-update', kwargs={'oid': secret.oid})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'passphrase')

    def test_multiple_secrets_independence(self):
        """Test that multiple secrets are independent"""
        # Create multiple secrets with different passphrases
        secrets_data = [
            ('secret1', 'pass1'),
            ('secret2', 'pass2'),
            ('secret3', 'pass3'),
        ]

        created_secrets = []
        for data, passphrase in secrets_data:
            response = self.client.post(reverse('secrets:secret-create'), {
                'data': data,
                'passphrase': passphrase
            })
            secret = Secret.objects.get(pk=Secret.objects.latest('created_at').pk)
            created_secrets.append((secret, data, passphrase))

        # Verify each can be accessed with its own passphrase
        for secret, expected_data, passphrase in created_secrets:
            response = self.client.post(
                reverse('secrets:secret-update', kwargs={'oid': secret.oid}),
                {'passphrase': passphrase}
            )
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, expected_data)

    def test_invalid_oid_returns_404(self):
        """Test that invalid OID in URL returns 404"""
        response = self.client.get(
            reverse('secrets:secret-update', kwargs={'oid': 'invalid-oid'})
        )
        self.assertEqual(response.status_code, 404)

    def test_secret_not_viewable_after_deletion(self):
        """Test that secret cannot be viewed after it's been accessed once"""
        # Create a secret
        form = SecretCreateForm(data={'data': 'one-time-secret', 'passphrase': 'pass'})
        self.assertTrue(form.is_valid())
        secret = form.save()
        oid = secret.oid

        # View it once
        response = self.client.post(
            reverse('secrets:secret-update', kwargs={'oid': oid}),
            {'passphrase': 'pass'}
        )
        self.assertEqual(response.status_code, 200)

        # Try to view it again
        response = self.client.get(
            reverse('secrets:secret-update', kwargs={'oid': oid})
        )
        self.assertEqual(response.status_code, 404)

    def test_wrong_passphrase_preserves_secret(self):
        """Test that entering wrong passphrase doesn't delete the secret"""
        # Create a secret
        form = SecretCreateForm(data={'data': 'secret', 'passphrase': 'correct'})
        self.assertTrue(form.is_valid())
        secret = form.save()
        oid = secret.oid

        # Try with wrong passphrase
        response = self.client.post(
            reverse('secrets:secret-update', kwargs={'oid': oid}),
            {'passphrase': 'wrong'}
        )

        # Secret should still exist
        self.assertEqual(Secret.objects.filter(pk=secret.pk).count(), 1)

        # Should be able to access with correct passphrase
        response = self.client.post(
            reverse('secrets:secret-update', kwargs={'oid': oid}),
            {'passphrase': 'correct'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'secret')

    def test_create_view_validation_error(self):
        """Test that validation errors are displayed on create view"""
        # Try to create with too large data
        large_data = 'x' * (50 * 1024 + 1)
        response = self.client.post(reverse('secrets:secret-create'), {
            'data': large_data,
            'passphrase': 'test'
        })

        # Should show form with error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'maximum')

    def test_concurrent_secret_access(self):
        """Test that secrets can be created and accessed concurrently"""
        # Create multiple secrets
        secrets = []
        for i in range(5):
            form = SecretCreateForm(data={'data': f'concurrent{i}', 'passphrase': f'pass{i}'})
            self.assertTrue(form.is_valid())
            secrets.append((form.save(), f'concurrent{i}', f'pass{i}'))

        # Access them in random order
        import random
        random.shuffle(secrets)

        for secret, expected_data, passphrase in secrets:
            response = self.client.post(
                reverse('secrets:secret-update', kwargs={'oid': secret.oid}),
                {'passphrase': passphrase}
            )
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, expected_data)
