"""
ITSS PRO TOOL — web entrypoint.

Run:
    python -m helpdesk.web.run

Configuration comes from environment variables:
    ITSS_PASS   shared access code (default: itss-pro-tool)
    SECRET_KEY  session signing key  (default: itss-pro-tool-dev-key)
    PORT        HTTP port            (default: 8000)
    DEBUG       "1"/"true" enables debug mode
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from helpdesk.web.app import app  # noqa: E402

if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8000'))
    debug = os.environ.get('DEBUG', '').lower() in ('1', 'true', 'yes')
    app.run(host='0.0.0.0', port=port, debug=debug)