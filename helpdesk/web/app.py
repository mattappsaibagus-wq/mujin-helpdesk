"""
Mujin HelpDesk Web Dashboard
Flask-based web interface for browsing IT troubleshooting KB across Debian 13, Windows 11, macOS.

Features:
- Search across all OS categories
- Browse by OS and category
- View full articles with formatted content
- Generate FreshService ticket templates
- Copy-command buttons via embedded JSON
"""

import json
import os
import sys
from flask import Flask, render_template, request, jsonify, send_from_directory
from helpdesk.kb import KnowledgeBase, format_ticket

# Ensure parent package is found for web module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'mujin-helpdesk-dev')

KB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'knowledge')
kb = KnowledgeBase(KB_PATH)


@app.route('/')
def index():
    """Dashboard home page with 3 OS sections and search."""
    # Get categories and article counts per OS
    categories = kb.get_all_categories()
    stats = kb.get_severity_stats()

    # Get sample articles per OS for preview
    samples = {}
    for os_name in ['debian', 'windows', 'mac']:
        articles = kb.get_articles(os_filter=os_name)
        if articles:
            samples[os_name] = articles[:3]  # First 3 articles

    # Get total article counts
    all_articles = kb.get_articles()
    total = len(all_articles)

    return render_template(
        'index.html',
        title='Mujin HelpDesk — IT Troubleshooting',
        categories=categories,
        stats=stats,
        samples=samples,
        total=total,
        year=2026
    )


@app.route('/api/articles')
def api_articles():
    """API endpoint returning all articles as JSON for client-side search."""
    os_filter = request.args.get('os', None)
    category_filter = request.args.get('category', None)

    articles = kb.get_articles(os_filter=os_filter, category_filter=category_filter)

    # Prepare data for client-side search
    results = []
    for article in articles:
        # Build searchable text
        text = " ".join([
            article.get('title', ''),
            " ".join(article.get('keywords', [])),
            " ".join(article.get('symptoms', [])),
            " ".join(article.get('causes', [])),
            " ".join(article.get('resolution', [])),
        ])

        results.append({
            'id': article['id'],
            'title': article['title'],
            'os': article['os'],
            'category': article['category'],
            'severity': article.get('severity', 'common'),
            'keywords': article.get('keywords', []),
            'symptoms': article.get('symptoms', []),
            'causes': article.get('causes', []),
            'resolution': article.get('resolution', []),
            'diagnosis': article.get('diagnosis', []),
            'commands': article.get('commands', []),
            'sources': article.get('sources', []),
            'search_text': text.lower(),
        })

    return jsonify({
        'articles': results,
        'total': len(results),
        'os_counts': {
            'debian': len(kb.get_articles(os_filter='debian')),
            'windows': len(kb.get_articles(os_filter='windows')),
            'mac': len(kb.get_articles(os_filter='mac')),
        }
    })


@app.route('/article/<article_id>')
def article_detail(article_id):
    """Full article view."""
    article = kb.get_article(article_id)

    if not article:
        return render_template('404.html', article_id=article_id), 404

    # Get related articles (same category or same OS)
    related = []
    category = article.get('category')
    os_name = article.get('os')

    if category:
        related_same_cat = kb.get_articles(os_filter=os_name, category_filter=category)
        # Exclude current article and take up to 3
        related = [a for a in related_same_cat if a['id'] != article_id][:3]

    if not related:
        # Try same OS
        related = kb.get_articles(os_filter=os_name)[:3]

    return render_template(
        'article.html',
        article=article,
        related=related,
        year=2026
    )


@app.route('/ticket', methods=['GET', 'POST'])
def ticket_generator():
    """FreshService ticket template generator."""
    if request.method == 'POST':
        data = request.form
        os_name = data.get('os', 'debian')
        symptom = data.get('symptom', '')

        template = kb.generate_ticket_template(os_name, symptom)
        return jsonify({
            'success': True,
            'ticket_text': format_ticket(template)
        })

    # GET - show form
    all_articles = kb.get_articles()
    # Group unique symptoms/categories for the form
    os_options = ['debian', 'windows', 'mac']
    categories_by_os = {}
    for os_name in os_options:
        categories = kb.get_categories(os_filter=os_name)
        categories_by_os[os_name] = categories

    return render_template(
        'ticket.html',
        title='FreshService Ticket Generator',
        os_options=os_options,
        categories_by_os=categories_by_os,
        year=2026
    )


@app.route('/search')
def search():
    """AJAX search endpoint."""
    query = request.args.get('q', '')
    os_filter = request.args.get('os', '')

    if not query:
        return jsonify({'results': [], 'query': query})

    matches = kb.search(query, os_filter=os_filter if os_filter else None)

    results = []
    for article in matches:
        results.append({
            'id': article['id'],
            'title': article['title'],
            'os': article['os'],
            'category': article['category'],
            'severity': article.get('severity', 'common'),
        })

    return jsonify({
        'results': results,
        'query': query,
        'total': len(results)
    })


@app.route('/diagnostic/<article_id>')
def diagnostic(article_id):
    """Return diagnostic commands for an article as JSON/HTML."""
    article = kb.get_article(article_id)

    if not article:
        return jsonify({'error': 'Article not found'}), 404

    formatted = kb.format_diagnostic(article)
    # Also return raw data for JS
    return jsonify({
        'formatted': formatted,
        'article': {
            'id': article['id'],
            'title': article['title'],
            'os': article['os'],
            'commands': article.get('commands', []),
            'diagnosis': article.get('diagnosis', []),
            'sources': article.get('sources', []),
        }
    })


@app.route('/ticket/<os_name>')
def ticket_page(os_name):
    """Show ticket template page for a given OS."""
    valid_oses = ['debian', 'windows', 'mac']
    if os_name not in valid_oses:
        return render_template('404.html', article_id=os_name), 404

    # Get an example article to show categories
    articles = kb.get_articles(os_filter=os_name)
    categories = kb.get_categories(os_filter=os_name) if articles else []

    return render_template(
        'ticket-page.html',
        title=f'Ticket Template: {os_name.title()}',
        os_name=os_name,
        categories=categories,
        articles=articles[:5],  # Show a few examples
        year=2026
    )


# Error handlers
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)