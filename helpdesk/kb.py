"""
Knowledge base loader and search engine for Mujin HelpDesk.
Handles YAML knowledge base loading, search indexing, and formatting.
"""

import os
import glob
import sys
import difflib
from typing import List, Dict, Any, Optional

import yaml


class KnowledgeBase:
    """
    Loads and searches a YAML-based knowledge base organized into
    debian/, windows/, and mac/ subdirectories.
    """

    def __init__(self, kb_path: str):
        self.kb_path = kb_path
        self._articles: List[Dict[str, Any]] = []
        self._index: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        """Load all YAML files from knowledge directory."""
        yaml_files = glob.glob(
            os.path.join(self.kb_path, '**', '*.yaml'),
            recursive=True
        ) + glob.glob(
            os.path.join(self.kb_path, '**', '*.yml'),
            recursive=True
        )

        for filepath in sorted(yaml_files):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data and isinstance(data, list):
                        for article in data:
                            self._validate_article(article)
                            self._articles.append(article)
                    elif data and isinstance(data, dict):
                        self._validate_article(data)
                        self._articles.append(data)
            except Exception as e:
                print(f"Warning: Failed to load {filepath}: {e}", file=__import__('sys').stderr)

        # Build lookup index
        for article in self._articles:
            self._index[article['id']] = article

    def _validate_article(self, article: Dict[str, Any]) -> None:
        """Ensure article has required fields."""
        required_fields = ['id', 'title', 'os', 'category', 'symptoms', 'resolution', 'commands', 'sources']
        for field in required_fields:
            if field not in article:
                raise ValueError(f"Article {article.get('id', 'unknown')} missing required field: {field}")

    def get_articles(
        self,
        os_filter: Optional[str] = None,
        category_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Filter articles by OS and/or category.
        Returns list of article dicts.
        """
        results = self._articles

        if os_filter:
            results = [a for a in results if a.get('os') == os_filter]

        if category_filter:
            results = [a for a in results if a.get('category') == category_filter]

        return results

    def get_article(self, article_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single article by ID."""
        return self._index.get(article_id)

    def search(
        self,
        query: str,
        os_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search articles by title, keywords, symptoms, and causes.
        Returns list of matching articles, sorted by relevance score.
        """
        query_lower = query.lower().strip()
        matches = []

        for article in self._articles:
            if os_filter and article.get('os') != os_filter:
                continue

            # Calculate relevance score
            score = 0
            text_blob_parts = [article.get('title', '')]

            # keywords as strings (filter out non-strings)
            keywords = article.get('keywords', [])
            keywords_str = [str(k) if not isinstance(k, str) else k for k in keywords]
            text_blob_parts.append(" ".join(keywords_str))

            text_blob_parts.extend(article.get('symptoms', []))
            text_blob_parts.extend(article.get('causes', []))
            text_blob_parts.extend(str(v) for v in article.get('resolution', []))

            text_blob = " ".join(text_blob_parts).lower()

            # Exact keyword matches
            for kw in keywords_str:
                if kw.lower() == query_lower:
                    score += 10
                elif kw.lower().startswith(query_lower):
                    score += 5

            # Fuzzy match in title
            if query_lower in article.get('title', '').lower():
                score += 8

            # In symptoms or causes
            for symptom in article.get('symptoms', []):
                if query_lower in symptom.lower():
                    score += 3

            # Exact phrase match
            if len(query_lower) > 2 and query_lower in text_blob:
                score += 6

            # Per-word scoring (ignore stop words; multi-word queries need
            # most meaningful words to match)
            stop_words = {'the', 'a', 'an', 'is', 'are', 'to', 'of', 'in', 'on',
                          'for', 'with', 'and', 'or', 'not', 'it', 'its', 'can',
                          'cannot', 'failed', 'failing', 'fail', 'error', 'issue',
                          'problem', 'issues'}
            query_words = [w for w in query_lower.split()
                           if w not in stop_words and len(w) > 1]
            if query_words:
                matched = [w for w in query_words if w in text_blob]
                score += 3 * len(matched)
                # Require that most meaningful words matched
                if len(matched) / len(query_words) < 0.5:
                    continue

            # Use difflib for fuzzy matching on title
            ratio = difflib.SequenceMatcher(None, query_lower, article.get('title', '').lower()).ratio()
            if ratio > 0.6:
                score += int(ratio * 5)

            if score > 0:
                matches.append((score, article))

        # Sort by relevance
        matches.sort(key=lambda x: -x[0])
        return [article for _, article in matches]

    def get_categories(self, os_filter: Optional[str] = None) -> List[str]:
        """Get unique categories, optionally filtered by OS."""
        categories = set()
        for article in self.get_articles(os_filter=os_filter):
            categories.add(article.get('category', ''))
        return sorted(categories)

    def get_all_categories(self) -> Dict[str, List[str]]:
        """Get categories organized by OS."""
        result = {}
        for os_name in ['debian', 'windows', 'mac']:
            result[os_name] = self.get_categories(os_filter=os_name)
        return result

    def get_severity_stats(self) -> Dict[str, Dict[str, int]]:
        """Get severity distribution by OS."""
        stats = {}
        for os_name in ['debian', 'windows', 'mac']:
            count = {'common': 0, 'moderate': 0, 'severe': 0}
            for article in self.get_articles(os_filter=os_name):
                sev = article.get('severity', 'common')
                count[sev] = count.get(sev, 0) + 1
            stats[os_name] = count
        return stats

    def generate_ticket_template(
        self,
        os_name: str,
        symptom: str
    ) -> Dict[str, Any]:
        """
        Generate a FreshService-ready ticket template based on OS and symptom.
        """
        matches = self.search(symptom, os_filter=os_name)

        if matches:
            best_match = matches[0]
            title = best_match['title']
            causes = best_match.get('causes', [])
            diagnosis = best_match.get('diagnosis', [])
            resolution = best_match.get('resolution', [])
            commands = best_match.get('commands', [])
            sources = best_match.get('sources', [])
        else:
            title = f"{os_name.title()}: {symptom}"
            causes = ['Unknown - needs investigation']
            diagnosis = ['Further investigation required']
            resolution = ['See diagnostic steps below']
            commands = []
            sources = []

        return {
            'os': os_name,
            'title': title,
            'symptom': symptom,
            'causes': causes,
            'diagnosis': diagnosis,
            'resolution': resolution,
            'commands': commands,
            'sources': sources,
            'article_id': matches[0]['id'] if matches else None
        }


def format_search_results(
    articles: List[Dict[str, Any]],
    title: str = "Search Results",
    max_per_page: int = 50
) -> str:
    """
    Format article search results for terminal display.
    """
    lines = []
    lines.append("")
    lines.append(f"╔══ {title} ({len(articles)} found)")

    if not articles:
        lines.append("╙── No articles found matching your query.")
        return "\n".join(lines)

    for article in articles[:max_per_page]:
        sev_marker = {'common': '[*]', 'moderate': '[!]', 'severe': '[X]'}.get(
            article.get('severity', 'common'), '[?]'
        )
        lines.append(f"╙── {sev_marker} [{article['os']}] {article['title']}")
        lines.append(f"    ID: {article['id']}")
        lines.append(f"    Category: {article['category']} | Severity: {article.get('severity', 'N/A')}")
        if article.get('symptoms'):
            lines.append(f"    Symptoms: {'; '.join(article['symptoms'][:3])}")
        lines.append("")

    if len(articles) > max_per_page:
        lines.append(f"  ... and {len(articles) - max_per_page} more (use 'mhd show <id>' for details)")

    return "\n".join(lines)


def format_article(article: Dict[str, Any]) -> str:
    """
    Format a full article for terminal display.
    """
    lines = []
    lines.append("")
    lines.append(f"┏━━ {article['title']} ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"  ID:       {article['id']}")
    lines.append(f"  OS:       {article['os']}  |  Category: {article['category']}  |  Severity: {article.get('severity', 'common')}")
    lines.append("")

    if article.get('keywords'):
        lines.append(f"  Keywords: {', '.join(article['keywords'])}")
        lines.append("")

    lines.append("━━ Symptoms ━━")
    for i, symptom in enumerate(article.get('symptoms', []), 1):
        lines.append(f"  {i}. {symptom}")

    if article.get('causes'):
        lines.append("")
        lines.append("━━ Causes ━━")
        for i, cause in enumerate(article['causes'], 1):
            lines.append(f"  {i}. {cause}")

    if article.get('diagnosis'):
        lines.append("")
        lines.append("━━ Diagnosis ━━")
        for i, step in enumerate(article['diagnosis'], 1):
            lines.append(f"  {i}. {step}")

    lines.append("")
    lines.append("━━ Resolution ━━")
    for i, step in enumerate(article.get('resolution', []), 1):
        lines.append(f"  {i}. {step}")

    if article.get('related'):
        lines.append("")
        lines.append("━━ See Also ━━")
        lines.append(f"  Related: {', '.join(article['related'])}")

    if article.get('sources'):
        lines.append("")
        lines.append("━━ Sources ━━")
        for source in article['sources']:
            lines.append(f"  • {source['name']}")
            lines.append(f"    {source['url']}")

    return "\n".join(lines)


def format_diagnostic(article: Dict[str, Any]) -> str:
    """
    Format diagnostic commands for copy-paste.
    """
    lines = []
    lines.append("")
    lines.append(f"┏━━ Diagnostic Commands: {article['title']} ━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"  Article ID: {article['id']}  |  OS: {article['os']}")
    lines.append("")

    if article.get('diagnosis'):
        lines.append("━━ Check this first ━━")
        for step in article['diagnosis']:
            lines.append(f"  $ {step}")
        lines.append("")

    if article.get('commands'):
        lines.append("━━ Commands to run on affected machine ━━")
        for cmd in article['commands']:
            lines.append(f"  $ {cmd}")
        lines.append("")

    if article.get('sources'):
        lines.append("━━ Reference ━━")
        for source in article['sources']:
            lines.append(f"  • {source['name']}: {source['url']}")

    return "\n".join(lines)


def format_ticket(template: Dict[str, Any]) -> str:
    """
    Format a FreshService ticket template for copy-paste into ticket description.
    """
    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("  MUJIN HELPDESK — TICKET TEMPLATE")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"[Title] {template['title']}")
    lines.append("")
    lines.append("━━ Symptom ━━")
    lines.append(template['symptom'])
    lines.append("")

    if template['article_id']:
        lines.append(f"━━ Related KB Article ━━")
        lines.append(f"ID: {template['article_id']}")
        lines.append("")

    lines.append("━━ Likely Causes ━━")
    for i, cause in enumerate(template['causes'], 1):
        lines.append(f"{i}. {cause}")
    lines.append("")

    lines.append("━━ Diagnostic Steps ━━")
    lines.append("Run the following on the affected machine and paste output:")
    lines.append("")
    for i, step in enumerate(template['diagnosis'], 1):
        lines.append(f"{i}. {step}")
    lines.append("")

    lines.append("━━ Commands to Run ━━")
    if template['commands']:
        for cmd in template['commands']:
            lines.append(f"$ {cmd}")
        lines.append("")
        lines.append("--- Paste output here ---")
        lines.append("")
    else:
        lines.append("(No specific commands - see diagnostic steps above)")
        lines.append("")

    lines.append("━━ Resolution Steps ━━")
    for i, step in enumerate(template['resolution'], 1):
        lines.append(f"{i}. {step}")
    lines.append("")

    if template['sources']:
        lines.append("━━ Reference Links ━━")
        for source in template['sources']:
            lines.append(f"• {source['name']}: {source['url']}")
        lines.append("")

    lines.append("━━ Environment Details ━━")
    lines.append("OS: " + template['os'].title())
    lines.append("User: [enter user name]")
    lines.append("Hostname: [enter hostname]")
    lines.append("Affected application/service: [enter details]")
    lines.append("")

    lines.append("━━ Ticket Status ━━")
    lines.append("Status: Open")
    lines.append("Priority: [Set based on impact]")
    lines.append("Assignee: [IT Support Engineer]")
    lines.append("Category: " + template['os'].title() + " Support")
    lines.append("Tags: " + ", ".join([template['os'], template.get('category', 'general')]))
    lines.append("")

    return "\n".join(lines)