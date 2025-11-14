# Security Documentation

## Security Update - Major Overhaul (2024)

This document describes the comprehensive security improvements made to the Ten Minute Secret application.

## Critical Vulnerabilities Fixed

### 1. ✅ Salt Reuse Vulnerability (CRITICAL)

**Previous Issue:**
- All secrets used the same salt (`SECRET_KEY`) for PBKDF2 key derivation
- Same passphrase → same encryption key across all secrets
- Enabled rainbow table attacks
- No forward secrecy

**Fix:**
- Each secret now generates a unique 16-byte random salt
- Salt stored in database alongside encrypted data
- Same passphrase produces different keys for different secrets
- PBKDF2 iterations increased from 100,000 to 600,000 (OWASP 2023 recommendation)

**Location:** `django-secrets/secrets/utils.py`, `models.py`, `forms.py`

### 2. ✅ Weak ID Space / Enumeration (CRITICAL)

**Previous Issue:**
- 32-bit sequential integer IDs (2.1 billion max)
- Knuth multiplicative hash easily reversible
- 6-character OIDs could be enumerated
- No rate limiting enabled enumeration attacks

**Fix:**
- Replaced with 128-bit UUIDs (2^128 = 340 undecillion possible IDs)
- Base64-encoded UUIDs in URLs (22+ characters)
- Cryptographically random, non-sequential
- Enumeration now computationally infeasible

**Location:** `django-secrets/secrets/models.py`, `utils.py`, `mixins.py`

### 3. ✅ No Rate Limiting (HIGH)

**Previous Issue:**
- Unlimited passphrase guessing attempts
- No protection against brute force attacks
- No abuse prevention for secret creation

**Fix:**
- Added `django-ratelimit` dependency
- Secret creation: 10 attempts per hour per IP
- Secret retrieval: 20 attempts per hour per IP
- Uses in-memory cache backend

**Location:** `django-secrets/secrets/views.py`

### 4. ✅ Outdated Dependencies with Known CVEs (CRITICAL)

**Previous Issues:**
- Django 1.9.4 (end-of-life, multiple CVEs)
- Python 3.4.3 (end-of-life)
- cryptography 1.2.3 (outdated)

**Fix:**
- Django upgraded to 4.2.11 (LTS)
- Python upgraded to 3.11.8
- cryptography upgraded to 42.0.5
- All dependencies updated to latest secure versions

**Location:** `requirements/base.txt`, `requirements/production.txt`, `runtime.txt`

### 5. ✅ Bytes Encoding Bug (MEDIUM)

**Previous Issue:**
- `decrypt()` returned `bytes` instead of `str`
- Templates may have displayed `b'secret text'` instead of actual content

**Fix:**
- Decrypt function now properly decodes bytes to UTF-8 string
- Added test to prevent regression

**Location:** `django-secrets/secrets/utils.py:79`

### 6. ✅ Hardcoded Secret Key in Repository (HIGH)

**Previous Issue:**
- Development `SECRET_KEY` committed to git
- Same key used as encryption salt (compounding the salt reuse issue)

**Fix:**
- Removed hardcoded key
- Development now uses environment variable or safe default
- Production requires `SECRET_KEY` environment variable

**Location:** `website/settings/development.py`

### 7. ✅ Weak Content Security Policy (MEDIUM)

**Previous Issue:**
- CSP allowed `'unsafe-inline'` for all sources
- Defeated XSS protection

**Fix:**
- Removed `'unsafe-inline'` directive
- Separated CSP directives by type
- Added specific allowed sources for scripts, styles, images

**Location:** `website/settings/base.py`

### 8. ✅ Missing Expiration Validation (MEDIUM)

**Previous Issue:**
- No double-check of expiration before displaying secret
- Potential race condition if form loaded before expiration but submitted after

**Fix:**
- Added expiration check in `form_valid()` before displaying
- Returns 404 if secret expired between form load and submission

**Location:** `django-secrets/secrets/views.py:36-41`

## Security Features Retained

These existing security features were preserved:

- ✅ HTTPS enforcement in production (HSTS enabled)
- ✅ Secure cookie flags (SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE)
- ✅ CSRF middleware enabled
- ✅ XSS filter enabled
- ✅ Clickjacking protection (X-Frame-Options: DENY)
- ✅ One-time view deletion
- ✅ 10-minute automatic expiration
- ✅ Zero-knowledge architecture (passphrases never stored)

## Testing

Comprehensive security tests added:

- **Crypto tests:** Unique salts, proper decryption, salt validation
- **Model tests:** UUID IDs, unique salts per secret, expiration
- **View tests:** One-time deletion, wrong passphrase handling, expiration
- **Regression tests:** Salt reuse prevention, enumeration prevention

**Run tests:**
```bash
python manage.py test secrets
```

## Deployment Requirements

### Environment Variables (Production)

**Required:**
- `SECRET_KEY` - Django secret key (generate with `get_random_secret_key()`)
- `DATABASE_URL` - PostgreSQL connection string

**Optional:**
- `GOOGLE_ANALYTICS_PROPERTY_ID` - GA tracking ID

**No longer required:**
- ~~`SECRET_KNUTH_PRIME`~~ - Removed (now using UUIDs)
- ~~`SECRET_KNUTH_INVERSE`~~ - Removed
- ~~`SECRET_KNUTH_RANDOM`~~ - Removed

### Database Migration

**⚠️ BREAKING CHANGE:** This update requires database migration that **deletes all existing secrets**.

Why: The old encryption scheme used a shared salt, making all existing secrets fundamentally insecure. They cannot be safely migrated.

**Migration steps:**
```bash
# Backup database (optional, but recommended)
python manage.py dumpdata > backup.json

# Run migrations (this will delete all secrets)
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput
```

## Security Best Practices

### For Developers

1. **Never commit secrets** to git
2. **Use environment variables** for sensitive config
3. **Keep dependencies updated** regularly
4. **Run security tests** before deploying
5. **Review CVE databases** for Django/Python/dependencies

### For Users

1. **Use strong passphrases** (12+ characters, mixed case, numbers, symbols)
2. **Don't reuse passphrases** across secrets
3. **Share URLs securely** (encrypted chat, not email)
4. **Verify recipient** before sharing
5. **Understand limitations** (10 min expiration, one-time view)

## Threat Model

### What This Application Protects Against

✅ Passive database compromise (encryption at rest)
✅ Rainbow table attacks (unique salts)
✅ Enumeration attacks (UUIDs)
✅ Brute force attacks (rate limiting)
✅ Man-in-the-middle (HTTPS/HSTS)
✅ XSS attacks (CSP, auto-escaping)
✅ CSRF attacks (CSRF tokens)

### What This Application DOES NOT Protect Against

❌ Active server compromise (attacker has shell access)
❌ Compromised client devices
❌ Keyloggers on sender/recipient machines
❌ Phishing attacks
❌ Weak user-chosen passphrases
❌ Social engineering

## Reporting Security Issues

If you discover a security vulnerability, please email: enrico@foltran.xyz

**Do not** open public GitHub issues for security vulnerabilities.

## Security Changelog

### 2024-01 - Major Security Overhaul
- Fixed critical salt reuse vulnerability
- Migrated to UUIDs from sequential IDs
- Added rate limiting
- Updated all dependencies (Django 1.9 → 4.2, Python 3.4 → 3.11)
- Strengthened CSP policy
- Added comprehensive security tests
- Increased PBKDF2 iterations to 600,000
- Fixed bytes encoding bug

### Previous
- Basic encryption with Fernet
- 10-minute expiration
- One-time view deletion
- HTTPS enforcement
