import { useCallback, useEffect, useRef, useState } from "react";

/**
 * ClientConversationsPanel
 *
 * Artisan-side view of client conversations. Fetches conversations, shows
 * message threads, sends encrypted messages, and receives live updates via SSE.
 *
 * Props:
 *   apiBase      — base URL of the atelier API
 *   authToken    — artisan JWT (from localStorage "atelier.auth_token")
 *   workspaceId  — current workspace id
 */
export function ClientConversationsPanel({ apiBase, authToken, workspaceId }) {
  const [conversations, setConversations] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [status, setStatus] = useState("idle");
  const [sendStatus, setSendStatus] = useState("idle");
  const [sseStatus, setSseStatus] = useState("disconnected");
  const sseRef = useRef(null);
  const messagesEndRef = useRef(null);

  const authHeaders = authToken ? { Authorization: `Bearer ${authToken}` } : {};

  // ── Fetch conversation list ───────────────────────────────────────────────
  const loadConversations = useCallback(async () => {
    if (!authToken) return;
    setStatus("loading");
    try {
      const qs = workspaceId ? `?workspace_id=${encodeURIComponent(workspaceId)}` : "";
      const res = await fetch(`${apiBase}/v1/client/conversations${qs}`, { headers: authHeaders });
      if (!res.ok) throw new Error(`${res.status}`);
      const data = await res.json();
      setConversations(Array.isArray(data) ? data : []);
      setStatus("idle");
    } catch (err) {
      setStatus(`error: ${err.message}`);
    }
  }, [apiBase, authToken, workspaceId]);

  useEffect(() => { loadConversations(); }, [loadConversations]);

  // ── Fetch messages for selected conversation ──────────────────────────────
  const loadMessages = useCallback(async (convId) => {
    if (!authToken || !convId) return;
    try {
      const res = await fetch(
        `${apiBase}/v1/client/conversations/${encodeURIComponent(convId)}/messages`,
        { headers: authHeaders },
      );
      if (!res.ok) throw new Error(`${res.status}`);
      const data = await res.json();
      setMessages(Array.isArray(data) ? data : []);
      // Opening a conversation marks messages read — refresh unread counts
      setConversations((prev) =>
        prev.map((c) => (c.id === convId ? { ...c, unread_count: 0 } : c)),
      );
    } catch {
      // non-fatal
    }
  }, [apiBase, authToken]);

  useEffect(() => {
    if (selectedId) loadMessages(selectedId);
    else setMessages([]);
  }, [selectedId, loadMessages]);

  // ── Auto-scroll to newest message ─────────────────────────────────────────
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── SSE subscription ──────────────────────────────────────────────────────
  useEffect(() => {
    if (sseRef.current) { sseRef.current.close(); sseRef.current = null; }
    setSseStatus("disconnected");
    if (!selectedId || !authToken) return;

    const url = `${apiBase}/v1/client/conversations/${encodeURIComponent(selectedId)}/events?token=${encodeURIComponent(authToken)}`;
    const es = new EventSource(url);
    sseRef.current = es;

    es.addEventListener("connected", () => setSseStatus("connected"));

    // New message arrived — re-fetch thread (server will decrypt and mark read)
    es.addEventListener("message", () => loadMessages(selectedId));

    // The other party read our messages — update read_at on sent messages locally
    es.addEventListener("read_receipt", (e) => {
      try {
        const payload = JSON.parse(e.data);
        const readAt = payload.read_at;
        if (!readAt) return;
        setMessages((prev) =>
          prev.map((msg) =>
            // Mark messages that were sent by us (not the client) and not yet read
            msg.sender_kind !== "client" && !msg.read_at
              ? { ...msg, read_at: readAt }
              : msg,
          ),
        );
      } catch {
        // malformed event — ignore
      }
    });

    es.onerror = () => setSseStatus("reconnecting");
    es.onopen = () => setSseStatus("connected");

    return () => { es.close(); sseRef.current = null; setSseStatus("disconnected"); };
  }, [selectedId, authToken, apiBase, loadMessages]);

  // ── Send message ──────────────────────────────────────────────────────────
  const sendMessage = useCallback(async () => {
    if (!draft.trim() || !selectedId || !authToken) return;
    setSendStatus("sending");
    try {
      const res = await fetch(
        `${apiBase}/v1/client/conversations/${encodeURIComponent(selectedId)}/messages`,
        {
          method: "POST",
          headers: { ...authHeaders, "Content-Type": "application/json" },
          body: JSON.stringify({ plaintext: draft.trim() }),
        },
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `${res.status}`);
      }
      setDraft("");
      setSendStatus("idle");
      await loadMessages(selectedId);
    } catch (err) {
      setSendStatus(`error: ${err.message}`);
    }
  }, [draft, selectedId, authToken, apiBase, authHeaders, loadMessages]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void sendMessage(); }
  };

  const selectedConv = conversations.find((c) => c.id === selectedId);
  const totalUnread = conversations.reduce((n, c) => n + (c.unread_count || 0), 0);

  return (
    <section className="panel">
      <h2>
        Client Conversations
        {totalUnread > 0 && (
          <span style={{
            marginLeft: "0.5rem",
            background: "var(--danger, #c0392b)",
            color: "#fff",
            borderRadius: "10px",
            padding: "0 0.45rem",
            fontSize: "0.65em",
            verticalAlign: "middle",
          }}>
            {totalUnread}
          </span>
        )}
      </h2>

      <div className="row">
        <button className="action" onClick={loadConversations}>Refresh List</button>
        <span className="badge">{`Status: ${status}`}</span>
        <span className="badge">{`SSE: ${sseStatus}`}</span>
        {selectedConv && (
          <>
            <span className="badge">{`Subject: ${selectedConv.subject || "(no subject)"}`}</span>
            <span className="badge">{`Guild: ${selectedConv.guild_id || "none"}`}</span>
            <span className="badge">{`Min rank: ${selectedConv.min_rank}`}</span>
            <span className="badge">{`Participants: ${selectedConv.participant_artisan_ids?.length ?? 0}`}</span>
          </>
        )}
      </div>

      <div style={{ display: "flex", gap: "1rem", marginTop: "0.5rem" }}>
        {/* Conversation list */}
        <div style={{ minWidth: "220px", maxWidth: "260px" }}>
          <div style={{ fontWeight: "bold", marginBottom: "0.3rem", fontSize: "0.85em" }}>Conversations</div>
          {conversations.length === 0 && <div style={{ fontSize: "0.8em", opacity: 0.6 }}>No conversations</div>}
          {conversations.map((conv) => {
            const unread = conv.unread_count || 0;
            return (
              <div
                key={conv.id}
                onClick={() => setSelectedId(conv.id)}
                style={{
                  padding: "0.3rem 0.5rem",
                  cursor: "pointer",
                  borderRadius: "4px",
                  marginBottom: "2px",
                  background: conv.id === selectedId ? "var(--accent, #444)" : "transparent",
                  fontSize: "0.85em",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                }}
              >
                <div>
                  <div style={{ fontWeight: unread > 0 || conv.id === selectedId ? "bold" : "normal" }}>
                    {conv.subject || "(no subject)"}
                  </div>
                  <div style={{ opacity: 0.6, fontSize: "0.8em" }}>
                    {conv.status} · {conv.updated_at?.slice(0, 16)}
                  </div>
                </div>
                {unread > 0 && (
                  <span style={{
                    background: "var(--danger, #c0392b)",
                    color: "#fff",
                    borderRadius: "10px",
                    padding: "0 0.4rem",
                    fontSize: "0.75em",
                    flexShrink: 0,
                  }}>
                    {unread}
                  </span>
                )}
              </div>
            );
          })}
        </div>

        {/* Message thread */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {!selectedId && (
            <div style={{ opacity: 0.5, fontSize: "0.9em" }}>Select a conversation to view messages.</div>
          )}
          {selectedId && (
            <>
              <div
                style={{
                  flex: 1,
                  minHeight: "200px",
                  maxHeight: "400px",
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
                {messages.length === 0 && <div style={{ opacity: 0.5 }}>No messages yet.</div>}
                {messages.map((msg) => {
                  const fromClient = msg.sender_kind === "client";
                  const isRead = !!msg.read_at;
                  return (
                    <div
                      key={msg.id}
                      style={{
                        padding: "0.3rem 0.5rem",
                        borderRadius: "4px",
                        background: "var(--surface2, #2a2a2a)",
                        maxWidth: "80%",
                        alignSelf: fromClient ? "flex-start" : "flex-end",
                      }}
                    >
                      <div style={{ opacity: 0.6, fontSize: "0.75em", marginBottom: "2px" }}>
                        {msg.sender_kind} · {msg.sent_at?.slice(11, 16)}
                        {/* Read receipt tick — only shown on messages we sent */}
                        {!fromClient && (
                          <span
                            title={isRead ? `Read ${msg.read_at?.slice(0, 16)}` : "Delivered"}
                            style={{ marginLeft: "0.3em", color: isRead ? "var(--accent-green, #2ecc71)" : "inherit" }}
                          >
                            {isRead ? "✓✓" : "✓"}
                          </span>
                        )}
                      </div>
                      <div>{msg.plaintext}</div>
                    </div>
                  );
                })}
                <div ref={messagesEndRef} />
              </div>

              <div className="row">
                <input
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Type a message… (Enter to send)"
                  style={{ flex: 1 }}
                />
                <button
                  className="action"
                  onClick={sendMessage}
                  disabled={!draft.trim() || sendStatus === "sending"}
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
