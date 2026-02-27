import { describe, expect, it } from "vitest";
import { consumeInboxBatch } from "./engineInbox";

function baseState() {
  return {
    tick: 0,
    post_inbox: [],
    tables: {}
  };
}

describe("engine inbox consume", () => {
  it("preserves order and writes level rules", () => {
    const inbox = [
      {
        action: "game_rule_level_apply",
        path: "/v1/game/rules/levels/apply",
        payload: { workspace_id: "main", actor_id: "p1", level: 2 },
        posted_at: "2026-02-27T00:00:00.000Z"
      },
      {
        action: "game_rule_level_apply",
        path: "/v1/game/rules/levels/apply",
        payload: { workspace_id: "main", actor_id: "p1", level: 3 },
        posted_at: "2026-02-27T00:00:01.000Z"
      }
    ];
    const out = consumeInboxBatch(baseState(), inbox, { take: 10, strictValidation: true });
    expect(out.result.applied).toBe(2);
    expect(out.result.rejected).toBe(0);
    expect(out.state.tables.levels_rules).toHaveLength(2);
    expect(out.state.tables.levels_rules[0].payload.level).toBe(2);
    expect(out.state.tables.levels_rules[1].payload.level).toBe(3);
  });

  it("skips duplicate envelope hashes", () => {
    const evt = {
      action: "game_rule_level_apply",
      path: "/v1/game/rules/levels/apply",
      payload: { workspace_id: "main", actor_id: "p1", level: 2 },
      posted_at: "2026-02-27T00:00:00.000Z"
    };
    const out = consumeInboxBatch(baseState(), [evt, evt], { take: 10, strictValidation: true });
    expect(out.result.applied).toBe(1);
    expect(out.result.skipped).toBe(1);
    expect(out.state.tables.levels_rules).toHaveLength(1);
  });

  it("rejects missing contract fields in strict mode", () => {
    const inbox = [
      {
        action: "game_rule_skill_train",
        path: "/v1/game/rules/skills/train",
        payload: { workspace_id: "main" },
        posted_at: "2026-02-27T00:00:00.000Z"
      }
    ];
    const out = consumeInboxBatch(baseState(), inbox, { take: 10, strictValidation: true });
    expect(out.result.applied).toBe(0);
    expect(out.result.rejected).toBe(1);
    expect(Array.isArray(out.state.rejected_posts)).toBe(true);
    expect(out.state.rejected_posts[0].missing).toContain("actor_id");
  });

  it("produces stable consume hash for same input", () => {
    const inbox = [
      {
        action: "game_scene_graph_emit",
        path: "/v1/game/scene-graph/emit",
        payload: { workspace_id: "main", scene_id: "lapidus/home", nodes: [] },
        posted_at: "2026-02-27T00:00:00.000Z"
      }
    ];
    const a = consumeInboxBatch(baseState(), inbox, { take: 10, strictValidation: true });
    const b = consumeInboxBatch(baseState(), inbox, { take: 10, strictValidation: true });
    expect(a.result.consume_hash).toBe(b.result.consume_hash);
  });

  it("supports custom handler map", () => {
    const inbox = [
      {
        action: "custom_market",
        path: "/v1/game/rules/market/trade",
        payload: { workspace_id: "main", actor_id: "p1", trade: "x" },
        posted_at: "2026-02-27T00:00:00.000Z"
      }
    ];
    const out = consumeInboxBatch(baseState(), inbox, {
      take: 10,
      strictValidation: true,
      handlerMap: {
        "/v1/game/rules/market/trade": {
          target: "tables.custom_market_log",
          mode: "append"
        }
      }
    });
    expect(out.result.custom_handlers).toBe(1);
    expect(out.state.tables.custom_market_log).toHaveLength(1);
    expect(out.state.tables.custom_market_log[0].payload.trade).toBe("x");
  });
});
