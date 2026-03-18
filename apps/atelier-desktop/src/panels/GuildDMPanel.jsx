import { useCallback, useEffect, useRef, useState } from "react";

/**
 * GuildDMPanel — artisan ↔ artisan encrypted direct messages.
 *
 * Uses the existing guild message encrypt/persist/history/decrypt pipeline with
 * conversation_kind = "member_dm". Conversation IDs are derived deterministically
 * so A→B and B→A always share the same thread.
 *
 * Props:
 *   apiBase                     — atelier API base URL
 *   apiCall(path, method, body) — pre-wired fetch with artisan auth headers
 *   guildId                     — current guild ID
 *   guildChannelId              — current channel ID (used as channel context for DMs)
 *   activeProfileMemberId       — the calling artisan's member ID
 *   artisanId                   — the calling artisan's user ID (sender_id)
 *   guildWandId                 — artisan's active wand ID
 *   guildWandPasskeyWard        — wand passkey ward (secret phrase)
 *   buildTempleEntropySourcePayload() → object
 *   buildTheatreEntropySourcePayload() → object
 *   workspaceId                 — current workspace
 *   authToken                   — raw JWT for SSE (EventSource query param)
 */
export function GuildDMPanel({
  apiBase,
  apiCall,
  guildId,
  guildChannelId,
  activeProfileMemberId,
  artisanId,
  guildWandId,
  guildWandPasskeyWard,
  buildTempleEntropySourcePayload,
  buildTheatreEntropySourcePayload,
  workspaceId,
  authToken,
}) {
  const [profiles, setProfiles] = useState([]);
  const [profilesStatus, setProfilesStatus] = useState("idle");
  const [recipient, setRecipient] = useState(null); // { artisan_id, display_name, member_id? }
  const [envelopes, setEnvelopes] = useState([]); // raw history rows
  const [decrypted, setDecrypted] = useState({}); // message_id → { plaintext, verified }
  const [decryptStatus, setDecryptStatus] = useState("idle");
  const [draft, setDraft] = useState("");
  const [sendStatus, setSendStatus] = useState("idle");
  const [sseStatus, setSseStatus] = useState("disconnected");
  const sseRef = useRef(null);
  const threadEndRef = useRef(null);

  // ── Derive deterministic DM conversation ID ───────────────────────────────
  const dmConversationId = useCallback((memberA, memberB) => {
    if (!memberA || !memberB) return null;
    return "dm::" + [memberA, memberB].sort().join("::");
  }, []);

  const activeConvId = dmConversationId(activeProfileMemberId, recipient?.member_id || recipient?.artisan_id);

  // ── Load guild profiles (public or all for steward) ───────────────────────
  const loadProfiles = useCallback(async () => {
    setProfilesStatus("loading");
    try {
      // Try admin list first; fall back to public list
      let data;
      try {
        data = await apiCall("/v1/guild/profiles", "GET", null);
      } catch {
        data = await apiCall("/v1/guild/profiles/public", "GET", null);
      }
      setProfiles(Array.isArray(data) ? data : []);
      setProfilesStatus("idle");
    } catch (err) {
      setProfilesStatus(`error: ${err.message}`);
    }
  }, [apiCall]);

  useEffect(() => { loadProfiles(); }, [loadProfiles]);

  // ── Upsert DM conversation when recipient is selected ────────────────────
  useEffect(() => {
    if (!activeConvId || !activeProfileMemberId || !recipient) return;
    const recipientMemberId = recipient.member_id || recipient.artisan_id;
    apiCall("/v1/guild/conversations", "POST", {
      conversation_id: activeConvId,
      conversation_kind: "member_dm",
      guild_id: guildId || "",
      channel_id: guildChannelId || "",
      thread_id: null,
      title: `DM: ${activeProfileMemberId} ↔ ${recipientMemberId}`,
      participant_member_ids: [activeProfileMemberId, recipientMemberId],
      participant_guild_ids: [guildId || ""],
      distribution_id: null,
      security_session: {},
      metadata: { source: "atelier.desktop.guild_dm", workspace_id: workspaceId },
    }).catch(() => {}); // non-fatal if conversation already exists
  }, [activeConvId]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Load message history ──────────────────────────────────────────────────
  const loadHistory = useCallback(async () => {
    if (!activeConvId) return;
    try {
      const params = new URLSearchParams({ conversation_id: activeConvId, limit: "50" });
      const data = await apiCall(`/v1/guild/messages/history?${params}`, "GET", null);
      const rows = Array.isArray(data) ? data : [];
      // History comes back newest-first; reverse to chronological order
      setEnvelopes([...rows].reverse());
    } catch {
      // non-fatal
    }
  }, [activeConvId, apiCall]);

  useEffect(() => {
    setEnvelopes([]);
    setDecrypted({});
    if (activeConvId) loadHistory();
  }, [activeConvId, loadHistory]);

  // ── Auto-scroll ───────────────────────────────────────────────────────────
  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [envelopes, decrypted]);

  // ── SSE subscription ──────────────────────────────────────────────────────
  useEffect(() => {
    if (sseRef.current) { sseRef.current.close(); sseRef.current = null; }
    setSseStatus("disconnected");
    if (!activeConvId || !authToken) return;

    const url = `${apiBase}/v1/guild/conversations/${encodeURIComponent(activeConvId)}/events?token=${encodeURIComponent(authToken)}`;
    const es = new EventSource(url);
    sseRef.current = es;
    es.addEventListener("connected", () => setSseStatus("connected"));
    es.addEventListener("guild_message", () => loadHistory());
    es.onerror = () => setSseStatus("reconnecting");
    es.onopen = () => setSseStatus("connected");

    return () => { es.close(); sseRef.current = null; setSseStatus("disconnected"); };
  }, [activeConvId, authToken, apiBase, loadHistory]);

  // ── Decrypt all loaded messages ───────────────────────────────────────────
  const decryptAll = useCallback(async () => {
    if (!guildWandId || envelopes.length === 0) return;
    setDecryptStatus("decrypting");
    const templeSource = buildTempleEntropySourcePayload?.() ?? {};
    const theatreSource = buildTheatreEntropySourcePayload?.() ?? {};
    const results = await Promise.allSettled(
      envelopes.map((item) =>
        apiCall("/v1/guild/messages/decrypt", "POST", {
          envelope: item.envelope,
          wand_id: guildWandId,
          wand_passkey_ward: guildWandPasskeyWard || null,
          temple_entropy_digest: null,
          theatre_entropy_digest: null,
          attestation_media_digests: [],
          temple_entropy_source: templeSource,
          theatre_entropy_source: theatreSource,
          attestation_sources: [],
          metadata: { workspace_id: workspaceId, source: "atelier.desktop.guild_dm" },
        }).then((res) => ({ message_id: item.message_id, ...res }))
      ),
    );
    const map = {};
    for (const r of results) {
      if (r.status === "fulfilled" && r.value?.message_id) {
        map[r.value.message_id] = { plaintext: r.value.plaintext || "", verified: !!r.value.verified };
      }
    }
    setDecrypted(map);
    setDecryptStatus("idle");
  }, [envelopes, guildWandId, guildWandPasskeyWard, apiCall, buildTempleEntropySourcePayload, buildTheatreEntropySourcePayload, workspaceId]);

  // ── Send DM ───────────────────────────────────────────────────────────────
  const sendDM = useCallback(async () => {
    if (!draft.trim() || !activeConvId || !guildWandId) return;
    setSendStatus("sending");
    const recipientMemberId = recipient?.member_id || recipient?.artisan_id || "";
    const templeSource = buildTempleEntropySourcePayload?.() ?? {};
    const theatreSource = buildTheatreEntropySourcePayload?.() ?? {};
    try {
      const envelope = await apiCall("/v1/guild/messages/encrypt", "POST", {
        guild_id: guildId || "",
        channel_id: guildChannelId || "",
        sender_id: artisanId || "",
        wand_id: guildWandId,
        wand_passkey_ward: guildWandPasskeyWard || null,
        message_text: draft.trim(),
        conversation_id: activeConvId,
        conversation_kind: "member_dm",
        sender_member_id: activeProfileMemberId || null,
        recipient_member_id: recipientMemberId || null,
        temple_entropy_source: templeSource,
        theatre_entropy_source: theatreSource,
        attestation_media_digests: [],
        attestation_sources: [],
        security_session: {},
        metadata: {
          workspace_id: workspaceId,
          source: "atelier.desktop.guild_dm",
          sender_member_id: activeProfileMemberId,
          recipient_member_id: recipientMemberId,
        },
      });
      await apiCall("/v1/guild/messages/persist", "POST", {
        envelope,
        metadata: { workspace_id: workspaceId, source: "atelier.desktop.guild_dm" },
      });
      setDraft("");
      setSendStatus("idle");
      await loadHistory();
    } catch (err) {
      setSendStatus(`error: ${err.message}`);
    }
  }, [draft, activeConvId, guildWandId, guildWandPasskeyWard, guildId, guildChannelId, artisanId, activeProfileMemberId, recipient, buildTempleEntropySourcePayload, buildTheatreEntropySourcePayload, workspaceId, apiCall, loadHistory]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void sendDM(); }
  };

  return (
    <section className="panel">
      <h2>Guild DMs</h2>

      <div className="row">
        <span className="badge">{`My member ID: ${activeProfileMemberId || "unset"}`}</span>
        <span className="badge">{`Wand: ${guildWandId || "unset"}`}</span>
        <span className="badge">{`SSE: ${sseStatus}`}</span>
        <span className="badge">{`Conv: ${activeConvId || "none"}`}</span>
        <button className="action" onClick={loadProfiles}>Refresh Profiles</button>
      </div>

      <div style={{ display: "flex", gap: "1rem", marginTop: "0.5rem" }}>
        {/* Profile list */}
        <div style={{ minWidth: "200px", maxWidth: "240px" }}>
          <div style={{ fontWeight: "bold", marginBottom: "0.3rem", fontSize: "0.85em" }}>
            {`Artisans (${profilesStatus})`}
          </div>
          {profiles.filter((p) => (p.artisan_id || p.id) !== artisanId).map((p) => {
            const pid = p.artisan_id || p.id;
            const isActive = (recipient?.artisan_id || recipient?.id) === pid;
            return (
              <div
                key={pid}
                onClick={() => setRecipient(p)}
                style={{
                  padding: "0.3rem 0.5rem",
                  cursor: "pointer",
                  borderRadius: "4px",
                  marginBottom: "2px",
                  background: isActive ? "var(--accent, #444)" : "transparent",
                  fontSize: "0.85em",
                }}
              >
                <div style={{ fontWeight: isActive ? "bold" : "normal" }}>
                  {p.display_name || pid}
                </div>
                <div style={{ opacity: 0.6, fontSize: "0.75em" }}>
                  {p.guild_rank || "artisan"}{p.steward_approved ? " ✓" : ""}
                </div>
              </div>
            );
          })}
        </div>

        {/* Thread */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {!recipient && (
            <div style={{ opacity: 0.5, fontSize: "0.9em" }}>Select an artisan to open a DM thread.</div>
          )}
          {recipient && (
            <>
              <div className="row">
                <span style={{ fontWeight: "bold", fontSize: "0.9em" }}>
                  {`DM with ${recipient.display_name || recipient.artisan_id}`}
                </span>
                <button className="action" onClick={loadHistory}>Refresh</button>
                <button
                  className="action"
                  onClick={decryptAll}
                  disabled={envelopes.length === 0 || !guildWandId || decryptStatus === "decrypting"}
                >
                  {decryptStatus === "decrypting" ? "Decrypting…" : `Decrypt All (${envelopes.length})`}
                </button>
              </div>

              <div
                style={{
                  flex: 1,
                  minHeight: "200px",
                  maxHeight: "380px",
                  overflowY: "auto",
                  border: "1px solid var(--border, #333)",
                  borderRadius: "4px",
                  padding: "0.5rem",
                  fontSize: "0.85em",
                  display: "flex",
                  flexDirection: "column",
                  gap: "0.4rem",
                }}
              >
                {envelopes.length === 0 && <div style={{ opacity: 0.5 }}>No messages yet.</div>}
                {envelopes.map((item) => {
                  const env = item.envelope || {};
                  const isMine = (env.sender_id || env.sender_member_id) === artisanId
                    || env.sender_member_id === activeProfileMemberId;
                  const dec = decrypted[item.message_id];
                  return (
                    <div
                      key={item.message_id}
                      style={{
                        padding: "0.3rem 0.5rem",
                        borderRadius: "4px",
                        background: "var(--surface2, #2a2a2a)",
                        maxWidth: "80%",
                        alignSelf: isMine ? "flex-end" : "flex-start",
                      }}
                    >
                      <div style={{ opacity: 0.6, fontSize: "0.75em", marginBottom: "2px" }}>
                        {env.sender_member_id || env.sender_id || "?"} · {item.recorded_at?.slice(11, 16)}
                        {dec?.verified === true && " ✓"}
                        {dec?.verified === false && " ✗"}
                      </div>
                      {dec
                        ? <div>{dec.plaintext || <em style={{ opacity: 0.5 }}>(empty)</em>}</div>
                        : <div style={{ opacity: 0.4, fontStyle: "italic" }}>encrypted — click Decrypt All</div>
                      }
                    </div>
                  );
                })}
                <div ref={threadEndRef} />
              </div>

              <div className="row">
                <input
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={guildWandId ? "Type a message… (Enter to send)" : "Set wand ID in Guild Hall to send"}
                  disabled={!guildWandId}
                  style={{ flex: 1 }}
                />
                <button
                  className="action"
                  onClick={sendDM}
                  disabled={!draft.trim() || !guildWandId || sendStatus === "sending"}
                >
                  {sendStatus === "sending" ? "Sending…" : "Send"}
                </button>
              </div>
              {sendStatus.startsWith("error") && (
                <div style={{ color: "red", fontSize: "0.8em" }}>{sendStatus}</div>
              )}
            </>
          )}
        </div>
      </div>
    </section>
  );
}
