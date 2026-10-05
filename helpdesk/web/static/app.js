/* ITSS PRO TOOL — inline behaviour: search, copy, ticket generator, saved tickets. */
(function () {
  'use strict';

  function qs(sel, root) { return (root || document).querySelector(sel); }
  function qsa(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

  /* --- Live search on the console --- */
  var form = qs('#searchForm');
  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var q = qs('#searchInput').value.trim();
      var osSel = qs('#searchOs');
      var os = osSel ? osSel.value : '';
      if (!q) return;
      var url = '/search?q=' + encodeURIComponent(q) + (os ? '&os=' + os : '');
      fetch(url).then(function (r) { return r.json(); }).then(function (data) {
        var box = qs('#searchResults');
        if (!data.results.length) {
          box.innerHTML = '<p class="empty">No articles matched "' + q + '".</p>';
          return;
        }
        box.innerHTML = data.results.map(function (a) {
          return '<a class="result" href="/article/' + a.id + '">' +
            '<span class="oschip ' + a.os + '">' + a.os + '</span>' +
            '<div><h4>' + a.title + '</h4><p>' + a.category +
            (a.symptom ? ' — ' + a.symptom : '') + '</p></div>' +
            '<span class="pill ' + a.severity + '">' + a.severity + '</span>' +
            '</a>';
        }).join('');
      }).catch(function () {
        qs('#searchResults').innerHTML = '<p class="empty">Search error — try again.</p>';
      });
    });
  }

  /* --- Copy buttons on article pages --- */
  document.addEventListener('click', function (e) {
    var copyBtn = e.target.closest && e.target.closest('[data-copy]');
    if (copyBtn) return copyToClipboard(copyBtn.getAttribute('data-copy'), copyBtn);

    var copyTarget = e.target.closest && e.target.closest('[data-copy-target]');
    if (copyTarget) {
      var el = document.getElementById('ticket-' + copyTarget.getAttribute('data-copy-target'));
      return copyToClipboard((el && el.textContent) || '', copyTarget);
    }

    var del = e.target.closest && e.target.closest('[data-delete]');
    if (del) return deleteTicket(del.getAttribute('data-delete'), del);
  });

  function copyToClipboard(text, btn) {
    var original = btn.textContent;
    var fallback = function () {
      var ta = document.createElement('textarea');
      ta.value = text; document.body.appendChild(ta);
      ta.select();
      try { document.execCommand('copy'); } finally { document.body.removeChild(ta); }
      flash(btn, original);
    };
    if (navigator.clipboard && window.isSecureContext !== false) {
      navigator.clipboard.writeText(text).then(function () { flash(btn, original); }).catch(fallback);
    } else {
      fallback();
    }
  }

  function flash(btn, original) {
    var old = btn.textContent;
    btn.textContent = 'Copied ✓';
    setTimeout(function () { btn.textContent = old; }, 1400);
  }

  function deleteTicket(id, btn) {
    if (!confirm('Delete this saved ticket?')) return;
    fetch('/tickets/' + id, { method: 'DELETE' })
      .then(function (r) {
        if (r.ok) {
          var item = btn.closest('[data-id]');
          if (item) item.remove();
        }
      })
      .catch(function () { /* leave the row; user can retry */ });
  }

  /* --- Ticket generator --- */
  var ticketForm = qs('#ticketForm');
  if (ticketForm) {
    ticketForm.addEventListener('submit', function (e) {
      e.preventDefault();
      var body = new FormData(ticketForm);
      // Only need os + symptom for the server template.
      var formData = new URLSearchParams();
      formData.set('os', body.get('os'));
      formData.set('symptom', body.get('symptom'));
      fetch('/ticket', { method: 'POST', body: formData })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (!data.success) return;
          window._lastTicket = data;
          var out = qs('#ticketOutput');
          out.textContent = data.ticket_text;
          out.style.display = 'block';
          qs('#ticketActions').hidden = false;
          qs('#saveStatus').textContent = '';
        });
    });

    qs('#copyTicket').addEventListener('click', function (e) {
      copyToClipboard(window._lastTicket ? window._lastTicket.ticket_text : '', e.target);
    });

    qs('#saveTicket').addEventListener('click', function () {
      if (!window._lastTicket) return;
      fetch('/tickets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(window._lastTicket)
      })
        .then(function (r) { return r.json(); })
        .then(function () {
          qs('#saveStatus').textContent = 'Saved ✓';
        });
    });
  }
})();