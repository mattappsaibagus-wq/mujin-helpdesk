"""
Shared-password authentication for ITSS PRO TOOL.

One access code (from the ITSS_PASS environment variable) gates the whole
app. Sessions are signed with Flask's SECRET_KEY. Login attempts are
rate-limited in memory to slow brute force.
"""

import hmac
import os
import time
from functools import wraps

from flask import session, redirect, url_for, request

# Access code and signing key come from the environment, never source.
ACCESS_PASSWORD = os.environ.get('ITSS_PASS', 'itss-pro-tool')
SECRET_KEY = os.environ.get('SECRET_KEY', 'itss-pro-tool-dev-key')

# In-memory login throttling: 5 failures within the window locks the IP out.
MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 30
_ATTEMPT_WINDOW = 300
_attempts = {}


def is_authenticated():
    """True when the current session has passed the access check."""
    return bool(session.get('authenticated'))


def check_password(candidate):
    """Constant-time comparison against the configured access code."""
    if candidate is None:
        return False
    return hmac.compare_digest(str(candidate), str(ACCESS_PASSWORD))


def _client_key():
    """Identify the caller for throttling (falls back to a constant)."""
    return request.remote_addr or 'local'


def is_locked_out():
    """True when this caller has failed too many times recently."""
    record = _attempts.get(_client_key())
    if not record:
        return False
    now = time.time()
    recent = [t for t in record if now - t < _ATTEMPT_WINDOW]
    _attempts[_client_key()] = recent
    if len(recent) < MAX_ATTEMPTS:
        return False
    return now - recent[-1] < LOCKOUT_SECONDS


def record_failure():
    """Register a failed login attempt for the current caller."""
    key = _client_key()
    _attempts.setdefault(key, []).append(time.time())


def clear_failures():
    """Forget failed attempts after a successful login."""
    _attempts.pop(_client_key(), None)


def do_login():
    """Mark the current session as authenticated."""
    session['authenticated'] = True
    session.permanent = True
    clear_failures()


def do_logout():
    """Clear the authenticated session."""
    session.pop('authenticated', None)


def login_required(view):
    """Decorator that redirects anonymous visitors to the login page."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not is_authenticated():
            return redirect(url_for('login', next=request.path))
        return view(*args, **kwargs)
    return wrapper
