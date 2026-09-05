"""
Shared pytest configuration.

Several modules call ``load_dotenv()`` at import time (e.g. ``api.main``), which
injects the developer's real ``.env`` into ``os.environ`` during collection.
That makes env-sensitive tests depend on whatever secrets happen to be on the
machine. To keep the suite hermetic, strip credential-bearing vars once at
session start so tests exercise the code's own defaults unless they opt in.
Individual tests still set exactly what they need via ``monkeypatch``.
"""

import os

import pytest

# Vars that a local ``.env`` might define but that tests must not inherit.
_STRIP = (
    "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD",
    "SMTP_FROM", "SMTP_SECURITY",
    "GMAIL_ADDRESS", "GMAIL_APP_PASSWORD",
    "TURSO_DATABASE_URL", "TURSO_AUTH_TOKEN",
    "HUNTER_API_KEY", "LINKEDIN_EMAIL", "LINKEDIN_PASSWORD",
)


@pytest.fixture(scope="session", autouse=True)
def _hermetic_env():
    for var in _STRIP:
        os.environ.pop(var, None)
    yield
