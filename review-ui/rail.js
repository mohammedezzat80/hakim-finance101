/* HAKIM shared left rail — ONE shell component for every page (fixes the per-page
   inconsistency where Accounts affordances flickered in and out). Injects identical
   markup + behaviour into <aside class="rail" id="hakim-rail"> and reads the current
   path to set the active nav. Relies on each page's existing .rail CSS classes. */
(function () {
  var rail = document.getElementById('hakim-rail') || document.querySelector('.rail');
  if (!rail) return;
  var esc = function (s) { return (s || '').replace(/[&<>"]/g, function (c) { return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]); }); };
  var money0 = function (n) { return Number(n || 0).toLocaleString('en-US', { maximumFractionDigits: 0 }); };
  var P = location.pathname;
  function active(href) { return href === '/' ? (P === '/' || P === '') : (P === href || P.indexOf(href) === 0); }
  // ---- Face layer: load the shared design tokens (safe/opt-in) + icon system on every page ----
  if (!document.getElementById('hakim-face-css')) {
    var fl = document.createElement('link'); fl.id = 'hakim-face-css'; fl.rel = 'stylesheet'; fl.href = '/face.css';
    document.head.appendChild(fl);
    var fj = document.createElement('script'); fj.src = '/face.js'; document.head.appendChild(fj);
  }
  // self-contained nav icons (inline so the rail never depends on face.js load order) — Tabler idiom
  var RIC = {
    '/dashboard': '<path d="M4 13h6V4H4zM14 20h6V10h-6zM14 7h6V4h-6zM4 20h6v-4H4z"/>',
    '/today': '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.4 1.4M17.6 17.6L19 19M19 5l-1.4 1.4M6.4 17.6L5 19"/>',
    '/family': '<circle cx="9" cy="8" r="3"/><path d="M3 20a6 6 0 0 1 12 0M16 5.5a3 3 0 0 1 0 5M17 20a6 6 0 0 0-2-4"/>',
    '/subscriptions': '<path d="M4 9a5 5 0 0 1 5-5h8l-3-3M20 15a5 5 0 0 1-5 5H7l3 3"/>',
    '/forecast': '<path d="M4 15l4-4 3 3 5-6M14 8h4v4"/>',
    '/debt': '<rect x="3" y="6" width="18" height="12" rx="2"/><path d="M3 10h18M7 15h3"/>',
    '/insights': '<path d="M9 18h6M10 21h4M12 3a6 6 0 0 1 4 10c-.7.7-1 1.3-1 2H9c0-.7-.3-1.3-1-2a6 6 0 0 1 4-10z"/>',
    '/budget': '<circle cx="12" cy="12" r="8"/><path d="M12 12V4a8 8 0 0 1 8 8z"/>',
    '/zakat': '<path d="M20 14a8 8 0 1 1-9-11 6.5 6.5 0 0 0 9 11z"/>',
    '/wealth': '<path d="M6 4h12l3 5-9 11L3 9z"/><path d="M3 9h18M9 4l-3 5 6 11 6-11-3-5"/>',
    '/': '<path d="M4 5h16v14H4z"/><path d="M4 9h4l2 3h4l2-3h4"/>',
    '/calendar': '<path d="M4 5h16v16H4z"/><path d="M4 9h16M8 3v4M16 3v4"/>',
    '/categories': '<path d="M12 3H5a2 2 0 0 0-2 2v7l9 9 9-9z"/><circle cx="8.5" cy="8.5" r="1.2"/>',
    '/reports': '<path d="M4 20V4M4 20h16"/><path d="M8 16v-4M12 16V8M16 16v-6"/>',
    '/goals': '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="1"/>',
    '/owed': '<path d="M12 8l-2-2a2 2 0 0 0-3 0L3 10l4 4 1-1"/><path d="M12 8l3-2a2 2 0 0 1 3 0l3 4-4 4-6-6"/>',
    '/accounts': '<path d="M3 10l9-6 9 6M5 10v9M19 10v9M9 19v-6M15 19v-6M3 21h18"/>',
    '/recurring': '<path d="M4 9a5 5 0 0 1 5-5h8l-3-3M20 15a5 5 0 0 1-5 5H7l3 3"/>',
    '/rules': '<path d="M13 3L4 14h7l-1 7 9-11h-7z"/>',
    '/guide': '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.8.4-1 .8-1 1.7M12 17h.01"/>',
    '/settings': '<circle cx="12" cy="12" r="3"/><path d="M19.4 13a7.5 7.5 0 0 0 0-2l2-1.5-2-3.4-2.3 1a7 7 0 0 0-1.7-1L14.5 3h-4l-.3 2.2a7 7 0 0 0-1.7 1l-2.3-1-2 3.4 2 1.5a7.5 7.5 0 0 0 0 2l-2 1.5 2 3.4 2.3-1a7 7 0 0 0 1.7 1l.3 2.2h4l.3-2.2a7 7 0 0 0 1.7-1l2.3 1 2-3.4z"/>'
  };
  function navIcon(href) { var p = RIC[href] || RIC['/']; return '<svg class="ic" viewBox="0 0 24 24" aria-hidden="true">' + p + '</svg>'; }
  // LIVE tabs (built). Recurring lives here now — it's live, not "coming".
  var NAV = [
    ['/dashboard', '◈', 'Dashboard'], ['/today', '☀', 'Today'], ['/', '▤', 'Desk', true], ['/calendar', '▦', 'Calendar'],
    ['/categories', '🏷️', 'Categories'], ['/reports', '📊', 'Reports'], ['/goals', '🎯', 'Goals'],
    ['/owed', '🤝', 'Owed to me'], ['/family', '👪', 'Family'], ['/subscriptions', '🔁', 'Subscriptions'],
    ['/forecast', '📈', 'Forecast'], ['/debt', '💳', 'Debt coach'], ['/insights', '💡', 'Insights'],
    ['/budget', '◐', 'Budget'], ['/zakat', '☾', 'Zakat'], ['/wealth', '◆', 'Wealth'],
    ['/accounts', '🏦', 'Accounts'], ['/recurring', '🔁', 'Recurring'], ['/rules', '⚡', 'Rules'],
    ['/guide', '؟', 'Guide'], ['/settings', '⚙', 'Settings']
  ];
  // COMING surfaces — every one traces to the blueprint/BLOCKED.md, in rough unlock order.
  // [slug, iconPath, label, unlock-whisper, oneActionAway] — an honest progress board, not a grey wall
  // THE OPENING complete — every gated surface is now a live tab. The board is empty by design.
  var SOON = [];
  // inject self-contained styling for the SOON rows so they read dimmed+compact on every
  // page regardless of that page's CSS (quiet — the future must not shout over the present).
  if (!document.getElementById('hakim-rail-css')) {
    var st = document.createElement('style'); st.id = 'hakim-rail-css';
    st.textContent = '.hakim-soon{display:flex;align-items:center;gap:10px;padding:6px 12px;color:#4b5260;text-decoration:none;border-radius:8px}'
      + '.hakim-soon:hover{background:#141821}'
      + '.hakim-soon .si{width:18px;flex:none;display:flex;justify-content:center;color:#4b5260;opacity:.72}.hakim-soon .si .ic{width:16px;height:16px}'
      + '.hakim-soon .sl{display:flex;flex-direction:column;line-height:1.22;min-width:0}'
      + '.hakim-soon .st{font-size:13px}.hakim-soon .su{font-size:9px;color:#3d4453;font-family:var(--mono,monospace);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}'
      + '.hakim-soon small{margin-left:auto;font-size:8px;letter-spacing:1px;text-transform:uppercase;color:#3d4453;font-family:var(--mono,monospace);align-self:flex-start;margin-top:2px}'
      + '.hakim-soon.near{color:#8A90A6}.hakim-soon.near .si{color:#72D5C8;opacity:.9}.hakim-soon.near .su{color:#5A6072}.hakim-soon.near small{color:#72D5C8}'
      + '@media(max-width:900px){.hakim-soon .sl,.hakim-soon small{display:none}}'
      // Ask Finance affordance (pinned above the status line) + global overlay
      + '.hakim-ask{display:flex;align-items:center;gap:9px;margin:0 2px 10px;padding:9px 12px;border:1px solid #2a3550;border-radius:10px;background:rgba(114,213,200,.05);cursor:pointer;color:#8A90A6;font-size:13px}'
      + '.hakim-ask:hover{border-color:#72D5C8;color:#cfd3db}.hakim-ask .sp{color:#72D5C8}.hakim-ask kbd{margin-left:auto;font-family:var(--mono,monospace);font-size:9px;color:#5A6072;border:1px solid #2a3550;border-radius:5px;padding:1px 5px}'
      + '.hakim-askov{position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:200;display:none;align-items:flex-start;justify-content:center;padding-top:12vh}'
      + '.hakim-askov.show{display:flex}.hakim-askbox{width:min(640px,92vw);background:#151823;border:1px solid #262B3A;border-radius:14px;overflow:hidden;box-shadow:0 24px 60px rgba(0,0,0,.6)}'
      + '.hakim-askbox form{display:flex;align-items:center;gap:10px;padding:14px 16px;border-bottom:1px solid #262B3A}.hakim-askbox .sp{color:#72D5C8;font-size:18px}'
      + '.hakim-askbox input{flex:1;background:transparent;border:none;color:#fff;font-size:16px;outline:none;font-family:inherit}'
      + '.hakim-askans{max-height:52vh;overflow-y:auto;padding:6px 16px 14px}.hakim-askans .m{padding:9px 0;font-size:14px;line-height:1.6}.hakim-askans .you{color:#5A6072}'
      + '.hakim-askhint{padding:11px 16px;border-top:1px solid #262B3A;font-family:var(--mono,monospace);font-size:11px;color:#5A6072;line-height:1.6}'
      // self-contained account-widget styles so the rail is identical on EVERY page even where
      // the page CSS lacks .acc/.rsec (was cramped on /settings before this)
      + '#hakim-rail .rsec{font-family:var(--mono,monospace);font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#4b5260;margin:18px 10px 8px;display:flex;align-items:center}'
      + '#hakim-rail .acc{display:flex;align-items:center;padding:7px 12px;border-radius:8px;cursor:pointer;font-size:13px}'
      + '#hakim-rail .acc:hover{background:#1a1d23}#hakim-rail .acc .an{flex:1;color:#8A90A6;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;padding-right:8px}'
      + '#hakim-rail .acc .av{font-family:var(--mono,monospace);font-weight:600}#hakim-rail .acc.crd .av{color:#c9a15f}'
      // ── sidebar reordering (Mohamed's own order) ──
      + '#hknav .navgrip,#hknav .naveye{display:none}'
      + '#hknav.editing .nav{cursor:grab}#hknav.editing .nav.drag{opacity:.45}'
      + '#hknav.editing .navgrip{display:inline-flex;align-items:center;color:#4b5260;font-size:13px;margin-right:2px;cursor:grab}'
      + '#hknav.editing .naveye{display:inline-flex;margin-left:auto;color:#5A6072;font-size:14px;padding:0 4px;cursor:pointer}'
      + '#hknav.editing .naveye:hover{color:#72D5C8}'
      + '#hknav .nav.nav-hidden{display:none}'
      + '#hknav.editing .nav.nav-hidden{display:flex;opacity:.4}#hknav.editing .nav.nav-hidden .naveye{color:#4b5260}'
      + '#hknav.editing .nav.dropline{box-shadow:inset 0 2px 0 #72D5C8}'
      + '#hknavbar{padding:6px 12px 2px;font-family:var(--mono,monospace);font-size:10px;letter-spacing:.5px;display:flex;align-items:center;gap:12px}'
      + '#hknavbar #hknavedit,#hknavbar #hknavdone{color:#4b5260;cursor:pointer}#hknavbar #hknavedit:hover,#hknavbar #hknavdone:hover{color:#8A90A6}'
      + '#hknavbar.on #hknavdone{color:#72D5C8}#hknavbar #hknavreset{color:#4b5260;cursor:pointer;margin-left:auto}#hknavbar #hknavreset:hover{color:#D98A93}';
    document.head.appendChild(st);
  }
  var navHtml = NAV.map(function (n) {
    var badge = n[3] ? '<span class="qbadge" id="railq" style="display:none"></span>' : '';
    return '<a href="' + n[0] + '" data-slug="' + n[0] + '" draggable="false" class="nav' + (active(n[0]) ? ' active' : '') + '">'
      + '<span class="navgrip" aria-hidden="true">⠿</span><i>' + navIcon(n[0]) + '</i><span class="navtx">' + n[2] + '</span>' + badge
      + '<span class="naveye" title="show / hide in sidebar" onclick="hkNavHide(event,\'' + n[0] + '\')">◠</span></a>';
  }).join('');
  var navWrap = '<div id="hknav">' + navHtml + '</div>'
    + '<div id="hknavbar"><span id="hknavedit" onclick="hkNavArrange()">⠿ Arrange sidebar</span>'
    + '<span id="hknavdone" onclick="hkNavArrange()" style="display:none">✓ Done</span>'
    + '<a id="hknavreset" onclick="hkNavReset()" style="display:none">reset order</a></div>';
  var soonHtml = SOON.map(function (s) {
    var near = s[4];
    return '<a href="/soon?s=' + s[0] + '" class="hakim-soon' + (near ? ' near' : '') + '" title="' + s[2] + ' — ' + s[3] + '">'
      + '<span class="si"><svg class="ic" viewBox="0 0 24 24">' + s[1] + '</svg></span>'
      + '<span class="sl"><span class="st">' + s[2] + '</span><span class="su">' + s[3] + '</span></span>'
      + '<small>' + (near ? 'next' : 'soon') + '</small></a>';
  }).join('');
  rail.innerHTML =
    '<div class="brand" onclick="location.href=\'/home\'"><span class="wm"><span class="sp">✦</span> HAKIM</span><span class="sub">FINANCE</span></div>'
    + navWrap
    + '<div class="rsec">Accounts <a href="/accounts" style="margin-left:auto;color:var(--gold2);font-size:9px;letter-spacing:1px">manage →</a></div><div id="railcash"></div>'
    + '<div class="rsec">Cards <span class="rt" id="cardtot"></span></div><div id="railcards"></div>'
    + (SOON.length ? '<div class="rsec">Coming in waves <a href="/soon" style="margin-left:auto;color:#4b5260;font-size:9px;letter-spacing:1px">all →</a></div>' + soonHtml : '')
    + '<div class="spacer"></div>'
    + '<div class="hakim-ask" onclick="hakimAsk()"><span class="sp">✦</span><span>Ask Finance…</span><kbd>⌘J</kbd></div>'
    + '<div class="railstat"><span class="live" id="rlive"><span class="d"></span><span class="t">SMS ?</span></span><span id="rqueue">QUEUE ··</span><span id="rbackup"></span><span id="rclock"></span></div>';

  // ---- Ask Finance: global, page-independent (moved out of the Desk into the shared shell) ----
  var ov = document.createElement('div'); ov.className = 'hakim-askov'; ov.id = 'hakim-askov';
  ov.innerHTML = '<div class="hakim-askbox">'
    + '<form onsubmit="return hakimAskSubmit(event)"><span class="sp">✦</span>'
    + '<input id="hakim-askq" placeholder="Ask Finance… e.g. what\'s my cash position?" autocomplete="off"></form>'
    + '<div class="hakim-askans" id="hakim-askans"></div>'
    + '<div class="hakim-askhint">Finance reads your <b>live ledger</b> — cash position, spending by category, “what is SADAD 902?”, where money went. It answers personal-finance only and defers business/trading/factory questions and the coaching still <a href="/soon" style="color:#72D5C8">coming in waves</a>.</div>'
    + '</div>';
  ov.addEventListener('click', function (e) { if (e.target === ov) closeAsk(); });
  document.body.appendChild(ov);
  function openAsk() { ov.classList.add('show'); setTimeout(function () { var i = document.getElementById('hakim-askq'); if (i) i.focus(); }, 40); }
  function closeAsk() { ov.classList.remove('show'); }
  window.hakimAsk = openAsk;
  window.hakimAskSubmit = function (e) {
    e.preventDefault();
    var q = (document.getElementById('hakim-askq').value || '').trim(); if (!q) return false;
    var ans = document.getElementById('hakim-askans');
    ans.innerHTML = '<div class="m you">You: ' + esc(q) + '</div><div class="m" id="hakim-thinking">thinking…</div>';
    fetch('/api/ai', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ q: q, page: P }) })
      .then(function (r) { return r.json(); })
      .then(function (d) { ans.innerHTML = '<div class="m you">You: ' + esc(q) + '</div><div class="m" dir="auto">' + esc(d.answer || '') + '</div>'; })
      .catch(function () { document.getElementById('hakim-thinking').textContent = '⚠️ Could not reach Finance right now — it’ll be back.'; });
    document.getElementById('hakim-askq').value = '';
    return false;
  };
  document.addEventListener('keydown', function (e) {
    if ((e.metaKey || e.ctrlKey) && (e.key === 'j' || e.key === 'J')) { e.preventDefault(); openAsk(); }
    else if (e.key === 'Escape') closeAsk();
  });

  // account clicks route to /accounts with that account expanded (one owner: /accounts)
  function loadRail() {
    fetch('/api/rail').then(function (r) { return r.json(); }).then(function (r) {
      document.getElementById('railcash').innerHTML = r.cash.map(function (c) {
        return '<div class="acc" onclick="location.href=\'/accounts?account=\'+encodeURIComponent(\'' + esc(c.name).replace(/'/g, "\\'") + '\')"><span class="an">' + esc(c.name) + '</span><span class="av">' + money0(c.bal) + '</span></div>';
      }).join('');
      document.getElementById('railcards').innerHTML = r.cards.map(function (c) {
        return '<div class="acc crd" onclick="location.href=\'/accounts?account=\'+encodeURIComponent(\'' + esc(c.name).replace(/'/g, "\\'") + '\')"><span class="an">' + esc(c.bank || '') + ' •' + esc(c.last4 || '') + '</span><span class="av">' + money0(Math.abs(c.bal)) + '</span></div>';
      }).join('');
      var ct = document.getElementById('cardtot'); if (ct) ct.textContent = 'SAR ' + money0(r.cards.reduce(function (a, c) { return a + Math.abs(c.bal); }, 0));
    }).catch(function () { });
  }
  function pollStatus() {
    fetch('/api/status').then(function (r) { return r.json(); }).then(function (s) {
      var l = document.getElementById('rlive'); if (l) { l.className = 'live ' + (s.sms_state === 'live' ? '' : (s.sms_state === 'amber' ? 'amber' : 'off')); l.querySelector('.t').textContent = s.sms_label || 'SMS ?'; }
      var b = document.getElementById('rbackup'); if (b) { if (s.backup_ok) { b.textContent = 'backup ✓'; b.className = ''; } else { b.textContent = '⚠ BACKUP FAILED'; b.className = 'bad'; } }
    }).catch(function () { }); setTimeout(pollStatus, 60000);
  }
  function qCount() {
    fetch('/api/queue').then(function (r) { return r.json(); }).then(function (q) {
      var n = (q.merchants || []).length + (q.onebyone || []).length;
      var rq = document.getElementById('rqueue'); if (rq) rq.textContent = 'QUEUE ' + String(n).padStart(2, '0');
      var b = document.getElementById('railq'); if (b) { b.textContent = n; b.style.display = n ? 'inline-block' : 'none'; }
    }).catch(function () { }); setTimeout(qCount, 120000);
  }
  function clock() { var el = document.getElementById('rclock'); if (el) el.textContent = new Date().toTimeString().slice(0, 8); setTimeout(clock, 1000); }
  if (new URL(location).searchParams.get('ask')) openAsk();  // deep-link to open Ask Finance
  loadRail(); pollStatus(); qCount(); clock();

  // ── Sidebar reordering (Mohamed's own nav order + hidden tabs) ──────────────
  // Order + hidden set persist server-side (/api/nav/prefs) so the shared rail renders them on EVERY
  // page. Hiding is DISPLAY-ONLY — the page stays reachable by URL and ⌘K search, never deleted.
  var NAVPREFS = { order: [], hidden: [] };
  function hkNavApply() {
    var wrap = document.getElementById('hknav'); if (!wrap) return;
    var arr = [].slice.call(wrap.querySelectorAll('.nav')), rows = {};
    arr.forEach(function (a) { rows[a.getAttribute('data-slug')] = a; });
    var seen = {};
    (NAVPREFS.order || []).forEach(function (s) { if (rows[s]) { wrap.appendChild(rows[s]); seen[s] = 1; } });
    arr.forEach(function (a) { var s = a.getAttribute('data-slug'); if (!seen[s]) wrap.appendChild(a); });  // new tabs keep default spot
    arr.forEach(function (a) {
      var s = a.getAttribute('data-slug'), hid = (NAVPREFS.hidden || []).indexOf(s) >= 0;
      a.classList.toggle('nav-hidden', hid);
      var eye = a.querySelector('.naveye'); if (eye) eye.textContent = hid ? '◡' : '◠';
    });
  }
  function hkNavLoad() {
    fetch('/api/nav/prefs').then(function (r) { return r.json(); }).then(function (d) {
      NAVPREFS = { order: d.order || [], hidden: d.hidden || [] }; hkNavApply();
    }).catch(function () { });
  }
  window.hkNavHide = function (e, slug) {
    e.stopPropagation(); e.preventDefault();
    var h = NAVPREFS.hidden || [], i = h.indexOf(slug);
    if (i >= 0) h.splice(i, 1); else h.push(slug);
    NAVPREFS.hidden = h; hkNavApply();
  };
  window.hkNavArrange = function () {
    var wrap = document.getElementById('hknav'), bar = document.getElementById('hknavbar');
    var editing = wrap.classList.toggle('editing'); bar.classList.toggle('on', editing);
    document.getElementById('hknavedit').style.display = editing ? 'none' : '';
    document.getElementById('hknavdone').style.display = editing ? '' : 'none';
    document.getElementById('hknavreset').style.display = editing ? '' : 'none';
    [].forEach.call(wrap.querySelectorAll('.nav'), function (a) { a.setAttribute('draggable', editing ? 'true' : 'false'); });
    if (!editing) hkNavSave();   // leaving edit mode persists the order + hidden set
  };
  function hkNavSave() {
    NAVPREFS.order = [].map.call(document.querySelectorAll('#hknav .nav'), function (a) { return a.getAttribute('data-slug'); });
    fetch('/api/nav/prefs', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ order: NAVPREFS.order, hidden: NAVPREFS.hidden }) }).catch(function () { });
  }
  window.hkNavReset = function () {
    fetch('/api/nav/prefs', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ order: [], hidden: [] }) }).then(function () { location.reload(); }).catch(function () { location.reload(); });
  };
  (function () {
    var wrap = document.getElementById('hknav'); if (!wrap) return; var dragEl = null;
    wrap.addEventListener('click', function (e) { if (wrap.classList.contains('editing')) e.preventDefault(); }, true);
    wrap.addEventListener('dragstart', function (e) {
      if (!wrap.classList.contains('editing')) { e.preventDefault(); return; }
      dragEl = e.target.closest('.nav'); if (dragEl) { dragEl.classList.add('drag'); e.dataTransfer.effectAllowed = 'move'; try { e.dataTransfer.setData('text/plain', ''); } catch (x) { } }
    });
    wrap.addEventListener('dragend', function () { if (dragEl) dragEl.classList.remove('drag'); [].forEach.call(wrap.querySelectorAll('.dropline'), function (x) { x.classList.remove('dropline'); }); dragEl = null; });
    wrap.addEventListener('dragover', function (e) {
      if (!wrap.classList.contains('editing') || !dragEl) return; e.preventDefault();
      var over = e.target.closest('.nav'); if (!over || over === dragEl) return;
      var r = over.getBoundingClientRect(), before = (e.clientY - r.top) < r.height / 2;
      [].forEach.call(wrap.querySelectorAll('.dropline'), function (x) { x.classList.remove('dropline'); });
      over.classList.add('dropline');
      wrap.insertBefore(dragEl, before ? over : over.nextSibling);
    });
    wrap.addEventListener('drop', function (e) { if (wrap.classList.contains('editing')) e.preventDefault(); });
  })();
  hkNavLoad();

  // ── Open-tab update signal ────────────────────────────────────────────────
  // A tab opened BEFORE a deploy keeps running its old in-memory JS forever (no-cache only
  // helps on RELOAD). So poll the server build id; when it changes, offer a one-click reload.
  // This is the fix for "the repair didn't reach me" — every fix now surfaces within a minute.
  var BUILD = null;
  function checkVersion() {
    fetch('/api/version', { cache: 'no-store' }).then(function (r) { return r.json(); }).then(function (d) {
      if (BUILD === null) { BUILD = d.build; return; }
      if (d.build && d.build !== BUILD) showUpdate();
    }).catch(function () { });
  }
  function showUpdate() {
    if (document.getElementById('hakim-update')) return;
    var el = document.createElement('div');
    el.id = 'hakim-update';
    el.innerHTML = '🔄 HAKIM was updated — <b>click to reload</b>';
    el.style.cssText = 'position:fixed;bottom:18px;left:50%;transform:translateX(-50%);z-index:9999;' +
      'background:#72D5C8;color:#0D0F16;font-weight:700;font-size:13px;padding:11px 18px;border-radius:12px;' +
      'font-family:-apple-system,system-ui,sans-serif;box-shadow:0 8px 28px rgba(0,0,0,.5);cursor:pointer;' +
      'animation:hkup .3s ease';
    el.onclick = function () { location.reload(true); };
    var st = document.createElement('style'); st.textContent = '@keyframes hkup{from{opacity:0;transform:translate(-50%,12px)}to{opacity:1;transform:translate(-50%,0)}}';
    document.head.appendChild(st); document.body.appendChild(el);
  }
  checkVersion(); setInterval(checkVersion, 45000);

  // ── Live DATA refresh (Wave N) ────────────────────────────────────────────
  // Poll a cheap ledger fingerprint; when it changes (new SMS transaction, an edit, a delete made
  // elsewhere), offer a non-disruptive refresh pill. A page that sets window.hakimReload refreshes
  // in place; otherwise the pill reloads. Same "the fix reaches open tabs" spirit, for data.
  var DVER = null;
  function checkData() {
    fetch('/api/data-version', { cache: 'no-store' }).then(function (r) { return r.json(); }).then(function (d) {
      if (DVER === null) { DVER = d.ver; return; }
      if (d.ver && d.ver !== DVER) { DVER = d.ver; showDataPill(); }
    }).catch(function () { });
  }
  function showDataPill() {
    if (document.getElementById('hakim-newdata')) return;
    var el = document.createElement('div');
    el.id = 'hakim-newdata';
    el.innerHTML = '🔄 New activity in your ledger — <b>refresh</b>';
    el.style.cssText = 'position:fixed;bottom:18px;left:50%;transform:translateX(-50%);z-index:9998;' +
      'background:#e8b95a;color:#0D0F16;font-weight:700;font-size:13px;padding:11px 18px;border-radius:12px;' +
      'font-family:-apple-system,system-ui,sans-serif;box-shadow:0 8px 28px rgba(0,0,0,.5);cursor:pointer;' +
      'animation:hkup .3s ease';
    el.onclick = function () {
      el.remove();
      if (typeof window.hakimReload === 'function') { try { window.hakimReload(); return; } catch (e) { } }
      location.reload(true);
    };
    document.body.appendChild(el);
  }
  checkData(); setInterval(checkData, 20000);

  // ── In-place explainers (single-sourced) ──────────────────────────────────
  // Any element with data-tip="key" gets a tap-to-explain popover. One dictionary, every page.
  var EXPLAIN = {
    committed: 'Money already spoken for this month — bills due + envelope contributions + loan/lease/BNPL instalments. A fact about obligations, NOT “what’s left to spend”.',
    networth: 'Everything you own minus everything you owe, right now. Negative just means debts exceed assets today — normal while cards carry balances.',
    restricted: 'Wealth you can’t touch yet — a certificate locked until maturity. It counts in net worth but is shown apart so “available” stays honest.',
    envelope: 'A pot: a monthly amount accumulates from a start date, your spending draws it down. The balance is your permission. Negative shows a pure-math recovery date — no nagging.',
    strict: 'Rollover posture. Carry (default): unspent rolls to next month. Strict: the budget resets each month — no carry-over.',
    riba: 'The real financing cost your loans, leases and BNPL plans booked — not an estimate. A mirror of the cost of debt, never advice.',
    paidstatus: 'Whether this bill is settled this period. Auto-matched by name, or you can mark it — paid bills drop out of “committed”.',
    cleared: 'Available = your live balance. Cleared = only what you’ve reconciled against the statement. They converge as you tick transactions reconciled.',
    owed: 'Money you lent, per person. Lending and repayment post real transfers, so net worth stays exact; the invariant line proves the ledger matches the account.',
    counted: 'When you last physically counted this cash. Turns amber after 45 days so you know what’s fresh.',
    hawl: 'A nightly record of whether your zakatable wealth is above nisab. It calculates no zakat — it only makes a future hawl (one lunar year) date knowable. The clock can’t be backfilled.',
    hijri: 'Budget this category by the lunar (Hijri) month instead of the Gregorian one — for Ramadan and seasonal spending.'
  };
  var pop = null;
  function closeTip() { if (pop) { pop.remove(); pop = null; } }
  document.addEventListener('click', function (e) {
    var el = e.target.closest ? e.target.closest('[data-tip]') : null;
    if (!el) { if (pop && !pop.contains(e.target)) closeTip(); return; }
    e.preventDefault(); e.stopPropagation();
    var txt = EXPLAIN[el.getAttribute('data-tip')]; if (!txt) return;
    closeTip();
    pop = document.createElement('div');
    pop.textContent = txt;
    var r = el.getBoundingClientRect();
    pop.style.cssText = 'position:fixed;z-index:10000;max-width:300px;background:#232837;color:#e7ebf3;' +
      'border:1px solid #3a4155;border-radius:10px;padding:11px 13px;font-size:12.5px;line-height:1.55;' +
      'font-family:-apple-system,system-ui,sans-serif;box-shadow:0 10px 30px rgba(0,0,0,.55);' +
      'top:' + Math.min(r.bottom + 8, window.innerHeight - 140) + 'px;left:' + Math.min(r.left, window.innerWidth - 320) + 'px';
    document.body.appendChild(pop);
  });
  // expose the tip styling helper so pages can render a consistent ⓘ
  window.hakimInfo = function (key) { return '<span data-tip="' + key + '" style="cursor:help;color:#72D5C8;font-size:11px;opacity:.8" title="what is this?">ⓘ</span>'; };
})();

/* ==== HAKIM date picker — one bank-style calendar for every date field, everywhere ============
   The May "osama marble" mistake was typing a date into a text field. The cure is choosing by
   sight: tap any date input → a themed calendar opens on the relevant month → arrows for month/
   year → tap the day. No raw typing. Auto-enhances every input[type=date] (full calendar) and
   input[type=month] (month grid) on every page, including ones created later in modals. Shows the
   Hijri (Umm al-Qura) date of the selected day as read-only context. */
(function () {
  var MON = ['January','February','March','April','May','June','July','August','September','October','November','December'];
  var DOW = ['S','M','T','W','T','F','S'];
  if (!document.getElementById('hkdate-css')) {
    var st = document.createElement('style'); st.id = 'hkdate-css';
    st.textContent =
      '.hkov{position:fixed;inset:0;background:rgba(6,8,14,.55);z-index:99998;display:flex;align-items:center;justify-content:center}' +
      '.hkcal{background:#141824;border:1px solid #2b3242;border-radius:16px;padding:14px;width:300px;box-shadow:0 24px 60px rgba(0,0,0,.6);font-family:-apple-system,system-ui,sans-serif;color:#e7ebf3}' +
      '.hkhd{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px}' +
      '.hkhd b{font-size:15px;font-weight:700}' +
      '.hknav{background:#1e2434;border:1px solid #2b3242;color:#cfd6e6;width:30px;height:30px;border-radius:9px;cursor:pointer;font-size:15px}' +
      '.hknav:hover{background:#2a3247}' +
      '.hkgrid{display:grid;grid-template-columns:repeat(7,1fr);gap:2px;margin-top:6px}' +
      '.hkdow{text-align:center;font-size:10px;color:#7b8399;font-family:ui-monospace,monospace;padding:3px 0}' +
      '.hkday{text-align:center;padding:7px 0;border-radius:9px;cursor:pointer;font-size:13px;font-variant-numeric:tabular-nums}' +
      '.hkday:hover{background:#232b3d}.hkday.oth{color:#4a5266}.hkday.today{outline:1px solid #4a5266}' +
      '.hkday.sel{background:#72D5C8;color:#0d0f16;font-weight:800}' +
      '.hkmn{text-align:center;padding:12px 0;border-radius:9px;cursor:pointer;font-size:13px}.hkmn:hover{background:#232b3d}.hkmn.sel{background:#72D5C8;color:#0d0f16;font-weight:800}' +
      '.hksub{margin-top:9px;font-family:ui-monospace,monospace;font-size:11px;color:#8b93a7;text-align:center;min-height:15px}' +
      '.hkfoot{display:flex;gap:8px;margin-top:10px}.hkbtn{flex:1;background:#1e2434;border:1px solid #2b3242;color:#cfd6e6;border-radius:9px;padding:8px;cursor:pointer;font-size:12px}.hkbtn:hover{background:#2a3247}';
    document.head.appendChild(st);
  }
  function hijri(d) {
    try { return new Intl.DateTimeFormat('en-u-ca-islamic-umalqura',
      {day:'numeric',month:'long',year:'numeric'}).format(d); } catch (e) { return ''; }
  }
  function pad(n){ return (n<10?'0':'')+n; }
  function close(){ var o=document.getElementById('hkov'); if(o) o.remove(); }
  function commit(input, val){
    input.value = val;
    input.dispatchEvent(new Event('input',{bubbles:true}));
    input.dispatchEvent(new Event('change',{bubbles:true}));
    close();
  }
  function openDate(input){
    close();
    var cur = /^\d{4}-\d\d-\d\d$/.test(input.value) ? input.value : new Date().toISOString().slice(0,10);
    var view = new Date(cur + 'T00:00:00'); view.setDate(1);
    var sel = cur;
    var ov = document.createElement('div'); ov.className='hkov'; ov.id='hkov';
    ov.onclick=function(e){ if(e.target===ov) close(); };
    var cal = document.createElement('div'); cal.className='hkcal'; ov.appendChild(cal);
    function render(){
      var y=view.getFullYear(), m=view.getMonth();
      var first=new Date(y,m,1).getDay(), dim=new Date(y,m+1,0).getDate();
      var todayS=new Date().toISOString().slice(0,10);
      var h='<div class="hkhd"><button class="hknav" data-a="-1">‹</button><b>'+MON[m]+' '+y+'</b><button class="hknav" data-a="1">›</button></div>';
      h+='<div class="hkgrid">'+DOW.map(function(d){return '<div class="hkdow">'+d+'</div>';}).join('');
      for(var i=0;i<first;i++) h+='<div class="hkday oth"></div>';
      for(var dd=1;dd<=dim;dd++){ var iso=y+'-'+pad(m+1)+'-'+pad(dd);
        var cls='hkday'+(iso===sel?' sel':'')+(iso===todayS?' today':'');
        h+='<div class="'+cls+'" data-d="'+iso+'">'+dd+'</div>'; }
      h+='</div><div class="hksub" id="hksub">'+hijri(new Date(sel+'T00:00:00'))+'</div>';
      h+='<div class="hkfoot"><button class="hkbtn" data-today>Today</button><button class="hkbtn" data-cancel>Cancel</button></div>';
      cal.innerHTML=h;
      cal.querySelectorAll('.hknav').forEach(function(b){b.onclick=function(){view.setMonth(view.getMonth()+ (+b.dataset.a)); render();};});
      cal.querySelectorAll('.hkday[data-d]').forEach(function(c){
        c.onmouseenter=function(){document.getElementById('hksub').textContent=hijri(new Date(c.dataset.d+'T00:00:00'));};
        c.onclick=function(){ commit(input, c.dataset.d); };});
      cal.querySelector('[data-today]').onclick=function(){ commit(input, todayS); };
      cal.querySelector('[data-cancel]').onclick=close;
    }
    render(); document.body.appendChild(ov);
  }
  function openMonth(input){
    close();
    var cur = /^\d{4}-\d\d$/.test(input.value) ? input.value : new Date().toISOString().slice(0,7);
    var y = +cur.slice(0,4), sel=cur;
    var ov=document.createElement('div'); ov.className='hkov'; ov.id='hkov';
    ov.onclick=function(e){ if(e.target===ov) close(); };
    var cal=document.createElement('div'); cal.className='hkcal'; ov.appendChild(cal);
    function render(){
      var h='<div class="hkhd"><button class="hknav" data-a="-1">‹</button><b>'+y+'</b><button class="hknav" data-a="1">›</button></div>';
      h+='<div class="hkgrid" style="grid-template-columns:repeat(3,1fr)">';
      for(var m=0;m<12;m++){ var v=y+'-'+pad(m+1); h+='<div class="hkmn'+(v===sel?' sel':'')+'" data-m="'+v+'">'+MON[m].slice(0,3)+'</div>'; }
      h+='</div><div class="hkfoot"><button class="hkbtn" data-cancel>Cancel</button></div>';
      cal.innerHTML=h;
      cal.querySelectorAll('.hknav').forEach(function(b){b.onclick=function(){y+= (+b.dataset.a); render();};});
      cal.querySelectorAll('.hkmn[data-m]').forEach(function(c){c.onclick=function(){ commit(input, c.dataset.m); };});
      cal.querySelector('[data-cancel]').onclick=close;
    }
    render(); document.body.appendChild(ov);
  }
  function enhance(root){
    (root||document).querySelectorAll('input[type="date"]:not([data-hk]),input[type="month"]:not([data-hk])').forEach(function(el){
      el.setAttribute('data-hk','1'); el.readOnly=true; el.style.cursor='pointer';
      var isMonth = el.type==='month';
      var open=function(e){ e.preventDefault(); (isMonth?openMonth:openDate)(el); el.blur(); };
      el.addEventListener('click', open);
      el.addEventListener('focus', open);
    });
  }
  window.hkEnhanceDates = enhance;
  document.addEventListener('DOMContentLoaded', function(){ enhance(document); });
  enhance(document);
  try {
    new MutationObserver(function(muts){ muts.forEach(function(mm){ mm.addedNodes.forEach(function(nd){
      if(nd.nodeType===1){ if(nd.matches && (nd.matches('input[type=date]')||nd.matches('input[type=month]'))) enhance(nd.parentNode||document); else enhance(nd); }
    }); }); }).observe(document.body, {childList:true, subtree:true});
  } catch(e){}
})();
