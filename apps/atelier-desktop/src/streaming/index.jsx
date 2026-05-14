/**
 * Streaming hub — broadcaster control room.
 *
 * This is the "Streaming" section of the Atelier desktop. It is specifically
 * for practitioners who are streaming — managing their broadcast, tracking
 * their BoK geometry, monitoring Wunashakoun session quality, and handling
 * post-session Roko assessment.
 *
 * Witnesses connect at stream.quantumquackery.com (stream.html), not here.
 * Discovery is on the website, not inside a production tool.
 *
 * Palette: alchemical theatre (black/plum ground, magenta/pink accent, gold rare).
 */
import React, { useEffect, useState } from 'react';
import { Broadcast } from './pages/Broadcast.jsx';
import './tokens.css';

export function StreamingHub({ authToken, artisanId }) {
  return (
    <div
      className="streaming-root"
      style={{ height: '100%', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}
    >
      <Broadcast authToken={authToken} artisanId={artisanId} />
    </div>
  );
}
