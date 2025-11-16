# Ten Minute Secret

A secure web application for sharing sensitive information that automatically self-destructs after 10 minutes or one view, whichever comes first.

**Live Demo:** https://xms.herokuapp.com/

## Overview

Ten Minute Secret provides a secure way to share passwords, API keys, credentials, and other sensitive information without leaving permanent traces. The recipient can only view the secret once, and it automatically expires after 10 minutes.

### Why Use This?

- **No permanent storage**: Secrets are deleted immediately after viewing
- **Time-limited**: All secrets expire after 10 minutes, regardless of whether they're viewed
- **Zero-knowledge architecture**: Passphrases are never stored on the server
- **End-to-end encryption**: Secrets are encrypted before storage using Fernet symmetric encryption
- **Protection against enumeration**: UUID-based identifiers prevent systematic secret discovery
- **Rate limiting**: Built-in protection against brute force and abuse

## Key Features

- **One-time view**: Secrets are automatically deleted after a single successful retrieval
- **10-minute expiration**: All secrets expire 10 minutes after creation
- **Strong encryption**: PBKDF2-HMAC-SHA256 with 600,000 iterations (OWASP 2023 recommendation)
- **Unique salts**: Each secret uses its own cryptographically random 16-byte salt
- **UUID identifiers**: 128-bit UUIDs prevent enumeration attacks (2^128 possible IDs)
- **Rate limiting**:
  - 10 secret creations per hour per IP
  - 20 retrieval attempts per hour per IP
- **Security headers**: CSP, HSTS, X-Frame-Options, and secure cookie flags
- **Mobile responsive**: Works seamlessly on all devices

## Security

This application implements multiple layers of security:

### Encryption
- **Algorithm**: Fernet (AES-128-CBC with HMAC-SHA256)
- **Key derivation**: PBKDF2-HMAC-SHA256 with 600,000 iterations
- **Unique salts**: Each secret generates and stores its own random 16-byte salt
- **Zero-knowledge**: Passphrases never touch the database

### Protection Mechanisms
- UUID-based secret identifiers (impossible to enumerate)
- Rate limiting on creation and retrieval
- HTTPS enforcement with HSTS
- CSRF protection
- XSS protection via Content Security Policy
- Clickjacking prevention (X-Frame-Options: DENY)

### What This Protects Against
- Database compromise (encryption at rest)
- Rainbow table attacks (unique salts)
- Enumeration attacks (UUIDs)
- Brute force attacks (rate limiting)
- Man-in-the-middle attacks (HTTPS/HSTS)
- XSS attacks (CSP + auto-escaping)
- CSRF attacks (CSRF tokens)

For detailed security information, see [SECURITY.md](SECURITY.md).

## Installation

### Prerequisites

- Python 3.11+
- PostgreSQL (for production)
- pip and virtualenv

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/enricofoltran/ten-minute-secret.git
   cd ten-minute-secret
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements/base.txt
   ```

4. **Set environment variables**
   ```bash
   export DJANGO_SETTINGS_MODULE=website.settings.debug
   export SECRET_KEY='your-secret-key-here'  # Generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Start development server**
   ```bash
   python manage.py runserver
   ```

7. **Access the application**

   Open http://localhost:8000 in your browser

### Production Deployment

#### Environment Variables

**Required:**
- `SECRET_KEY` - Django secret key (generate with `get_random_secret_key()`)
- `DATABASE_URL` - PostgreSQL connection string (e.g., `postgres://user:pass@host:5432/dbname`)

**Optional:**
- `GOOGLE_ANALYTICS_PROPERTY_ID` - Google Analytics tracking ID

#### Deployment Steps

1. **Install production dependencies**
   ```bash
   pip install -r requirements/production.txt
   ```

2. **Set production environment variables**
   ```bash
   export DJANGO_SETTINGS_MODULE=website.settings.production
   export SECRET_KEY='your-production-secret-key'
   export DATABASE_URL='your-postgres-connection-string'
   ```

3. **Run migrations**
   ```bash
   python manage.py migrate
   ```

4. **Collect static files**
   ```bash
   python manage.py collectstatic --noinput
   ```

5. **Start with Gunicorn**
   ```bash
   gunicorn website.wsgi:application --bind 0.0.0.0:8000
   ```

#### Heroku Deployment

This application is configured for Heroku deployment:

```bash
heroku create your-app-name
heroku addons:create heroku-postgresql:mini
heroku config:set SECRET_KEY='your-secret-key'
git push heroku main
heroku run python manage.py migrate
```

## Usage

### Creating a Secret

1. Navigate to the application homepage
2. Enter your secret message (max 50KB)
3. Choose a strong passphrase
4. Click "Create Secret"
5. Share the generated URL and passphrase separately with the recipient

### Retrieving a Secret

1. Open the shared URL
2. Enter the passphrase
3. View the secret (it will be deleted immediately after)

### Best Practices

**For Senders:**
- Use strong, unique passphrases (12+ characters)
- Share the URL and passphrase through different channels
- Verify the recipient before sharing
- Don't reuse passphrases

**For Recipients:**
- Retrieve the secret as soon as possible
- Copy the secret to a secure location immediately
- Don't refresh or navigate back (the secret will be gone)

## Development

### Running Tests

```bash
python manage.py test django_secrets
```

### Project Structure

```
ten-minute-secret/
├── django-secrets/          # Reusable Django app for secrets management
│   └── django_secrets/
│       ├── models.py        # Secret model with UUID and encryption
│       ├── views.py         # Create and retrieve views with rate limiting
│       ├── forms.py         # Forms with encryption/decryption logic
│       ├── utils.py         # Crypto utilities (encrypt, decrypt, salts)
│       ├── managers.py      # Custom QuerySet for available secrets
│       └── tests.py         # Comprehensive security tests
├── website/                 # Django project configuration
│   ├── settings/            # Environment-specific settings
│   ├── templates/           # HTML templates
│   └── static/              # CSS, JS, images
├── requirements/            # Dependency specifications
├── manage.py                # Django management script
└── Procfile                 # Heroku deployment configuration
```

### Tech Stack

- **Framework**: Django 4.2 LTS
- **Language**: Python 3.11
- **Database**: PostgreSQL (production), SQLite (development)
- **Encryption**: cryptography (Fernet)
- **Rate Limiting**: django-ratelimit
- **Web Server**: Gunicorn
- **Frontend**: Foundation 6, Crispy Forms

### Dependencies

See [requirements/base.txt](requirements/base.txt) for the full list. Key dependencies:

- Django 4.2.11
- cryptography 42.0.5
- django-ratelimit 4.1.0
- django-csp 4.0b1
- gunicorn 21.2.0 (production)
- psycopg2-binary 2.9.9 (production)

## Security Considerations

### Threat Model

This application is designed for sharing moderately sensitive information (passwords, API keys, credentials) with a known recipient over a short time window.

**Suitable for:**
- Sharing passwords with team members
- Transmitting API keys to contractors
- One-time credential sharing
- Temporary secure note passing

**Not suitable for:**
- Long-term secret storage
- Highly classified information
- Sharing with untrusted parties
- Situations requiring audit trails

### Limitations

- Does not protect against compromised client devices
- Does not protect against keyloggers
- Does not protect against active server compromise
- Relies on users choosing strong passphrases
- Does not provide identity verification

### Reporting Security Issues

If you discover a security vulnerability, please email: enrico@foltran.xyz

**Do not** open public GitHub issues for security vulnerabilities.

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Contribution Guidelines

- Write tests for new features
- Follow PEP 8 style guidelines
- Update documentation as needed
- Ensure all tests pass before submitting PR
- Consider security implications of changes

## Changelog

### 2024 - Major Security Overhaul
- Fixed critical salt reuse vulnerability
- Migrated from sequential IDs to UUIDs
- Added comprehensive rate limiting
- Updated Django 1.9 → 4.2 LTS
- Updated Python 3.4 → 3.11
- Increased PBKDF2 iterations to 600,000
- Added security test suite
- Strengthened Content Security Policy
- Fixed bytes encoding bug

See [SECURITY.md](SECURITY.md) for detailed security changelog.

## Authors

See [AUTHORS](AUTHORS) file.

## Acknowledgments

- Built with Django and the Python cryptography library
- Foundation framework for responsive design
- Inspired by the need for secure, temporary information sharing

## Support

For issues, questions, or feature requests, please open an issue on GitHub.

---

**Remember**: This application is designed for temporary, one-time secret sharing. For long-term secret storage, use a dedicated password manager.
