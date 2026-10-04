"""
Mujin HelpDesk package

Core troubleshooting knowledge base and formatting utilities for IT support
covering Debian 13, Windows 11, and macOS.

Usage:
    from helpdesk.kb import KnowledgeBase
    kb = KnowledgeBase('../knowledge')
    results = kb.search('apt lock')
"""

from .kb import KnowledgeBase

__all__ = ['KnowledgeBase']
__version__ = '1.0.0'