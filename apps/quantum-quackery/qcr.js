/**
 * qcr.js — Queried Collapse Routing client library
 * Quantum Quackery Divine Arts · quantumquackery.org
 *
 * Two modes:
 *   Keyword (free, no key): section.keywords matched against query locally.
 *   TCE (with guild key):   full Hopfield convergence over the Shygazun
 *                            byte table via the QCR service API.
 *
 * Usage:
 *
 *   const qcr = new QCR({ apiKey: 'qcr_xxxx_yyyy', apiBase: 'https://quantumquackery.org/api' });
 *
 *   qcr.section('garden',   el, { tongues: ['Lotus','Cannabis'],  keywords: ['grow','life','seed'] })
 *      .section('library',  el, { tongues: ['Dragon','Protist'],  keywords: ['knowledge','archive'] })
 *      .section('workshop', el, { tongues: ['Fold','Topology'],   keywords: ['build','make','tool'] });
 *
 *   qcr.route('what grows in the dark', ({ activations, mode }) => {
 *     for (const { section_id, score } of activations) {
 *       document.getElementById(section_id)?.style.setProperty('--qcr-activation', score);
 *     }
 *   });
 *
 * Data-attribute auto-init (no JS required beyond the script tag):
 *
 *   <script src="/qcr.js"
 *           data-api-key="qcr_xxxx"
 *           data-input="#qcr-input"
 *           data-on-route="myRouteHandler">
 *   </script>
 *
 *   <div data-qcr-section="garden"
 *        data-qcr-tongues="Lotus,Cannabis"
 *        data-qcr-keywords="grow,life,seed,flower">
 *   </div>
 */

(function (root) {
  'use strict';

  // ── Tongue → concept keyword map (for inferring tongues from free text) ──
  const TONGUE_KEYWORDS = {
    Lotus:          ['earth','water','fire','air','presence','pattern','intellect','experience','grow','seed','elemental'],
    Rose:           ['number','color','vector','spectrum','red','violet','green','indigo','ratio','count'],
    Sakura:         ['space','direction','here','there','front','back','top','bottom','position','location'],
    Daisy:          ['structure','segment','identity','mechanism','component','integrator','deadzone'],
    AppleBlossom:   ['alchemy','sulphur','mercury','salt','transmute','compound','mixture','lava','alkahest'],
    Aster:          ['chiral','time','loop','linear','exponential','fold','frozen','spiral'],
    Grapevine:      ['network','ceremony','connect','web','relation','ritual','gather'],
    Cannabis:       ['awareness','consciousness','perception','relational','transformative','chiral','duration'],
    Dragon:         ['void','organism','encode','knowledge','archive','language','lore'],
    Neural:         ['mind','neural','signal','process','compute','intelligence','cognition'],
    Serpent:        ['fire','soul','shakti','memory','sacred','residue','axis','ontic'],
    Moon:           ['time','eternal','complete','cycle','temporal','expression','closure'],
    Lotus:          ['foundation','material','beginning','closure','feeling','memory','thought','pattern'],
    Fold:           ['topology','fold','structure','architecture','scaffold'],
    Topology:       ['topology','surface','manifold','connection','knot'],
    Phase:          ['phase','transition','state','change','gradient'],
    Gradient:       ['gradient','energy','field','descent','landscape'],
    Curvature:      ['curvature','curve','bend','shape','space'],
    Blood:          ['blood','void','flow','life','death'],
    Koi:            ['exchange','balance','trade','reciprocal'],
    Rope:           ['bond','bind','constraint','hold','tie'],
    Hook:           ['mechanism','predation','trap','catch'],
    Fang:           ['nature','predator','instinct','primal'],
    Circle:         ['unity','ritual','whole','complete','ring'],
    Ledger:         ['account','record','bureaucracy','error','administration'],
  };

  function inferTongues(query) {
    const q = query.toLowerCase();
    const matched = [];
    for (const [tongue, kws] of Object.entries(TONGUE_KEYWORDS)) {
      if (kws.some(kw => q.includes(kw))) matched.push(tongue);
    }
    return matched.length ? [...new Set(matched)] : ['Lotus', 'Rose'];
  }

  // ── Keyword matching ───────────────────────────────────────────────────────

  function keywordScore(query, keywords) {
    const words = query.toLowerCase().split(/\W+/).filter(w => w.length > 1);
    let s = 0;
    for (const w of words)
      for (const kw of keywords)
        if (w.includes(kw.toLowerCase()) || kw.toLowerCase().includes(w)) s += 0.4;
    return Math.min(1.0, s);
  }

  function normalizeScores(activations) {
    const max = Math.max(0.001, ...activations.map(a => a.score));
    return activations.map(a => ({ ...a, score: Math.round((a.score / max) * 1000) / 1000 }));
  }

  // ── QCR class ──────────────────────────────────────────────────────────────

  function QCR(opts) {
    opts = opts || {};
    this.apiBase   = (opts.apiBase  || 'https://quantumquackery.org/api').replace(/\/$/, '');
    this.apiKey    = opts.apiKey    || null;
    this.fallback  = opts.fallback  !== false;
    this._sections = [];
  }

  QCR.prototype.section = function (id, el, opts) {
    opts = opts || {};
    this._sections.push({
      id,
      el,
      tongues:  opts.tongues  || [],
      keywords: opts.keywords || [],
      weight:   opts.weight   || 1.0,
    });
    return this;
  };

  QCR.prototype.route = function (query, callback) {
    const self = this;
    if (self.apiKey) {
      return self._tceRoute(query).then(callback).catch(function () {
        if (self.fallback) callback(self._keywordRoute(query));
      });
    }
    const result = self._keywordRoute(query);
    if (callback) callback(result);
    return Promise.resolve(result);
  };

  QCR.prototype._keywordRoute = function (query) {
    const activations = this._sections.map(sec => ({
      section_id: sec.id,
      score:      keywordScore(query, sec.keywords.concat(sec.tongues)),
      mode:       'keyword',
    }));
    return { activations: normalizeScores(activations), mode: 'keyword', shannon_h: null };
  };

  QCR.prototype._tceRoute = function (query) {
    const self = this;
    const body = {
      query,
      sections: self._sections.map(s => ({
        id:       s.id,
        tongues:  s.tongues,
        keywords: s.keywords,
        weight:   s.weight,
      })),
      kernel: 'keshi',
      temp:   0.35,
    };

    return fetch(self.apiBase + '/v1/qcr/route', {
      method:  'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-QCR-Key':    self.apiKey,
      },
      body: JSON.stringify(body),
    }).then(r => {
      if (!r.ok) throw new Error(r.status);
      return r.json();
    }).then(data => ({
      activations:       data.activations,
      converged_tongues: data.converged_tongues,
      energy:            data.energy,
      shannon_h:         data.shannon_h,
      mode:              data.mode,
    }));
  };

  // ── Field info ─────────────────────────────────────────────────────────────

  QCR.field = function (apiBase) {
    const base = (apiBase || 'https://quantumquackery.org/api').replace(/\/$/, '');
    return fetch(base + '/v1/qcr/field').then(r => r.json());
  };

  // ── Data-attribute auto-init ───────────────────────────────────────────────

  function autoInit() {
    const script = document.currentScript
      || document.querySelector('script[data-api-key], script[src*="qcr.js"]');
    if (!script) return;

    const apiKey   = script.dataset.apiKey   || null;
    const inputSel = script.dataset.input    || null;
    const onRoute  = script.dataset.onRoute  || null;
    const apiBase  = script.dataset.apiBase  || undefined;

    const qcr = new QCR({ apiKey, apiBase });

    // Register sections from data attributes
    document.querySelectorAll('[data-qcr-section]').forEach(el => {
      const id       = el.dataset.qcrSection;
      const tongues  = (el.dataset.qcrTongues  || '').split(',').map(s => s.trim()).filter(Boolean);
      const keywords = (el.dataset.qcrKeywords || '').split(',').map(s => s.trim()).filter(Boolean);
      qcr.section(id, el, { tongues, keywords });
    });

    // Callback
    const cb = onRoute && typeof root[onRoute] === 'function'
      ? root[onRoute]
      : function ({ activations }) {
          activations.forEach(({ section_id, score }) => {
            const el = document.getElementById(section_id);
            if (el) {
              el.style.setProperty('--qcr-activation', score);
              el.dataset.qcrScore = score;
              el.classList.toggle('qcr-lit', score > 0.4);
            }
          });
        };

    // Wire input
    if (inputSel) {
      const input = document.querySelector(inputSel);
      if (input) {
        input.addEventListener('keydown', function (e) {
          if (e.key === 'Enter') qcr.route(this.value.trim(), cb);
        });
      }
    }

    root._qcr = qcr;
  }

  // Export
  root.QCR = QCR;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', autoInit);
  } else {
    autoInit();
  }

}(window));
