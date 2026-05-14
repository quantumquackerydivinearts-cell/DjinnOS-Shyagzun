/**
 * marble.js — Julia set renderer for alchemical marble surfaces.
 *
 * The BoK (BreathOfKo) save state is defined as a region of the Mandelbrot set
 * parameterised by a complex number c.  This renderer maps that c value to a
 * Julia set and color-maps iteration counts into the alchemical palette:
 *   iteration 0–15%  → black/plum (escaped quickly — ground)
 *   iteration 15–60% → magenta spectrum (approaching attractor)
 *   iteration 60–90% → pink → gold (deep orbit)
 *   iteration 90%+   → bright gold (bounded — the attractor itself)
 *
 * Three surface variants:
 *   css        — pure CSS gradients (no Canvas, cheap)
 *   svg        — SVG turbulence filter (medium fidelity)
 *   mandelbrot — full Julia set render (signature surface)
 *
 * All render functions return a CSS string for use as `background` or write
 * directly to a provided Canvas.
 */

// ── Color palette ──────────────────────────────────────────────────────────────

const PAL_BLACK   = [10,  10,  10];
const PAL_PLUM    = [58,  10,  42];
const PAL_MAGENTA = [233, 30,  150];
const PAL_PINK    = [255, 183, 221];
const PAL_GOLD    = [212, 175, 55];
const PAL_GOLD_BR = [255, 200, 87];

function lerp3(a, b, t) {
  return [
    a[0] + (b[0] - a[0]) * t,
    a[1] + (b[1] - a[1]) * t,
    a[2] + (b[2] - a[2]) * t,
  ];
}

function iterToColor(iter, maxIter) {
  if (iter === maxIter) return PAL_PLUM;  // bounded
  const t = iter / maxIter;
  if (t < 0.15) return lerp3(PAL_BLACK,   PAL_PLUM,    t / 0.15);
  if (t < 0.45) return lerp3(PAL_PLUM,    PAL_MAGENTA, (t - 0.15) / 0.30);
  if (t < 0.70) return lerp3(PAL_MAGENTA, PAL_PINK,    (t - 0.45) / 0.25);
  if (t < 0.88) return lerp3(PAL_PINK,    PAL_GOLD,    (t - 0.70) / 0.18);
  return lerp3(PAL_GOLD, PAL_GOLD_BR, (t - 0.88) / 0.12);
}

// ── Julia iteration ────────────────────────────────────────────────────────────

function juliaIter(zx, zy, cx, cy, maxIter) {
  let x = zx, y = zy;
  for (let i = 0; i < maxIter; i++) {
    const x2 = x * x, y2 = y * y;
    if (x2 + y2 > 4) return i;
    const nx = x2 - y2 + cx;
    y = 2 * x * y + cy;
    x = nx;
  }
  return maxIter;
}

// ── CSS marble (no Canvas) ────────────────────────────────────────────────────

export function cssMarbletStyle(cx = -0.7, cy = 0.27) {
  // Deterministic pseudo-random veins from the c parameter.
  const angle = (Math.atan2(cy, cx) * 180 / Math.PI + 360) % 360;
  const r     = Math.sqrt(cx * cx + cy * cy);
  const v1    = `${(angle * 0.7).toFixed(1)}deg`;
  const v2    = `${((angle + 90) * 0.6).toFixed(1)}deg`;
  const spread = (30 + r * 40).toFixed(1);

  return {
    background: `
      radial-gradient(ellipse at ${(30 + r*30).toFixed()}% ${(40 + cy*20).toFixed()}%,
        rgba(233,30,150,0.18) 0%, transparent ${spread}%),
      conic-gradient(from ${v1} at 35% 55%,
        #3A0A2A 0%, #220618 35%, rgba(212,175,55,0.06) 50%, #3A0A2A 65%, #0A0A0A 100%),
      radial-gradient(ellipse at 65% 30%,
        rgba(255,183,221,0.08) 0%, transparent 50%),
      conic-gradient(from ${v2} at 70% 45%,
        #0A0A0A 0%, #3A0A2A 40%, rgba(233,30,150,0.1) 55%, #0A0A0A 100%)
    `,
  };
}

// ── SVG turbulence marble (medium fidelity) ───────────────────────────────────

export function svgMarbleDataUrl(width = 400, height = 200, cx = -0.7, cy = 0.27) {
  const seed  = Math.abs(Math.round(cx * 1000 + cy * 1000)) % 9999 + 1;
  const freq  = (0.012 + Math.abs(cy) * 0.008).toFixed(4);
  const svg = `
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}">
  <defs>
    <filter id="marble">
      <feTurbulence type="fractalNoise" baseFrequency="${freq} ${(+freq*0.6).toFixed(4)}"
                    numOctaves="4" seed="${seed}" result="noise"/>
      <feDisplacementMap in="SourceGraphic" in2="noise" scale="60" xChannelSelector="R" yChannelSelector="G"/>
      <feColorMatrix type="matrix"
        values="0.3 0   0   0 0.04
                0   0   0   0 0.04
                0   0   0.1 0 0.04
                0   0   0   1 0"/>
    </filter>
    <linearGradient id="base" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%"   stop-color="#220618"/>
      <stop offset="40%"  stop-color="#3A0A2A"/>
      <stop offset="70%"  stop-color="#1A0612" stop-opacity="0.9"/>
      <stop offset="100%" stop-color="#0A0A0A"/>
    </linearGradient>
    <linearGradient id="vein" x1="${(0.3+cx*0.2).toFixed(2)}" y1="0"
                              x2="${(0.7+cy*0.1).toFixed(2)}" y2="1">
      <stop offset="0%"   stop-color="#E91E96" stop-opacity="0.0"/>
      <stop offset="45%"  stop-color="#E91E96" stop-opacity="0.22"/>
      <stop offset="55%"  stop-color="#FFB7DD" stop-opacity="0.08"/>
      <stop offset="100%" stop-color="#D4AF37" stop-opacity="0.06"/>
    </linearGradient>
  </defs>
  <rect width="100%" height="100%" fill="url(#base)"/>
  <rect width="100%" height="100%" fill="url(#vein)" filter="url(#marble)"/>
</svg>`.trim();
  return `data:image/svg+xml;base64,${btoa(svg)}`;
}

// ── Full Julia set render ─────────────────────────────────────────────────────

/**
 * Render a Julia set for parameter (cx, cy) onto a Canvas element.
 *
 * @param {HTMLCanvasElement} canvas
 * @param {number} cx   Real part of Julia parameter (BoK.re)
 * @param {number} cy   Imaginary part of Julia parameter (BoK.im)
 * @param {object} opts
 *   centerX, centerY  — view center in complex plane (default 0,0)
 *   zoom              — pixels per unit (default 120)
 *   maxIter           — iteration depth (default 80)
 *   quality           — 1=full, 2=half-res upscaled (default 1)
 */
export function renderJulia(canvas, cx, cy, opts = {}) {
  const {
    centerX = 0,
    centerY = 0,
    zoom    = 120,
    maxIter = 80,
    quality = 1,
  } = opts;

  const W = canvas.width;
  const H = canvas.height;
  const ctx = canvas.getContext('2d');
  const step = quality;
  const imgData = ctx.createImageData(W, H);
  const data    = imgData.data;

  for (let py = 0; py < H; py += step) {
    for (let px = 0; px < W; px += step) {
      const zx = (px - W / 2) / zoom + centerX;
      const zy = (py - H / 2) / zoom + centerY;
      const iter = juliaIter(zx, zy, cx, cy, maxIter);
      const [r, g, b] = iterToColor(iter, maxIter);

      for (let dy = 0; dy < step && py + dy < H; dy++) {
        for (let dx = 0; dx < step && px + dx < W; dx++) {
          const i = ((py + dy) * W + (px + dx)) * 4;
          data[i]     = r;
          data[i + 1] = g;
          data[i + 2] = b;
          data[i + 3] = 255;
        }
      }
    }
  }
  ctx.putImageData(imgData, 0, 0);
}

/**
 * Async wrapper: renders off-main-thread using requestIdleCallback fallback.
 * Calls onDone(canvas) when finished.
 */
export function renderJuliaAsync(canvas, cx, cy, opts = {}, onDone) {
  const schedule = typeof requestIdleCallback === 'function'
    ? (fn) => requestIdleCallback(fn, { timeout: 2000 })
    : (fn) => setTimeout(fn, 0);

  schedule(() => {
    renderJulia(canvas, cx, cy, { quality: 2, ...opts });
    if (onDone) onDone(canvas);
    // Second pass at full quality
    schedule(() => {
      renderJulia(canvas, cx, cy, { quality: 1, ...opts });
      if (onDone) onDone(canvas);
    });
  });
}

// ── Default BoK parameter ────────────────────────────────────────────────────

/** When no BoK is available, render c = -0.7 + 0.27i (classic Julia). */
export const DEFAULT_BOK = { re: -0.7, im: 0.27 };

/** Parse a BoK string "re,im" or return DEFAULT_BOK. */
export function parseBok(bok) {
  if (!bok) return DEFAULT_BOK;
  const [re, im] = String(bok).split(',').map(Number);
  if (isNaN(re) || isNaN(im)) return DEFAULT_BOK;
  return { re, im };
}
