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

2. Update your urls setting like this::

    urlpatterns = [
        url(r'', include('secrets.urls', 'secrets')),
        //...
    ]

3. Run `python manage.py migrate` to create the secrets models.
