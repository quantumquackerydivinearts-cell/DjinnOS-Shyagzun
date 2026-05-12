// http_intel.rs — Semantic substrate HTTP routes for DjinnOS.
//
// Mounted at:
//   GET  /field                      — embedded semantic field web page
//   GET  /api/intel/candidates       — all 1358 candidates as JSON
//   POST /api/intel/query/tongue     — Hopfield query by tongue register(s)
//   POST /api/intel/query/near       — query by byte address proximity
//   POST /api/intel/query/diff       — navigate by semantic diff operator
//
// All POST bodies are JSON objects.  Minimal JSON parser handles only
// what these endpoints need (no serde — bare-metal no_std).

extern crate alloc;
use alloc::vec::Vec;

// ── Route dispatch ────────────────────────────────────────────────────────────

pub fn try_handle(method: &str, path: &str, body: &str) -> Option<Vec<u8>> {
    crate::intel::init();
    // Building (queried collapse routing)
    if let Some(r) = crate::http_building::try_handle(path) { return Some(r); }
    match (method, path) {
        ("GET",  "/field")                     => Some(serve_field_page()),
        ("GET",  "/api/intel/candidates")      => Some(serve_candidates()),
        ("POST", "/api/intel/query/tongue")    => Some(serve_tongue(body)),
        ("POST", "/api/intel/query/near")      => Some(serve_near(body)),
        ("POST", "/api/intel/query/diff")      => Some(serve_diff(body)),
        ("OPTIONS", _) if path.starts_with("/api/intel") => Some(cors_preflight()),
        _ => None,
    }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

fn response(status: &str, ct: &[u8], body: &[u8]) -> Vec<u8> {
    let mut r = Vec::new();
    r.extend_from_slice(b"HTTP/1.0 ");
    r.extend_from_slice(status.as_bytes());
    r.extend_from_slice(b"\r\nContent-Type: ");
    r.extend_from_slice(ct);
    r.extend_from_slice(b"\r\nAccess-Control-Allow-Origin: *\r\nAccess-Control-Allow-Methods: GET,POST,OPTIONS\r\nAccess-Control-Allow-Headers: Content-Type\r\nConnection: close\r\nContent-Length: ");
    let mut len_buf = [0u8; 12];
    let ln = write_u32(&mut len_buf, body.len() as u32);
    r.extend_from_slice(&len_buf[..ln]);
    r.extend_from_slice(b"\r\n\r\n");
    r.extend_from_slice(body);
    r
}

fn cors_preflight() -> Vec<u8> {
    response("204 No Content", b"text/plain", b"")
}

fn write_u32(buf: &mut [u8; 12], n: u32) -> usize {
    if n == 0 { buf[0] = b'0'; return 1; }
    let mut tmp = [0u8; 12];
    let mut i = 0; let mut v = n;
    while v > 0 { tmp[i] = b'0' + (v % 10) as u8; i += 1; v /= 10; }
    for j in 0..i { buf[j] = tmp[i - 1 - j]; }
    i
}

// ── Minimal JSON parser ───────────────────────────────────────────────────────

fn json_str<'a>(json: &'a str, key: &str) -> Option<&'a str> {
    let pat = alloc::format!("\"{}\":\"", key);
    let start = json.find(pat.as_str())? + pat.len();
    let end = json[start..].find('"')? + start;
    Some(&json[start..end])
}

fn json_f32(json: &str, key: &str) -> f32 {
    let pat = alloc::format!("\"{}\":", key);
    let start = match json.find(pat.as_str()) {
        Some(i) => i + pat.len(),
        None => return 0.0,
    };
    let end = json[start..].find(|c: char| c == ',' || c == '}')
        .map(|i| i + start).unwrap_or(json.len());
    json[start..end].trim().parse::<f32>().unwrap_or(0.0)
}

fn json_i32(json: &str, key: &str) -> i32 {
    let pat = alloc::format!("\"{}\":", key);
    let start = match json.find(pat.as_str()) {
        Some(i) => i + pat.len(),
        None => return 0,
    };
    let end = json[start..].find(|c: char| c == ',' || c == '}')
        .map(|i| i + start).unwrap_or(json.len());
    json[start..end].trim().parse::<i32>().unwrap_or(0)
}

fn json_str_array<'a>(json: &'a str, key: &str) -> Vec<&'a str> {
    let pat = alloc::format!("\"{}\":[", key);
    let start = match json.find(pat.as_str()) {
        Some(i) => i + pat.len(),
        None => return Vec::new(),
    };
    let end = match json[start..].find(']') {
        Some(i) => i + start,
        None => return Vec::new(),
    };
    let arr = &json[start..end];
    let mut result = Vec::new();
    let mut rest = arr;
    loop {
        let s = match rest.find('"') {
            Some(i) => i + 1,
            None => break,
        };
        let e = match rest[s..].find('"') {
            Some(i) => i + s,
            None => break,
        };
        result.push(&rest[s..e]);
        rest = &rest[e + 1..];
    }
    result
}

// ── JSON output helpers ───────────────────────────────────────────────────────

fn push_str(out: &mut Vec<u8>, s: &str) {
    out.extend_from_slice(s.as_bytes());
}

fn push_json_str(out: &mut Vec<u8>, s: &str) {
    out.push(b'"');
    for b in s.bytes() {
        match b {
            b'"'  => { out.push(b'\\'); out.push(b'"'); }
            b'\\' => { out.push(b'\\'); out.push(b'\\'); }
            _     => out.push(b),
        }
    }
    out.push(b'"');
}

fn push_f32(out: &mut Vec<u8>, v: f32) {
    // Simple fixed-point: 4 decimal places, handles [-9999.9999..9999.9999]
    if v < 0.0 { out.push(b'-'); }
    let abs = v.abs();
    let int = abs as u32;
    let frac = ((abs - int as f32) * 10000.0) as u32;
    let mut tmp = [0u8; 12];
    let n = write_u32(&mut tmp, int);
    out.extend_from_slice(&tmp[..n]);
    out.push(b'.');
    // 4-digit fraction with leading zeros
    let mut tmp2 = [b'0'; 4];
    let mut f = frac;
    for i in (0..4).rev() { tmp2[i] = b'0' + (f % 10) as u8; f /= 10; }
    out.extend_from_slice(&tmp2);
}

fn push_usize(out: &mut Vec<u8>, v: usize) {
    let mut tmp = [0u8; 12];
    let n = write_u32(&mut tmp, v as u32);
    out.extend_from_slice(&tmp[..n]);
}

// ── Serialise a query result ──────────────────────────────────────────────────

fn serialise_result(
    active: &[usize],
    state: &[f32],
    energy: f32,
    iters: usize,
) -> Vec<u8> {
    let cands = crate::intel::cands();
    let mut out = Vec::new();
    push_str(&mut out, "{\"active\":[");
    for (i, &idx) in active.iter().enumerate() {
        if i > 0 { out.push(b','); }
        push_usize(&mut out, idx);
    }
    push_str(&mut out, "],\"candidates\":[");
    for (i, &idx) in active.iter().enumerate() {
        if i > 0 { out.push(b','); }
        let c = &cands[idx];
        push_str(&mut out, "{\"addr\":");
        push_usize(&mut out, c.addr as usize);
        push_str(&mut out, ",\"tongue\":");
        push_json_str(&mut out, tongue_name(c.tongue));
        push_str(&mut out, ",\"symbol\":");
        push_json_str(&mut out, "");   // symbols live in Python side; addr is enough
        push_str(&mut out, ",\"lotus_gated\":");
        out.extend_from_slice(if c.lotus_gated() { b"true" } else { b"false" });
        push_str(&mut out, "}");
    }
    push_str(&mut out, "],\"energy\":");
    push_f32(&mut out, energy);
    push_str(&mut out, ",\"iterations\":");
    push_usize(&mut out, iters);
    push_str(&mut out, ",\"state\":[");
    for (i, &v) in state.iter().enumerate() {
        if i > 0 { out.push(b','); }
        push_f32(&mut out, v);
    }
    push_str(&mut out, "]}");
    out
}

fn tongue_name(t: u8) -> &'static str {
    match t {
         1 => "Lotus",         2 => "Rose",
         3 => "Sakura",        4 => "Daisy",
         5 => "AppleBlossom",  6 => "Aster",
         7 => "Grapevine",     8 => "Cannabis",
         9 => "Dragon",       10 => "Virus",
        11 => "Bacteria",     12 => "Excavata",
        13 => "Archaeplastida",14 => "Myxozoa",
        15 => "Archaea",      16 => "Protist",
        17 => "Immune",       18 => "Neural",
        19 => "Serpent",      20 => "Beast",
        21 => "Cherub",       22 => "Chimera",
        23 => "Faerie",       24 => "Djinn",
        25 => "Fold",         26 => "Topology",
        27 => "Phase",        28 => "Gradient",
        29 => "Curvature",    30 => "Prion",
        31 => "Blood",        32 => "Moon",
        33 => "Koi",          34 => "Rope",
        35 => "Hook",         36 => "Fang",
        37 => "Circle",       38 => "Ledger",
        _  => "Unknown",
    }
}

// ── Endpoint handlers ─────────────────────────────────────────────────────────

fn serve_candidates() -> Vec<u8> {
    let cands = crate::intel::cands();
    let mut body = Vec::new();
    push_str(&mut body, "[");
    for (i, c) in cands.iter().enumerate() {
        if i > 0 { body.push(b','); }
        push_str(&mut body, "{\"idx\":");
        push_usize(&mut body, i);
        push_str(&mut body, ",\"addr\":");
        push_usize(&mut body, c.addr as usize);
        push_str(&mut body, ",\"tongue\":");
        push_json_str(&mut body, tongue_name(c.tongue));
        push_str(&mut body, ",\"gated\":");
        body.extend_from_slice(if c.lotus_gated() { b"true" } else { b"false" });
        push_str(&mut body, "}");
    }
    push_str(&mut body, "]");
    response("200 OK", b"application/json", &body)
}

fn serve_tongue(body: &str) -> Vec<u8> {
    let tongues_raw = json_str_array(body, "tongues");
    let kernel_str  = json_str(body, "kernel").unwrap_or("giann");
    let temp        = json_f32(body, "temp");

    // Map tongue names to tongue numbers
    let mut tongue_nums: Vec<u8> = Vec::new();
    for name in &tongues_raw {
        if let Some(n) = tongue_num_from_name(name) {
            tongue_nums.push(n);
        }
    }

    use crate::intel::{DjinnMode, query_by_tongue};
    let mode = parse_mode(kernel_str, temp, 10, 16.0);
    let (out_indices, n) = query_by_tongue(&tongue_nums, mode);

    let state = unsafe { &crate::intel::STATE_V[..] };
    let energy = compute_energy(state);
    let result_body = serialise_result(&out_indices[..n], state, energy, 0);
    response("200 OK", b"application/json", &result_body)
}

fn serve_near(body: &str) -> Vec<u8> {
    let addr   = json_i32(body, "addr") as u16;
    let radius = json_i32(body, "radius") as u16;
    let kernel = json_str(body, "kernel").unwrap_or("giann");
    let temp   = json_f32(body, "temp");

    use crate::intel::query_near;
    let _ = (kernel, temp);  // query_near uses Giann internally
    let (out_indices, n) = query_near(addr, radius.max(1));

    let state = unsafe { &crate::intel::STATE_V[..] };
    let energy = compute_energy(state);
    let result_body = serialise_result(&out_indices[..n], state, energy, 0);
    response("200 OK", b"application/json", &result_body)
}

fn serve_diff(body: &str) -> Vec<u8> {
    use crate::intel::cands;
    let seed  = json_i32(body, "seed_addr");
    let delta = json_i32(body, "delta");
    let kernel= json_str(body, "kernel").unwrap_or("keshi");
    let temp  = json_f32(body, "temp").max(0.1);

    // Pin the seed candidate; soft-attract toward seed+delta
    let cs = cands();
    unsafe {
        for x in crate::intel::STATE_V.iter_mut() { *x = -0.3; }
        for (i, c) in cs.iter().enumerate() {
            if c.addr as i32 == seed {
                crate::intel::STATE_V[i] = 1.0;
            } else {
                let d = (c.addr as i32 - (seed + delta)).abs();
                if d <= 4 {
                    crate::intel::STATE_V[i] = 0.5 - d as f32 * 0.1;
                }
            }
        }
    }

    // Run a few Keshi steps
    let mode = parse_mode(kernel, temp, 10, 16.0);
    {
        let mut st = unsafe { crate::intel::State { v: &mut crate::intel::STATE_V } };
        crate::intel::converge(&mut st, &mode, &[], 16);
    }

    let state = unsafe { &crate::intel::STATE_V[..] };
    let active: Vec<usize> = (0..crate::intel::N_CANDS)
        .filter(|&i| state[i] > 0.5).collect();
    let energy = compute_energy(state);
    let result_body = serialise_result(&active, state, energy, 0);
    response("200 OK", b"application/json", &result_body)
}

fn parse_mode(
    kernel: &str,
    temp: f32,
    window: u64,
    threshold: f32,
) -> crate::intel::DjinnMode {
    use crate::intel::DjinnMode;
    match kernel {
        "keshi"    => DjinnMode::Keshi { temp: temp.max(0.01) },
        "drovitth" => DjinnMode::Drovitth { epoch: 0, window },
        "saelith"  => DjinnMode::Giann,  // threshold needs fn ptr; use Giann fallback
        _          => DjinnMode::Giann,
    }
}

fn tongue_num_from_name(name: &str) -> Option<u8> {
    match name {
        "Lotus"=>Some(1),"Rose"=>Some(2),"Sakura"=>Some(3),"Daisy"=>Some(4),
        "AppleBlossom"=>Some(5),"Aster"=>Some(6),"Grapevine"=>Some(7),"Cannabis"=>Some(8),
        "Dragon"=>Some(9),"Virus"=>Some(10),"Bacteria"=>Some(11),"Excavata"=>Some(12),
        "Archaeplastida"=>Some(13),"Myxozoa"=>Some(14),"Archaea"=>Some(15),"Protist"=>Some(16),
        "Immune"=>Some(17),"Neural"=>Some(18),"Serpent"=>Some(19),"Beast"=>Some(20),
        "Cherub"=>Some(21),"Chimera"=>Some(22),"Faerie"=>Some(23),"Djinn"=>Some(24),
        "Fold"=>Some(25),"Topology"=>Some(26),"Phase"=>Some(27),"Gradient"=>Some(28),
        "Curvature"=>Some(29),"Prion"=>Some(30),"Blood"=>Some(31),"Moon"=>Some(32),
        "Koi"=>Some(33),"Rope"=>Some(34),"Hook"=>Some(35),"Fang"=>Some(36),
        "Circle"=>Some(37),"Ledger"=>Some(38),
        _ => None,
    }
}

fn compute_energy(s: &[f32]) -> f32 {
    // Approximate energy: negative sum of squared activations (fast proxy).
    -s.iter().map(|&v| v * v).sum::<f32>() * 0.5
}

// ── Embedded semantic field page ──────────────────────────────────────────────
//
// Self-contained HTML/CSS/JS.  No external dependencies.
// Fetches /api/intel/candidates on load, then queries on demand.
// Works in any browser that can reach DjinnOS over USB tether.

fn serve_field_page() -> Vec<u8> {
    let html = br#"<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DjinnOS - Semantic Field</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#080610;color:#c0b0d8;font-family:monospace;font-size:13px;height:100vh;display:flex;flex-direction:column}
#hdr{padding:10px 16px;display:flex;gap:12px;align-items:center;border-bottom:1px solid #1a1030;background:#0a0818}
#hdr h1{color:#9060d0;font-size:14px;letter-spacing:1px}
#hdr .sub{color:#403058;font-size:11px}
#ctrl{padding:8px 16px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;border-bottom:1px solid #120c20}
#modes{display:flex;gap:4px}
.mode-btn{padding:3px 10px;background:#100820;color:#604878;border:1px solid #201838;border-radius:3px;cursor:pointer;font:12px monospace}
.mode-btn.active{background:#2a1650;color:#b080e0;border-color:#5030a0}
#tongue-list{display:flex;gap:3px;flex-wrap:wrap;flex:1;max-width:600px}
.t-btn{padding:2px 6px;border-radius:2px;cursor:pointer;font:11px monospace;border:1px solid #201838;background:#100820;transition:background .1s}
.t-btn.sel{border-color:#6040a0}
#addr-row{display:flex;gap:6px;align-items:center}
input[type=number]{width:70px;background:#100820;color:#b080e0;border:1px solid #201838;padding:2px 6px;border-radius:3px;font:12px monospace}
select{background:#100820;color:#9060c0;border:1px solid #201838;padding:2px 6px;border-radius:3px;font:12px monospace}
label{color:#504060;font-size:11px}
#go{padding:4px 14px;background:#2a1060;color:#c090f0;border:1px solid #5030a0;border-radius:3px;cursor:pointer;font:12px monospace}
#go:hover{background:#381880}
#field{flex:1;position:relative;overflow:hidden}
canvas{display:block;width:100%;height:100%}
#results{height:160px;overflow-y:auto;padding:6px 16px;background:#060410;border-top:1px solid #100820}
.cand{display:flex;gap:8px;padding:2px 0;border-bottom:1px solid #0e0820;cursor:pointer}
.cand:hover{background:#120a20}
.cand .addr{color:#302048;width:36px}
.cand .tongue{width:80px;font-size:11px}
.cand .status{padding:2px 4px;background:#0a0618;color:#a060d0;border-radius:2px;font:11px monospace;border:1px solid #2a1050}
#status{color:#403058;font-size:11px;padding:4px 16px;background:#080612}
</style>
</head>
<body>
<div id="hdr">
  <h1>* Semantic Field</h1>
  <span class="sub" id="cand-count">loading...</span>
  <span class="sub" id="q-status"></span>
</div>
<div id="ctrl">
  <div id="modes">
    <button class="mode-btn active" onclick="setMode('tongue')" id="m-tongue">Tongue</button>
    <button class="mode-btn" onclick="setMode('near')" id="m-near">Near</button>
    <button class="mode-btn" onclick="setMode('diff')" id="m-diff">D Diff</button>
  </div>
  <div id="tongue-list"></div>
  <div id="addr-row" style="display:none">
    <label>addr</label>
    <input type="number" id="addr-in" value="582" min="0" max="1403">
    <span id="delta-wrap">
      <label>d</label>
      <input type="number" id="delta-in" value="24" min="-1403" max="1403">
    </span>
  </div>
  <select id="kernel">
    <option value="giann">Giann: deterministic</option>
    <option value="keshi">Keshi: entropic</option>
    <option value="drovitth">Drovitth: periodic</option>
    <option value="saelith">Saelith: threshold</option>
  </select>
  <button id="go" onclick="runQuery()">converge</button>
</div>
<div id="field"><canvas id="cv"></canvas></div>
<div id="results"><div style="color:#302048;padding:4px 0">converge to see active candidates</div></div>
<div id="status">DjinnOS semantic substrate / 38 tongues / Hopfield network</div>

<script>
const API = '';  // same origin
let CANDS = [];
let mode = 'tongue';
let selTongues = [];
let lastState = null;

const TONGUE_COLORS = {
  Lotus:'#c8783c',Rose:'#d44060',Sakura:'#e8a0b0',Daisy:'#80d080',
  AppleBlossom:'#a060d0',Aster:'#4080d0',Grapevine:'#d0a040',Cannabis:'#60c080',
  Dragon:'#c04040',Virus:'#8040c0',Bacteria:'#40c0a0',Excavata:'#c08040',
  Archaeplastida:'#40a0c0',Myxozoa:'#a04080',Archaea:'#80c040',Protist:'#c0c040',
  Immune:'#4060c0',Neural:'#c04060',Serpent:'#60d0c0',Beast:'#d06040',
  Cherub:'#a080d0',Chimera:'#d080a0',Faerie:'#80d0d0',Djinn:'#d0d080',
  Fold:'#a0c080',Topology:'#80a0c0',Phase:'#c080c0',Gradient:'#c0a060',
  Curvature:'#60c0a0',Prion:'#a06080',Blood:'#d04040',Moon:'#c0c0d0',
  Koi:'#60a0d0',Rope:'#d06080',Hook:'#80d060',Fang:'#d0a080',
  Circle:'#a0d0a0',Ledger:'#8080a0'
};

async function load() {
  const r = await fetch(API + '/api/intel/candidates');
  CANDS = await r.json();
  document.getElementById('cand-count').textContent = CANDS.length + ' candidates / 38 tongues';
  buildTongueButtons();
  drawField(null, []);
}

function buildTongueButtons() {
  const tongues = [...new Set(CANDS.map(c => c.tongue))];
  const el = document.getElementById('tongue-list');
  el.innerHTML = '';
  for (const t of tongues) {
    const b = document.createElement('button');
    b.className = 't-btn';
    b.textContent = t;
    b.style.color = TONGUE_COLORS[t] || '#888';
    b.onclick = () => {
      const i = selTongues.indexOf(t);
      if (i >= 0) { selTongues.splice(i,1); b.classList.remove('sel'); b.style.background='#100820'; }
      else        { selTongues.push(t);     b.classList.add('sel');    b.style.background=(TONGUE_COLORS[t]||'#888')+'22'; }
    };
    el.appendChild(b);
  }
}

function setMode(m) {
  mode = m;
  ['tongue','near','diff'].forEach(x => {
    document.getElementById('m-'+x).classList.toggle('active', x===m);
  });
  document.getElementById('tongue-list').style.display = m==='tongue'?'flex':'none';
  document.getElementById('addr-row').style.display = m!=='tongue'?'flex':'none';
  document.getElementById('delta-wrap').style.display = m==='diff'?'flex':'none';
}

async function runQuery() {
  const kernel = document.getElementById('kernel').value;
  document.getElementById('q-status').textContent = 'converging...';
  let url, body;
  if (mode === 'tongue') {
    url = '/api/intel/query/tongue';
    body = {tongues: selTongues, kernel, temp: kernel==='keshi'?2.0:0.0};
  } else if (mode === 'near') {
    url = '/api/intel/query/near';
    body = {addr: +document.getElementById('addr-in').value, kernel, temp: kernel==='keshi'?2.0:0.0, radius: 48};
  } else {
    url = '/api/intel/query/diff';
    body = {seed_addr: +document.getElementById('addr-in').value,
            delta: +document.getElementById('delta-in').value, kernel, temp: 1.5};
  }
  try {
    const r = await fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    const data = await r.json();
    lastState = data.state;
    const activeSet = new Set(data.active);
    drawField(data.state, activeSet);
    renderResults(data.candidates);
    document.getElementById('q-status').textContent =
      data.active.length + ' active  E=' + data.energy.toFixed(2) + '  iter=' + data.iterations;
  } catch(e) {
    document.getElementById('q-status').textContent = 'error: ' + e.message;
  }
}

function drawField(state, activeSet) {
  const canvas = document.getElementById('cv');
  const W = canvas.offsetWidth; const H = canvas.offsetHeight;
  canvas.width = W; canvas.height = H;
  const ctx = canvas.getContext('2d');
  const bg = ctx.createLinearGradient(0,0,0,H);
  bg.addColorStop(0,'#0a0810'); bg.addColorStop(1,'#060508');
  ctx.fillStyle = bg; ctx.fillRect(0,0,W,H);
  if (!CANDS.length) return;
  const maxAddr = 1403;
  const ax = a => 16 + (Math.log1p(a)/Math.log1p(maxAddr)) * (W-32);
  const vy = v => H-12 - ((v+1)/2)*(H-24);
  // Field curve
  if (state) {
    ctx.beginPath();
    CANDS.forEach((c,i) => {
      const x=ax(c.addr), y=vy(state[i]||0);
      i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);
    });
    ctx.strokeStyle='rgba(100,160,220,0.25)'; ctx.lineWidth=1; ctx.stroke();
  }
  // Tongue boundary lines
  let lastTongue='';
  for (const c of CANDS) {
    if (c.tongue !== lastTongue) {
      lastTongue = c.tongue;
      const x = ax(c.addr);
      ctx.strokeStyle='rgba(255,255,255,0.03)'; ctx.lineWidth=1;
      ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,H); ctx.stroke();
      ctx.fillStyle='rgba(255,255,255,0.12)'; ctx.font='9px monospace';
      ctx.fillText(c.tongue.slice(0,4), x+2, 11);
    }
  }
  // Nodes
  for (let i=0; i<CANDS.length; i++) {
    const c = CANDS[i];
    const act = state ? (state[i]||0) : 0;
    const isActive = activeSet.has ? activeSet.has(i) : false;
    const x = ax(c.addr);
    const y = state ? vy(act) : H/2;
    const col = TONGUE_COLORS[c.tongue]||'#888';
    const alpha = isActive ? 1.0 : Math.max(0.08, 0.1 + 0.3*Math.max(0,act));
    const r = isActive ? 4 : 1.5;
    ctx.beginPath(); ctx.arc(x,y,r,0,Math.PI*2);
    ctx.fillStyle = col + Math.round(alpha*255).toString(16).padStart(2,'0');
    ctx.fill();
    if (isActive) {
      ctx.beginPath(); ctx.arc(x,y,r+5,0,Math.PI*2);
      ctx.fillStyle = col+'18'; ctx.fill();
    }
  }
}

function renderResults(cands) {
  const el = document.getElementById('results');
  el.innerHTML = '';
  if (!cands || !cands.length) { el.innerHTML='<div style="color:#302048;padding:4px 0">no active candidates</div>'; return; }
  for (const c of cands.slice(0,60)) {
    const d = document.createElement('div');
    d.className='cand';
    d.onclick = () => {
      document.getElementById('addr-in').value = c.addr;
      setMode('near');
      runQuery();
    };
    d.innerHTML = `<span class="addr">${c.addr}</span>
      <span class="tongue" style="color:${TONGUE_COLORS[c.tongue]||'#888'}">${c.tongue}</span>
      <span class="status">${c.gated?'* lotus':'open'}</span>`;
    el.appendChild(d);
  }
  if (cands.length > 60) {
    const m = document.createElement('div');
    m.style.color='#302048'; m.style.padding='4px 0';
    m.textContent= '+' + (cands.length-60) + ' more';
    el.appendChild(m);
  }
}

window.addEventListener('resize', () => { if (lastState) drawField(lastState, new Set()); });
load();
</script>
</body>
</html>"#;
    response("200 OK", b"text/html; charset=utf-8", html)
}
