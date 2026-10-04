/**
 * Mujin HelpDesk - Frontend JavaScript
 * Handles client-side search, interactions, and UI enhancements
 */

class HelpDeskApp {
    constructor() {
        this.articles = [];
        this.isLoaded = false;
        this.debounceTimer = null;
        this.init();
    }

    async init() {
        await this.loadArticles();
        this.setupEventListeners();
    }

    async loadArticles() {
        try {
            const response = await fetch('/api/articles');
            const data = await response.json();
            this.articles = data.articles || [];
            this.isLoaded = true;
            this.buildSearchIndex();
            this.updateStats(data);
        } catch (error) {
            console.error('Failed to load articles:', error);
        }
    }

    buildSearchIndex() {
        // Create a simple inverted index for fast client-side search
        this.searchIndex = {};
        this.articles.forEach((article, idx) => {
            const text = article.search_text || '';
            const words = text.toLowerCase().split(/\s+/);
            words.forEach(word => {
                if (word.length > 2) {
                    if (!this.searchIndex[word]) {
                        this.searchIndex[word] = [];
                    }
                    if (!this.searchIndex[word].includes(idx)) {
                        this.searchIndex[word].push(idx);
                    }
                }
            });
        });
    }

    updateStats(data) {
        // Update the stat numbers if they exist on the page
        if (data.os_counts) {
            Object.entries(data.os_counts).forEach(([os, count]) => {
                const element = document.getElementById(`stat-${os}`);
                if (element) {
                    element.textContent = count;
                }
            });
        }
    }

    setupEventListeners() {
        // Global search input
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => this.handleSearch(e));
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.performSearch(e.target.value, document.getElementById('searchOs')?.value || 'all');
                }
            });
        }

        // Search OS filter
        const searchOs = document.getElementById('searchOs');
        if (searchOs) {
            searchOs.addEventListener('change', (e) => {
                this.performSearch(searchInput?.value || '', e.target.value);
            });
        }

        // Keyboard shortcut: / to focus search
        document.addEventListener('keydown', (e) => {
            if (e.key === '/' && document.activeElement.tagName !== 'INPUT' &&
                document.activeElement.tagName !== 'TEXTAREA' &&
                document.activeElement.tagName !== 'SELECT') {
                e.preventDefault();
                searchInput?.focus();
            }
        });
    }

    handleSearch(event) {
        const query = event.target.value.trim();
        const osFilter = document.getElementById('searchOs')?.value || 'all';

        // Debounce
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
            this.performSearch(query, osFilter);
        }, 200);
    }

    async performSearch(query, osFilter) {
        const resultsContainer = document.getElementById('searchResults');
        if (!resultsContainer) return;

        if (!query) {
            resultsContainer.classList.add('hidden');
            return;
        }

        try {
            // Try server-side search first
            const params = new URLSearchParams({ q: query });
            if (osFilter !== 'all') params.append('os', osFilter);

            const response = await fetch(`/api/search?${params}`);
            const data = await response.json();

            this.renderSearchResults(data.results, resultsContainer);
            resultsContainer.classList.remove('hidden');
        } catch (error) {
            console.error('Search error:', error);
            // Fallback to client-side search
            this.clientSideSearch(query, osFilter, resultsContainer);
            resultsContainer.classList.remove('hidden');
        }
    }

    clientSideSearch(query, osFilter, container) {
        const lowerQuery = query.toLowerCase();
        const results = [];

        this.articles.forEach((article, idx) => {
            if (osFilter !== 'all' && article.os !== osFilter) return;

            // Check in search index
            const words = lowerQuery.split(/\s+/);
            let score = 0;

            words.forEach(word => {
                if (word.length > 2 && this.searchIndex[word]?.includes(idx)) {
                    score += 1;
                }
            });

            // Bonus for exact matches in title
            if (article.title.toLowerCase().includes(lowerQuery)) {
                score += 5;
            }

            if (score > 0) {
                results.push({ ...article, score });
            }
        });

        // Sort by score
        results.sort((a, b) => b.score - a.score);

        this.renderSearchResults(results.slice(0, 20), container);
    }

    renderSearchResults(results, container) {
        if (!results || results.length === 0) {
            container.innerHTML = '<div class="empty-state">No articles found for your search</div>';
            return;
        }

        let html = '<div class="search-result-list">';
        results.forEach(article => {
            const sev = article.severity || 'common';
            html += `
                <div class="search-result-item" onclick="window.location.href='/article/${article.id}'">
                    <div class="search-result-header">
                        <span class="search-result-os ${article.os}">${article.os.toUpperCase()}</span>
                        <span class="search-result-severity ${sev}">${{ 'common': '●', 'moderate': '◑', 'severe': '✖' }[sev]}</span>
                    </div>
                    <h4>${this.escapeHtml(article.title)}</h4>
                    <p>Category: ${this.escapeHtml(article.category)}</p>
                </div>
            `;
        });
        html += '</div>';
        container.innerHTML = html;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Utility methods for other parts of the app
    static async copyToClipboard(text) {
        if (navigator.clipboard) {
            try {
                await navigator.clipboard.writeText(text);
                return true;
            } catch (err) {
                console.error('Clipboard API failed:', err);
            }
        }

        // Fallback
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();

        try {
            const successful = document.execCommand('copy');
            document.body.removeChild(textArea);
            return successful;
        } catch (err) {
            console.error('Fallback copy failed:', err);
            document.body.removeChild(textArea);
            return false;
        }
    }

    static showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 12px 24px;
            border-radius: 6px;
            color: white;
            font-weight: 500;
            z-index: 1000;
            background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#2563eb'};
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            animation: slideIn 0.3s ease;
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {
                if (document.body.contains(notification)) {
                    document.body.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }

    static async fetchArticle(id) {
        try {
            const response = await fetch(`/api/articles/${id}`);
            return await response.json();
        } catch (error) {
            console.error('Failed to fetch article:', error);
            return null;
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.helpDesk = new HelpDeskApp();
});

// Add animation styles
const style = document.createElement('style');
style.textContent = `
@keyframes slideIn {
    from { transform: translateX(100%); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
}
@keyframes slideOut {
    from { transform: translateX(0); opacity: 1; }
    to { transform: translateX(100%); opacity: 0; }
}
`;
document.head.appendChild(style);

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = HelpDeskApp;
}