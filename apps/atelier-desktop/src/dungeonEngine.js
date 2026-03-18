/**
 * dungeonEngine.js
 *
 * Turn-based dungeon run engine for KLGS roguelike dungeons.
 *
 * Responsibilities:
 *   - Maintains ephemeral run state (player position, turn count, encounter queue)
 *   - Drives movement over the collision map
 *   - Resolves encounters (delegating resolution details to the caller via callbacks)
 *   - Fires stack events at run end via the /v1/orrery/record API
 *
 * The engine does NOT own the dungeon layout — that belongs to dungeonGenerator.js.
 * The engine does NOT own persistence — that belongs to the multiverse stack.
 *
 * Usage:
 *   const engine = createDungeonEngine({
 *     dungeonDef,
 *     generated,          // output of dungeonGenerator.generate()
 *     workspaceId,
 *     gameId,
 *     actorId,
 *     apiBase,
 *     onStateChange,      // (runState) => void
 *     onEncounter,        // (encounter, runState) => Promise<EncounterResult>
 *     onRunEnd,           // (runOutcome) => void
 *   });
 *
 *   engine.start();
 *   engine.move("north");    // "north" | "south" | "east" | "west"
 *   engine.act("engage");    // "engage" | "flee" | "observe" | "wait"
 *   engine.abandon();
 */

import { buildCollisionMap } from "./collisionMap";

// ── Direction vectors ─────────────────────────────────────────────────────────
const DIRECTIONS = {
  north: { dx:  0, dy: -1 },
  south: { dx:  0, dy:  1 },
  east:  { dx:  1, dy:  0 },
  west:  { dx: -1, dy:  0 },
};

// ── Run outcome constants ─────────────────────────────────────────────────────
export const RUN_OUTCOMES = {
  CLEARED: "cleared",     // player reached the exit
  FLED:    "fled",        // player abandoned mid-run
  DEFEATED:"defeated",    // player was defeated
};

// ── Stack event firer ─────────────────────────────────────────────────────────
async function fireStackEvent(apiBase, workspaceId, gameId, actorId, actionKind, payload) {
  try {
    const res = await fetch(`${apiBase}/v1/orrery/record`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        workspace_id: workspaceId,
        game_id: gameId,
        actor_id: actorId,
        action_kind: actionKind,
        payload,
      }),
    });
    if (!res.ok) {
      console.warn(`[dungeonEngine] stack event ${actionKind} returned ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    console.warn(`[dungeonEngine] stack event ${actionKind} failed:`, err);
    return null;
  }
}

// ── Void Wraith observation firer ─────────────────────────────────────────────
async function fireWraithObservation(apiBase, workspaceId, gameId, observationKind, subject, context) {
  try {
    await fetch(`${apiBase}/v1/orrery/void_wraith`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        workspace_id: workspaceId,
        game_id: gameId,
        observation_kind: observationKind,
        subject,
        context,
      }),
    });
  } catch (err) {
    console.warn(`[dungeonEngine] wraith observation ${observationKind} failed:`, err);
  }
}

// ── createDungeonEngine ───────────────────────────────────────────────────────
/**
 * @param {object} config
 * @param {object}   config.dungeonDef       — from dungeonRegistry
 * @param {object}   config.generated        — from dungeonGenerator.generate()
 * @param {string}   config.workspaceId
 * @param {string}   config.gameId           — e.g. "7_KLGS"
 * @param {string}   config.actorId          — player actor id
 * @param {string}   config.apiBase          — e.g. "http://127.0.0.1:9000"
 * @param {Function} config.onStateChange    — called after every mutation
 * @param {Function} config.onEncounter      — async (encounter, runState) => { outcome, killed }
 * @param {Function} config.onRunEnd         — (runOutcome) => void
 */
export function createDungeonEngine(config) {
  const {
    dungeonDef,
    generated,
    workspaceId,
    gameId,
    actorId,
    apiBase,
    onStateChange = () => {},
    onEncounter   = async () => ({ outcome: "resolved", killed: false }),
    onRunEnd      = () => {},
  } = config;

  // Build collision map from generated voxels
  const collisionMap = buildCollisionMap(generated.voxels);

  // Locate entry point
  const entrySpecial = generated.specials.find(s => s.type === "entry");
  const exitSpecial  = generated.specials.find(s => s.type === "exit");

  // ── Run state ─────────────────────────────────────────────────────────────
  let runState = null;

  function initRunState() {
    return {
      running: false,
      turn: 0,
      player: { x: entrySpecial?.x ?? 1, y: entrySpecial?.y ?? 1, z: 0 },
      exit:   { x: exitSpecial?.x  ?? 1, y: exitSpecial?.y  ?? 1 },
      cleared_encounters: new Set(),
      kills: 0,
      silences: 0,              // speech opportunities declined
      speech_opportunities: 0,  // encounters that offered dialogue
      omissions: {},            // action_kind → { opportunities, taken }
      loot: [],
      outcome: null,
      dungeon_id: dungeonDef.id,
      game_id: gameId,
    };
  }

  function emitState() {
    onStateChange({ ...runState, player: { ...runState.player } });
  }

  // ── Passability check ─────────────────────────────────────────────────────
  function canMoveTo(x, y, z = 0) {
    const key = `${x},${y},${z}`;
    // If not in collision map at all, treat as impassable (outside dungeon bounds)
    if (!collisionMap.grid.has(key)) return false;
    return collisionMap.passable.has(key);
  }

  // ── Omission tracking ─────────────────────────────────────────────────────
  function recordOpportunity(actionKind) {
    if (!runState.omissions[actionKind]) {
      runState.omissions[actionKind] = { opportunities: 0, taken: 0 };
    }
    runState.omissions[actionKind].opportunities++;
  }

  function recordTaken(actionKind) {
    if (!runState.omissions[actionKind]) {
      runState.omissions[actionKind] = { opportunities: 0, taken: 0 };
    }
    runState.omissions[actionKind].taken++;
  }

  // ── Encounter resolution ──────────────────────────────────────────────────
  async function resolveEncounters() {
    if (!runState.running) return;

    const { x, y } = runState.player;
    const pending = generated.encounters.filter(enc => {
      if (runState.cleared_encounters.has(enc.room_index)) return false;
      return enc.x === x && enc.y === y;
    });

    for (const enc of pending) {
      runState.cleared_encounters.add(enc.room_index);

      // Track dialogue opportunity
      if (enc.kind === "negotiation" || enc.kind === "lore") {
        runState.speech_opportunities++;
        recordOpportunity("speech");
      }
      recordOpportunity(`encounter.${enc.kind}`);

      const result = await onEncounter(enc, { ...runState });

      // Process kill
      if (result.killed) {
        runState.kills++;
        recordTaken(`encounter.${enc.kind}`);
        await fireWraithObservation(
          apiBase, workspaceId, gameId,
          "kill",
          `${dungeonDef.id}.${enc.kind}`,
          { turn: runState.turn, x, y, encounter_kind: enc.kind }
        );
      }

      // Process silence (dialogue available, not taken)
      if ((enc.kind === "negotiation" || enc.kind === "lore") && !result.spoke) {
        runState.silences++;
        await fireWraithObservation(
          apiBase, workspaceId, gameId,
          "silence",
          `${dungeonDef.id}.dialogue_skipped`,
          { turn: runState.turn, x, y, encounter_kind: enc.kind }
        );
      } else if (result.spoke) {
        recordTaken("speech");
      }

      // Loot
      if (result.loot?.length) {
        runState.loot.push(...result.loot);
      }

      emitState();
    }
  }

  // ── Omission flush: fire Vios observations at run end ─────────────────────
  async function flushOmissions() {
    const MIN_OPPORTUNITIES = 3;
    for (const [actionKind, counts] of Object.entries(runState.omissions)) {
      const missed = counts.opportunities - counts.taken;
      if (counts.opportunities >= MIN_OPPORTUNITIES && missed >= MIN_OPPORTUNITIES) {
        await fireWraithObservation(
          apiBase, workspaceId, gameId,
          "omission",
          `${dungeonDef.id}.${actionKind}`,
          {
            opportunities: counts.opportunities,
            taken: counts.taken,
            missed,
            dungeon_id: dungeonDef.id,
          }
        );
      }
    }
  }

  // ── Run end ───────────────────────────────────────────────────────────────
  async function endRun(outcomeKind) {
    if (!runState.running) return;
    runState.running = false;
    runState.outcome = outcomeKind;

    await flushOmissions();

    const runOutcome = {
      dungeon_id: dungeonDef.id,
      game_id: gameId,
      outcome: outcomeKind,
      turns: runState.turn,
      kills: runState.kills,
      silences: runState.silences,
      speech_opportunities: runState.speech_opportunities,
      loot: runState.loot,
      cleared_encounter_count: runState.cleared_encounters.size,
      omissions: runState.omissions,
    };

    // Fire run-end stack event
    const stackActionKind = `${dungeonDef.stack_event_prefix}.run.${outcomeKind}`;
    await fireStackEvent(
      apiBase, workspaceId, gameId, actorId,
      stackActionKind,
      runOutcome
    );

    emitState();
    onRunEnd(runOutcome);
  }

  // ── Public API ────────────────────────────────────────────────────────────
  return {
    /** Start a new run. Resets all run state. */
    start() {
      runState = initRunState();
      runState.running = true;
      emitState();
    },

    /** Current run state snapshot (read-only copy). */
    getState() {
      if (!runState) return null;
      return { ...runState, player: { ...runState.player } };
    },

    /** The collision map built from the generated layout. */
    collisionMap,

    /** Generated voxel array (for renderer). */
    voxels: generated.voxels,

    /** Generated dungeon metadata. */
    metadata: generated.metadata,

    /**
     * Move the player one step.
     * @param {"north"|"south"|"east"|"west"} direction
     * @returns {boolean} true if move succeeded
     */
    async move(direction) {
      if (!runState?.running) return false;

      const dir = DIRECTIONS[direction];
      if (!dir) return false;

      const nx = runState.player.x + dir.dx;
      const ny = runState.player.y + dir.dy;
      const nz = runState.player.z;

      if (!canMoveTo(nx, ny, nz)) return false;

      runState.player.x = nx;
      runState.player.y = ny;
      runState.turn++;

      // Check exit
      if (exitSpecial && nx === exitSpecial.x && ny === exitSpecial.y) {
        emitState();
        await endRun(RUN_OUTCOMES.CLEARED);
        return true;
      }

      // Resolve any encounters at new position
      await resolveEncounters();

      emitState();
      return true;
    },

    /**
     * Perform a deliberate action (not movement).
     * Records taken/missed opportunities for Vios tracking.
     * @param {"engage"|"flee"|"observe"|"wait"|"speak"|"loot"} action
     */
    async act(action) {
      if (!runState?.running) return;

      runState.turn++;
      recordOpportunity(action);

      switch (action) {
        case "engage":
        case "speak":
        case "loot":
        case "observe":
          recordTaken(action);
          break;
        case "wait":
        case "flee":
          // Deliberately not taken — Vios notices deliberate waiting/fleeing patterns
          break;
      }

      if (action === "flee") {
        await endRun(RUN_OUTCOMES.FLED);
        return;
      }

      emitState();
    },

    /**
     * Mark the player as defeated. Ends the run.
     */
    async defeat() {
      if (!runState?.running) return;
      await endRun(RUN_OUTCOMES.DEFEATED);
    },

    /**
     * Abandon the run (player-initiated quit). Same as flee for stack purposes.
     */
    async abandon() {
      if (!runState?.running) return;
      await endRun(RUN_OUTCOMES.FLED);
    },
  };
}
