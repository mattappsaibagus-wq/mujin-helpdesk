"""
ITSS PRO TOOL — web application.

A Flask operations console for IT support: search the troubleshooting
knowledge base (Debian 13, Windows 11, macOS), read guided diagnostics, and
generate and save FreshService ticket templates. Access is gated by a single
shared password.
"""

import os
import sys
from datetime import timedelta

from flask import (
    Flask, render_template, request, jsonify, redirect, url_for, session,
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from helpdesk.kb import (  # noqa: E402
    KnowledgeBase, format_ticket, format_diagnostic,
)
from helpdesk.web import auth  # noqa: E402
from helpdesk.web import tickets as ticket_store  # noqa: E402

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
)
app.config['SECRET_KEY'] = auth.SECRET_KEY
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('DEBUG', '').lower() not in (
    '1', 'true', 'yes',
)

KB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'knowledge'
)
kb = KnowledgeBase(KB_PATH)

OS_LABELS = {'debian': 'Debian 13', 'windows': 'Windows 11', 'mac': 'macOS'}
PUBLIC_ENDPOINTS = {'login', 'health', 'static'}


@app.before_request
def require_login():
    """Redirect anonymous visitors to the login page, except public routes."""
    if request.endpoint in PUBLIC_ENDPOINTS or request.endpoint is None:
        return None
    if not auth.is_authenticated():
        if request.path.startswith('/api') or request.is_json:
            return jsonify({'error': 'authentication required'}), 401
        return redirect(url_for('login', next=request.path))
    return None


@app.context_processor
def inject_globals():
    """Values available to every template."""
    return {'os_labels': OS_LABELS, 'brand': 'ITSS PRO TOOL'}


def _article_payload(article):
    """Shape one article for JSON responses."""
    keywords = [str(k) for k in article.get('keywords', [])]
    return {
        'id': article['id'],
        'title': article['title'],
        'os': article['os'],
        'category': article['category'],
        'severity': article.get('severity', 'common'),
        'keywords': keywords,
        'symptoms': article.get('symptoms', []),
        'causes': article.get('causes', []),
        'resolution': article.get('resolution', []),
        'diagnosis': article.get('diagnosis', []),
        'commands': article.get('commands', []),
        'sources': article.get('sources', []),
    }


# --- Authentication -------------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Shared-password gate."""
    if auth.is_authenticated():
        return redirect(url_for('index'))

    error = None
    if request.method == 'POST':
        if auth.is_locked_out():
            error = 'Too many attempts. Wait a moment and try again.'
        elif auth.check_password(request.form.get('password', '')):
            auth.do_login()
            target = request.args.get('next') or url_for('index')
            if not target.startswith('/'):
                target = url_for('index')
            return redirect(target)
        else:
            auth.record_failure()
            error = 'Incorrect access code.'

    return render_template('login.html', error=error)


@app.route('/logout', methods=['POST'])
def logout():
    """End the session."""
    auth.do_logout()
    return redirect(url_for('login'))


@app.route('/health')
def health():
    """Unauthenticated liveness check for deployments."""
    return jsonify({'status': 'ok', 'articles': len(kb.get_articles())})


# --- Dashboard ------------------------------------------------------------

@app.route('/')
def index():
    """Operations console: search, per-OS panels, and saved tickets."""
    samples = {}
    counts = {}
    for os_name in OS_LABELS:
        articles = kb.get_articles(os_filter=os_name)
        counts[os_name] = len(articles)
        samples[os_name] = articles[:4]
    return render_template(
        'index.html',
        samples=samples,
        counts=counts,
        total=len(kb.get_articles()),
        categories=kb.get_all_categories(),
        saved=ticket_store.list_tickets()[:6],
    )


@app.route('/browse/<os_name>')
def browse(os_name):
    """All articles for one operating system, grouped by category."""
    if os_name not in OS_LABELS:
        return render_template('404.html'), 404
    articles = kb.get_articles(os_filter=os_name)
    grouped = {}
    for article in articles:
        grouped.setdefault(article.get('category', 'general'), []).append(article)
    return render_template(
        'browse.html',
        os_name=os_name,
        grouped=grouped,
        total=len(articles),
    )


# --- Knowledge base -------------------------------------------------------

@app.route('/api/articles')
def api_articles():
    """All articles as JSON for client-side search."""
    os_filter = request.args.get('os') or None
    articles = kb.get_articles(os_filter=os_filter)
    return jsonify({
        'articles': [_article_payload(a) for a in articles],
        'total': len(articles),
    })


@app.route('/search')
def search():
    """Server-side search across the knowledge base."""
    query = request.args.get('q', '').strip()
    os_filter = request.args.get('os') or None
    if not query:
        return jsonify({'results': [], 'query': query, 'total': 0})
    matches = kb.search(query, os_filter=os_filter)
    results = [
        {
            'id': a['id'], 'title': a['title'], 'os': a['os'],
            'category': a['category'],
            'severity': a.get('severity', 'common'),
            'symptom': (a.get('symptoms') or [''])[0],
        }
        for a in matches
    ]
    return jsonify({'results': results, 'query': query, 'total': len(results)})


@app.route('/article/<article_id>')
def article_detail(article_id):
    """Full article with diagnosis, resolution, and commands."""
    article = kb.get_article(article_id)
    if not article:
        return render_template('404.html'), 404
    related = [
        a for a in kb.get_articles(
            os_filter=article.get('os'),
            category_filter=article.get('category'),
        )
        if a['id'] != article_id
    ][:3]
    return render_template('article.html', article=article, related=related)


@app.route('/diagnostic/<article_id>')
def diagnostic(article_id):
    """Diagnostic command block for one article."""
    article = kb.get_article(article_id)
    if not article:
        return jsonify({'error': 'Article not found'}), 404
    return jsonify({
        'formatted': format_diagnostic(article),
        'article': _article_payload(article),
    })


# --- Ticket generator + saved tickets -------------------------------------

@app.route('/ticket', methods=['GET', 'POST'])
def ticket_generator():
    """Build a FreshService ticket template from an OS and a symptom."""
    if request.method == 'POST':
        os_name = request.form.get('os', 'debian')
        symptom = request.form.get('symptom', '').strip()
        template = kb.generate_ticket_template(os_name, symptom)
        return jsonify({
            'success': True,
            'ticket_text': format_ticket(template),
            'title': template['title'],
            'os': template['os'],
            'symptom': symptom,
            'article_id': template.get('article_id'),
        })

    categories_by_os = {
        name: kb.get_categories(os_filter=name) for name in OS_LABELS
    }
    return render_template('ticket.html', categories_by_os=categories_by_os)


@app.route('/tickets', methods=['GET', 'POST'])
def saved_tickets():
    """List saved tickets, or store a newly generated one."""
    if request.method == 'POST':
        payload = request.get_json(silent=True) or request.form
        record = ticket_store.save_ticket({
            'title': payload.get('title', ''),
            'os': payload.get('os', ''),
            'symptom': payload.get('symptom', ''),
            'ticket_text': payload.get('ticket_text', ''),
            'article_id': payload.get('article_id'),
        })
        return jsonify({'success': True, 'ticket': record}), 201
    return render_template('tickets.html', tickets=ticket_store.list_tickets())


@app.route('/tickets/<ticket_id>', methods=['DELETE'])
def delete_saved_ticket(ticket_id):
    """Remove one saved ticket."""
    removed = ticket_store.delete_ticket(ticket_id)
    if not removed:
        return jsonify({'error': 'not found'}), 404
    return jsonify({'success': True})


# --- Errors ---------------------------------------------------------------

@app.errorhandler(404)
def not_found(_error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(_error):
    return render_template('500.html'), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8000'))
    debug = os.environ.get('DEBUG', '').lower() in ('1', 'true', 'yes')
    app.run(host='0.0.0.0', port=port, debug=debug)
