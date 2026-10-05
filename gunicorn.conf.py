"""
ITSS PRO TOOL — gunicorn server configuration.

Loaded automatically when gunicorn is started from the project root, e.g.:

    python3 -m gunicorn -c gunicorn.conf.py

Override via environment variables: GUNICORN_BIND, GUNICORN_WORKERS.
"""

import multiprocessing
import os

# Bind to all interfaces on port 8000 by default — the app is gated by the
# shared password (ITSS_PASS). Restrict with GUNICORN_BIND if it must be
# reachable only from localhost, e.g. GUNICORN_BIND=127.0.0.1:8000.
bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:8000')

# One worker per CPU + 1, capped at 4 for a small internal tool.
cpus = multiprocessing.cpu_count() or 1
workers = int(os.environ.get('GUNICORN_WORKERS', str(min(4, cpus + 1))))

timeout = 45
graceful_timeout = 15
accesslog = '-'
errorlog = '-'

wsgi_app = 'helpdesk.web.run:app'