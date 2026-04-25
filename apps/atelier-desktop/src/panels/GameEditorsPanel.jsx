/**
 * GameEditorsPanel.jsx
 * ====================
 * Four structured game-data editors for 7_KLGS:
 *   1. Dialogue Tree Editor   — NPC dialogue paths, branching, witness conditions
 *   2. Quest Editor           — quest steps as Cannabis witness entries
 *   3. Encounter Editor       — encounter placement, combatants, loot
 *   4. Audio Track Registry   — track catalogue with realm/quest conditions
 *
 * All editors produce structured JSON matching the qqva DialoguePath /
 * QuestState / encounter / audio schemas.  Export is via in-browser download.
 * Props
 * -----
 *   apiBase   : string  — API URL root for POST calls
 *   apiPost   : async (endpoint, body) => data  — shared fetch helper
 */
import React, { useState } from "react";
import {
  CHARACTERS,
  QUESTS,
  ITEMS,
  CHARACTER_BY_ID,
} from "../game7Registry.js";
import { ALL_PERKS } from "../skillRegistry.js";

const REALMS = ["lapidus", "mercurie", "sulphera"];
const SULPHERA_GATE_ENTRY = "0009_KLST";
const COMBATANT_ROLES = ["minion", "leader", "boss", "elite"];
const AUDIO_CHANNELS = ["music", "sfx", "ambient", "narrative"];

// ── helpers ──────────────────────────────────────────────────────────────────

function downloadJson(filename, obj) {
  const blob = new Blob([JSON.stringify(obj, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function uid() {
  return Math.random().toString(36).slice(2, 9);
}

function csvToList(str) {
  return str
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

// ── 1. Dialogue Tree Editor ───────────────────────────────────────────────────

function DialogueEditor() {
  const [charId, setCharId] = useState("");
  const [questCtx, setQuestCtx] = useState("");
  const [realm, setRealm] = useState("lapidus");
  const [pathId, setPathId] = useState("path_001");
  const [priority, setPriority] = useState("0");
  const [requiredWitnesses, setRequiredWitnesses] = useState("");
  const [blockedWitnesses, setBlockedWitnesses] = useState("");
  const [speakerInput, setSpeakerInput] = useState("");
  const [textInput, setTextInput] = useState("");
  const [shygazunInput, setShygazunInput] = useState("");
  const [lines, setLines] = useState([]);
  const [paths, setPaths] = useState([]);
  const [selectedPathIdx, setSelectedPathIdx] = useState(null);

  function addLine() {
    const speaker = speakerInput.trim() || charId || "unknown";
    const text = textInput.trim();
    if (!text) return;
    setLines((prev) => [
      ...prev,
      { speaker, text, shygazun: shygazunInput.trim() },
    ]);
    setTextInput("");
    setShygazunInput("");
  }

  function removeLine(idx) {
    setLines((prev) => prev.filter((_, i) => i !== idx));
  }

  function savePath() {
    if (!charId || !pathId.trim()) return;
    const path = {
      path_id: pathId.trim(),
      character_id: charId,
      realm_id: realm,
      priority: parseInt(priority, 10) || 0,
      required_witnesses: csvToList(requiredWitnesses),
      blocked_witnesses: csvToList(blockedWitnesses),
      lines: [...lines],
      meta: questCtx ? { quest_id: questCtx } : {},
    };
    if (selectedPathIdx !== null) {
      setPaths((prev) =>
        prev.map((p, i) => (i === selectedPathIdx ? path : p))
      );
      setSelectedPathIdx(null);
    } else {
      setPaths((prev) => [...prev, path]);
    }
    setLines([]);
  }

  function loadPath(idx) {
    const p = paths[idx];
    setCharId(p.character_id);
    setRealm(p.realm_id);
    setPathId(p.path_id);
    setPriority(String(p.priority));
    setRequiredWitnesses(p.required_witnesses.join(", "));
    setBlockedWitnesses(p.blocked_witnesses.join(", "));
    setLines([...p.lines]);
    setQuestCtx(p.meta?.quest_id || "");
    setSelectedPathIdx(idx);
  }

  function removePath(idx) {
    setPaths((prev) => prev.filter((_, i) => i !== idx));
    if (selectedPathIdx === idx) setSelectedPathIdx(null);
  }

  function exportPaths() {
    if (!paths.length) return;
    const charLabel = charId ? CHARACTER_BY_ID[charId]?.name || charId : "unknown";
    downloadJson(
      `dialogue_${charLabel.replace(/\s/g, "_")}.json`,
      { character_id: charId, paths }
    );
  }

  const char = CHARACTER_BY_ID[charId];

  return (
    <section className="panel">
      <h2>Dialogue Tree Editor</h2>
      <p>
        Author branching NPC dialogue paths with witness conditions.
        Each path matches a <code>DialoguePath</code> in the qqva dialogue_runtime schema.
      </p>

      <h3>Character &amp; Context</h3>
      <div className="row">
        <select value={charId} onChange={(e) => setCharId(e.target.value)}>
          <option value="">— character —</option>
          {CHARACTERS.filter((c) => c.id && c.type !== "test").map((c) => (
            <option key={c.id} value={c.id}>
              {c.name} [{c.type}]
            </option>
          ))}
        </select>
        <select value={questCtx} onChange={(e) => setQuestCtx(e.target.value)}>
          <option value="">— quest context (optional) —</option>
          {QUESTS.map((q) => (
            <option key={q.id} value={q.id}>
              {q.id} — {q.name}
            </option>
          ))}
        </select>
        <select value={realm} onChange={(e) => setRealm(e.target.value)}>
          {REALMS.map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
      </div>
      {char && (
        <p className="badge">
          {char.name} · {char.type}
          {char.role ? ` · ${char.role}` : ""}
          {char.realm ? ` · realm: ${char.realm}` : ""}
        </p>
      )}

      <h3>Path Settings</h3>
      <div className="row">
        <input
          value={pathId}
          onChange={(e) => setPathId(e.target.value)}
          placeholder="path_id (e.g. path_pre_quest)"
        />
        <input
          value={priority}
          onChange={(e) => setPriority(e.target.value)}
          placeholder="priority (higher = preferred)"
          style={{ width: 140 }}
        />
      </div>
      <div className="row">
        <input
          value={requiredWitnesses}
          onChange={(e) => setRequiredWitnesses(e.target.value)}
          placeholder="required_witnesses (comma-separated entry_ids)"
          style={{ flex: 1 }}
        />
        <input
          value={blockedWitnesses}
          onChange={(e) => setBlockedWitnesses(e.target.value)}
          placeholder="blocked_witnesses (comma-separated entry_ids)"
          style={{ flex: 1 }}
        />
      </div>
      {realm === "sulphera" && (
        <p className="badge" style={{ background: "#441" }}>
          ⚠ Sulphera: requires {SULPHERA_GATE_ENTRY} (Demons and Diamonds) in required_witnesses
        </p>
      )}

      <h3>Dialogue Lines</h3>
      <div className="row">
        <input
          value={speakerInput}
          onChange={(e) => setSpeakerInput(e.target.value)}
          placeholder={`speaker (default: ${charId || "character_id"})`}
          style={{ width: 200 }}
        />
        <input
          value={textInput}
          onChange={(e) => setTextInput(e.target.value)}
          placeholder="line text"
          style={{ flex: 1 }}
        />
        <input
          value={shygazunInput}
          onChange={(e) => setShygazunInput(e.target.value)}
          placeholder="Shygazun (optional)"
          style={{ width: 160 }}
        />
        <button className="action action-xs" onClick={addLine}>+ Line</button>
      </div>

      {lines.length > 0 && (
        <div className="dialogue-box" style={{ maxHeight: 200, overflowY: "auto", margin: "8px 0" }}>
          {lines.map((ln, i) => (
            <div className="dialogue-line" key={i} style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
              <strong style={{ minWidth: 120, flexShrink: 0 }}>{ln.speaker}</strong>
              <span style={{ flex: 1 }}>{ln.text}</span>
              {ln.shygazun && <code style={{ color: "#8af", fontSize: "0.85em" }}>{ln.shygazun}</code>}
              <button className="action action-xs" onClick={() => removeLine(i)}>✕</button>
            </div>
          ))}
        </div>
      )}

      <div className="row">
        <button className="action" onClick={savePath}>
          {selectedPathIdx !== null ? "Update Path" : "Save Path"}
        </button>
        {selectedPathIdx !== null && (
          <button className="action action-xs" onClick={() => { setSelectedPathIdx(null); setLines([]); }}>
            Cancel Edit
          </button>
        )}
        <span className="badge">{lines.length} line{lines.length !== 1 ? "s" : ""}</span>
      </div>

      <h3>Authored Paths</h3>
      {paths.length === 0 ? (
        <p className="dialogue-empty">No paths saved yet.</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85em" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", padding: "4px 8px" }}>path_id</th>
              <th>realm</th>
              <th>priority</th>
              <th>required</th>
              <th>lines</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {paths.map((p, i) => (
              <tr key={p.path_id} style={{ borderTop: "1px solid #333" }}>
                <td style={{ padding: "4px 8px" }}>{p.path_id}</td>
                <td style={{ textAlign: "center" }}>{p.realm_id}</td>
                <td style={{ textAlign: "center" }}>{p.priority}</td>
                <td style={{ fontSize: "0.8em", color: "#8af" }}>
                  {p.required_witnesses.join(", ") || "—"}
                </td>
                <td style={{ textAlign: "center" }}>{p.lines.length}</td>
                <td>
                  <button className="action action-xs" onClick={() => loadPath(i)}>Edit</button>
                  <button className="action action-xs" onClick={() => removePath(i)}>✕</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div className="row" style={{ marginTop: 8 }}>
        <button className="action action-primary" onClick={exportPaths} disabled={!paths.length}>
          Export Paths JSON
        </button>
        <button className="action action-xs" onClick={() => { setPaths([]); setLines([]); setSelectedPathIdx(null); }}>
          Clear All
        </button>
        <span className="badge">{paths.length} path{paths.length !== 1 ? "s" : ""}</span>
      </div>
    </section>
  );
}

// ── 2. Quest Editor ───────────────────────────────────────────────────────────

function QuestEditor() {
  const [questId, setQuestId] = useState("");
  const [npcGiver, setNpcGiver] = useState("");
  const [entryId, setEntryId] = useState("");
  const [entryDesc, setEntryDesc] = useState("");
  const [candA, setCandA] = useState("");
  const [candB, setCandB] = useState("");
  const [steps, setSteps] = useState([]);
  const [rewardPerk, setRewardPerk] = useState("");
  const [rewardItems, setRewardItems] = useState("");
  const [questNotes, setQuestNotes] = useState("");
  const [allQuests, setAllQuests] = useState({});

  const quest = QUESTS.find((q) => q.id === questId);

  function addStep() {
    if (!entryId.trim()) return;
    setSteps((prev) => [
      ...prev,
      {
        entry_id: entryId.trim(),
        description: entryDesc.trim(),
        candidate_a_label: candA.trim() || "Option A",
        candidate_b_label: candB.trim() || "Option B",
      },
    ]);
    setEntryId("");
    setEntryDesc("");
    setCandA("");
    setCandB("");
  }

  function removeStep(idx) {
    setSteps((prev) => prev.filter((_, i) => i !== idx));
  }

  function saveQuest() {
    if (!questId) return;
    const data = {
      quest_id: questId,
      name: quest?.name || questId,
      npc_giver: npcGiver || null,
      steps,
      reward: {
        perk: rewardPerk || null,
        items: csvToList(rewardItems),
      },
      notes: questNotes,
      game_id: "7_KLGS",
    };
    setAllQuests((prev) => ({ ...prev, [questId]: data }));
  }

  function exportQuest() {
    const data = allQuests[questId];
    if (!data) return;
    downloadJson(`quest_${questId}.json`, data);
  }

  function exportAllQuests() {
    if (!Object.keys(allQuests).length) return;
    downloadJson("7_KLGS_quests.json", allQuests);
  }

  return (
    <section className="panel">
      <h2>Quest Editor</h2>
      <p>
        Author quest steps as Cannabis witness entries.
        Each step maps to a <code>WitnessEntry</code> in the quest state machine.
      </p>

      <h3>Quest</h3>
      <div className="row">
        <select value={questId} onChange={(e) => { setQuestId(e.target.value); setSteps([]); }}>
          <option value="">— select quest —</option>
          {QUESTS.map((q) => (
            <option key={q.id} value={q.id}>
              {q.id} — {q.name}
            </option>
          ))}
        </select>
        <select value={npcGiver} onChange={(e) => setNpcGiver(e.target.value)}>
          <option value="">— NPC giver (optional) —</option>
          {CHARACTERS.filter((c) => c.id && c.type !== "test").map((c) => (
            <option key={c.id} value={c.id}>
              {c.name} [{c.type}]
            </option>
          ))}
        </select>
      </div>
      {quest?.note && (
        <p style={{ fontSize: "0.85em", color: "#aaa", margin: "4px 0" }}>{quest.note}</p>
      )}
      <textarea
        className="editor"
        style={{ minHeight: 48 }}
        value={questNotes}
        onChange={(e) => setQuestNotes(e.target.value)}
        placeholder="Quest notes / summary (optional)"
      />

      <h3>Steps (Cannabis Witness Entries)</h3>
      <div className="row">
        <input
          value={entryId}
          onChange={(e) => setEntryId(e.target.value)}
          placeholder="entry_id (e.g. step_01)"
          style={{ width: 180 }}
        />
        <input
          value={entryDesc}
          onChange={(e) => setEntryDesc(e.target.value)}
          placeholder="step description"
          style={{ flex: 1 }}
        />
      </div>
      <div className="row">
        <input
          value={candA}
          onChange={(e) => setCandA(e.target.value)}
          placeholder="candidate A label (e.g. Accept the deal)"
          style={{ flex: 1 }}
        />
        <input
          value={candB}
          onChange={(e) => setCandB(e.target.value)}
          placeholder="candidate B label (e.g. Reject the deal)"
          style={{ flex: 1 }}
        />
        <button className="action action-xs" onClick={addStep}>+ Step</button>
      </div>

      {steps.length > 0 && (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85em", margin: "8px 0" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", padding: "4px 8px" }}>entry_id</th>
              <th style={{ textAlign: "left" }}>description</th>
              <th>candidate A</th>
              <th>candidate B</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {steps.map((s, i) => (
              <tr key={s.entry_id} style={{ borderTop: "1px solid #333" }}>
                <td style={{ padding: "4px 8px", color: "#8af" }}>{s.entry_id}</td>
                <td>{s.description}</td>
                <td style={{ textAlign: "center" }}>{s.candidate_a_label}</td>
                <td style={{ textAlign: "center" }}>{s.candidate_b_label}</td>
                <td>
                  <button className="action action-xs" onClick={() => removeStep(i)}>✕</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h3>Rewards</h3>
      <div className="row">
        <select value={rewardPerk} onChange={(e) => setRewardPerk(e.target.value)}>
          <option value="">— perk reward (optional) —</option>
          {ALL_PERKS.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name} [{p.required_skill}]
            </option>
          ))}
        </select>
        <input
          value={rewardItems}
          onChange={(e) => setRewardItems(e.target.value)}
          placeholder="item rewards (comma-separated)"
          style={{ flex: 1 }}
        />
      </div>

      <div className="row" style={{ marginTop: 8 }}>
        <button className="action" onClick={saveQuest} disabled={!questId}>
          Save Quest
        </button>
        <button className="action action-primary" onClick={exportQuest} disabled={!allQuests[questId]}>
          Export Quest JSON
        </button>
        <button className="action action-primary" onClick={exportAllQuests} disabled={!Object.keys(allQuests).length}>
          Export All Quests
        </button>
        <button className="action action-xs" onClick={() => { setSteps([]); setRewardPerk(""); setRewardItems(""); setQuestNotes(""); }}>
          Clear
        </button>
        <span className="badge">{Object.keys(allQuests).length} saved</span>
      </div>

      {allQuests[questId] && (
        <pre style={{ fontSize: "0.75em", maxHeight: 160, overflowY: "auto", marginTop: 8 }}>
          {JSON.stringify(allQuests[questId], null, 2)}
        </pre>
      )}
    </section>
  );
}

// ── 3. Encounter Editor ───────────────────────────────────────────────────────

function EncounterEditor() {
  const [encId, setEncId] = useState(`enc_${uid()}`);
  const [encName, setEncName] = useState("");
  const [zone, setZone] = useState("");
  const [trigger, setTrigger] = useState("always");
  const [triggerEntry, setTriggerEntry] = useState("");
  const [triggerCandidate, setTriggerCandidate] = useState("a");
  const [charInput, setCharInput] = useState("");
  const [levelInput, setLevelInput] = useState("1");
  const [roleInput, setRoleInput] = useState("minion");
  const [combatants, setCombatants] = useState([]);
  const [lootInput, setLootInput] = useState("");
  const [loot, setLoot] = useState([]);
  const [encounters, setEncounters] = useState({});
  const [xpReward, setXpReward] = useState("0");

  function addCombatant() {
    if (!charInput.trim()) return;
    setCombatants((prev) => [
      ...prev,
      {
        character_id: charInput.trim(),
        level: parseInt(levelInput, 10) || 1,
        role: roleInput,
      },
    ]);
    setCharInput("");
    setLevelInput("1");
  }

  function removeCombatant(idx) {
    setCombatants((prev) => prev.filter((_, i) => i !== idx));
  }

  function addLoot() {
    const item = lootInput.trim();
    if (!item) return;
    setLoot((prev) => [...prev, item]);
    setLootInput("");
  }

  function saveEncounter() {
    const data = {
      encounter_id: encId,
      name: encName || encId,
      zone,
      trigger: {
        type: trigger,
        entry_id: trigger !== "always" ? triggerEntry : null,
        candidate: trigger !== "always" ? triggerCandidate : null,
      },
      combatants: [...combatants],
      loot: [...loot],
      xp_reward: parseInt(xpReward, 10) || 0,
      game_id: "7_KLGS",
    };
    setEncounters((prev) => ({ ...prev, [encId]: data }));
  }

  function exportEncounters() {
    if (!Object.keys(encounters).length) return;
    downloadJson("7_KLGS_encounters.json", encounters);
  }

  return (
    <section className="panel">
      <h2>Encounter Editor</h2>
      <p>
        Define encounters: combatant rosters, zone placement, and quest-gated trigger conditions.
      </p>

      <h3>Encounter</h3>
      <div className="row">
        <input
          value={encId}
          onChange={(e) => setEncId(e.target.value)}
          placeholder="encounter_id"
          style={{ width: 200 }}
        />
        <input
          value={encName}
          onChange={(e) => setEncName(e.target.value)}
          placeholder="name"
          style={{ flex: 1 }}
        />
        <input
          value={zone}
          onChange={(e) => setZone(e.target.value)}
          placeholder="zone / scene id"
          style={{ width: 200 }}
        />
      </div>

      <h3>Trigger</h3>
      <div className="row">
        <select value={trigger} onChange={(e) => setTrigger(e.target.value)}>
          <option value="always">always</option>
          <option value="quest_witnessed">quest_witnessed (entry attested)</option>
          <option value="quest_unwitnessed">quest_unwitnessed (entry not yet attested)</option>
        </select>
        {trigger !== "always" && (
          <>
            <input
              value={triggerEntry}
              onChange={(e) => setTriggerEntry(e.target.value)}
              placeholder="entry_id (e.g. 0009_KLST)"
              style={{ flex: 1 }}
            />
            <select
              value={triggerCandidate}
              onChange={(e) => setTriggerCandidate(e.target.value)}
              style={{ width: 80 }}
            >
              <option value="a">cand A</option>
              <option value="b">cand B</option>
            </select>
          </>
        )}
      </div>

      <h3>Combatants</h3>
      <div className="row">
        <select value={charInput} onChange={(e) => setCharInput(e.target.value)}>
          <option value="">— character —</option>
          {CHARACTERS.filter((c) => c.id && c.type !== "test").map((c) => (
            <option key={c.id} value={c.id}>
              {c.name} [{c.type}]
            </option>
          ))}
        </select>
        <input
          value={levelInput}
          onChange={(e) => setLevelInput(e.target.value)}
          placeholder="level"
          style={{ width: 70 }}
          type="number"
          min="1"
        />
        <select value={roleInput} onChange={(e) => setRoleInput(e.target.value)}>
          {COMBATANT_ROLES.map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
        <button className="action action-xs" onClick={addCombatant}>+ Add</button>
      </div>

      {combatants.length > 0 && (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85em", margin: "8px 0" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", padding: "4px 8px" }}>character_id</th>
              <th>name</th>
              <th>level</th>
              <th>role</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {combatants.map((c, i) => (
              <tr key={`${c.character_id}_${i}`} style={{ borderTop: "1px solid #333" }}>
                <td style={{ padding: "4px 8px", color: "#8af" }}>{c.character_id}</td>
                <td>{CHARACTER_BY_ID[c.character_id]?.name || "—"}</td>
                <td style={{ textAlign: "center" }}>{c.level}</td>
                <td style={{ textAlign: "center" }}>{c.role}</td>
                <td>
                  <button className="action action-xs" onClick={() => removeCombatant(i)}>✕</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h3>Loot &amp; XP</h3>
      <div className="row">
        <select value={lootInput} onChange={(e) => setLootInput(e.target.value)}>
          <option value="">— item —</option>
          {ITEMS.map((item) => (
            <option key={item.name} value={item.name}>{item.name}</option>
          ))}
        </select>
        <input
          value={lootInput}
          onChange={(e) => setLootInput(e.target.value)}
          placeholder="or type item name"
          style={{ flex: 1 }}
        />
        <button className="action action-xs" onClick={addLoot}>+ Loot</button>
        <input
          value={xpReward}
          onChange={(e) => setXpReward(e.target.value)}
          placeholder="XP reward"
          style={{ width: 80 }}
          type="number"
          min="0"
        />
      </div>
      {loot.length > 0 && (
        <div className="row" style={{ flexWrap: "wrap", gap: 4, marginTop: 4 }}>
          {loot.map((item, i) => (
            <span key={i} className="badge" style={{ cursor: "pointer" }}
              onClick={() => setLoot((prev) => prev.filter((_, j) => j !== i))}>
              {item} ✕
            </span>
          ))}
        </div>
      )}

      <div className="row" style={{ marginTop: 8 }}>
        <button className="action" onClick={saveEncounter}>Save Encounter</button>
        <button className="action action-primary" onClick={exportEncounters} disabled={!Object.keys(encounters).length}>
          Export All Encounters
        </button>
        <button className="action action-xs" onClick={() => { setCombatants([]); setLoot([]); setEncId(`enc_${uid()}`); setEncName(""); setZone(""); }}>
          New
        </button>
        <span className="badge">{Object.keys(encounters).length} saved</span>
      </div>
    </section>
  );
}

// ── 4. Audio Track Registry ───────────────────────────────────────────────────

function AudioTrackRegistry() {
  const [trackId, setTrackId] = useState(`track_${uid()}`);
  const [trackName, setTrackName] = useState("");
  const [trackFile, setTrackFile] = useState("");
  const [trackRealm, setTrackRealm] = useState("");
  const [trackChannel, setTrackChannel] = useState("music");
  const [trackLoop, setTrackLoop] = useState(true);
  const [trackConditionEntry, setTrackConditionEntry] = useState("");
  const [trackConditionType, setTrackConditionType] = useState("none");
  const [trackConditionCand, setTrackConditionCand] = useState("a");
  const [trackQuestCtx, setTrackQuestCtx] = useState("");
  const [tracks, setTracks] = useState([]);

  function addTrack() {
    if (!trackFile.trim() && !trackName.trim()) return;
    const track = {
      track_id: trackId,
      name: trackName.trim() || trackFile.trim(),
      file: trackFile.trim(),
      realm: trackRealm || null,
      channel: trackChannel,
      loop: trackLoop,
      quest_context: trackQuestCtx || null,
      condition: trackConditionType === "none"
        ? null
        : {
            type: trackConditionType,
            entry_id: trackConditionEntry,
            candidate: trackConditionCand,
          },
    };
    setTracks((prev) => [...prev, track]);
    setTrackId(`track_${uid()}`);
    setTrackName("");
    setTrackFile("");
    setTrackConditionEntry("");
  }

  function removeTrack(idx) {
    setTracks((prev) => prev.filter((_, i) => i !== idx));
  }

  function exportTracks() {
    if (!tracks.length) return;
    downloadJson("7_KLGS_audio_tracks.json", { game_id: "7_KLGS", tracks });
  }

  return (
    <section className="panel">
      <h2>Audio Track Registry</h2>
      <p>
        Catalogue music, SFX, and ambient tracks with realm context and
        quest witness conditions.
      </p>

      <h3>Track</h3>
      <div className="row">
        <input
          value={trackId}
          onChange={(e) => setTrackId(e.target.value)}
          placeholder="track_id"
          style={{ width: 160 }}
        />
        <input
          value={trackName}
          onChange={(e) => setTrackName(e.target.value)}
          placeholder="name"
          style={{ flex: 1 }}
        />
        <input
          value={trackFile}
          onChange={(e) => setTrackFile(e.target.value)}
          placeholder="file path (e.g. audio/bg_overworld.ogg)"
          style={{ flex: 2 }}
        />
      </div>
      <div className="row">
        <select value={trackChannel} onChange={(e) => setTrackChannel(e.target.value)}>
          {AUDIO_CHANNELS.map((ch) => (
            <option key={ch} value={ch}>{ch}</option>
          ))}
        </select>
        <select value={trackRealm} onChange={(e) => setTrackRealm(e.target.value)}>
          <option value="">— realm (any) —</option>
          {REALMS.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        <select value={trackQuestCtx} onChange={(e) => setTrackQuestCtx(e.target.value)}>
          <option value="">— quest context —</option>
          {QUESTS.map((q) => (
            <option key={q.id} value={q.id}>{q.id} — {q.name}</option>
          ))}
        </select>
        <label style={{ display: "flex", alignItems: "center", gap: 4, whiteSpace: "nowrap" }}>
          <input type="checkbox" checked={trackLoop} onChange={(e) => setTrackLoop(e.target.checked)} />
          loop
        </label>
      </div>

      <h3>Playback Condition</h3>
      <div className="row">
        <select value={trackConditionType} onChange={(e) => setTrackConditionType(e.target.value)}>
          <option value="none">no condition (always plays in context)</option>
          <option value="quest_witnessed">quest_witnessed</option>
          <option value="quest_unwitnessed">quest_unwitnessed</option>
        </select>
        {trackConditionType !== "none" && (
          <>
            <input
              value={trackConditionEntry}
              onChange={(e) => setTrackConditionEntry(e.target.value)}
              placeholder="entry_id"
              style={{ flex: 1 }}
            />
            <select
              value={trackConditionCand}
              onChange={(e) => setTrackConditionCand(e.target.value)}
              style={{ width: 80 }}
            >
              <option value="a">cand A</option>
              <option value="b">cand B</option>
            </select>
          </>
        )}
      </div>

      <div className="row" style={{ marginTop: 8 }}>
        <button className="action" onClick={addTrack}>Add Track</button>
      </div>

      <h3>Track List</h3>
      {tracks.length === 0 ? (
        <p className="dialogue-empty">No tracks yet.</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85em" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", padding: "4px 8px" }}>track_id</th>
              <th style={{ textAlign: "left" }}>name</th>
              <th>channel</th>
              <th>realm</th>
              <th>loop</th>
              <th>condition</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {tracks.map((t, i) => (
              <tr key={t.track_id} style={{ borderTop: "1px solid #333" }}>
                <td style={{ padding: "4px 8px", color: "#8af" }}>{t.track_id}</td>
                <td>{t.name}</td>
                <td style={{ textAlign: "center" }}>{t.channel}</td>
                <td style={{ textAlign: "center" }}>{t.realm || "any"}</td>
                <td style={{ textAlign: "center" }}>{t.loop ? "✓" : "—"}</td>
                <td style={{ fontSize: "0.8em" }}>
                  {t.condition
                    ? `${t.condition.type}:${t.condition.entry_id}`
                    : "—"}
                </td>
                <td>
                  <button className="action action-xs" onClick={() => removeTrack(i)}>✕</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div className="row" style={{ marginTop: 8 }}>
        <button className="action action-primary" onClick={exportTracks} disabled={!tracks.length}>
          Export Track Registry
        </button>
        <span className="badge">{tracks.length} track{tracks.length !== 1 ? "s" : ""}</span>
      </div>
    </section>
  );
}

// ── Root export ───────────────────────────────────────────────────────────────

export function GameEditorsPanel() {
  const [activeTab, setActiveTab] = useState("dialogue");

  const tabs = [
    { id: "dialogue",  label: "Dialogue Tree" },
    { id: "quest",     label: "Quest Editor" },
    { id: "encounter", label: "Encounter Editor" },
    { id: "audio",     label: "Audio Registry" },
  ];

  return (
    <div className="game-editors-panel">
      <div className="row" style={{ borderBottom: "1px solid #333", marginBottom: 16, gap: 0 }}>
        {tabs.map((t) => (
          <button
            key={t.id}
            className={`action${activeTab === t.id ? " action-primary" : ""}`}
            style={{ borderRadius: 0, borderBottom: activeTab === t.id ? "2px solid #8af" : "none" }}
            onClick={() => setActiveTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === "dialogue"  && <DialogueEditor />}
      {activeTab === "quest"     && <QuestEditor />}
      {activeTab === "encounter" && <EncounterEditor />}
      {activeTab === "audio"     && <AudioTrackRegistry />}
    </div>
  );
}