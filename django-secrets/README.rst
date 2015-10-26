=======
SECRETS
=======

Quick start
-----------

1. Add "secrets" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = (
        ...
        'secrets',
    )

2. Run `python manage.py migrate` to create the secrets models.

3. Start the development server and visit http://127.0.0.1:8000/admin/
   (you'll need the Admin app enabled).
