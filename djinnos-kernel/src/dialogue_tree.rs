// dialogue_tree.rs — Fallout-style branching conversation trees for 7_KLGS.
//
// Each NPC that has a scripted entry sequence gets a ConvTree.
// Ambient/topic-selector lines remain in dialogue.rs (CoilState routing).
//
// Tree evaluation:
//   - open() finds the tree for entity_id, starts at Node 0
//   - Each ConvNode contains NPC speech + a list of ConvChoice
//   - ConvChoice gates are invisible: choices simply absent when not met
//   - On selection: apply side effects, advance to next_node
//   - NODE_EXIT (0xFFFF) closes the conversation
//
// Gate types (all invisible to player):
//   quest_req / quest_state  — quest must be in given state
//   flag_req                 — all these flags must be set
//   flag_absent              — none of these flags may be set

pub const NODE_EXIT: u16 = 0xFFFF;

// ── Quest state constants (mirror dialogue.rs) ────────────────────────────────

pub const QS_ANY:         u8 = 0;
pub const QS_OFFERED:     u8 = 1;
pub const QS_IN_PROGRESS: u8 = 2;
pub const QS_COMPLETE:    u8 = 3;

// ── Data structures ───────────────────────────────────────────────────────────

#[derive(Copy, Clone, PartialEq)]
pub enum QuestOp { None, Offer, Accept, Complete }

pub struct ConvChoice {
    pub text:          &'static [u8],
    pub next_node:     u16,
    // Invisible gates
    pub quest_req:     u32,   // 0 = no requirement
    pub quest_state:   u8,
    pub flag_req:      &'static [u32],
    pub flag_absent:   &'static [u32],
    // Side effects (applied on selection)
    pub quest_action:  &'static [u8],
    pub quest_op:      QuestOp,
    pub sets_flag:     u8,    // 0 = none
    pub teaches_perk:  u8,    // 0 = none
    pub gives_item:    u16,   // 0 = none
}

pub struct ConvNode {
    pub node_id:  u16,
    pub npc_text: &'static [u8],
    pub choices:  &'static [ConvChoice],
}

pub struct ConvTree {
    pub entity_id: &'static [u8],
    pub nodes:     &'static [ConvNode],
}

impl ConvTree {
    pub fn find_node(&self, node_id: u16) -> Option<&'static ConvNode> {
        self.nodes.iter().find(|n| n.node_id == node_id)
    }
    pub fn root(&self) -> Option<&'static ConvNode> {
        self.find_node(0)
    }
}

// ── Gate evaluation ───────────────────────────────────────────────────────────

pub fn choice_visible(
    choice:        &ConvChoice,
    active_quests: &[(u32, u8)],
    flags:         &[u32],
) -> bool {
    if choice.quest_req != 0 {
        let ok = active_quests.iter().any(|&(id, st)| {
            id == choice.quest_req
            && (choice.quest_state == QS_ANY || st == choice.quest_state)
        });
        if !ok { return false; }
    }
    for &req in choice.flag_req {
        if !flags.contains(&req) { return false; }
    }
    for &absent in choice.flag_absent {
        if flags.contains(&absent) { return false; }
    }
    true
}

// ── Tree registry ─────────────────────────────────────────────────────────────

pub fn find_tree(entity_id: &[u8]) -> Option<&'static ConvTree> {
    static TREES: &[&ConvTree] = &[
        &TREE_ELSA,
        &TREE_HYPATIA,
    ];
    TREES.iter().find(|t| t.entity_id == entity_id).copied()
}

// ── ELSA (0024_TOWN) — Scene 0001 "Fate Knocks" ──────────────────────────────
//
// She saw the castle seal.  She has lived on Wiltoll Lane thirty years.
// She has watched three lottery letters come and go from this street.
// She knows Hypatia by observation and thirty years of proximity.

pub static TREE_ELSA: ConvTree = ConvTree {
    entity_id: b"0024_TOWN",
    nodes: ELSA_NODES,
};

static ELSA_NODES: &[ConvNode] = &[

    // Node 0 — entry
    ConvNode {
        node_id: 0,
        npc_text: b"I saw the seal on that. Castle Azoth. You all right?",
        choices: &[
            ConvChoice {
                text: b"I don't know yet.",
                next_node: 1,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"I've been wondering if I could refuse.",
                next_node: 2,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"What do you know about how this works?",
                next_node: 3,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"What do you know about Hypatia?",
                next_node: 4,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"I'm fine.",
                next_node: NODE_EXIT,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
        ],
    },

    // Node 1 — honest answer
    ConvNode {
        node_id: 1,
        npc_text: b"Fair answer. I've seen three of those come and go in \
                   thirty years. None of them came back worse for it. \
                   Changed, not worse.",
        choices: &[
            ConvChoice {
                text: b"What kind of changed?",
                next_node: 5,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"None of them refused?",
                next_node: 2,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"Thank you.",
                next_node: NODE_EXIT,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
        ],
    },

    // Node 2 — refusal
    ConvNode {
        node_id: 2,
        npc_text: b"Not that I've seen. But I've never seen someone try. \
                   The letter is a letter. The choice is yours. \
                   The city is not kind about certain choices.",
        choices: &[
            ConvChoice {
                text: b"So effectively no.",
                next_node: NODE_EXIT,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"Has everyone on this street gotten one?",
                next_node: 3,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"I see.",
                next_node: NODE_EXIT,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
        ],
    },

    // Node 3 — what she knows about the lottery
    ConvNode {
        node_id: 3,
        npc_text: b"Not the first, not the last. Someone in the middle of a list. \
                   Make of that what you will.",
        choices: &[
            ConvChoice {
                text: b"The seventh name this season.",
                next_node: 6,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"Three in thirty years is a small number.",
                next_node: 1,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"That's enough.",
                next_node: NODE_EXIT,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
        ],
    },

    // Node 4 — about Hypatia
    ConvNode {
        node_id: 4,
        npc_text: b"Quiet. Works. Keeps the lane. She's good at what she does \
                   -- I mean that plainly. I've watched her for thirty years. \
                   The light at the end of the lane went out two nights ago.",
        choices: &[
            ConvChoice {
                text: b"She's already gone?",
                next_node: 7,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"What's she like?",
                next_node: 7,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"Thank you.",
                next_node: NODE_EXIT,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
        ],
    },

    // Node 5 — changed how
    ConvNode {
        node_id: 5,
        npc_text: b"Quiet in a different way. Careful. Like they had learned \
                   something that required them to be more deliberate with \
                   what they said. I thought about that a long time. \
                   I think it's not a bad thing to learn.",
        choices: &[
            ConvChoice {
                text: b"Have you ever wished you'd gotten one?",
                next_node: 8,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"I'll keep that in mind.",
                next_node: NODE_EXIT,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
        ],
    },

    // Node 6 — seventh name / middle of list
    ConvNode {
        node_id: 6,
        npc_text: b"Just that someone read your name on a list and it didn't \
                   come with a special reason. The city doesn't explain itself \
                   to anyone. That's the only kind of neutral there is here.",
        choices: &[
            ConvChoice {
                text: b"Seven. That's something.",
                next_node: NODE_EXIT,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"I'd have preferred a reason.",
                next_node: NODE_EXIT,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
        ],
    },

    // Node 7 — Hypatia gone / travels light
    ConvNode {
        node_id: 7,
        npc_text: b"I always notice that light. Before sunrise, packed and gone \
                   -- I've seen her do it once before. She travels light. \
                   You might want to know that before you go to find her.",
        choices: &[
            ConvChoice {
                text: b"Travels light. Good to know.",
                next_node: NODE_EXIT,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 7, // F_HYPATIA_SOUGHT
                teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"Thank you, Elsa.",
                next_node: NODE_EXIT,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
        ],
    },

    // Node 8 — do you wish you'd gotten one
    ConvNode {
        node_id: 8,
        npc_text: b"No. Twenty years ago I thought it meant I had done \
                   something wrong. Now I understand it means the lottery \
                   hasn't looked hard enough at my address yet.",
        choices: &[
            ConvChoice {
                text: b"You think it's rigged.",
                next_node: 9,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"Fair.",
                next_node: NODE_EXIT,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
        ],
    },

    // Node 9 — rigged
    ConvNode {
        node_id: 9,
        npc_text: b"I think some questions have answers that change what \
                   you can still do about them. I'll leave that one to you.",
        choices: &[
            ConvChoice {
                text: b"Fair.",
                next_node: NODE_EXIT,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
        ],
    },
];

// ── HYPATIA (0000_0451) — Scene 0002 "Destiny Calls" ─────────────────────────
//
// She is at Castle Azoth.  She was notified the same day the player was.
// She already made enough tea.  She has been preparing for months.
// Alzedroswune: precision is ontology, not performance.
// Wu (Process/Way): she teaches process, not recipe.

pub static TREE_HYPATIA: ConvTree = ConvTree {
    entity_id: b"0000_0451",
    nodes: HYPATIA_NODES,
};

static HYPATIA_NODES: &[ConvNode] = &[

    // Node 0 — entry
    ConvNode {
        node_id: 0,
        npc_text: b"Come in. I made enough tea.",
        choices: &[
            ConvChoice {
                text: b"How did you know I was coming?",
                next_node: 1,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"I got a letter from the castle.",
                next_node: 2,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"What are you going to teach me?",
                next_node: 3,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"Are you already packed?",
                next_node: 4,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"Thank you.",
                next_node: 5,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
        ],
    },

    // Node 1 — how did you know
    ConvNode {
        node_id: 1,
        npc_text: b"I was notified the same day you were, from a different letter. \
                   The draw goes to both parties in parallel. \
                   I've been waiting to see who they'd send.",
        choices: &[
            ConvChoice {
                text: b"What were you expecting?",
                next_node: 6,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"What will you teach me?",
                next_node: 3,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"Why you as the mentor?",
                next_node: 7,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
        ],
    },

    // Node 2 — I got a letter
    ConvNode {
        node_id: 2,
        npc_text: b"I know. So did I. They wrote to the mentor and the \
                   apprentice at the same time. \
                   I've been preparing for this for a few months.",
        choices: &[
            ConvChoice {
                text: b"Preparing how?",
                next_node: 8,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"What will you teach me?",
                next_node: 3,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"What happens now?",
                next_node: 4,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
        ],
    },

    // Node 3 — what will you teach
    ConvNode {
        node_id: 3,
        npc_text: b"Alchemy, first. How materials transform. How to read a process \
                   instead of following a recipe. Later, depending on what you \
                   turn out to be good at, other things.",
        choices: &[
            ConvChoice {
                text: b"How do you work? What should I know?",
                next_node: 9,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"I'm ready.",
                next_node: 10,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
        ],
    },

    // Node 4 — are you packed / what now
    ConvNode {
        node_id: 4,
        npc_text: b"Pack lightly if you can. Whatever you can carry without \
                   a second trip. Nothing you can't afford to lose. \
                   Alchemy tools if you have any. I'll supply the rest.",
        choices: &[
            ConvChoice {
                text: b"How long will we be there?",
                next_node: 11,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"I'll be ready.",
                next_node: 10,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
        ],
    },

    // Node 5 — thank you / sit down
    ConvNode {
        node_id: 5,
        npc_text: b"Sit down. We have things to discuss and the tea is \
                   better while it's warm.",
        choices: &[
            ConvChoice {
                text: b"What will you teach me?",
                next_node: 3,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"What should I know about you?",
                next_node: 9,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
        ],
    },

    // Node 6 — what were you expecting
    ConvNode {
        node_id: 6,
        npc_text: b"Someone the lottery had the sense to pick. You're here.",
        choices: &[
            ConvChoice {
                text: b"That's a generous read.",
                next_node: 3,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"What will you teach me?",
                next_node: 3,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
        ],
    },

    // Node 7 — why you as mentor
    ConvNode {
        node_id: 7,
        npc_text: b"I've been in the Royal Ring's orbit for two years. The mentor \
                   slot requires someone the Ring can trust to handle the process. \
                   I have a record. The record is adequate.",
        choices: &[
            ConvChoice {
                text: b"Two years in the Ring.",
                next_node: 12,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"Understood.",
                next_node: 3,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
        ],
    },

    // Node 8 — preparing how
    ConvNode {
        node_id: 8,
        npc_text: b"Material sets. Reagents that travel well. I left some things \
                   with neighbors who will need them more than I will. \
                   The kind of preparation you do when you know you're leaving.",
        choices: &[
            ConvChoice {
                text: b"You seem calm about it.",
                next_node: 13,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"What will you teach me?",
                next_node: 3,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
        ],
    },

    // Node 9 — how you work
    ConvNode {
        node_id: 9,
        npc_text: b"I work in the mornings. I don't explain things twice, \
                   but I do explain them once very carefully. \
                   I'll tell you when you've made a mistake \
                   and I won't say it again after.",
        choices: &[
            ConvChoice {
                text: b"That seems fair.",
                next_node: 10,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"What if I make the same mistake twice?",
                next_node: 14,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
        ],
    },

    // Node 10 — THE DAGGER (quest 0002 advance)
    // Gives the dagger (item ID 1 = 0001_KLIT) and completes quest 0002.
    ConvNode {
        node_id: 10,
        npc_text: b"This belonged to my teacher. I want you to hold onto it \
                   for me. Someone will come asking for it. When they do -- \
                   don't agree immediately. Think about what they're offering \
                   and why.",
        choices: &[
            ConvChoice {
                text: b"I'll keep it safe.",
                next_node: NODE_EXIT,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: b"0002_KLST",
                quest_op: QuestOp::Complete,
                sets_flag: 0, teaches_perk: 0,
                gives_item: 1, // item slot 1 = the dagger (0001_KLIT)
            },
            ConvChoice {
                text: b"Why me?",
                next_node: 15,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
        ],
    },

    // Node 11 — how long
    ConvNode {
        node_id: 11,
        npc_text: b"I don't know. I've learned not to estimate. There are things \
                   that need to happen in a specific order and the order takes \
                   as long as it takes.",
        choices: &[
            ConvChoice {
                text: b"Understood.",
                next_node: 10,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
        ],
    },

    // Node 12 — two years in the ring
    ConvNode {
        node_id: 12,
        npc_text: b"It is. I made choices that made it necessary. \
                   I don't regret them.",
        choices: &[
            ConvChoice {
                text: b"What's down there that needs that long?",
                next_node: 16,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"Understood.",
                next_node: 3,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
        ],
    },

    // Node 13 — you seem calm
    ConvNode {
        node_id: 13,
        npc_text: b"The calm is earned, not given.",
        choices: &[
            ConvChoice {
                text: b"I'll remember that.",
                next_node: 3,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
        ],
    },

    // Node 14 — same mistake twice
    ConvNode {
        node_id: 14,
        npc_text: b"Then I'll explain it once more very carefully and hope the \
                   second time creates something the first didn't. I've been \
                   wrong about what a person can learn before. \
                   I prefer to be wrong in that direction.",
        choices: &[
            ConvChoice {
                text: b"That's generous.",
                next_node: 10,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
            ConvChoice {
                text: b"I'll try not to need it.",
                next_node: 10,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
        ],
    },

    // Node 15 — why me (dagger)
    ConvNode {
        node_id: 15,
        npc_text: b"Because you came here. Because you haven't left. \
                   Because you're asking the right questions.",
        choices: &[
            ConvChoice {
                text: b"I'll hold it.",
                next_node: NODE_EXIT,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: b"0002_KLST",
                quest_op: QuestOp::Complete,
                sets_flag: 0, teaches_perk: 0,
                gives_item: 1,
            },
        ],
    },

    // Node 16 — what's in the ring
    ConvNode {
        node_id: 16,
        npc_text: b"Something being born. Something that requires the chain to \
                   close correctly. My job is to make sure the chain closes \
                   correctly. That's all I'll say until you have the context \
                   to understand the rest.",
        choices: &[
            ConvChoice {
                text: b"I'll learn the context.",
                next_node: 3,
                quest_req: 0, quest_state: QS_ANY,
                flag_req: &[], flag_absent: &[],
                quest_action: &[], quest_op: QuestOp::None,
                sets_flag: 0, teaches_perk: 0, gives_item: 0,
            },
        ],
    },
];
