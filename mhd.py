#!/usr/bin/env python3
"""
Mujin HelpDesk (mhd) — IT troubleshooting CLI for Debian 13, Windows 11, macOS

Use `python mhd.py <command> --help` for per-command help.
Run `python mhd.py web` to start the web dashboard on http://localhost:5000
"""

import argparse
import os
import sys
import yaml
from pathlib import Path

# Add local path for helpdesk module
helpdesk_path = os.path.join(os.path.dirname(__file__), 'helpdesk')
sys.path.insert(0, helpdesk_path)

from helpdesk.kb import KnowledgeBase, format_search_results, format_article, format_diagnostic, format_ticket

KB_PATH = os.path.join(os.path.dirname(__file__), 'knowledge')


def main():
    parser = argparse.ArgumentParser(
        prog='mhd',
        description='Mujin HelpDesk — IT troubleshooting CLI and web dashboard',
        epilog='Use `python mhd.py web` to start the web dashboard',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # General overview
    parser.add_argument('--version', action='version', version='Mujin HelpDesk 1.0.0')

    # web command
    web_parser = subparsers.add_parser('web', help='Start web dashboard')

    # Basic commands
    list_parser = subparsers.add_parser('list', help='List articles by OS/category')
    list_parser.add_argument('os', nargs='?', choices=['debian', 'windows', 'mac', 'all'],
                            default='all', help='OS to list (default: all)')
    list_parser.add_argument('--category', '-c', help='Filter by category')

    # Search command
    search_parser = subparsers.add_parser('search', help='Search for articles')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--os', '-o', choices=['debian', 'windows', 'mac'],
                              help='Filter by OS')

    # Show command
    show_parser = subparsers.add_parser('show', help='Show full article')
    show_parser.add_argument('id', help='Article ID (e.g., deb-apt-lock)')

    # Category command
    cat_parser = subparsers.add_parser('cat', help='Show articles in category')
    cat_parser.add_argument('os', choices=['debian', 'windows', 'mac'], help='OS')
    cat_parser.add_argument('category', help='Category name')

    # Diagnostic command
    diag_parser = subparsers.add_parser('diag', help='Print diagnostic command block')
    diag_parser.add_argument('id_or_topic', help='Article ID or topic to search for diagnostic commands')

    # Ticket command
    ticket_parser = subparsers.add_parser('ticket', help='Generate FreshService ticket template')
    ticket_parser.add_argument('os', choices=['debian', 'windows', 'mac'], help='OS')
    ticket_parser.add_argument('--symptom', '-s', help='Symptom to base ticket on')

    # Sources command
    sources_parser = subparsers.add_parser('sources', help='Show source links for article')
    sources_parser.add_argument('id', nargs='?', help='Article ID (show all if omitted)')

    # Config command
    config_parser = subparsers.add_parser('config', help='Show configuration info')
    config_parser.add_argument('--path', action='store_true', help='Show knowledge base path')

    # Parse arguments
    args = parser.parse_args()

    # Initialize knowledge base
    kb = KnowledgeBase(KB_PATH)

    # Route commands
    if args.command == 'web':
        # Import and start ITSS PRO TOOL web app
        import os as _os
        from helpdesk.web.app import app
        port = int(_os.environ.get('PORT', '8000'))
        debug = _os.environ.get('DEBUG', '').lower() in ('1', 'true', 'yes')
        print(f"ITSS PRO TOOL web app on http://localhost:{port} (login required)")
        print("Press Ctrl+C to stop")
        app.run(host='0.0.0.0', port=port, debug=debug)

    elif args.command == 'list':
        articles = kb.get_articles(os_filter=args.os if args.os != 'all' else None,
                                 category_filter=args.category)
        print(format_search_results(articles, title=f"Articles ({args.os if args.os != 'all' else 'all OSes'})"))

    elif args.command == 'search':
        articles = kb.search(args.query, os_filter=args.os)
        print(format_search_results(articles, title=f"Search: {args.query}"))

    elif args.command == 'show':
        article = kb.get_article(args.id)
        if article:
            print(format_article(article))
        else:
            print(f"Article '{args.id}' not found.")
            sys.exit(1)

    elif args.command == 'cat':
        articles = kb.get_articles(os_filter=args.os, category_filter=args.category)
        print(format_search_results(articles, title=f"Category: {args.category} ({args.os})"))

    elif args.command == 'diag':
        # Try to find by ID first, then search for symptom
        article = kb.get_article(args.id_or_topic)
        if not article:
            # Search for symptom
            articles = kb.search(args.id_or_topic)
            if articles:
                article = articles[0]
            else:
                print(f"Could not find article matching '{args.id_or_topic}'")
                sys.exit(1)

        print(format_diagnostic(article))

    elif args.command == 'ticket':
        if not args.symptom:
            print("Please provide a symptom using --symptom option:")
            print("Example: python mhd.py ticket debian --symptom 'apt update failed'")
            sys.exit(1)

        template = kb.generate_ticket_template(args.os, args.symptom)
        print(format_ticket(template))

    elif args.command == 'sources':
        if args.id:
            article = kb.get_article(args.id)
            if article:
                for i, source in enumerate(article.get('sources', []), 1):
                    print(f"{i}. {source['name']}")
                    print(f"   {source['url']}")
            else:
                print(f"Article '{args.id}' not found.")
                sys.exit(1)
        else:
            # Show all sources
            articles = kb.get_articles()
            sources_seen = set()
            for article in articles:
                for source in article.get('sources', []):
                    source_id = source['url']
                    if source_id not in sources_seen:
                        sources_seen.add(source_id)
                        print(f"{source['name']}")
                        print(f"   {source['url']}")
            print(f"\nTotal unique sources: {len(sources_seen)}")

    elif args.command == 'config':
        if args.path:
            print(f"Knowledge base path: {KB_PATH}")
            # List available YAML files
            for root, dirs, files in os.walk(KB_PATH):
                level = root.replace(KB_PATH, '').count(os.sep)
                indent = ' ' * 2 * level
                print(f"{indent}{os.path.basename(root)}/")
                subindent = ' ' * 2 * (level + 1)
                for file in files:
                    if file.endswith('.yaml') or file.endswith('.yml'):
                        print(f"{subindent}{file}")
        else:
            print("Mujin HelpDesk Configuration")
            print(f"Knowledge base: {KB_PATH}")
            articles = kb.get_articles()
            os_counts = {}
            for article in articles:
                os_name = article.get('os', 'unknown')
                os_counts[os_name] = os_counts.get(os_name, 0) + 1
            print(f"Articles: {len(articles)}")
            print(f"  Debian: {os_counts.get('debian', 0)}")
            print(f"  Windows: {os_counts.get('windows', 0)}")
            print(f"  macOS: {os_counts.get('mac', 0)}")
            print(f"Web dashboard: Available via 'python mhd.py web'")

    else:
        # Default help
        parser.print_help()


if __name__ == '__main__':
    main()