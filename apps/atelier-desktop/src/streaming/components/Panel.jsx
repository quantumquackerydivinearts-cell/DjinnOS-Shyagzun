import React, { useEffect, useRef } from 'react';
import { cssMarbletStyle, svgMarbleDataUrl, renderJuliaAsync, parseBok }
  from '../marble.js';

/** Basic panel with plum-elevated background and 1px plum border. */
export function Panel({ children, style, className = '', gold = false }) {
  return (
    <div
      className={`s-panel${gold ? '-gold' : ''} ${className}`}
      style={style}
    >
      {children}
    </div>
  );
}

/**
 * MarblePanel — hero panel with a marble surface.
 *
 * variant: 'css' | 'svg' | 'mandelbrot'
 * bok:     { re, im } — Julia parameter for mandelbrot variant
 * children are rendered on top; keep them text-light.
 */
export function MarblePanel({
  children,
  variant = 'css',
  bok,
  style,
  className = '',
  minHeight = 180,
}) {
  const canvasRef = useRef(null);
  const { re, im } = parseBok(bok) || { re: -0.7, im: 0.27 };

  // Mandelbrot variant: render Julia set onto a canvas
  useEffect(() => {
    if (variant !== 'mandelbrot') return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    renderJuliaAsync(canvas, re, im, { zoom: 100, maxIter: 80 }, null);
  }, [variant, re, im]);

  const surfaceStyle = (() => {
    switch (variant) {
      case 'svg': {
        const url = svgMarbleDataUrl(600, 200, re, im);
        return { backgroundImage: `url("${url}")`, backgroundSize: 'cover' };
      }
      case 'mandelbrot':
        return {};  // drawn onto canvas
      default:
        return cssMarbletStyle(re, im);
    }
  })();

  return (
    <div
      className={`s-marble-panel ${className}`}
      style={{
        position:     'relative',
        minHeight,
        borderRadius: 'var(--radius-lg)',
        overflow:     'hidden',
        border:       'var(--border-gold)',
        ...surfaceStyle,
        ...style,
      }}
    >
      {variant === 'mandelbrot' && (
        <canvas
          ref={canvasRef}
          width={600}
          height={minHeight}
          style={{
            position: 'absolute', inset: 0,
            width: '100%', height: '100%',
            objectFit: 'cover',
          }}
        />
      )}
      {/* Gradient scrim so text over marble stays legible */}
      <div style={{
        position: 'absolute', inset: 0,
        background: 'linear-gradient(180deg, rgba(10,10,10,0.3) 0%, rgba(10,10,10,0.7) 100%)',
      }} />
      <div style={{ position: 'relative', zIndex: 1 }}>
        {children}
      </div>
    </div>
  );
}
