export function MessagesPanel(props) {
  const {
    messageDraft,
    setMessageDraft,
    encryptGuildMessage,
    decryptGuildMessage,
    profileName,
    profileEmail,
    activeProfileMemberId,
    guildWandStatus,
    guildId,
    guildChannelId,
    guildWandId,
    guildWandPasskeyWard,
    guildConversationId,
    guildConversationKind,
    guildConversationTitle,
    guildRecipientActorId,
    guildRecipientDistributionId,
    guildRecipientGuildId,
    guildPersistOutput,
    guildMessageHistory,
    guildDecryptOutput,
    messageLog,
  } = props;

  return (
    <section className="panel">
      <h2>Messages</h2>
      <p>Guild message drafting with wand, temple, and theatre derived envelope generation.</p>
      <div className="row">
        <input value={messageDraft} onChange={(e) => setMessageDraft(e.target.value)} placeholder="message text" />
        <button className="action" onClick={encryptGuildMessage} disabled={guildWandStatus?.revoked === true}>Encrypt via Guild Hall</button>
        <button className="action" onClick={decryptGuildMessage}>Decrypt Current Envelope</button>
      </div>
      <div className="row">
        <span className="badge">{`Profile: ${profileName || "Artisan"}`}</span>
        <span className="badge">{`Email: ${profileEmail || "unset"}`}</span>
        <span className="badge">{`Member: ${activeProfileMemberId || "unset"}`}</span>
        <span className="badge">{`Guild: ${guildId}`}</span>
        <span className="badge">{`Channel: ${guildChannelId}`}</span>
        <span className="badge">{`Conversation: ${guildConversationId || "none"}`}</span>
        <span className="badge">{`Mode: ${guildConversationKind || "guild_channel"}`}</span>
        <span className="badge">{`Title: ${guildConversationTitle || "untitled"}`}</span>
        <span className="badge">{`Wand: ${guildWandId}`}</span>
        <span className="badge">{`Passkey ward: ${guildWandPasskeyWard ? "set" : "unset"}`}</span>
        <span className="badge">{`Revocation: ${guildWandStatus?.revoked ? "blocked" : "clear"}`}</span>
        <span className="badge">{`Status: ${String(guildWandStatus?.status || "unknown")}`}</span>
        <span className="badge">{`Remote: ${guildRecipientDistributionId || "none"} / ${guildRecipientGuildId || "none"} / ${guildRecipientActorId || "none"}`}</span>
        <span className="badge">{`Relay: ${String(guildPersistOutput?.relay_status || guildMessageHistory?.[0]?.metadata?.relay_status || "unknown")}`}</span>
      </div>
      <pre>{JSON.stringify(guildDecryptOutput || {}, null, 2)}</pre>
      <pre>{JSON.stringify(guildMessageHistory || [], null, 2)}</pre>
      <pre>{JSON.stringify(messageLog, null, 2)}</pre>
    </section>
  );
}
