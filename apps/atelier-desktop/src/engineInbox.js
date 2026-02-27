export function stableStringify(value) {
  if (value === null || typeof value !== "object") {
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map((item) => stableStringify(item)).join(",")}]`;
  }
  const entries = Object.entries(value).sort(([a], [b]) => a.localeCompare(b));
  return `{${entries.map(([k, v]) => `${JSON.stringify(k)}:${stableStringify(v)}`).join(",")}}`;
}

export function localStringHash(text) {
  let hash = 0;
  const input = String(text);
  for (let i = 0; i < input.length; i += 1) {
    hash = (hash * 31 + input.charCodeAt(i)) >>> 0;
  }
  return `h_local_${hash.toString(16).padStart(8, "0")}`;
}

export function canonicalRuleBucket(path) {
  if (typeof path !== "string") {
    return "misc";
  }
  if (path.includes("/rules/levels/")) return "levels";
  if (path.includes("/rules/skills/")) return "skills";
  if (path.includes("/rules/perks/")) return "perks";
  if (path.includes("/rules/alchemy/")) return "alchemy";
  if (path.includes("/rules/blacksmith/")) return "blacksmith";
  if (path.includes("/rules/combat/")) return "combat";
  if (path.includes("/rules/market/")) return "market";
  if (path.includes("/vitriol/")) return "vitriol";
  return "misc";
}

export function endpointContract(path) {
  if (path === "/v1/game/quests/headless/emit") {
    return ["workspace_id", "quest_id"];
  }
  if (path === "/v1/game/meditation/emit") {
    return ["workspace_id", "session_id"];
  }
  if (path === "/v1/game/scene-graph/emit") {
    return ["workspace_id", "scene_id"];
  }
  if (path.startsWith("/v1/game/rules/")) {
    return ["workspace_id", "actor_id"];
  }
  if (path.startsWith("/v1/game/vitriol/")) {
    return ["workspace_id", "actor_id"];
  }
  return [];
}

export function missingContractFields(path, payload) {
  const required = endpointContract(path);
  if (required.length === 0) {
    return [];
  }
  const source = payload && typeof payload === "object" ? payload : {};
  return required.filter((field) => source[field] === undefined || source[field] === null || String(source[field]) === "");
}

export function applyCustomHandler(nextState, action, path, payload, now, customHandler) {
  if (!customHandler || typeof customHandler !== "object") {
    return false;
  }
  const target = typeof customHandler.target === "string" ? customHandler.target : "";
  const mode = typeof customHandler.mode === "string" ? customHandler.mode : "append";
  if (!target) {
    return false;
  }
  if (target.startsWith("tables.")) {
    const tableKey = target.slice("tables.".length);
    if (!tableKey) {
      return false;
    }
    const current = nextState.tables && typeof nextState.tables === "object" ? nextState.tables : {};
    const tableValue = current[tableKey];
    if (mode === "replace") {
      nextState.tables = {
        ...current,
        [tableKey]: payload
      };
    } else {
      const row = { action, path, payload, at: now };
      const rows = Array.isArray(tableValue) ? tableValue : [];
      nextState.tables = {
        ...current,
        [tableKey]: [...rows, row].slice(-500)
      };
    }
    return true;
  }
  if (target === "quests") {
    const current = Array.isArray(nextState.quests) ? nextState.quests : [];
    nextState.quests = [...current, { ...payload, _meta: { action, path, at: now } }].slice(-500);
    return true;
  }
  if (target === "meditation_sessions") {
    const current = Array.isArray(nextState.meditation_sessions) ? nextState.meditation_sessions : [];
    nextState.meditation_sessions = [...current, { ...payload, _meta: { action, path, at: now } }].slice(-500);
    return true;
  }
  return false;
}

export function applyInboxEnvelope(state, envelope, strictValidation, handlerMap) {
  const nextState = state && typeof state === "object" ? { ...state } : {};
  const payload = envelope && envelope.payload && typeof envelope.payload === "object" ? envelope.payload : {};
  const path = envelope && typeof envelope.path === "string" ? envelope.path : "";
  const action = envelope && typeof envelope.action === "string" ? envelope.action : "post_action";
  const now = new Date().toISOString();
  const envelopeHash = localStringHash(stableStringify({
    action,
    path,
    payload,
    posted_at: envelope && envelope.posted_at ? envelope.posted_at : null
  }));
  const missing = missingContractFields(path, payload);

  if (!nextState.tables || typeof nextState.tables !== "object") {
    nextState.tables = {};
  }
  if (!Array.isArray(nextState.processed_posts)) {
    nextState.processed_posts = [];
  }
  if (!Array.isArray(nextState.processed_post_ids)) {
    nextState.processed_post_ids = [];
  }
  if (!Array.isArray(nextState.rejected_posts)) {
    nextState.rejected_posts = [];
  }
  if (nextState.processed_post_ids.includes(envelopeHash)) {
    return {
      state: nextState,
      status: "skipped_duplicate",
      envelope_hash: envelopeHash,
      reason: "already_processed"
    };
  }
  if (strictValidation && missing.length > 0) {
    nextState.rejected_posts = [
      ...nextState.rejected_posts,
      { action, path, envelope_hash: envelopeHash, missing, at: now }
    ].slice(-500);
    return {
      state: nextState,
      status: "rejected_contract",
      envelope_hash: envelopeHash,
      reason: `missing:${missing.join(",")}`
    };
  }

  const customHandler = handlerMap && typeof handlerMap === "object" ? handlerMap[path] : null;
  const customApplied = applyCustomHandler(nextState, action, path, payload, now, customHandler);
  if (customApplied) {
    // handled by custom map
  } else if (path.startsWith("/v1/game/rules/") || path.startsWith("/v1/game/vitriol/")) {
    const bucket = canonicalRuleBucket(path);
    const tableKey = `${bucket}_rules`;
    const current = Array.isArray(nextState.tables[tableKey]) ? nextState.tables[tableKey] : [];
    nextState.tables[tableKey] = [...current, { action, path, payload, at: now }].slice(-200);
  } else if (path === "/v1/game/quests/headless/emit") {
    const current = Array.isArray(nextState.quests) ? nextState.quests : [];
    nextState.quests = [...current, { ...payload, _meta: { action, path, at: now } }].slice(-200);
  } else if (path === "/v1/game/meditation/emit") {
    const current = Array.isArray(nextState.meditation_sessions) ? nextState.meditation_sessions : [];
    nextState.meditation_sessions = [...current, { ...payload, _meta: { action, path, at: now } }].slice(-200);
  } else if (path === "/v1/game/scene-graph/emit") {
    const current = nextState.scene_graphs && typeof nextState.scene_graphs === "object" ? nextState.scene_graphs : {};
    const sceneId = String(payload.scene_id || "scene_unknown");
    nextState.scene_graphs = {
      ...current,
      [sceneId]: { ...payload, _meta: { action, path, at: now } }
    };
  } else {
    const current = Array.isArray(nextState.unhandled_posts) ? nextState.unhandled_posts : [];
    nextState.unhandled_posts = [...current, { action, path, payload, at: now }].slice(-200);
  }

  nextState.processed_posts = [
    ...nextState.processed_posts,
    { action, path, envelope_hash: envelopeHash, at: now }
  ].slice(-500);
  nextState.processed_post_ids = [...nextState.processed_post_ids, envelopeHash].slice(-2000);
  nextState.last_post_action = action;
  nextState.last_post_path = path;
  nextState.last_post_at = now;
  return {
    state: nextState,
    status: "applied",
    envelope_hash: envelopeHash,
    reason: ""
  };
}

export function consumeInboxBatch(state, inbox, options = {}) {
  const strictValidation = options.strictValidation !== false;
  const handlerMap = options.handlerMap && typeof options.handlerMap === "object" ? options.handlerMap : {};
  const take = Math.max(1, Math.min(200, Number.parseInt(String(options.take ?? "25"), 10) || 25));
  const currentState = state && typeof state === "object" ? { ...state } : {};
  const sourceInbox = Array.isArray(inbox) ? inbox : [];
  const toConsume = sourceInbox.slice(0, take);

  let nextState = { ...currentState };
  const consumeLog = [];
  let applied = 0;
  let skipped = 0;
  let rejected = 0;
  for (const envelope of toConsume) {
    const step = applyInboxEnvelope(nextState, envelope, strictValidation, handlerMap);
    nextState = step.state;
    consumeLog.push({
      action: envelope && envelope.action ? envelope.action : "post_action",
      path: envelope && envelope.path ? envelope.path : "",
      status: step.status,
      envelope_hash: step.envelope_hash,
      reason: step.reason
    });
    if (step.status === "applied") {
      applied += 1;
    } else if (step.status === "skipped_duplicate") {
      skipped += 1;
    } else {
      rejected += 1;
    }
  }
  const remaining = sourceInbox.slice(toConsume.length);
  nextState.post_inbox = remaining;
  const consumeHash = localStringHash(stableStringify({
    applied,
    skipped,
    rejected,
    remaining: remaining.length,
    strict: Boolean(strictValidation),
    sample: consumeLog.slice(0, 5)
  }));
  return {
    state: nextState,
    result: {
      ok: true,
      strict_validation: Boolean(strictValidation),
      consumed: toConsume.length,
      applied,
      skipped,
      rejected,
      remaining: remaining.length,
      custom_handlers: Object.keys(handlerMap).length,
      last_action: nextState.last_post_action || null,
      consume_hash: consumeHash,
      sample: consumeLog.slice(0, 10)
    }
  };
}
