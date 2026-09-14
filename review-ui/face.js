/* ============================================================================
   HAKIM — the Face icon system. Self-hosted outline icons (local-first, no CDN),
   one stroke weight, currentColor, in the Tabler idiom. window.ic(name, extraClass)
   returns an inline <svg class="ic"> string; window.iconFor maps a category to an
   icon name. Loaded synchronously in the <head> of every CONVERTED page so ic() is
   defined before that page's render code runs. Emoji survive only in Guide prose.
   ============================================================================ */
(function () {
  // each entry is the inner markup of a 24x24 viewBox, outline, no fill.
  var P = {
    // ---- nav ----
    dashboard: '<path d="M4 13h6V4H4zM14 20h6V10h-6zM14 7h6V4h-6zM4 20h6v-4H4z"/>',
    desk: '<path d="M4 5h16v14H4z"/><path d="M4 9h4l2 3h4l2-3h4"/>',
    calendar: '<path d="M4 5h16v16H4z"/><path d="M4 9h16M8 3v4M16 3v4"/>',
    tag: '<path d="M12 3H5a2 2 0 0 0-2 2v7l9 9 9-9z"/><circle cx="8.5" cy="8.5" r="1.2"/>',
    chart: '<path d="M4 20V4M4 20h16"/><path d="M8 16v-4M12 16V8M16 16v-6"/>',
    target: '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="1"/>',
    handshake: '<path d="M12 8l-2-2a2 2 0 0 0-3 0L3 10l4 4 1-1"/><path d="M12 8l3-2a2 2 0 0 1 3 0l3 4-4 4-6-6"/>',
    bank: '<path d="M3 10l9-6 9 6M5 10v9M19 10v9M9 19v-6M15 19v-6M3 21h18"/>',
    repeat: '<path d="M4 9a5 5 0 0 1 5-5h8l-3-3M20 15a5 5 0 0 1-5 5H7l3 3"/>',
    bolt: '<path d="M13 3L4 14h7l-1 7 9-11h-7z"/>',
    help: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.8.4-1 .8-1 1.7M12 17h.01"/>',
    settings: '<circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 0 0-.1-1.3l2-1.5-2-3.4-2.3 1a7 7 0 0 0-2.3-1.3L14 3h-4l-.3 2.2a7 7 0 0 0-2.3 1.3l-2.3-1-2 3.4 2 1.5A7 7 0 0 0 5 12a7 7 0 0 0 .1 1.3l-2 1.5 2 3.4 2.3-1a7 7 0 0 0 2.3 1.3L10 21h4l.3-2.2a7 7 0 0 0 2.3-1.3l2.3 1 2-3.4-2-1.5A7 7 0 0 0 19 12z"/>',
    // ---- composer / desk ----
    receipt: '<path d="M6 3h12v18l-3-2-3 2-3-2-3 2z"/><path d="M9 8h6M9 12h6"/>',
    coins: '<ellipse cx="9" cy="7" rx="5" ry="2.5"/><path d="M4 7v5c0 1.4 2.2 2.5 5 2.5s5-1.1 5-2.5V7"/><path d="M14 12.5c.6.3 1.6.5 2.5.5 2.8 0 5-1.1 5-2.5S19.3 8 16.5 8c-.5 0-1 .05-1.5.13"/>',
    transfer: '<path d="M4 8h13l-3-3M20 16H7l3 3"/>',
    backspace: '<path d="M8 5h12v14H8l-6-7z"/><path d="M12 10l4 4M16 10l-4 4"/>',
    scale: '<path d="M12 4v16M7 20h10M12 6l-6 2 6-2 6-2M6 8l-2.5 5a2.5 2.5 0 0 0 5 0zM18 8l-2.5 5a2.5 2.5 0 0 0 5 0z"/>',
    split: '<circle cx="6" cy="6" r="2"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="18" r="2"/><path d="M6 8v3a2 2 0 0 0 2 2h8M6 16v-2"/>',
    folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h6a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    plane: '<path d="M10 5.5a1.5 1.5 0 0 1 3 0V10l7 4v2l-7-2v3l2 1.5V20l-3.5-1L11 20v-1.5L13 17v-3l-7 2v-2l7-4z"/>',
    card: '<rect x="3" y="6" width="18" height="12" rx="2"/><path d="M3 10h18M7 15h3"/>',
    certificate: '<path d="M5 3h9l5 5v13H5z"/><path d="M14 3v5h5M8 13h8M8 17h5"/>',
    calculator: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M8 7h8M8 11h.01M12 11h.01M16 11h.01M8 15h.01M12 15h.01M16 15h.01"/>',
    star: '<path d="M12 4l2.4 5 5.6.6-4.2 3.8 1.2 5.6L12 16.9 7 19l1.2-5.6L4 9.6 9.6 9z"/>',
    lock: '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
    alert: '<path d="M12 4l9 16H3z"/><path d="M12 10v4M12 17h.01"/>',
    check: '<path d="M5 12l5 5L20 7"/>',
    x: '<path d="M6 6l12 12M18 6L6 18"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    trash: '<path d="M5 7h14M10 7V5h4v2M6 7l1 13h10l1-13"/>',
    edit: '<path d="M4 20h4L18.5 9.5a2 2 0 0 0-3-3L5 17z"/>',
    wallet: '<path d="M4 7a2 2 0 0 1 2-2h11v4M4 7v10a2 2 0 0 0 2 2h13V9H6a2 2 0 0 1-2-2z"/><path d="M16 13h.01"/>',
    arrowRight: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    undo: '<path d="M9 7L4 12l5 5M4 12h11a5 5 0 0 1 0 10h-1"/>',
    filter: '<path d="M4 5h16l-6 7v6l-4 2v-8z"/>',
    refresh: '<path d="M4 12a8 8 0 0 1 14-5l2 2M20 12a8 8 0 0 1-14 5l-2-2M18 4v5h-5M6 20v-5h5"/>',
    home: '<path d="M4 11l8-7 8 7M6 10v9h12v-9"/>',
    bell: '<path d="M6 9a6 6 0 0 1 12 0c0 5 2 6 2 6H4s2-1 2-6"/><path d="M10 20a2 2 0 0 0 4 0"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.4 1.4M17.6 17.6L19 19M19 5l-1.4 1.4M6.4 17.6L5 19"/>',
    budget: '<circle cx="12" cy="12" r="8"/><path d="M12 12V4a8 8 0 0 1 8 8z"/>',
    forecast: '<path d="M4 15l4-4 3 3 5-6M14 8h4v4"/>',
    moon: '<path d="M20 14a8 8 0 1 1-9-11 6.5 6.5 0 0 0 9 11z"/>',
    gem: '<path d="M6 4h12l3 5-9 11L3 9z"/><path d="M3 9h18M9 4l-3 5 6 11 6-11-3-5"/>',
    // ---- categories ----
    cart: '<circle cx="9" cy="20" r="1.4"/><circle cx="17" cy="20" r="1.4"/><path d="M3 4h2l2.5 12h11l2-8H6"/>',
    food: '<path d="M4 9h16a8 8 0 0 1-16 0zM6 13h12v1a3 3 0 0 1-3 3H9a3 3 0 0 1-3-3zM4 20h16"/>',
    car: '<path d="M5 13l1.5-4.5A2 2 0 0 1 8.4 7h7.2a2 2 0 0 1 1.9 1.5L19 13M4 13h16v4H4z"/><circle cx="7.5" cy="17" r="1.3"/><circle cx="16.5" cy="17" r="1.3"/>',
    pill: '<rect x="3" y="9" width="18" height="6" rx="3" transform="rotate(45 12 12)"/><path d="M9 9l6 6"/>',
    shirt: '<path d="M8 4l4 3 4-3 4 3-2 3-2-1v11H8V9L6 10 4 7z"/>',
    device: '<rect x="7" y="3" width="10" height="18" rx="2"/><path d="M11 18h2"/>',
    bulb: '<path d="M9 18h6M10 21h4M12 3a6 6 0 0 1 4 10c-.7.7-1 1.3-1 2H9c0-.7-.3-1.3-1-2a6 6 0 0 1 4-10z"/>',
    gift: '<rect x="4" y="9" width="16" height="11" rx="1"/><path d="M4 13h16M12 9v11M12 9c-2-4-6-2-4 0M12 9c2-4 6-2 4 0"/>',
    mosque: '<path d="M4 20V11a8 8 0 0 1 16 0v9M4 20h16M9 20v-4a3 3 0 0 1 6 0v4M12 3v-1"/>',
    heart: '<path d="M12 20S3 14 3 8.5A4.5 4.5 0 0 1 12 6a4.5 4.5 0 0 1 9 2.5C21 14 12 20 12 20z"/>',
    ticket: '<path d="M4 8a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2 2 2 0 0 0 0 4 2 2 0 0 1 0 4v0a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2 2 2 0 0 0 0-4 2 2 0 0 1 0-4z"/>',
    dumbbell: '<path d="M4 9v6M7 7v10M17 7v10M20 9v6M7 12h10"/>',
    book: '<path d="M5 4h11a2 2 0 0 1 2 2v14H7a2 2 0 0 1-2-2z"/><path d="M9 8h5M9 12h5"/>',
    tools: '<path d="M14 6a3.5 3.5 0 0 0 4.5 4.5L21 13l-8 8-2.5-2.5A3.5 3.5 0 0 0 6 14L3 11l3-3 3 3"/>',
    doc: '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M9 13h6M9 17h4"/>',
    coin: '<circle cx="12" cy="12" r="8"/><path d="M12 7v10M9.5 9.5A2.5 2 0 0 1 12 8c1.4 0 2.5.7 2.5 1.5S13.4 11 12 11s-2.5.7-2.5 1.5S10.6 15 12 15a2.5 2 0 0 0 2.5-1.5"/>',
    users: '<circle cx="9" cy="8" r="3"/><path d="M3 20a6 6 0 0 1 12 0M16 5.5a3 3 0 0 1 0 5M17 20a6 6 0 0 0-2-4"/>',
    dots: '<circle cx="5" cy="12" r="1.4"/><circle cx="12" cy="12" r="1.4"/><circle cx="19" cy="12" r="1.4"/>',
    factory: '<path d="M3 21V10l6 4V10l6 4V6l3 2 .5 11z"/><path d="M3 21h18"/>',
    shield: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    link: '<path d="M9 15l6-6"/><path d="M8 12l-2 2a3 3 0 0 0 4 4l2-2M16 12l2-2a3 3 0 0 0-4-4l-2 2"/>',
    attach: '<path d="M8 12l6-6a3 3 0 0 1 4 4l-8 8a5 5 0 0 1-7-7l8-8"/>',
    briefcase: '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12h18"/>',
    scissors: '<circle cx="6" cy="6" r="2.5"/><circle cx="6" cy="18" r="2.5"/><path d="M8 8l12 10M8 16L20 6"/>',
    luggage: '<rect x="6" y="7" width="12" height="13" rx="2"/><path d="M9 7V4h6v3M9 20v1M15 20v1"/>',
    bag: '<path d="M6 8h12l1 12H5z"/><path d="M9 8a3 3 0 0 1 6 0"/>',
    gold: '<circle cx="12" cy="12" r="8"/><path d="M8 12h8M12 8v8"/>',
    balloon: '<path d="M12 4a5 5 0 0 1 5 5c0 3.5-3 6-5 6s-5-2.5-5-6a5 5 0 0 1 5-5z"/><path d="M12 15v3M11 21h2"/>',
    fund: '<path d="M4 19V5M4 19h16"/><path d="M8 15l3-4 3 2 4-6"/>',
    eyeoff: '<path d="M4 4l16 16M10 6a9 9 0 0 1 10 6 12 12 0 0 1-2.5 3.5M6.5 8.5A12 12 0 0 0 4 12a9 9 0 0 0 12 5"/>',
    flag: '<path d="M5 21V4M5 4h11l-2 4 2 4H5"/>',
    door: '<path d="M6 3h9v18H6z"/><path d="M12 12h.01"/>',
    envelope: '<rect x="3" y="6" width="18" height="12" rx="2"/><path d="M4 7l8 6 8-6"/>',
    wave: '<path d="M3 8c2-2 4-2 6 0s4 2 6 0 4-2 6 0M3 14c2-2 4-2 6 0s4 2 6 0 4-2 6 0"/>',
    camera: '<rect x="3" y="7" width="18" height="13" rx="2"/><circle cx="12" cy="13" r="3.5"/><path d="M8 7l1.5-2h5L16 7"/>'
  };
  // category (parent name) -> icon
  var CAT = {
    'Groceries & supermarket': 'cart', 'Eating out & delivery': 'food', 'Car': 'car',
    'Medical & pharmacy': 'pill', 'Clothing & accessories': 'shirt', 'Electronics & gadgets': 'device',
    'Utilities & telecom': 'bulb', 'Home & maintenance': 'tools', 'Home creation (villa)': 'home',
    'Household staff': 'users', 'Personal care': 'heart', 'Entertainment & outings': 'ticket',
    'Subscriptions & digital': 'device', 'Sports & fitness': 'dumbbell', 'School & education': 'book',
    'Government & documents': 'doc', 'Travel': 'plane', 'Gifts & occasions': 'gift',
    'Hajj & Umrah (حج وعمرة)': 'mosque', 'Zakat & charity (زكاة وصدقة)': 'heart',
    'Insurance': 'shield', 'Bank & fees': 'bank', 'Other (miscellaneous)': 'dots',
    'Transport & taxis': 'car', 'Capital contribution: Factory': 'factory',
    'Salary & allowances': 'coins', 'Other income': 'coins', 'Investment income': 'coin',
    'Sarah shopping': 'cart', 'Hisham shopping': 'cart', 'Adam shopping': 'cart', 'Aser shopping': 'cart',
    'To review': 'help',
    'Business income': 'briefcase', 'Rental income': 'home', 'Interest income': 'forecast',
    'Gifts received': 'gift', 'Reimbursements': 'undo', 'Hajj & Umrah': 'mosque',
    'Zakat & charity': 'heart'
  };
  window.ic = function (name, cls) {
    var inner = P[name];
    if (!inner) inner = P.dots;
    return '<svg class="ic' + (cls ? ' ' + cls : '') + '" viewBox="0 0 24 24" aria-hidden="true">' + inner + '</svg>';
  };
  window.icName = function (cat) {
    if (!cat) return 'receipt';
    var main = String(cat).split(':')[0].trim();
    return CAT[main] || CAT[cat] || 'receipt';
  };
  window.icFor = function (cat, cls) { return window.ic(window.icName(cat), cls); };

  // THE OPENING · shared honest-maturity banner. Every gated surface uses this to name — from the real
  // ledger (m = /api/maturity payload), never hardcoded — how much history a claim needs and the date
  // it's met. `what` describes the analysis; when met, returns a quiet "based on N months" footnote form.
  window.matBanner = function (m, what, opts) {
    m = m || {}; opts = opts || {};
    var need = m.need, have = m.have || 0;
    if (m.met) {
      if (opts.hideWhenMet) return '';
      return '<div class="matbanner met">' + window.ic('check') +
        '<span>' + (what || 'This') + ' · based on <b>' + have + ' complete month' + (have === 1 ? '' : 's') + '</b> of data</span></div>';
    }
    return '<div class="matbanner">' + window.ic('clock') +
      '<span><b>' + (what || 'This') + '</b> needs <b>' + need + ' complete months</b> · you have <b>' + have +
      '</b> · <b class="rdy">ready ' + (m.ready_label || 'soon') + '</b></span></div>';
  };
  // inline "provisional · N months" tag for a single computed number (not a whole surface)
  window.matTag = function (m) {
    m = m || {}; if (m.met) return '';
    return '<span class="mattag">provisional · ' + (m.have || 0) + '/' + m.need + ' mo</span>';
  };

  // ── ONE shared chart tooltip (one-owner rule) ─────────────────────────────
  // A chart you can't read values off is decoration. Any element carrying a `data-tip` attribute (bars,
  // donut segments, sparkline points…) shows a follow-cursor, edge-clamped, dark-theme tooltip in the face
  // language. Line charts call window.hkTip.show(html,x,y) from their own nearest-point handlers — same
  // popup, one styling, not per-chart reimplementations.
  // numeric-polish money for tooltips — SINGLE-quoted spans so it's safe inside a data-tip="…" attribute.
  window.hkMoney = function (n) {
    n = Number(n || 0); var neg = n < 0; n = Math.abs(n);
    var i = Math.floor(n).toLocaleString('en-US'); var d = (n - Math.floor(n)).toFixed(2).slice(1);
    return "<span class='c'>SAR</span>" + (neg ? '−' : '') + i + "<span class='d'>" + d + "</span>";
  };
  // build a period·in·out·net tooltip body (the cash-flow / month shape shape) — one formatter, reused
  window.hkTipFlow = function (label, inv, outv) {
    var net = (inv || 0) - (outv || 0);
    return "<div class='tt-hd'>" + label + "</div>" +
      "<div class='tt-row'><span class='k'>in</span><span class='v pos'>+" + window.hkMoney(inv) + "</span></div>" +
      "<div class='tt-row'><span class='k'>out</span><span class='v neg'>−" + window.hkMoney(outv) + "</span></div>" +
      "<div class='tt-row'><span class='k'>net</span><span class='v " + (net >= 0 ? 'pos' : 'neg') + "'>" +
      (net >= 0 ? '+' : '−') + window.hkMoney(Math.abs(net)) + "</span></div>";
  };
  var _tip = null;
  function _ensureTip() {
    if (_tip) return _tip;
    _tip = document.createElement('div'); _tip.className = 'hktip'; _tip.id = 'hktip';
    (document.body || document.documentElement).appendChild(_tip);
    return _tip;
  }
  window.hkTip = {
    show: function (html, x, y) {
      var t = _ensureTip(); t.innerHTML = html; t.style.display = 'block';
      var w = t.offsetWidth, h = t.offsetHeight, pad = 12;
      var vw = window.innerWidth, vh = window.innerHeight;
      var left = x + 14; if (left + w + pad > vw) left = x - w - 14; if (left < pad) left = pad;
      var top = y - h - 12; if (top < pad) top = y + 18; if (top + h + pad > vh) top = vh - h - pad;
      t.style.left = left + 'px'; t.style.top = top + 'px';
    },
    hide: function () { if (_tip) _tip.style.display = 'none'; }
  };
  // delegated element-hover: works for every current + future [data-tip] on any page
  document.addEventListener('mouseover', function (e) {
    var el = e.target && e.target.closest ? e.target.closest('[data-tip]') : null;
    if (el) window.hkTip.show(el.getAttribute('data-tip'), e.clientX, e.clientY);
  });
  document.addEventListener('mousemove', function (e) {
    var el = e.target && e.target.closest ? e.target.closest('[data-tip]') : null;
    if (el) window.hkTip.show(el.getAttribute('data-tip'), e.clientX, e.clientY);
    else if (_tip && _tip.style.display === 'block' && !(e.target.closest && e.target.closest('.hktip'))) {
      // only hide when leaving a data-tip element (line charts manage their own hide)
    }
  });
  document.addEventListener('mouseout', function (e) {
    var el = e.target && e.target.closest ? e.target.closest('[data-tip]') : null;
    if (el) window.hkTip.hide();
  });
})();
