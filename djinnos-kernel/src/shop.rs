// shop.rs — Shop system for Ko's Labyrinth (7_KLGS).
//
// Two distinct shop types:
//
//   ShopKind::PlayerOwned  — the player IS the proprietor.
//     They set stock, set prices, open/close for customers, and may buy
//     from suppliers to restock.  NPC customers auto-resolve via Barter check.
//
//   ShopKind::NpcOwned     — an NPC owns the shop.
//     The player visits as a customer.  Barter skill discounts prices.
//     NPC shops have their own inventory managed by world state.
//
// Coin unit: mark (smallest Lapidus denomination).

use crate::input::Key;
use crate::gpu::GpuSurface;
use crate::render2d::It;
use crate::style;

// ── Stock entry ────────────────────────────────────────────────────────────────

const MAX_STOCK: usize = 32;

#[derive(Copy, Clone)]
pub struct StockEntry {
    pub item_id: u16,
    pub count:   u16,
    pub price:   u16,   // base price in marks
}

impl StockEntry {
    const EMPTY: Self = Self { item_id: 0, count: 0, price: 0 };
    pub fn is_empty(&self) -> bool { self.item_id == 0 }
}

// ── NPC shop registry ─────────────────────────────────────────────────────────
//
// NPC shops are defined statically.  Each has a name and a default stock.
// Actual runtime stock lives in NpcShopState (Sa-persisted).

// Item ID shorthands used in shop stock (numeric part of _KLIT entity IDs).
// These match kos_labyrnth.py §11.5 Item Registry exactly.
const ITEM_HEALTH_POTION:   u16 = 0x0001;  // 0001_KLIT
const ITEM_CHERRY:          u16 = 0x0002;  // 0002_KLIT
const ITEM_APPLE:           u16 = 0x0003;  // 0003_KLIT
const ITEM_POMEGRANATE:     u16 = 0x0004;  // 0004_KLIT
const ITEM_BARLEY:          u16 = 0x0005;  // 0005_KLIT
const ITEM_PINE_NEEDLE:     u16 = 0x0006;  // 0006_KLIT
const ITEM_BASIC_TINCTURE:  u16 = 0x0022;  // 0034_KLIT (craftable)
const ITEM_RESTORE_TINCT:   u16 = 0x0023;  // 0035_KLIT (craftable)
const ITEM_DAGGER:          u16 = 0x0011;  // 0017_KLIT
const ITEM_ARROW:           u16 = 0x0015;  // 0021_KLIT

#[derive(Copy, Clone, PartialEq)]
pub enum NpcShopId {
    GoldshootMarket,      // Temple District + Goldshoot — commerce and faith
    TempleApothecary,     // Temple District — medicinal goods
    HopefarePawnbroker,   // Slum pawnshop (Hopefare district) — buys almost anything
    AlchemistWorkshop,    // Rare alchemical objects and reagents
    // Three June Street markets ("where people actually live"):
    JuneProvisions,       // Food, produce, everyday staples
    JuneArmsAndTools,     // Weapons, tools, working gear
    JuneHerbalist,        // Herbs, tinctures, folk remedies
}

struct NpcShopDef {
    id:    NpcShopId,
    name:  &'static str,
    // Default stock: (item_id, count, base_price_in_marks)
    stock: &'static [(u16, u16, u16)],
}

const NPC_SHOPS: &[NpcShopDef] = &[
    NpcShopDef {
        id:   NpcShopId::GoldshootMarket,
        name: "Goldshoot Market",
        stock: &[
            (ITEM_BASIC_TINCTURE, 4, 18),
            (ITEM_CHERRY,         8,  2),
            (ITEM_APPLE,          6,  3),
        ],
    },
    NpcShopDef {
        id:   NpcShopId::TempleApothecary,
        name: "Temple Apothecary",
        stock: &[
            (ITEM_HEALTH_POTION,  3, 30),
            (ITEM_RESTORE_TINCT,  2, 45),
            (ITEM_BASIC_TINCTURE, 5, 15),
        ],
    },
    NpcShopDef {
        id:   NpcShopId::HopefarePawnbroker,
        name: "Hopefare Pawnbroker",
        stock: &[
            (ITEM_DAGGER,  2, 35),
            (ITEM_ARROW,  12,  2),
        ],
    },
    NpcShopDef {
        id:   NpcShopId::AlchemistWorkshop,
        name: "Alchemist's Workshop",
        stock: &[
            // Alchemist sells objects (KLOB), not items (KLIT).
            // Object purchases go to workbench, not KLIT inventory.
            // Using ITEM IDs here as stand-ins until object inventory is separate:
            (ITEM_BASIC_TINCTURE,  2, 25),
            (ITEM_RESTORE_TINCT,   1, 60),
        ],
    },
    // ── Three June Street markets ─────────────────────────────────────────────
    NpcShopDef {
        id:   NpcShopId::JuneProvisions,
        name: "June Provisions (June St.)",
        stock: &[
            (ITEM_CHERRY,       12,  2),
            (ITEM_APPLE,        10,  3),
            (ITEM_POMEGRANATE,   6,  5),
            (ITEM_BARLEY,       20,  1),
        ],
    },
    NpcShopDef {
        id:   NpcShopId::JuneArmsAndTools,
        name: "June Arms & Tools (June St.)",
        stock: &[
            (ITEM_DAGGER,  3, 30),
            (ITEM_ARROW,  20,  2),
        ],
    },
    NpcShopDef {
        id:   NpcShopId::JuneHerbalist,
        name: "June Herbalist (June St.)",
        stock: &[
            (ITEM_PINE_NEEDLE,    8,  3),
            (ITEM_BASIC_TINCTURE, 4, 14),
            (ITEM_HEALTH_POTION,  2, 25),
        ],
    },
];

// ── Shop kind / mode ──────────────────────────────────────────────────────────

#[derive(Copy, Clone, PartialEq)]
pub enum ShopKind { PlayerOwned, NpcOwned(NpcShopId) }

#[derive(Copy, Clone, PartialEq)]
enum ViewMode { Manage, Browse }   // Manage = proprietor mgmt; Browse = customer view

// ── Ledger ────────────────────────────────────────────────────────────────────

#[derive(Copy, Clone, Default)]
pub struct Ledger {
    pub earned: u32,
    pub spent:  u32,
    pub txns:   u16,
}

// ── Main shop state ───────────────────────────────────────────────────────────

pub struct Shop {
    pub kind:     ShopKind,
    pub mode:     ViewMode,

    // Player-owned shop
    pub stock:    [StockEntry; MAX_STOCK],
    pub stock_n:  usize,
    pub open:     bool,
    pub ledger:   Ledger,

    // NPC shop view (filled from NpcShopDef when opening an NPC shop)
    pub npc_stock:   [StockEntry; MAX_STOCK],
    pub npc_stock_n: usize,
    pub npc_name:    [u8; 32],
    pub npc_name_n:  usize,

    pub coin:         u32,   // player's coin (shared across both kinds)
    pub cursor:       usize,
    pub price_edit:   bool,
    pub price_buf:    [u8; 6],
    pub price_n:      usize,
    pub exited:       bool,
    rule_y:           u32,
}

static mut SHOP: Shop = Shop {
    kind:     ShopKind::PlayerOwned,
    mode:     ViewMode::Manage,
    stock:    [StockEntry::EMPTY; MAX_STOCK],
    stock_n:  0,
    open:     false,
    ledger:   Ledger { earned: 0, spent: 0, txns: 0 },
    npc_stock:   [StockEntry::EMPTY; MAX_STOCK],
    npc_stock_n: 0,
    npc_name:    [0u8; 32],
    npc_name_n:  0,
    coin:     50,
    cursor:   0,
    price_edit: false,
    price_buf: [0u8; 6],
    price_n:  0,
    exited:   false,
    rule_y:   0,
};

pub fn shop() -> &'static mut Shop { unsafe { &mut SHOP } }

static mut REQ: bool = false;
pub fn request_open()    { unsafe { REQ = true; } }
pub fn consume_request() -> bool { unsafe { let r = REQ; REQ = false; r } }

// ── Shop impl ─────────────────────────────────────────────────────────────────

impl Shop {
    /// Open the player's own shop management view.
    pub fn open_player_shop(&mut self, rule_y: u32) {
        self.kind   = ShopKind::PlayerOwned;
        self.mode   = ViewMode::Manage;
        self.rule_y = rule_y;
        self.exited = false;
        self.cursor = 0;
        self.price_edit = false;
    }

    /// Open an NPC-owned shop.  Player is the customer.
    pub fn open_npc_shop(&mut self, rule_y: u32, id: NpcShopId) {
        self.kind   = ShopKind::NpcOwned(id);
        self.mode   = ViewMode::Browse;
        self.rule_y = rule_y;
        self.exited = false;
        self.cursor = 0;
        self.npc_stock_n = 0;

        // Load NPC stock from definition.
        if let Some(def) = NPC_SHOPS.iter().find(|d| d.id == id) {
            let n = def.name.as_bytes();
            let nl = n.len().min(32);
            self.npc_name[..nl].copy_from_slice(&n[..nl]);
            self.npc_name_n = nl;
            for &(item_id, count, base_price) in def.stock {
                if self.npc_stock_n >= MAX_STOCK { break; }
                // Barter discount: skill rank + O (Ostentation) VITRIOL modifier.
                // O VITRIOL 5 (neutral) = no bonus. O VITRIOL 10 = +5% extra off.
                let barter   = crate::player_state::skill_rank(crate::skills::SKILL_BARTER_IDX);
                let o_mod    = crate::skills::vitriol_mod(crate::skills::SKILL_BARTER_IDX).max(0) as u32;
                let discount = ((barter as u32 / 10) * 5 + o_mod).min(45);
                let price = ((base_price as u32 * (100 - discount)) / 100).max(1) as u16;
                self.npc_stock[self.npc_stock_n] = StockEntry { item_id, count, price };
                self.npc_stock_n += 1;
            }
        }
    }

    pub fn exited(&self) -> bool { self.exited }

    // ── Player-shop management ────────────────────────────────────────────────

    pub fn list_item(&mut self, item_id: u16, count: u16, price: u16) -> bool {
        if !crate::player_state::inv_remove(item_id, count) { return false; }
        for i in 0..self.stock_n {
            if self.stock[i].item_id == item_id {
                self.stock[i].count  = self.stock[i].count.saturating_add(count);
                self.stock[i].price  = price;
                return true;
            }
        }
        if self.stock_n >= MAX_STOCK { return false; }
        self.stock[self.stock_n] = StockEntry { item_id, count, price };
        self.stock_n += 1;
        true
    }

    pub fn delist(&mut self, idx: usize) {
        if idx >= self.stock_n { return; }
        crate::player_state::inv_add(self.stock[idx].item_id, self.stock[idx].count);
        for i in idx..self.stock_n - 1 { self.stock[i] = self.stock[i + 1]; }
        self.stock[self.stock_n - 1] = StockEntry::EMPTY;
        self.stock_n -= 1;
        if self.cursor > 0 && self.cursor >= self.stock_n { self.cursor -= 1; }
    }

    /// NPC customer buys from the player's shop (auto-resolve).
    pub fn npc_buys(&mut self, idx: usize, count: u16) -> bool {
        if idx >= self.stock_n { return false; }
        let e = &self.stock[idx];
        if e.count < count { return false; }
        let revenue = (e.price as u32) * (count as u32);
        self.coin += revenue;
        self.stock[idx].count -= count;
        if self.stock[idx].count == 0 { self.delist(idx); }
        self.ledger.earned += revenue;
        self.ledger.txns   += 1;
        true
    }

    // ── Player buying from NPC shop ───────────────────────────────────────────

    pub fn player_buys_from_npc(&mut self, idx: usize, count: u16) -> bool {
        if idx >= self.npc_stock_n { return false; }
        let e = &self.npc_stock[idx];
        let cost = (e.price as u32) * (count as u32);
        if self.coin < cost || e.count < count { return false; }
        self.coin -= cost;
        crate::player_state::inv_add(e.item_id, count);
        self.npc_stock[idx].count -= count;
        if self.npc_stock[idx].count == 0 {
            let n = self.npc_stock_n;
            for i in idx..n-1 { self.npc_stock[i] = self.npc_stock[i+1]; }
            self.npc_stock[n-1] = StockEntry::EMPTY;
            self.npc_stock_n -= 1;
            if self.cursor > 0 && self.cursor >= self.npc_stock_n { self.cursor -= 1; }
        }
        self.ledger.spent += cost;
        self.ledger.txns  += 1;
        crate::eigenstate::advance(crate::eigenstate::T_GRAPEVINE);
        true
    }

    // ── Key handling ──────────────────────────────────────────────────────────

    pub fn handle_key(&mut self, key: Key) {
        match (self.kind, self.mode) {
            (ShopKind::PlayerOwned, ViewMode::Manage)  => self.key_manage(key),
            (ShopKind::PlayerOwned, ViewMode::Browse)  => self.key_browse_own(key),
            (ShopKind::NpcOwned(_), _)                 => self.key_browse_npc(key),
        }
    }

    fn key_manage(&mut self, key: Key) {
        if self.price_edit {
            match key {
                Key::Char(c) if c >= b'0' && c <= b'9' && self.price_n < 5 => {
                    self.price_buf[self.price_n] = c; self.price_n += 1;
                }
                Key::Backspace => { if self.price_n > 0 { self.price_n -= 1; } }
                Key::Enter => {
                    let p = parse_u16(&self.price_buf[..self.price_n]);
                    if self.cursor < self.stock_n { self.stock[self.cursor].price = p; }
                    self.price_edit = false;
                }
                Key::Escape => { self.price_edit = false; }
                _ => {}
            }
            return;
        }
        match key {
            Key::Up    => { if self.cursor > 0 { self.cursor -= 1; } }
            Key::Down  => { if self.cursor + 1 < self.stock_n { self.cursor += 1; } }
            Key::Char(b'p') | Key::Char(b'P') => {
                if self.cursor < self.stock_n { self.price_edit = true; self.price_n = 0; }
            }
            Key::Char(b'd') | Key::Char(b'D') => self.delist(self.cursor),
            Key::Char(b'o') | Key::Char(b'O') => self.open = !self.open,
            Key::Char(b'v') | Key::Char(b'V') => {
                // Toggle to customer preview of own shop
                self.mode = ViewMode::Browse; self.cursor = 0;
            }
            Key::Escape => { self.exited = true; }
            _ => {}
        }
    }

    fn key_browse_own(&mut self, key: Key) {
        match key {
            Key::Up    => { if self.cursor > 0 { self.cursor -= 1; } }
            Key::Down  => { if self.cursor + 1 < self.stock_n { self.cursor += 1; } }
            Key::Escape => { self.mode = ViewMode::Manage; self.cursor = 0; }
            _ => {}
        }
    }

    fn key_browse_npc(&mut self, key: Key) {
        match key {
            Key::Up    => { if self.cursor > 0 { self.cursor -= 1; } }
            Key::Down  => { if self.cursor + 1 < self.npc_stock_n { self.cursor += 1; } }
            Key::Enter | Key::Char(b'b') | Key::Char(b'B') => {
                self.player_buys_from_npc(self.cursor, 1);
            }
            Key::Escape => { self.exited = true; }
            _ => {}
        }
    }

    // ── Render ────────────────────────────────────────────────────────────────

    pub fn render(&self, gpu: &dyn GpuSurface) {
        let it  = It::new(gpu);
        let t   = style::get();
        let top = self.rule_y + 8;
        it.fill(0, top, gpu.width(), gpu.height().saturating_sub(top), t.bg);
        match (self.kind, self.mode) {
            (ShopKind::PlayerOwned, ViewMode::Manage)  => self.render_manage(&it, &t, top),
            (ShopKind::PlayerOwned, ViewMode::Browse)  => self.render_browse(&it, &t, top,
                &self.stock, self.stock_n, "Your Shop (Preview)"),
            (ShopKind::NpcOwned(_), _) => {
                let name = core::str::from_utf8(&self.npc_name[..self.npc_name_n])
                    .unwrap_or("Shop");
                self.render_browse(&it, &t, top, &self.npc_stock, self.npc_stock_n, name)
            }
        }
    }

    fn render_manage(&self, it: &It, t: &style::Theme, top: u32) {
        let title = if self.open { "Your Shop — OPEN" } else { "Your Shop — Closed" };
        it.text(40, top + 4,  title, 2, if self.open { t.accent } else { t.text_dim });
        // Coin
        let mut cb = [0u8; 12]; let cn = write_u32(&mut cb, self.coin);
        it.text(40, top + 28, "Marks: ", 1, t.text_dim);
        it.text(96, top + 28, core::str::from_utf8(&cb[..cn]).unwrap_or("?"), 1, t.accent);
        // Ledger summary
        let mut eb = [0u8; 12]; let en = write_u32(&mut eb, self.ledger.earned);
        it.text(200, top + 28, "Earned: ", 1, t.text_dim);
        it.text(256, top + 28, core::str::from_utf8(&eb[..en]).unwrap_or("?"), 1, t.text);

        it.text(40, top + 46, "Item               Count  Price", 1, t.text_dim);
        for i in 0..self.stock_n {
            let e   = &self.stock[i];
            let col = if i == self.cursor { t.accent } else { t.text };
            let y   = top + 60 + i as u32 * 14;
            it.text(44, y, item_name_short(e.item_id), 1, col);
            let mut nb = [0u8;6]; let nn = write_u16(&mut nb, e.count);
            it.text(188, y, core::str::from_utf8(&nb[..nn]).unwrap_or("?"), 1, col);
            let mut pb = [0u8;6]; let pn = write_u16(&mut pb, e.price);
            it.text(228, y, core::str::from_utf8(&pb[..pn]).unwrap_or("?"), 1, col);
        }
        if self.stock_n == 0 {
            it.text(44, top + 60, "(empty — use 'list_item' from shell to stock)", 1, t.text_dim);
        }
        if self.price_edit {
            let pe_s = core::str::from_utf8(&self.price_buf[..self.price_n]).unwrap_or("");
            it.text(44, top + 60 + self.stock_n as u32 * 14 + 4, "New price: ", 1, t.accent);
            it.text(148, top + 60 + self.stock_n as u32 * 14 + 4, pe_s, 1, t.accent);
        }
        let cy = top + 60 + MAX_STOCK as u32 * 14 + 4;
        it.text(40, cy,     "[P]rice  [D]elist  [O]open/close  [V]preview  Esc=back", 1, t.text_dim);
    }

    fn render_browse(&self, it: &It, t: &style::Theme, top: u32,
                     stock: &[StockEntry; MAX_STOCK], n: usize, title: &str)
    {
        it.text(40, top + 4, title, 2, t.header);
        // Coin
        let mut cb = [0u8;12]; let cn = write_u32(&mut cb, self.coin);
        it.text(40, top + 28, "Your marks: ", 1, t.text_dim);
        it.text(148, top + 28, core::str::from_utf8(&cb[..cn]).unwrap_or("?"), 1, t.accent);

        it.text(40, top + 46, "Item               Count  Price", 1, t.text_dim);
        for i in 0..n {
            let e   = &stock[i];
            let col = if i == self.cursor { t.accent } else { t.text };
            let y   = top + 60 + i as u32 * 14;
            it.text(44, y, item_name_short(e.item_id), 1, col);
            let mut nb = [0u8;6]; let nn = write_u16(&mut nb, e.count);
            it.text(188, y, core::str::from_utf8(&nb[..nn]).unwrap_or("?"), 1, col);
            let mut pb = [0u8;6]; let pn = write_u16(&mut pb, e.price);
            it.text(228, y, core::str::from_utf8(&pb[..pn]).unwrap_or("?"), 1, col);
        }
        if n == 0 { it.text(44, top + 60, "(nothing for sale)", 1, t.text_dim); }
        let cy = top + 60 + MAX_STOCK as u32 * 14 + 4;
        it.text(40, cy, "[B/Enter]=buy 1  Esc=back", 1, t.text_dim);
    }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

fn item_name_short(id: u16) -> &'static str {
    match id {
        0x0001 => "Health Potion",
        0x0002 => "Cherry",
        0x0003 => "Apple",
        0x0004 => "Pomegranate",
        0x0005 => "Barley",
        0x0006 => "Pine Needle",
        0x000E => "Ring",
        0x000F => "Ingot",
        0x0010 => "Coin",
        0x0011 => "Dagger",
        0x0012 => "Sword",
        0x0015 => "Arrow",
        0x0022 => "Basic Tincture",
        0x0023 => "Restorative Tincture",
        0x0024 => "Desire Fragment",
        0x0025 => "Infernal Salve",
        0x0026 => "Angelic Salve",
        _      => "???",
    }
}

fn parse_u16(s: &[u8]) -> u16 {
    let mut n = 0u32;
    for &b in s { if b < b'0' || b > b'9' { break; } n = n * 10 + (b - b'0') as u32; }
    n.min(9999) as u16
}

fn write_u16(buf: &mut [u8], v: u16) -> usize {
    if v == 0 { if !buf.is_empty() { buf[0] = b'0'; } return 1; }
    let mut tmp = [0u8;5]; let mut n = 0; let mut x = v;
    while x > 0 { tmp[n] = b'0' + (x % 10) as u8; n += 1; x /= 10; }
    for i in 0..n { buf[i] = tmp[n-1-i]; }
    n
}

fn write_u32(buf: &mut [u8], v: u32) -> usize {
    if v == 0 { if !buf.is_empty() { buf[0] = b'0'; } return 1; }
    let mut tmp = [0u8;10]; let mut n = 0; let mut x = v;
    while x > 0 { tmp[n] = b'0' + (x % 10) as u8; n += 1; x /= 10; }
    for i in 0..n { buf[i] = tmp[n-1-i]; }
    n
}
