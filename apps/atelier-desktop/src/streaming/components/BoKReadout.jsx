import React, { useCallback, useEffect, useRef, useState } from 'react';
import { renderJuliaAsync, parseBok, DEFAULT_BOK } from '../marble.js';

/**
 * BoKReadout — live geometric position display for the current session.
 *
 * Renders the Julia set corresponding to the current BoK c parameter.
 * Edge boundedness (iterations reaching maxIter > 60% of pixels) highlights in gold.
 * Animates smoothly when the BoK position changes.
 *
 * Props:
 *   bok     : { re, im } | "re,im" | null  — current BoK parameter
 *   label   : string — override label (default "BoK Position")
 *   width   : canvas width (default 320)
 *   height  : canvas height (default 200)
 */
export function BoKReadout({ bok, label = 'BoK Position', width = 320, height = 200 }) {
  const canvasRef   = useRef(null);
  const [edge, setEdge] = useState(false);
  const [shimmer, setShimmer] = useState(false);
  const prevBok = useRef(null);

  const doRender = useCallback((cx, cy) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    renderJuliaAsync(canvas, cx, cy, { zoom: height * 0.55, maxIter: 100 }, (c) => {
      // Estimate boundedness: scan center region
      const ctx = c.getContext('2d');
      const d   = ctx.getImageData(width / 4, height / 4, width / 2, height / 2);
      let bounded = 0;
      for (let i = 0; i < d.data.length; i += 4) {
        // Gold-ish = bounded (high R, mid G, low B)
        if (d.data[i] > 180 && d.data[i+1] > 140 && d.data[i+2] < 80) bounded++;
      }
      const fraction = bounded / (d.data.length / 4);
      const isEdge   = fraction > 0.08;
      if (isEdge !== edge) {
        setEdge(isEdge);
        if (isEdge) { setShimmer(true); setTimeout(() => setShimmer(false), 1200); }
      }
    });
  }, [width, height, edge]);

  useEffect(() => {
    const { re, im } = parseBok(bok) || DEFAULT_BOK;
    if (prevBok.current?.re === re && prevBok.current?.im === im) return;
    prevBok.current = { re, im };
    doRender(re, im);
  }, [bok, doRender]);

  const { re, im } = parseBok(bok) || DEFAULT_BOK;
  const borderColor = edge ? 'var(--gold-alchemical)' : 'var(--pink-muted)';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)' }}>
          {label}
        </span>
        {edge && (
          <span style={{ fontSize: 11, color: 'var(--gold-alchemical)', fontFamily: 'var(--font-mono)' }}>
            ✦ edge bounded
          </span>
        )}
      </div>
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        className={shimmer ? 's-shimmer' : ''}
        style={{
          borderRadius: 'var(--radius-md)',
          border: `1px solid ${borderColor}`,
          boxShadow: edge ? 'var(--glow-gold)' : 'none',
          display: 'block',
          maxWidth: '100%',
          transition: 'border-color 0.4s, box-shadow 0.4s',
        }}
      />
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)', textAlign: 'center' }}>
        c = {re.toFixed(6)} + {im.toFixed(6)}i
      </div>
    </div>
  );
}
