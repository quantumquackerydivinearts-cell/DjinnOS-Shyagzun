export function GuildHallPanel(props) {
  const {
    listLessons,
    listModules,
    guildId,
    setGuildId,
    profileName,
    guildDistributionId,
    setGuildDistributionId,
    guildRecipientDistributionId,
    setGuildRecipientDistributionId,
    guildRecipientGuildId,
    guildRecipientChannelId,
    guildRecipientActorId,
    setGuildRecipientGuildId,
    setGuildRecipientChannelId,
    setGuildRecipientActorId,
    guildWandId,
    setGuildWandId,
    guildSelectedRegistryWandId,
    setGuildSelectedRegistryWandId,
    guildWandPasskeyWard,
    setGuildWandPasskeyWard,
    guildWandStatus,
    guildPersistOutput,
    guildMessageHistory,
    distributionHandshakeList,
    guildDisplayName,
    setGuildDisplayName,
    registerGuildRegistryEntry,
    loadGuildRegistryEntry,
    loadGuildRegistryList,
    guildRegistryList,
    distributionId,
    setDistributionId,
    distributionDisplayName,
    setDistributionDisplayName,
    distributionBaseUrl,
    setDistributionBaseUrl,
    distributionTransportKind,
    setDistributionTransportKind,
    distributionPublicKeyRef,
    setDistributionPublicKeyRef,
    distributionProtocolFamily,
    setDistributionProtocolFamily,
    distributionProtocolVersion,
    setDistributionProtocolVersion,
    distributionSupportedProtocolVersionsText,
    setDistributionSupportedProtocolVersionsText,
    distributionGuildIdsText,
    setDistributionGuildIdsText,
    distributionMetadataText,
    setDistributionMetadataText,
    registerDistributionRegistryEntry,
    loadDistributionRegistryEntry,
    loadDistributionRegistryList,
    distributionRegistryList,
    distributionHandshakeLocalId,
    setDistributionHandshakeLocalId,
    distributionHandshakeMode,
    setDistributionHandshakeMode,
    distributionHandshakeProtocolFamily,
    setDistributionHandshakeProtocolFamily,
    distributionHandshakeLocalProtocolVersion,
    setDistributionHandshakeLocalProtocolVersion,
    distributionHandshakeRemoteProtocolVersion,
    setDistributionHandshakeRemoteProtocolVersion,
    distributionHandshakeNegotiatedProtocolVersion,
    setDistributionHandshakeNegotiatedProtocolVersion,
    registerDistributionHandshake,
    loadDistributionCapabilities,
    loadDistributionHandshakes,
    loadMigrationStatus,
    loadServiceReadiness,
    loadFederationHealth,
    adminVerified,
    role,
    wandRegistryWandId,
    setWandRegistryWandId,
    wandRegistryMakerId,
    setWandRegistryMakerId,
    wandRegistryMakerDate,
    setWandRegistryMakerDate,
    wandRegistryAtelierOrigin,
    setWandRegistryAtelierOrigin,
    wandRegistryStructuralFingerprint,
    setWandRegistryStructuralFingerprint,
    wandRegistryCraftRecordHash,
    setWandRegistryCraftRecordHash,
    registerWandRegistryEntry,
    wandRegistryMinimumReady,
    loadWandRegistryEntry,
    loadWandRegistryList,
    wandRegistryList,
    wandRegistryMaterialProfileText,
    setWandRegistryMaterialProfileText,
    wandRegistryDimensionsText,
    setWandRegistryDimensionsText,
    wandRegistryOwnershipChainText,
    setWandRegistryOwnershipChainText,
    wandRegistryMetadataText,
    setWandRegistryMetadataText,
    guildChannelId,
    setGuildChannelId,
    guildThreadId,
    setGuildThreadId,
    guildSenderId,
    setGuildSenderId,
    guildConversationId,
    setGuildConversationId,
    guildConversationKind,
    setGuildConversationKind,
    guildConversationTitle,
    setGuildConversationTitle,
    guildParticipantMemberIdsText,
    setGuildParticipantMemberIdsText,
    guildParticipantGuildIdsText,
    setGuildParticipantGuildIdsText,
    guildSecuritySessionText,
    setGuildSecuritySessionText,
    guildSessionMode,
    setGuildSessionMode,
    guildSessionSenderIdentityKeyRef,
    setGuildSessionSenderIdentityKeyRef,
    guildSessionSenderSignedPreKeyRef,
    setGuildSessionSenderSignedPreKeyRef,
    guildSessionSenderOneTimePreKeyRef,
    setGuildSessionSenderOneTimePreKeyRef,
    guildSessionRecipientIdentityKeyRef,
    setGuildSessionRecipientIdentityKeyRef,
    guildSessionRecipientSignedPreKeyRef,
    setGuildSessionRecipientSignedPreKeyRef,
    guildSessionRecipientOneTimePreKeyRef,
    setGuildSessionRecipientOneTimePreKeyRef,
    guildSessionEpoch,
    setGuildSessionEpoch,
    guildSessionSealedSender,
    setGuildSessionSealedSender,
    guildConversationList,
    guildConversationOutput,
    registerGuildConversation,
    loadGuildConversation,
    loadGuildConversationList,
    runAction,
    applyRegisteredWandSelection,
    loadGuildWandStatus,
    distributionCapabilitiesOutput,
    guildProtocolStatus,
    guildTempleEntropyDigest,
    setGuildTempleEntropyDigest,
    guildTheatreEntropyDigest,
    setGuildTheatreEntropyDigest,
    guildTempleProvenanceId,
    setGuildTempleProvenanceId,
    guildTempleSourceType,
    setGuildTempleSourceType,
    guildTempleGardenId,
    setGuildTempleGardenId,
    guildTemplePlotId,
    setGuildTemplePlotId,
    guildTheatreProvenanceId,
    setGuildTheatreProvenanceId,
    guildTheatreSourceType,
    setGuildTheatreSourceType,
    guildTheatrePerformanceId,
    setGuildTheatrePerformanceId,
    guildTheatreUploadId,
    setGuildTheatreUploadId,
    guildTempleProvenanceHistory,
    guildTheatreProvenanceHistory,
    fillTempleEntropySourcePreset,
    fillTheatreEntropySourcePreset,
    guildAttestationDigestsText,
    setGuildAttestationDigestsText,
    guildAttestationSourcesText,
    setGuildAttestationSourcesText,
    deriveGuildEntropyMix,
    updateGuildMessageRelayStatus,
    loadGuildMessageHistory,
    guildRelayStatus,
    setGuildRelayStatus,
    guildRelayReceiptText,
    setGuildRelayReceiptText,
    guildRegistryOutput,
    distributionRegistryOutput,
    distributionHandshakeOutput,
    migrationStatus,
    serviceReadinessOutput,
    federationHealthOutput,
    wandRegistryOutput,
    guildEntropyMixOutput,
    guildEncryptOutput,
    buildTempleEntropySourcePayload,
    buildTheatreEntropySourcePayload,
  } = props;

  const readiness = serviceReadinessOutput && typeof serviceReadinessOutput === "object" ? serviceReadinessOutput : {};
  const readinessStatus = String(readiness.status || "unknown");
  const readinessBadgeClass =
    readinessStatus === "ready" ? "badge-ok" : readinessStatus === "not_ready" ? "badge-warn" : readinessStatus === "error" ? "badge-error" : "";
  const federation = federationHealthOutput && typeof federationHealthOutput === "object" ? federationHealthOutput : {};
  const federationStatus = String(federation.status || "unknown");
  const federationBadgeClass =
    federationStatus === "ok" ? "badge-ok" : federationStatus === "degraded" ? "badge-warn" : federationStatus === "error" ? "badge-error" : "";
  const currentFederationTarget = Array.isArray(federation.targets) && federation.targets.length > 0 ? federation.targets[0] : null;
  const currentFederationTrust = String(currentFederationTarget?.trust_grade || "unknown");
  const currentFederationTrustClass =
    currentFederationTrust === "active"
      ? "badge-ok"
      : currentFederationTrust === "unreachable" || currentFederationTrust === "untrusted"
        ? "badge-error"
        : currentFederationTrust === "key_known" || currentFederationTrust === "key_only"
          ? "badge-warn"
          : "";

  return (
    <section className="panel guild-hall-shell">
      <h2>Guild Hall</h2>
      <p>Guild administration and message encryption derivation inputs.</p>
      <div className="row">
        <button className="action" onClick={listLessons}>Refresh Lessons</button>
        <button className="action" onClick={listModules}>Refresh Modules</button>
      </div>
      <div className="guild-summary-strip">
        <span className="badge">{`Guild: ${guildId || "unset"}`}</span>
        <span className="badge">{`Profile: ${profileName || "Artisan"}`}</span>
        <span className="badge">{`Home distribution: ${guildDistributionId || "unset"}`}</span>
        <span className="badge">{`Remote target: ${guildRecipientDistributionId || "local"} / ${guildRecipientGuildId || "none"}`}</span>
        <span className="badge">{`Wand: ${guildWandId || "unset"}`}</span>
        <span className="badge">{`Registry wand: ${guildSelectedRegistryWandId || "unset"}`}</span>
        <span className="badge">{`Passkey ward: ${guildWandPasskeyWard ? "set" : "unset"}`}</span>
        <span className="badge">{`Conversation: ${guildConversationId || "unset"}`}</span>
        <span className="badge">{`Mode: ${guildConversationKind || "guild_channel"}`}</span>
        <span className="badge">{`Wand status: ${String(guildWandStatus?.status || "unknown")}`}</span>
        <span className="badge">{`Revoked: ${guildWandStatus?.revoked ? "yes" : "no"}`}</span>
        <span className="badge">{`Relay: ${String(guildPersistOutput?.relay_status || guildMessageHistory?.[0]?.metadata?.relay_status || "idle")}`}</span>
        <span className="badge">{`Handshakes: ${distributionHandshakeList.length}`}</span>
        <span className={`badge ${guildProtocolStatus?.level === "ok" ? "badge-ok" : guildProtocolStatus?.level === "error" ? "badge-error" : guildProtocolStatus?.level === "warning" ? "badge-warn" : ""}`}>{`${guildProtocolStatus?.label || "Protocol Unknown"}`}</span>
        <span className={`badge ${readinessBadgeClass}`}>{`Ready: ${readinessStatus}`}</span>
        <span className={`badge ${String(readiness?.database?.status || "") === "up" ? "badge-ok" : String(readiness?.database?.status || "") === "down" ? "badge-error" : ""}`}>{`DB: ${String(readiness?.database?.status || "unknown")}`}</span>
        <span className={`badge ${String(readiness?.kernel?.status || "") === "up" ? "badge-ok" : String(readiness?.kernel?.status || "") === "down" ? "badge-error" : ""}`}>{`Kernel: ${String(readiness?.kernel?.status || "unknown")}`}</span>
        <span className={`badge ${federationBadgeClass}`}>{`Federation: ${federationStatus}`}</span>
        <span className={`badge ${currentFederationTrustClass}`}>{`Trust: ${currentFederationTrust}`}</span>
      </div>

      <div className="guild-hall-grid">
        <section className="panel guild-subpanel">
          <h3>Identity</h3>
          <p className="guild-subcopy">Register the local guild and the distributions it can speak to.</p>
          <div className="guild-subgroup">
            <h4>Guild Registry</h4>
            <div className="row">
              <input value={guildId} onChange={(e) => setGuildId(e.target.value)} placeholder="guild id" />
              <input value={guildDisplayName} onChange={(e) => setGuildDisplayName(e.target.value)} placeholder="guild display name" />
              <input value={guildDistributionId} onChange={(e) => setGuildDistributionId(e.target.value)} placeholder="distribution id" />
            </div>
            <div className="row">
              <button className="action" onClick={registerGuildRegistryEntry}>Register Guild</button>
              <button className="action" onClick={() => loadGuildRegistryEntry()}>Load Guild</button>
              <button className="action" onClick={loadGuildRegistryList}>Load Guild Registry</button>
            </div>
            <div className="row">
              <select value={guildId} onChange={(e) => setGuildId(e.target.value)}>
                <option value="">select registered guild</option>
                {guildRegistryList.map((item) => (
                  <option key={`guild-reg-${String(item?.guild_id || "")}`} value={String(item?.guild_id || "")}>
                    {`${String(item?.guild_id || "")} :: ${String(item?.display_name || "")}`}
                  </option>
                ))}
              </select>
              <span className="badge">{`Guild registry count: ${guildRegistryList.length}`}</span>
            </div>
          </div>
          <div className="guild-subgroup">
            <h4>Distribution Registry</h4>
            <div className="row">
              <input value={distributionId} onChange={(e) => setDistributionId(e.target.value)} placeholder="distribution id" />
              <input value={distributionDisplayName} onChange={(e) => setDistributionDisplayName(e.target.value)} placeholder="distribution display name" />
              <input value={distributionBaseUrl} onChange={(e) => setDistributionBaseUrl(e.target.value)} placeholder="base url" />
            </div>
            <div className="row">
              <input value={distributionTransportKind} onChange={(e) => setDistributionTransportKind(e.target.value)} placeholder="transport kind" />
              <input value={distributionPublicKeyRef} onChange={(e) => setDistributionPublicKeyRef(e.target.value)} placeholder="public key ref" />
              <input value={distributionProtocolFamily} onChange={(e) => setDistributionProtocolFamily(e.target.value)} placeholder="protocol family" />
              <input value={distributionProtocolVersion} onChange={(e) => setDistributionProtocolVersion(e.target.value)} placeholder="protocol version" />
            </div>
            <div className="row">
              <textarea value={distributionSupportedProtocolVersionsText} onChange={(e) => setDistributionSupportedProtocolVersionsText(e.target.value)} placeholder="supported protocol versions JSON array" rows={4} />
              <textarea value={distributionGuildIdsText} onChange={(e) => setDistributionGuildIdsText(e.target.value)} placeholder="guild ids JSON array" rows={4} />
              <textarea value={distributionMetadataText} onChange={(e) => setDistributionMetadataText(e.target.value)} placeholder="distribution metadata JSON" rows={4} />
            </div>
            <div className="row">
              <button className="action" onClick={registerDistributionRegistryEntry}>Register Distribution</button>
              <button className="action" onClick={() => loadDistributionRegistryEntry()}>Load Distribution</button>
              <button className="action" onClick={loadDistributionRegistryList}>Load Distribution Registry</button>
            </div>
            <div className="row">
              <select value={distributionId} onChange={(e) => setDistributionId(e.target.value)}>
                <option value="">select registered distribution</option>
                {distributionRegistryList.map((item) => (
                  <option key={`distribution-reg-${String(item?.distribution_id || "")}`} value={String(item?.distribution_id || "")}>
                    {`${String(item?.distribution_id || "")} :: ${String(item?.display_name || "")}`}
                  </option>
                ))}
              </select>
              <button className="action" onClick={() => {
                const next = String(distributionId || "").trim();
                if (next) {
                  setGuildRecipientDistributionId(next);
                }
              }}>Use As Recipient Target</button>
              <span className="badge">{`Distribution registry count: ${distributionRegistryList.length}`}</span>
            </div>
          </div>
        </section>

        <section className="panel guild-subpanel">
          <h3>Trust Fabric</h3>
          <p className="guild-subcopy">Manage the artifact and handshake state that gates secure relay.</p>
          <div className="guild-subgroup">
            <h4>Distribution Handshake</h4>
            <div className="row">
              <input value={distributionHandshakeLocalId} onChange={(e) => setDistributionHandshakeLocalId(e.target.value)} placeholder="local distribution id" />
              <input value={distributionHandshakeMode} onChange={(e) => setDistributionHandshakeMode(e.target.value)} placeholder="handshake mode" />
              <input value={distributionHandshakeProtocolFamily} onChange={(e) => setDistributionHandshakeProtocolFamily(e.target.value)} placeholder="protocol family" />
              <input value={distributionHandshakeLocalProtocolVersion} onChange={(e) => setDistributionHandshakeLocalProtocolVersion(e.target.value)} placeholder="local protocol version" />
            </div>
            <div className="row">
              <input value={distributionHandshakeRemoteProtocolVersion} onChange={(e) => setDistributionHandshakeRemoteProtocolVersion(e.target.value)} placeholder="remote protocol version" />
              <input value={distributionHandshakeNegotiatedProtocolVersion} onChange={(e) => setDistributionHandshakeNegotiatedProtocolVersion(e.target.value)} placeholder="negotiated protocol version" />
            </div>
            <div className="row">
              <button className="action" onClick={registerDistributionHandshake}>Register Handshake</button>
              <button className="action" onClick={() => loadDistributionCapabilities()}>Load Capabilities</button>
              <button className="action" onClick={() => loadDistributionHandshakes()}>Load Handshakes</button>
              <button className="action" onClick={loadServiceReadiness}>Load Readiness</button>
              <button className="action" onClick={() => loadFederationHealth()}>Load Federation Health</button>
              <button className="action" onClick={loadMigrationStatus} disabled={!adminVerified || role !== "steward"}>Load Migration Status</button>
            </div>
            <div className="row">
              <span className={`badge ${guildProtocolStatus?.level === "ok" ? "badge-ok" : guildProtocolStatus?.level === "error" ? "badge-error" : guildProtocolStatus?.level === "warning" ? "badge-warn" : ""}`}>{guildProtocolStatus?.label || "Protocol Unknown"}</span>
              <span className="badge">{guildProtocolStatus?.detail || "Load remote capabilities to assess protocol compatibility."}</span>
            </div>
            <div className="row">
              <span className={`badge ${readinessBadgeClass}`}>{`Service readiness: ${readinessStatus}`}</span>
              <span className={`badge ${String(readiness?.migrations?.status || "") === "up" ? "badge-ok" : String(readiness?.migrations?.status || "") === "down" ? "badge-error" : ""}`}>{`Migrations: ${String(readiness?.migrations?.status || "unknown")}`}</span>
              <span className={`badge ${String(readiness?.config?.status || "") === "up" ? "badge-ok" : String(readiness?.config?.status || "") === "warning" ? "badge-warn" : ""}`}>{`Config: ${String(readiness?.config?.status || "unknown")}`}</span>
            </div>
            <div className="row">
              <span className={`badge ${federationBadgeClass}`}>{`Federation health: ${federationStatus}`}</span>
              <span className="badge">{`Targets: ${Number(federation?.target_count || 0)}`}</span>
              <span className="badge">{`Active trust: ${Number(federation?.active_trust_count || 0)}`}</span>
              <span className={`badge ${currentFederationTrustClass}`}>{`Current trust: ${currentFederationTrust}`}</span>
            </div>
            {(readinessStatus === "error" || federationStatus === "error") ? (
              <div className="row">
                <span className="badge badge-error">
                  {`Probe detail: ${String(readiness?.category || federation?.category || "request_failed")}`}
                </span>
                <span className="badge">
                  {String(readiness?.detail || federation?.detail || "See diagnostics for full payload.")}
                </span>
              </div>
            ) : null}
          </div>
          <div className="guild-subgroup">
            <h4>Wand Registry</h4>
            <div className="row">
              <input value={wandRegistryWandId} onChange={(e) => setWandRegistryWandId(e.target.value)} placeholder="wand id" />
              <input value={wandRegistryMakerId} onChange={(e) => setWandRegistryMakerId(e.target.value)} placeholder="maker id" />
              <input value={wandRegistryMakerDate} onChange={(e) => setWandRegistryMakerDate(e.target.value)} placeholder="maker date" />
              <input value={wandRegistryAtelierOrigin} onChange={(e) => setWandRegistryAtelierOrigin(e.target.value)} placeholder="atelier origin" />
            </div>
            <div className="row">
              <input value={wandRegistryStructuralFingerprint} onChange={(e) => setWandRegistryStructuralFingerprint(e.target.value)} placeholder="structural fingerprint" />
              <input value={wandRegistryCraftRecordHash} onChange={(e) => setWandRegistryCraftRecordHash(e.target.value)} placeholder="craft record hash" />
            </div>
            <div className="row">
              <button className="action" onClick={registerWandRegistryEntry} disabled={!wandRegistryMinimumReady}>Register Wand</button>
              <button className="action" onClick={() => loadWandRegistryEntry()}>Load Wand</button>
              <button className="action" onClick={loadWandRegistryList}>Load Registry</button>
            </div>
            <div className="row">
              <span className="badge">{wandRegistryMinimumReady ? "Registry minimum met" : "Register Wand requires wand id + maker id"}</span>
              <span className="badge">Optional: maker date, dimensions, material profile</span>
              <span className="badge">{`Registry count: ${wandRegistryList.length}`}</span>
            </div>
            <div className="row">
              <textarea value={wandRegistryMaterialProfileText} onChange={(e) => setWandRegistryMaterialProfileText(e.target.value)} placeholder="material profile JSON" rows={4} />
              <textarea value={wandRegistryDimensionsText} onChange={(e) => setWandRegistryDimensionsText(e.target.value)} placeholder="dimensions JSON" rows={4} />
            </div>
            <div className="row">
              <textarea value={wandRegistryOwnershipChainText} onChange={(e) => setWandRegistryOwnershipChainText(e.target.value)} placeholder="ownership chain JSON array" rows={4} />
              <textarea value={wandRegistryMetadataText} onChange={(e) => setWandRegistryMetadataText(e.target.value)} placeholder="wand metadata JSON" rows={4} />
            </div>
            <div className="row">
              <select value={wandRegistryWandId} onChange={(e) => setWandRegistryWandId(e.target.value)}>
                <option value="">select registered wand</option>
                {wandRegistryList.map((item) => (
                  <option key={`wand-reg-${String(item?.wand_id || "")}`} value={String(item?.wand_id || "")}>
                    {`${String(item?.wand_id || "")} :: ${String(item?.maker_id || "")}`}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </section>

        <section className="panel guild-subpanel panel-wide">
          <h3>Delivery Pass</h3>
          <p className="guild-subcopy">Set sender, artifact, remote target, entropy provenance, then derive and relay.</p>
          <div className="guild-subgroup">
            <h4>Conversation</h4>
            <div className="row">
              <input value={guildConversationId} onChange={(e) => setGuildConversationId(e.target.value)} placeholder="conversation id" />
              <select value={guildConversationKind} onChange={(e) => setGuildConversationKind(e.target.value)}>
                <option value="guild_channel">guild channel</option>
                <option value="member_dm">member direct message</option>
                <option value="guild_federated">federated guild thread</option>
              </select>
              <input value={guildConversationTitle} onChange={(e) => setGuildConversationTitle(e.target.value)} placeholder="conversation title" />
            </div>
            <div className="row">
              <select value={guildConversationId} onChange={(e) => setGuildConversationId(e.target.value)}>
                <option value="">select known conversation</option>
                {guildConversationList.map((item) => (
                  <option key={`guild-conversation-${String(item?.conversation_id || "")}`} value={String(item?.conversation_id || "")}>
                    {`${String(item?.conversation_id || "")} :: ${String(item?.title || item?.conversation_kind || "")}`}
                  </option>
                ))}
              </select>
              <button className="action" onClick={registerGuildConversation}>Register Conversation</button>
              <button className="action" onClick={() => loadGuildConversation()}>Load Conversation</button>
              <button className="action" onClick={loadGuildConversationList}>Load Conversations</button>
              <span className="badge">{`Conversations: ${guildConversationList.length}`}</span>
            </div>
            <div className="row">
              <textarea value={guildParticipantMemberIdsText} onChange={(e) => setGuildParticipantMemberIdsText(e.target.value)} placeholder="participant member ids JSON array" rows={4} />
              <textarea value={guildParticipantGuildIdsText} onChange={(e) => setGuildParticipantGuildIdsText(e.target.value)} placeholder="participant guild ids JSON array" rows={4} />
            </div>
            <div className="row">
              <select value={guildSessionMode} onChange={(e) => setGuildSessionMode(e.target.value)}>
                <option value="double_ratchet_like">double ratchet like</option>
                <option value="sealed_sender_channel">sealed sender channel</option>
                <option value="guild_channel_state">guild channel state</option>
              </select>
              <input value={guildSessionSenderIdentityKeyRef} onChange={(e) => setGuildSessionSenderIdentityKeyRef(e.target.value)} placeholder="sender identity key ref" />
              <input value={guildSessionRecipientIdentityKeyRef} onChange={(e) => setGuildSessionRecipientIdentityKeyRef(e.target.value)} placeholder="recipient identity key ref" />
              <input value={guildSessionEpoch} onChange={(e) => setGuildSessionEpoch(e.target.value)} placeholder="session epoch" />
            </div>
            <div className="row">
              <input value={guildSessionSenderSignedPreKeyRef} onChange={(e) => setGuildSessionSenderSignedPreKeyRef(e.target.value)} placeholder="sender signed pre-key ref" />
              <input value={guildSessionSenderOneTimePreKeyRef} onChange={(e) => setGuildSessionSenderOneTimePreKeyRef(e.target.value)} placeholder="sender one-time pre-key ref" />
              <input value={guildSessionRecipientSignedPreKeyRef} onChange={(e) => setGuildSessionRecipientSignedPreKeyRef(e.target.value)} placeholder="recipient signed pre-key ref" />
              <input value={guildSessionRecipientOneTimePreKeyRef} onChange={(e) => setGuildSessionRecipientOneTimePreKeyRef(e.target.value)} placeholder="recipient one-time pre-key ref" />
            </div>
            <div className="row">
              <label className="checkbox">
                <input type="checkbox" checked={guildSessionSealedSender} onChange={(e) => setGuildSessionSealedSender(e.target.checked)} />
                sealed sender
              </label>
            </div>
            <div className="row">
              <textarea value={guildSecuritySessionText} onChange={(e) => setGuildSecuritySessionText(e.target.value)} placeholder="security session JSON" rows={4} />
            </div>
          </div>
          <div className="guild-subgroup">
            <h4>Thread and Sender</h4>
            <div className="row">
              <input value={guildChannelId} onChange={(e) => setGuildChannelId(e.target.value)} placeholder="channel id" />
              <input value={guildThreadId} onChange={(e) => setGuildThreadId(e.target.value)} placeholder="thread id" />
              <input value={guildSenderId} onChange={(e) => setGuildSenderId(e.target.value)} placeholder="sender id" />
            </div>
            <div className="row">
              <input value={guildWandId} onChange={(e) => setGuildWandId(e.target.value)} placeholder="wand id" />
              <select value={guildSelectedRegistryWandId} onChange={(e) => setGuildSelectedRegistryWandId(e.target.value)}>
                <option value="">select registered wand</option>
                {wandRegistryList.map((item) => (
                  <option key={`guild-wand-${String(item?.wand_id || "")}`} value={String(item?.wand_id || "")}>
                    {`${String(item?.wand_id || "")} :: ${String(item?.maker_id || "")}`}
                  </option>
                ))}
              </select>
              <button className="action" onClick={() => runAction("guild_use_registered_wand", () => applyRegisteredWandSelection(guildSelectedRegistryWandId, { target: "guild", loadEntry: true }))}>Use Registry Wand</button>
              <button className="action" onClick={loadGuildWandStatus}>Load Wand Status</button>
            </div>
            <div className="row">
              <input
                type="password"
                value={guildWandPasskeyWard}
                onChange={(e) => setGuildWandPasskeyWard(e.target.value)}
                placeholder="bearer-only passkey ward"
                autoComplete="off"
              />
              <span className="badge">Not persisted into registry</span>
              <span className="badge">Mixed into live message derivation only</span>
            </div>
          </div>
          <div className="guild-subgroup">
            <h4>Remote Target</h4>
            <div className="row">
              <select value={guildRecipientDistributionId} onChange={(e) => setGuildRecipientDistributionId(e.target.value)}>
                <option value="">select recipient distribution</option>
                {distributionRegistryList.map((item) => (
                  <option key={`guild-recipient-distribution-${String(item?.distribution_id || "")}`} value={String(item?.distribution_id || "")}>
                    {`${String(item?.distribution_id || "")} :: ${String(item?.display_name || "")}`}
                  </option>
                ))}
              </select>
              <select value={guildRecipientGuildId} onChange={(e) => setGuildRecipientGuildId(e.target.value)}>
                <option value="">select recipient guild</option>
                {(Array.isArray(distributionCapabilitiesOutput?.guilds) ? distributionCapabilitiesOutput.guilds : guildRegistryList).map((item) => (
                  <option key={`guild-recipient-guild-${String(item?.guild_id || "")}`} value={String(item?.guild_id || "")}>
                    {`${String(item?.guild_id || "")} :: ${String(item?.display_name || "")}`}
                  </option>
                ))}
              </select>
              <select value={guildRecipientChannelId} onChange={(e) => setGuildRecipientChannelId(e.target.value)}>
                <option value="">select recipient channel</option>
                {(() => {
                  const guilds = Array.isArray(distributionCapabilitiesOutput?.guilds) ? distributionCapabilitiesOutput.guilds : [];
                  const selectedGuild = guilds.find((item) => String(item?.guild_id || "") === String(guildRecipientGuildId || "").trim());
                  const channels = Array.isArray(selectedGuild?.channels) ? selectedGuild.channels : [];
                  return channels.map((item) => (
                    <option key={`guild-recipient-channel-${String(item || "")}`} value={String(item || "")}>
                      {String(item || "")}
                    </option>
                  ));
                })()}
              </select>
              <input value={guildRecipientActorId} onChange={(e) => setGuildRecipientActorId(e.target.value)} placeholder="recipient actor id" />
            </div>
          </div>
          <div className="guild-subgroup">
            <h4>Entropy Provenance</h4>
            <div className="row">
              <input value={guildTempleEntropyDigest} onChange={(e) => setGuildTempleEntropyDigest(e.target.value)} placeholder="temple entropy digest" />
              <input value={guildTheatreEntropyDigest} onChange={(e) => setGuildTheatreEntropyDigest(e.target.value)} placeholder="theatre entropy digest" />
            </div>
            <div className="row">
              <input value={guildTempleProvenanceId} onChange={(e) => setGuildTempleProvenanceId(e.target.value)} placeholder="temple provenance id" />
              <input value={guildTempleSourceType} onChange={(e) => setGuildTempleSourceType(e.target.value)} placeholder="temple source type" />
              <input value={guildTempleGardenId} onChange={(e) => setGuildTempleGardenId(e.target.value)} placeholder="garden id" />
              <input value={guildTemplePlotId} onChange={(e) => setGuildTemplePlotId(e.target.value)} placeholder="plot id" />
            </div>
            <div className="row">
              <input value={guildTheatreProvenanceId} onChange={(e) => setGuildTheatreProvenanceId(e.target.value)} placeholder="theatre provenance id" />
              <input value={guildTheatreSourceType} onChange={(e) => setGuildTheatreSourceType(e.target.value)} placeholder="theatre source type" />
              <input value={guildTheatrePerformanceId} onChange={(e) => setGuildTheatrePerformanceId(e.target.value)} placeholder="performance id" />
              <input value={guildTheatreUploadId} onChange={(e) => setGuildTheatreUploadId(e.target.value)} placeholder="upload id" />
            </div>
            <div className="row">
              <select value={guildTempleProvenanceId} onChange={(e) => setGuildTempleProvenanceId(e.target.value)}>
                <option value="">select temple provenance history</option>
                {guildTempleProvenanceHistory.map((item) => (
                  <option key={`temple-prov-${item}`} value={item}>{item}</option>
                ))}
              </select>
              <select value={guildTheatreProvenanceId} onChange={(e) => setGuildTheatreProvenanceId(e.target.value)}>
                <option value="">select theatre provenance history</option>
                {guildTheatreProvenanceHistory.map((item) => (
                  <option key={`theatre-prov-${item}`} value={item}>{item}</option>
                ))}
              </select>
              <button className="action" onClick={fillTempleEntropySourcePreset}>Temple Source Preset</button>
              <button className="action" onClick={fillTheatreEntropySourcePreset}>Theatre Source Preset</button>
            </div>
            <div className="row">
              <input value={guildAttestationDigestsText} onChange={(e) => setGuildAttestationDigestsText(e.target.value)} placeholder="attestation media digests, comma-separated" />
              <input value={guildAttestationSourcesText} onChange={(e) => setGuildAttestationSourcesText(e.target.value)} placeholder="attestation sources JSON array" />
            </div>
          </div>
          <div className="guild-subgroup">
            <h4>Relay Controls</h4>
            <div className="row">
              <button className="action" onClick={deriveGuildEntropyMix}>Derive Entropy Mix</button>
              <button className="action" onClick={updateGuildMessageRelayStatus}>Update Relay Status</button>
              <button className="action" onClick={loadGuildMessageHistory}>Load Message History</button>
            </div>
            <div className="row">
              <input value={guildRelayStatus} onChange={(e) => setGuildRelayStatus(e.target.value)} placeholder="relay status" />
              <textarea value={guildRelayReceiptText} onChange={(e) => setGuildRelayReceiptText(e.target.value)} placeholder="relay receipt JSON" rows={3} />
            </div>
          </div>
        </section>

        <section className="panel guild-subpanel panel-wide">
          <h3>Diagnostics</h3>
          <p className="guild-subcopy">Keep raw payloads available, but out of the main workflow.</p>
          <details className="guild-diagnostic">
            <summary>Conversation State</summary>
            <pre>{JSON.stringify(guildConversationOutput || {}, null, 2)}</pre>
            <pre>{JSON.stringify(guildConversationList || [], null, 2)}</pre>
          </details>
          <details className="guild-diagnostic">
            <summary>Guild Registry State</summary>
            <pre>{JSON.stringify(guildRegistryOutput || {}, null, 2)}</pre>
            <pre>{JSON.stringify(guildRegistryList || [], null, 2)}</pre>
          </details>
          <details className="guild-diagnostic">
            <summary>Distribution Registry and Capabilities</summary>
            <pre>{JSON.stringify(distributionRegistryOutput || {}, null, 2)}</pre>
            <pre>{JSON.stringify(distributionRegistryList || [], null, 2)}</pre>
            <pre>{JSON.stringify(distributionCapabilitiesOutput || {}, null, 2)}</pre>
          </details>
          <details className="guild-diagnostic">
            <summary>Handshake and Migration Status</summary>
            <pre>{JSON.stringify(distributionHandshakeOutput || {}, null, 2)}</pre>
            <pre>{JSON.stringify(distributionHandshakeList || [], null, 2)}</pre>
            <pre>{JSON.stringify(migrationStatus || {}, null, 2)}</pre>
            <pre>{JSON.stringify(serviceReadinessOutput || {}, null, 2)}</pre>
            <pre>{JSON.stringify(federationHealthOutput || {}, null, 2)}</pre>
          </details>
          <details className="guild-diagnostic">
            <summary>Wand Registry and Status</summary>
            <pre>{JSON.stringify(wandRegistryOutput || {}, null, 2)}</pre>
            <pre>{JSON.stringify(wandRegistryList || [], null, 2)}</pre>
            <pre>{JSON.stringify(guildWandStatus || {}, null, 2)}</pre>
          </details>
          <details className="guild-diagnostic">
            <summary>Entropy and Message Outputs</summary>
            <pre>{JSON.stringify(guildEntropyMixOutput || {}, null, 2)}</pre>
            <pre>{JSON.stringify(guildEncryptOutput || {}, null, 2)}</pre>
            <pre>{JSON.stringify(guildPersistOutput || {}, null, 2)}</pre>
            <pre>{JSON.stringify(guildMessageHistory || [], null, 2)}</pre>
          </details>
          <details className="guild-diagnostic">
            <summary>Temple and Theatre Source Payloads</summary>
            <pre>{JSON.stringify(buildTempleEntropySourcePayload(), null, 2)}</pre>
            <pre>{JSON.stringify(buildTheatreEntropySourcePayload(), null, 2)}</pre>
          </details>
        </section>
      </div>
    </section>
  );
}
