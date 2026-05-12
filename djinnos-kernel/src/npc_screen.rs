// npc_screen.rs — NPC dialogue screen for Ko's Labyrinth (7_KLGS).
//
// Two modes:
//
//  Tree mode  — entity has a ConvTree in dialogue_tree.rs.
//               Fallout layout: portrait left | NPC text upper-right | choices lower-right.
//               Player selects numbered choices; invisible gates filter the list.
//               On selection: side effects applied, advance to next node.
//
//  Topic mode — entity has no tree (ambient/CoilState pool lines).
//               Legacy topic-selector layout.  NPC name + topic menu + line display.
//
// Both modes route through the same open() entry point; the screen detects
// which system to use and sets Phase accordingly.

use crate::input::Key;
use crate::gpu::GpuSurface;
use crate::render2d::It;
use crate::style;
use crate::agent::InteractionKind;
use crate::dialogue;
use crate::dialogue_tree::{self, ConvChoice, QuestOp, NODE_EXIT};

// ── Phase ────────────────────────────────────────────────────────────────────

#[derive(Copy, Clone, PartialEq)]
enum Phase {
    Tree,       // Fallout-style branching tree
    Topics,     // legacy topic selector
    ShowLine,   // legacy: showing a single returned line
}

// ── Sizes/layout constants ────────────────────────────────────────────────────

const PORTRAIT_W:  u32 = 220;
const PAD:         u32 = 12;
const CHOICE_H:    u32 = 18;

// ── Topic (legacy) ────────────────────────────────────────────────────────────

#[derive(Copy, Clone)]
struct Topic {
    kind:    InteractionKind,
    label:   [u8; 36],
    label_n: usize,
}

impl Topic {
    fn new(kind: InteractionKind) -> Self {
        let s: &[u8] = match kind {
            InteractionKind::Dialogue        => b"Greet",
            InteractionKind::QuestOffer      => b"Ask about work...",
            InteractionKind::QuestAdvance    => b"How is it going?",
            InteractionKind::QuestComplete   => b"I finished it.",
            InteractionKind::TeachSkill      => b"Teach me.",
            InteractionKind::LoreAccess      => b"Tell me more...",
            InteractionKind::MeditationGuide => b"Guide me in meditation.",
            _ => b"Talk",
        };
        let mut t = Self { kind, label: [0u8; 36], label_n: 0 };
        let n = s.len().min(35);
        t.label[..n].copy_from_slice(&s[..n]);
        t.label_n = n;
        t
    }
}

// ── NpcScreen ────────────────────────────────────────────────────────────────

pub struct NpcScreen {
    pub exited:  bool,
    rule_y:      u32,
    entity_id:   [u8; 16],
    entity_n:    usize,
    npc_name:    [u8; 32],
    name_n:      usize,
    phase:       Phase,

    // ── Tree state ───────────────────────────────────────────────────────────
    tree_node_id:   u16,
    vis_choices:    [u8; 8],   // indices into node.choices[]
    vis_choice_n:   usize,
    tree_cursor:    usize,

    // ── Topic state (legacy) ─────────────────────────────────────────────────
    topics:     [Topic; 8],
    topic_n:    usize,
    cursor:     usize,

    // ── ShowLine state (legacy) ───────────────────────────────────────────────
    text:            [u8; 512],
    text_n:          usize,
    pending_quest:   [u8; 12],
    pending_quest_n: usize,
    pending_perk:    u8,
    pending_kind:    InteractionKind,

    // ── Shared ───────────────────────────────────────────────────────────────
    msg:    [u8; 64],
    msg_n:  usize,
}

static mut NPC_SCR: NpcScreen = NpcScreen {
    exited:   false,
    rule_y:   0,
    entity_id: [0u8; 16],
    entity_n:  0,
    npc_name:  [0u8; 32],
    name_n:    0,
    phase:     Phase::Tree,
    tree_node_id:  0,
    vis_choices:   [0u8; 8],
    vis_choice_n:  0,
    tree_cursor:   0,
    topics:    [Topic { kind: InteractionKind::Dialogue, label: [0u8; 36], label_n: 0 }; 8],
    topic_n:   0,
    cursor:    0,
    text:            [0u8; 512],
    text_n:          0,
    pending_quest:   [0u8; 12],
    pending_quest_n: 0,
    pending_perk:    0,
    pending_kind:    InteractionKind::Dialogue,
    msg:    [0u8; 64],
    msg_n:  0,
};

pub fn screen() -> &'static mut NpcScreen { unsafe { &mut NPC_SCR } }

static mut NPC_REQ: bool = false;
pub fn request()         { unsafe { NPC_REQ = true; } }
pub fn consume_request() -> bool { unsafe { let r = NPC_REQ; NPC_REQ = false; r } }

// ── Helpers ───────────────────────────────────────────────────────────────────

impl NpcScreen {
    fn entity_id_slice(&self) -> &[u8] { &self.entity_id[..self.entity_n] }

    fn set_met_flag(&self) {
        use crate::ko_flags;
        match self.entity_id_slice() {
            b"0020_TOWN" => ko_flags::ko_set(ko_flags::F_SIDHAL_MET),
            b"0006_WTCH" => ko_flags::ko_set(ko_flags::F_ALFIR_MET),
            _ => {}
        }
    }

    fn build_quest_flag_lists(&self) -> ([(u32, u8); 32], [u32; 64]) {
        let ps = crate::player_state::get();
        let mut aq = [(0u32, 0u8); 32];
        for i in 0..ps.quest_count as usize {
            let slug = &ps.quests[i].slug;
            if let Some(n) = crate::ko_flags::quest_num(slug) {
                aq[i] = (n as u32, ps.quests[i].state);
            }
        }
        let mut fl = [0u32; 64];
        let mut fi = 0usize;
        for flag in 0u8..=255 {
            if crate::ko_flags::ko_test(flag) && fi < 64 {
                fl[fi] = flag as u32;
                fi += 1;
            }
        }
        (aq, fl)
    }
}

// ── Open ──────────────────────────────────────────────────────────────────────

impl NpcScreen {
    pub fn open(&mut self, rule_y: u32, entity_id: &[u8]) {
        self.rule_y = rule_y;
        self.exited = false;
        self.msg_n  = 0;
        self.text_n = 0;
        self.pending_quest_n = 0;
        self.pending_perk    = 0;

        let n = entity_id.len().min(16);
        self.entity_id[..n].copy_from_slice(&entity_id[..n]);
        self.entity_n = n;

        if let Some(p) = crate::npc_placements::npc_by_id(entity_id) {
            let nn = p.name.len().min(31);
            self.npc_name[..nn].copy_from_slice(&p.name[..nn]);
            self.name_n = nn;
        } else {
            self.npc_name[0] = b'?';
            self.name_n = 1;
        }

        self.set_met_flag();

        // If a conversation tree exists for this entity, use Tree mode.
        if dialogue_tree::find_tree(entity_id).is_some() {
            self.phase = Phase::Tree;
            self.tree_node_id = 0;
            self.tree_cursor  = 0;
            self.refresh_tree_choices();
        } else {
            self.phase = Phase::Topics;
            self.build_topics();
        }
    }
}

// ── Tree mode ─────────────────────────────────────────────────────────────────

impl NpcScreen {
    fn refresh_tree_choices(&mut self) {
        self.vis_choice_n = 0;
        let tree = match dialogue_tree::find_tree(self.entity_id_slice()) {
            Some(t) => t,
            None    => return,
        };
        let node = match tree.find_node(self.tree_node_id) {
            Some(n) => n,
            None    => return,
        };
        let (aq, fl) = self.build_quest_flag_lists();
        for (i, choice) in node.choices.iter().enumerate() {
            if dialogue_tree::choice_visible(choice, &aq, &fl) {
                if self.vis_choice_n < 8 {
                    self.vis_choices[self.vis_choice_n] = i as u8;
                    self.vis_choice_n += 1;
                }
            }
        }
        if self.tree_cursor >= self.vis_choice_n {
            self.tree_cursor = 0;
        }
    }

    fn select_tree_choice(&mut self, vis_idx: usize) {
        if vis_idx >= self.vis_choice_n { return; }
        let choice_idx = self.vis_choices[vis_idx] as usize;
        let tree = match dialogue_tree::find_tree(self.entity_id_slice()) {
            Some(t) => t,
            None    => { self.exited = true; return; }
        };
        let node = match tree.find_node(self.tree_node_id) {
            Some(n) => n,
            None    => { self.exited = true; return; }
        };
        if choice_idx >= node.choices.len() { return; }
        let choice: &'static ConvChoice = &node.choices[choice_idx];

        // Apply side effects.
        self.apply_tree_effects(choice);

        // Advance.
        if choice.next_node == NODE_EXIT {
            self.exited = true;
        } else {
            self.tree_node_id = choice.next_node;
            self.tree_cursor  = 0;
            self.refresh_tree_choices();
        }
    }

    fn apply_tree_effects(&mut self, choice: &'static ConvChoice) {
        // Quest action.
        if !choice.quest_action.is_empty() {
            match choice.quest_op {
                QuestOp::Offer    => { crate::quest_tracker::offer(choice.quest_action); }
                QuestOp::Accept   => { crate::quest_tracker::accept(choice.quest_action); }
                QuestOp::Complete => { crate::quest_tracker::complete(choice.quest_action); }
                QuestOp::None     => {}
            }
        }
        // Flag.
        if choice.sets_flag != 0 {
            crate::ko_flags::ko_set(choice.sets_flag);
        }
        // Perk.
        if choice.teaches_perk != 0 {
            let _ = crate::skills::unlock_perk_by_id(choice.teaches_perk);
        }
        // Item.
        if choice.gives_item != 0 {
            let _ = crate::player_state::inv_add(choice.gives_item, 1);
        }
    }

    fn tree_key(&mut self, key: Key) {
        match key {
            Key::Escape => { self.exited = true; }
            Key::Up     => {
                if self.tree_cursor > 0 { self.tree_cursor -= 1; }
                else if self.vis_choice_n > 0 {
                    self.tree_cursor = self.vis_choice_n - 1;
                }
            }
            Key::Down   => {
                if self.vis_choice_n > 0 {
                    self.tree_cursor = (self.tree_cursor + 1).min(self.vis_choice_n - 1);
                }
            }
            Key::Enter  => { let c = self.tree_cursor; self.select_tree_choice(c); }
            Key::Char(b'1') => { self.select_tree_choice(0); }
            Key::Char(b'2') => { self.select_tree_choice(1); }
            Key::Char(b'3') => { self.select_tree_choice(2); }
            Key::Char(b'4') => { self.select_tree_choice(3); }
            Key::Char(b'5') => { self.select_tree_choice(4); }
            Key::Char(b'6') => { self.select_tree_choice(5); }
            Key::Char(b'7') => { self.select_tree_choice(6); }
            Key::Char(b'8') => { self.select_tree_choice(7); }
            _ => {}
        }
    }
}

// ── Legacy topic mode ─────────────────────────────────────────────────────────

impl NpcScreen {
    fn build_topics(&mut self) {
        self.topic_n = 0;
        self.cursor  = 0;
        let (aq, fl) = self.build_quest_flag_lists();
        let mask = dialogue::available_kinds(self.entity_id_slice(), &aq, &fl);
        const ORDER: &[InteractionKind] = &[
            InteractionKind::Dialogue,
            InteractionKind::QuestOffer,
            InteractionKind::QuestAdvance,
            InteractionKind::QuestComplete,
            InteractionKind::LoreAccess,
            InteractionKind::TeachSkill,
            InteractionKind::MeditationGuide,
        ];
        for &kind in ORDER {
            if mask & (1 << kind as u8) != 0 && self.topic_n < 7 {
                self.topics[self.topic_n] = Topic::new(kind);
                self.topic_n += 1;
            }
        }
        if self.topic_n < 8 {
            let mut bye = Topic::new(InteractionKind::Dialogue);
            bye.label[..7].copy_from_slice(b"Goodbye");
            bye.label_n = 7;
            self.topics[self.topic_n] = bye;
            self.topic_n += 1;
        }
    }

    fn topics_key(&mut self, key: Key) {
        match key {
            Key::Escape => { self.exited = true; }
            Key::Up     => {
                if self.cursor > 0 { self.cursor -= 1; }
                else { self.cursor = self.topic_n.saturating_sub(1); }
            }
            Key::Down   => {
                if self.topic_n > 0 {
                    self.cursor = (self.cursor + 1).min(self.topic_n - 1);
                }
            }
            Key::Enter  => { self.select_topic(); }
            _ => {}
        }
    }

    fn select_topic(&mut self) {
        if self.cursor >= self.topic_n { return; }
        let topic = self.topics[self.cursor];
        if &topic.label[..topic.label_n.min(7)] == b"Goodbye" {
            self.exited = true;
            return;
        }
        let (aq, fl) = self.build_quest_flag_lists();
        let line = dialogue::select_npc_line(
            self.entity_id_slice(), topic.kind, &aq, &fl);
        if let Some(dl) = line {
            let n = dl.text.len().min(511);
            self.text[..n].copy_from_slice(&dl.text[..n]);
            self.text_n = n;
            self.pending_kind = topic.kind;
            let qn = dl.quest_action.len().min(12);
            self.pending_quest[..qn].copy_from_slice(&dl.quest_action[..qn]);
            self.pending_quest_n = qn;
            self.pending_perk    = dl.teaches_perk;
            self.phase = Phase::ShowLine;
        } else {
            self.set_msg(b"They have nothing to say about that right now.");
        }
    }

    fn line_key(&mut self, key: Key) {
        match key {
            Key::Enter | Key::Escape => {
                self.apply_line_side_effects();
                self.phase = Phase::Topics;
                self.build_topics();
                self.msg_n = 0;
            }
            _ => {}
        }
    }

    fn apply_line_side_effects(&mut self) {
        if self.pending_quest_n > 0 {
            let slug = &self.pending_quest[..self.pending_quest_n];
            match self.pending_kind {
                InteractionKind::QuestOffer    => {
                    crate::quest_tracker::offer(slug);
                    self.set_msg(b"New quest offered -- check your journal.");
                }
                InteractionKind::QuestAdvance  => { crate::quest_tracker::accept(slug); }
                InteractionKind::QuestComplete
                | InteractionKind::TeachSkill
                | InteractionKind::MeditationGuide => {
                    crate::quest_tracker::complete(slug);
                    self.set_msg(b"Quest completed.");
                }
                _ => {}
            }
            self.pending_quest_n = 0;
        }
        if self.pending_perk != 0 {
            let pid = self.pending_perk;
            self.pending_perk = 0;
            let _ = crate::skills::unlock_perk_by_id(pid);
        }
    }

    fn set_msg(&mut self, m: &[u8]) {
        let n = m.len().min(64);
        self.msg[..n].copy_from_slice(&m[..n]);
        self.msg_n = n;
    }
}

// ── Key dispatch ──────────────────────────────────────────────────────────────

impl NpcScreen {
    pub fn handle_key(&mut self, key: Key) {
        match self.phase {
            Phase::Tree     => self.tree_key(key),
            Phase::Topics   => self.topics_key(key),
            Phase::ShowLine => self.line_key(key),
        }
    }
}

// ── Render ────────────────────────────────────────────────────────────────────

impl NpcScreen {
    pub fn render(&self, gpu: &dyn GpuSurface) {
        match self.phase {
            Phase::Tree     => self.render_tree(gpu),
            Phase::Topics   => self.render_topics_screen(gpu),
            Phase::ShowLine => self.render_topics_screen(gpu),
        }
    }

    // ── Tree render (Fallout layout) ──────────────────────────────────────────
    //
    //  ┌──────────┬─────────────────────────────────────────┐
    //  │ portrait │  NPC NAME                               │
    //  │          ├─────────────────────────────────────────┤
    //  │          │  "NPC text here, word-wrapped..."       │
    //  │          │                                         │
    //  │          ├─────────────────────────────────────────┤
    //  │          │  1. choice one                          │
    //  │          │  2. choice two                          │
    //  │          │  3. choice three                        │
    //  └──────────┴─────────────────────────────────────────┘

    fn render_tree(&self, gpu: &dyn GpuSurface) {
        let it = It::new(gpu);
        let t  = style::warm_theme();
        let w  = gpu.width();
        let h  = gpu.height();
        let y0 = self.rule_y + 2;
        let area_h = h.saturating_sub(y0);

        // ── Portrait panel ────────────────────────────────────────────────────
        it.fill(0, y0, PORTRAIT_W, area_h, t.surface);
        // Portrait placeholder frame
        let pf_x = PAD;
        let pf_y = y0 + PAD;
        let pf_w = PORTRAIT_W - PAD * 2;
        let pf_h = (area_h / 2).min(200);
        it.fill(pf_x, pf_y, pf_w, pf_h, t.bg);
        it.fill(pf_x, pf_y, pf_w, 1, t.rule);
        it.fill(pf_x, pf_y + pf_h, pf_w, 1, t.rule);
        it.fill(pf_x, pf_y, 1, pf_h, t.rule);
        it.fill(pf_x + pf_w, pf_y, 1, pf_h, t.rule);
        // NPC name inside portrait box (centered)
        let name_str = core::str::from_utf8(&self.npc_name[..self.name_n]).unwrap_or("?");
        let nw = crate::truetype::inter_width(name_str, 14.0);
        let nx = (pf_x as i32 + (pf_w as i32 - nw) / 2).max(pf_x as i32);
        it.tt(nx, (pf_y + pf_h / 2) as i32, name_str, 14.0, t.header);

        // Divider
        it.fill(PORTRAIT_W, y0, 2, area_h, t.rule);

        // ── Content panel ─────────────────────────────────────────────────────
        let cx = PORTRAIT_W + PAD;
        let cw = w.saturating_sub(cx + PAD);

        // NPC name header
        it.fill(PORTRAIT_W + 2, y0, w.saturating_sub(PORTRAIT_W + 2), area_h, t.bg);
        it.tt(cx as i32, (y0 + 8) as i32, name_str, 17.0, t.header);
        it.fill(cx, y0 + 30, cw, 1, t.rule);

        // NPC text (word-wrapped)
        let text_y0 = y0 + 38;
        let npc_text = self.current_npc_text();
        let text_end_y = self.render_wrapped(
            &it, &t, cx as i32, text_y0 as i32, cw, npc_text, 13.0);

        // Separator before choices
        let sep_y = (text_end_y + 8) as u32;
        it.fill(cx, sep_y, cw, 1, t.rule);

        // Choices
        let mut cy = (sep_y + 8) as i32;
        for i in 0..self.vis_choice_n {
            if cy as u32 + CHOICE_H > h.saturating_sub(20) { break; }
            let choice_idx = self.vis_choices[i] as usize;
            let choice_text = self.choice_text_at(choice_idx);
            let sel = i == self.tree_cursor;
            let col = if sel { t.accent } else { t.text };
            // Cursor indicator
            if sel { it.tt(cx as i32, cy, ">", 13.0, t.accent); }
            // Number
            let num = match i {
                0 => "1.", 1 => "2.", 2 => "3.", 3 => "4.",
                4 => "5.", 5 => "6.", 6 => "7.", 7 => "8.",
                _ => "?.",
            };
            it.tt(cx as i32 + 10, cy, num, 13.0, col);
            // Choice text
            it.tt(cx as i32 + 26, cy, choice_text, 13.0, col);
            cy += CHOICE_H as i32;
        }

        // Status bar
        it.fill(0, h.saturating_sub(16), w, 16, t.surface);
        it.tt(8, h.saturating_sub(13) as i32,
              "Up/Down=select  1-8=pick  Enter=confirm  Esc=leave",
              11.0, t.text_dim);
    }

    fn current_npc_text(&self) -> &str {
        let tree = match dialogue_tree::find_tree(self.entity_id_slice()) {
            Some(t) => t, None => return "",
        };
        let node = match tree.find_node(self.tree_node_id) {
            Some(n) => n, None => return "",
        };
        core::str::from_utf8(node.npc_text).unwrap_or("")
    }

    fn choice_text_at(&self, choice_idx: usize) -> &str {
        let tree = match dialogue_tree::find_tree(self.entity_id_slice()) {
            Some(t) => t, None => return "",
        };
        let node = match tree.find_node(self.tree_node_id) {
            Some(n) => n, None => return "",
        };
        if choice_idx >= node.choices.len() { return ""; }
        core::str::from_utf8(node.choices[choice_idx].text).unwrap_or("")
    }

    // Renders word-wrapped text; returns the y coordinate after the last line.
    fn render_wrapped(
        &self,
        it:    &It,
        t:     &crate::style::Theme,
        x:     i32,
        y:     i32,
        w:     u32,
        text:  &str,
        px:    f32,
    ) -> i32 {
        let line_h = (px as i32) + 4;
        let cpl = ((w as f32) / (px * 0.55)).max(20.0) as usize;
        let bytes = text.as_bytes();
        let mut dy = y;
        let mut buf = [0u8; 160];
        let mut bn  = 0usize;
        let mut idx = 0usize;
        let mut lines = 0u32;
        while lines < 12 {
            if idx >= bytes.len() {
                if bn > 0 {
                    it.tt(x, dy, core::str::from_utf8(&buf[..bn]).unwrap_or(""), px, t.text);
                    dy += line_h;
                }
                break;
            }
            let ws = idx;
            while idx < bytes.len() && bytes[idx] != b' ' { idx += 1; }
            let wlen = idx - ws;
            while idx < bytes.len() && bytes[idx] == b' ' { idx += 1; }
            let need = if bn == 0 { wlen } else { 1 + wlen };
            if bn + need > cpl && bn > 0 {
                it.tt(x, dy, core::str::from_utf8(&buf[..bn]).unwrap_or(""), px, t.text);
                dy += line_h;
                lines += 1;
                bn = 0;
            }
            if bn > 0 && bn < 159 { buf[bn] = b' '; bn += 1; }
            let copy = wlen.min(159 - bn);
            if copy > 0 {
                buf[bn..bn+copy].copy_from_slice(&bytes[ws..ws+copy]);
                bn += copy;
            }
        }
        dy
    }

    // ── Topic/ShowLine render (legacy) ─────────────────────────────────────────

    fn render_topics_screen(&self, gpu: &dyn GpuSurface) {
        let it = It::new(gpu);
        let t  = style::get();
        let w  = gpu.width();
        let h  = gpu.height();
        let y0 = self.rule_y + 4;
        it.fill(0, y0, w, h.saturating_sub(y0), t.bg);

        let name = core::str::from_utf8(&self.npc_name[..self.name_n]).unwrap_or("?");
        it.text(20, y0 + 4, name, 2, t.header);
        it.fill(0, y0 + 22, w, 1, t.rule);

        if self.phase == Phase::Topics {
            let menu_y = y0 + 28;
            for i in 0..self.topic_n {
                let vy  = menu_y + i as u32 * 16;
                if vy + 16 >= h.saturating_sub(30) { break; }
                let sel = i == self.cursor;
                let col = if sel { t.accent } else { t.text };
                if sel { it.text(8, vy, ">", 1, t.accent); }
                let lbl = &self.topics[i].label[..self.topics[i].label_n];
                it.text(22, vy, core::str::from_utf8(lbl).unwrap_or("?"), 1, col);
            }
        } else {
            // ShowLine: word-wrapped line display
            let mut dy  = y0 + 28;
            let cpl = ((w.saturating_sub(40)) / 8) as usize;
            let mut buf = [0u8; 128];
            let mut bn  = 0usize;
            let mut idx = 0usize;
            let mut drawn = 0usize;
            let text_n = self.text_n;
            let mut tbuf = [0u8; 512];
            tbuf[..text_n].copy_from_slice(&self.text[..text_n]);
            let text = &tbuf[..text_n];
            while drawn < 12 {
                if idx >= text.len() {
                    if bn > 0 {
                        it.text(20, dy, core::str::from_utf8(&buf[..bn]).unwrap_or(""), 1, t.text);
                        drawn += 1;
                    }
                    break;
                }
                let ws = idx;
                while idx < text.len() && text[idx] != b' ' { idx += 1; }
                let wlen = idx - ws;
                while idx < text.len() && text[idx] == b' ' { idx += 1; }
                let need = if bn == 0 { wlen } else { 1 + wlen };
                if bn + need > cpl && bn > 0 {
                    it.text(20, dy, core::str::from_utf8(&buf[..bn]).unwrap_or(""), 1, t.text);
                    dy += 14;
                    drawn += 1;
                    bn = 0;
                }
                if bn > 0 && bn < 127 { buf[bn] = b' '; bn += 1; }
                let copy = wlen.min(127 - bn);
                if copy > 0 {
                    buf[bn..bn+copy].copy_from_slice(&text[ws..ws+copy]);
                    bn += copy;
                }
            }
            let tag: &str = match self.pending_kind {
                InteractionKind::QuestOffer      => "[QUEST OFFERED]",
                InteractionKind::QuestComplete   => "[QUEST COMPLETE]",
                InteractionKind::TeachSkill      => "[SKILL TAUGHT]",
                InteractionKind::MeditationGuide => "[MEDITATION GUIDANCE]",
                InteractionKind::LoreAccess      => "[LORE]",
                _                                => "",
            };
            if !tag.is_empty() {
                it.text(20, dy + 8, tag, 1, t.text_dim);
            }
        }

        if self.msg_n > 0 {
            let ms = core::str::from_utf8(&self.msg[..self.msg_n]).unwrap_or("");
            it.text(20, h.saturating_sub(24), ms, 1, t.accent);
        }
        it.fill(0, h.saturating_sub(14), w, 14, t.surface);
        let hint = if self.phase == Phase::Topics {
            "Up/Down=select  Enter=ask  Esc=leave"
        } else {
            "Enter=continue"
        };
        it.text(8, h.saturating_sub(12), hint, 1, t.text_dim);
    }
}
