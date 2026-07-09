"""HTTP Basic Auth dependency for admin endpoints.

Credentials are read from environment variables on every call (not cached at
module load) so rotating ADMIN_USERNAME / ADMIN_PASSWORD in backend/.env does
not require a server restart. Comparison uses ``secrets.compare_digest`` to
defeat timing attacks.
"""
import os
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

# `auto_error=False` lets us return a single, consistent 401 with the
# ``WWW-Authenticate`` header whether the client sent no header, the wrong
# header, or a malformed one.
_basic = HTTPBasic(auto_error=False)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing admin credentials",
        headers={"WWW-Authenticate": 'Basic realm="SupportIQ Admin"'},
    )


def verify_admin_credentials(
    credentials: HTTPBasicCredentials | None = Depends(_basic),
) -> None:
    """FastAPI dependency that gates access to admin endpoints.

    Reads ``ADMIN_USERNAME`` and ``ADMIN_PASSWORD`` from the environment on
    every call, compares them with ``secrets.compare_digest`` against the
    credentials supplied in the ``Authorization: Basic ...`` header, and
    raises a 401 with ``WWW-Authenticate: Basic realm="SupportIQ Admin"`` on
    any mismatch or missing header.
    """
    expected_user = os.getenv("ADMIN_USERNAME")
    expected_pass = os.getenv("ADMIN_PASSWORD")

    # If the env vars are unset, refuse all access rather than fall through.
    if not expected_user or not expected_pass:
        raise _unauthorized()

    if credentials is None:
        raise _unauthorized()

    user_ok = secrets.compare_digest(credentials.username or "", expected_user)
    pass_ok = secrets.compare_digest(credentials.password or "", expected_pass)

    if not (user_ok and pass_ok):
        raise _unauthorized()
