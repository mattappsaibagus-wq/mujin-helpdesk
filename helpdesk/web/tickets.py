"""
Saved-ticket store for ITSS PRO TOOL.

Persists generated FreshService ticket templates to a JSON file so an
engineer can come back to a ticket they started. The file lives under
data/tickets.json relative to the project root.
"""

import json
import os
import threading
import time
import uuid

_LOCK = threading.Lock()


def _store_path():
    """Absolute path to the JSON store, created on first use."""
    root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_dir = os.path.join(root, 'data')
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, 'tickets.json')


def _read():
    """Load all tickets from disk, tolerating a missing or empty file."""
    path = _store_path()
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as handle:
        try:
            data = json.load(handle)
        except json.JSONDecodeError:
            return []
    return data if isinstance(data, list) else []


def _write(tickets):
    """Persist the full ticket list atomically."""
    path = _store_path()
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as handle:
        json.dump(tickets, handle, indent=2)
    os.replace(tmp, path)


def list_tickets():
    """Return saved tickets, newest first."""
    with _LOCK:
        tickets = _read()
    return sorted(tickets, key=lambda t: t.get('created_at', 0), reverse=True)


def get_ticket(ticket_id):
    """Return one ticket by id, or None."""
    for ticket in list_tickets():
        if ticket.get('id') == ticket_id:
            return ticket
    return None


def save_ticket(entry):
    """
    Store a new ticket and return the saved record.

    entry keys: title, os, symptom, ticket_text, article_id (all optional).
    """
    record = {
        'id': uuid.uuid4().hex[:12],
        'title': str(entry.get('title', '')).strip() or 'Untitled ticket',
        'os': str(entry.get('os', '')).strip(),
        'symptom': str(entry.get('symptom', '')).strip(),
        'ticket_text': str(entry.get('ticket_text', '')),
        'article_id': entry.get('article_id') or None,
        'created_at': int(time.time()),
    }
    with _LOCK:
        tickets = _read()
        tickets.append(record)
        _write(tickets)
    return record


def delete_ticket(ticket_id):
    """Remove a ticket by id. Returns True if one was removed."""
    with _LOCK:
        tickets = _read()
        kept = [t for t in tickets if t.get('id') != ticket_id]
        if len(kept) == len(tickets):
            return False
        _write(kept)
    return True
