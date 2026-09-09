"""Minimal Django configuration for testing django_forge's own code in
isolation -- not the demo project. providers.py etc. read django.conf.settings
at call time, so it needs to be configured, but nothing here needs a real app.
"""

import django
from django.conf import settings


def pytest_configure():
    if not settings.configured:
        settings.configure(USE_TZ=True)
        django.setup()
