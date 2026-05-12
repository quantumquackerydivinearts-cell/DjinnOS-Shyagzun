// http_building.rs -- Queried collapse routing: first-person building.
//
// Two render modes:
//   HTTP (external browser) -- canvas raycaster + JS collapse routing
//   djinn:// (Faerie)       -- text-based rooms + link navigation
//
// djinn:// URL scheme:
//   djinn://building            foyer (all corridors visible)
//   djinn://building/garden     navigate to garden
//   djinn://building/library    navigate to library
//   djinn://building/workshop   navigate to workshop
//   djinn://building/lab        navigate to laboratory
//   djinn://building/info       navigate to information desk
//   djinn://building?q=WORDS    collapse routing from foyer

extern crate alloc;
use alloc::vec::Vec;
use alloc::string::String;

// ── Public entry points ───────────────────────────────────────────────────────

/// Called from http_intel for HTTP requests (external browser).
pub fn try_handle(path: &str) -> Option<Vec<u8>> {
    match path {
        "/building" | "/building/"       => Some(http_response(include_bytes!("building.html"))),
        "/whitepaper" | "/whitepaper/"   => Some(http_response(include_bytes!("whitepaper.html"))),
        _ => None,
    }
}

/// Called from browser.rs fetch_djinn for djinn:// requests (Faerie — text mode).
/// path_bytes is everything after "djinn://building" — e.g. "/garden" or "?q=games"
pub fn faerie_handle(path_bytes: &[u8]) -> Vec<u8> {
    crate::intel::init();
    let path = core::str::from_utf8(path_bytes).unwrap_or("");

    // Parse query string (?q=...)
    let (room_path, query) = if let Some(i) = path.find('?') {
        let qs = &path[i+1..];
        let q = if qs.starts_with("q=") {
            url_decode(&qs[2..])
        } else {
            String::new()
        };
        (&path[..i], q)
    } else {
        (path, String::new())
    };

    // Collapse routing: compute room activations
    let acts = collapse(&query);

    let room = match room_path.trim_matches('/') {
        "garden"   => Room::Garden,
        "library"  => Room::Library,
        "workshop" => Room::Workshop,
        "lab"      => Room::Lab,
        "info"     => Room::Info,
        _          => Room::Foyer,
    };

    render_room(room, &acts, &query)
}

// ── Rooms ─────────────────────────────────────────────────────────────────────

#[derive(Clone, Copy, PartialEq)]
enum Room { Foyer, Garden, Library, Workshop, Lab, Info }

struct Activations { garden: f32, library: f32, workshop: f32, lab: f32, info: f32 }

impl Activations {
    fn for_room(&self, r: Room) -> f32 {
        match r {
            Room::Garden   => self.garden,
            Room::Library  => self.library,
            Room::Workshop => self.workshop,
            Room::Lab      => self.lab,
            Room::Info     => self.info,
            Room::Foyer    => 0.5,
        }
    }
}

// Keyword collapse routing (inline, no network needed)
fn collapse(query: &str) -> Activations {
    let q = query.to_lowercase();
    let words: Vec<&str> = q.split(|c: char| !c.is_alphanumeric()).filter(|s| s.len() > 1).collect();

    let garden_kw   = ["garden","lotus","rose","sakura","daisy","cannabis","kael","grow","life","seed","flower","plant","nature","organic","living","bloom","generative"];
    let library_kw  = ["library","dragon","virus","bacteria","archaeplastida","knowledge","book","learn","memory","archive","history","lore","encode","organism","sequence","record","fossil"];
    let workshop_kw = ["workshop","topology","fold","phase","kobra","build","make","create","produce","tool","structure","scaffold","atelier","production","design","craft","forge","scene"];
    let lab_kw      = ["lab","laboratory","gradient","curvature","prion","blood","experiment","research","discover","compute","semantic","hopfield","collapse","field","energy","transform"];
    let info_kw     = ["info","about","who","what","where","help","contact","company","studio","qqva","quantum","quackery","moon","grapevine","network","this","here","us","we"];

    let score = |kws: &[&str]| -> f32 {
        let mut s = 0.0f32;
        for word in &words {
            for kw in kws {
                if word.contains(kw) || kw.contains(*word) { s += 0.4; }
            }
        }
        s.min(1.0)
    };

    let g = score(&garden_kw);
    let l = score(&library_kw);
    let w = score(&workshop_kw);
    let x = score(&lab_kw);
    let i = score(&info_kw);
    let max = [g,l,w,x,i].iter().cloned().fold(0.001f32, f32::max);

    Activations {
        garden:   g / max,
        library:  l / max,
        workshop: w / max,
        lab:      x / max,
        info:     i / max,
    }
}

// ── Room renderer (Faerie text mode) ─────────────────────────────────────────

fn render_room(room: Room, acts: &Activations, query: &str) -> Vec<u8> {
    let mut out = Vec::new();
    push(&mut out, b"<!DOCTYPE html><html><head><meta charset='utf-8'>");
    push(&mut out, b"<style>");
    push(&mut out, b"body{background:#080610;color:#c0b0d8;font-family:monospace;font-size:14px;padding:20px;max-width:700px;line-height:1.6}");
    push(&mut out, b"h1{font-size:18px;letter-spacing:3px;margin-bottom:4px}");
    push(&mut out, b".dim{color:#302048}.lit{font-weight:bold}.bar{color:#1a1030;user-select:none}");
    push(&mut out, b"a{text-decoration:none;padding:2px 0}.sep{color:#1a1030;margin:0 6px}");
    push(&mut out, b".corridor{display:block;padding:6px 0;border-bottom:1px solid #0e0820}");
    push(&mut out, b".query-hint{color:#403058;font-size:12px;margin-top:16px;border-top:1px solid #0e0820;padding-top:12px}");
    push(&mut out, b".content{margin:16px 0;color:#a090c8;border-left:2px solid #2a1850;padding-left:12px}");
    push(&mut out, b".suggest{display:inline-block;margin:4px 4px 0 0;padding:3px 10px;background:#100820;border:1px solid #2a1040}");
    push(&mut out, b"</style></head><body>");

    // Room header
    let (room_color, room_name, room_desc) = room_meta(room);
    push(&mut out, b"<h1 style='color:");
    push(&mut out, room_color);
    push(&mut out, b"'>");
    push(&mut out, room_name);
    push(&mut out, b"</h1>");
    push(&mut out, b"<div class='dim' style='margin-bottom:16px'>");
    push(&mut out, room_desc);
    push(&mut out, b"</div>");

    // Room content
    push(&mut out, b"<div class='content'>");
    push_room_content(&mut out, room, query);
    push(&mut out, b"</div>");

    // Corridors / navigation
    push(&mut out, b"<div style='margin-top:16px'>");
    push(&mut out, b"<div class='dim' style='font-size:11px;margin-bottom:8px'>corridors</div>");

    let corridors: &[(Room, &str, &str, &str)] = &[
        (Room::Garden,   "#80d080",  "djinn://building/garden",   "GARDEN"),
        (Room::Library,  "#d05050",  "djinn://building/library",  "LIBRARY"),
        (Room::Workshop, "#5090d0",  "djinn://building/workshop", "WORKSHOP"),
        (Room::Lab,      "#d09040",  "djinn://building/lab",      "LABORATORY"),
        (Room::Info,     "#a080d0",  "djinn://building/info",     "INFORMATION DESK"),
        (Room::Foyer,    "#c0b0d8",  "djinn://building",          "FOYER"),
    ];

    for (r, color, href, label) in corridors {
        if *r == room { continue; }
        let act = acts.for_room(*r);
        let is_lit = act > 0.35;
        push(&mut out, b"<a class='corridor' href='");
        push(&mut out, href.as_bytes());
        push(&mut out, b"' style='color:");
        if is_lit { push(&mut out, color.as_bytes()); } else { push(&mut out, b"#302048"); }
        push(&mut out, b"'>");
        // Activation bar
        let bars = (act * 8.0) as usize;
        push(&mut out, b"[");
        for i in 0..8 { if i < bars { push(&mut out, b"#"); } else { push(&mut out, b" "); } }
        push(&mut out, b"] ");
        push(&mut out, label.as_bytes());
        if is_lit { push(&mut out, b" <span style='font-size:11px'>(lit)</span>"); }
        push(&mut out, b"</a>");
    }
    push(&mut out, b"</div>");

    // Suggested queries
    push(&mut out, b"<div style='margin-top:16px'>");
    push(&mut out, b"<div class='dim' style='font-size:11px;margin-bottom:6px'>ask something</div>");
    let suggestions = room_suggestions(room);
    for s in suggestions {
        push(&mut out, b"<a class='suggest dim' href='djinn://building?q=");
        let sq = s.replace(' ', "+");
        push(&mut out, str_bytes(&sq));
        push(&mut out, b"'>");
        push(&mut out, s.as_bytes());
        push(&mut out, b"</a>");
    }
    push(&mut out, b"</div>");

    // Current query context
    if !query.is_empty() {
        push(&mut out, b"<div class='query-hint'>last query: <span style='color:#6040a0'>");
        push(&mut out, query.as_bytes());
        push(&mut out, b"</span><br>navigate: type djinn://building?q=your+question in the URL bar</div>");
    } else {
        push(&mut out, b"<div class='query-hint'>navigate: type djinn://building?q=your+question in the URL bar</div>");
    }

    push(&mut out, b"</body></html>");
    out
}

fn room_meta(room: Room) -> (&'static [u8], &'static [u8], &'static [u8]) {
    match room {
        Room::Foyer    => (b"#c0b0d8", b"FOYER",            b"You are at the entrance. All corridors lead from here."),
        Room::Garden   => (b"#80d080", b"GARDEN",           b"Growth. Generative life. The Lotus-to-Cannabis spectrum."),
        Room::Library  => (b"#d05050", b"LIBRARY",          b"Encoded knowledge. Void-organisms. Dragon Tongue archives."),
        Room::Workshop => (b"#5090d0", b"WORKSHOP",         b"Structural production. Topology, Fold, Phase. Where things are made."),
        Room::Lab      => (b"#d09040", b"LABORATORY",       b"Energy landscapes. Gradient and Curvature. Prion self-templating."),
        Room::Info     => (b"#a080d0", b"INFORMATION DESK", b"What this place is. Who built it. What it is for."),
    }
}

fn push_room_content(out: &mut Vec<u8>, room: Room, _query: &str) {
    match room {
        Room::Foyer => {
            push(out, b"This is Quantum Quackery Virtual Atelier.<br><br>");
            push(out, b"A building navigated by what you ask, not by where you click.<br>");
            push(out, b"Type a question in the URL bar. The corridors respond.<br><br>");
            push(out, b"Ask about the games. Ask about the language. Ask about the studio.");
        }
        Room::Garden => {
            push(out, b"Where things begin and return to begin again.<br><br>");
            push(out, b"The Shygazun byte table starts here -- Lotus at byte 0, Cannabis at 184.<br>");
            push(out, b"Every akinen grew from this ground.<br><br>");
            push(out, b"The 31-game Ko's Labyrinth series lives in this register.");
        }
        Room::Library => {
            push(out, b"Ko's Labyrinth: 31 games, one world, one language.<br><br>");
            push(out, b"Game 7 is current: Ko's Labyrinth -- The Royal Lottery.<br>");
            push(out, b"Hypatia, a Royal Ring survivor, navigates Azonithia.<br><br>");
            push(out, b"The Dragon Tongue void-organisms encode the game's cosmology.");
        }
        Room::Workshop => {
            push(out, b"Studio 42/6. QQVA production tools.<br><br>");
            push(out, b"Kobra: scene expression language running in the kernel.<br>");
            push(out, b"Render lab: voxel-to-triangle export, AMD GPU rendering.<br>");
            push(out, b"Atelier: the full authoring stack for the KLGS series.");
        }
        Room::Lab => {
            push(out, b"The semantic substrate lives here.<br><br>");
            push(out, b"Hopfield network over 1358 Shygazun candidates.<br>");
            push(out, b"Queried collapse routing: you are using it right now.<br><br>");
            push(out, b"This building navigates by energy descent, not hyperlinks.");
        }
        Room::Info => {
            push(out, b"Quantum Quackery Virtual Atelier -- Studio 42/6.<br><br>");
            push(out, b"Building games, tools, and language infrastructure<br>");
            push(out, b"for the Ko's Labyrinth series (31 games) and beyond.<br><br>");
            push(out, b"Contact: quantumquackery.org");
        }
    }
}

fn room_suggestions(room: Room) -> &'static [&'static str] {
    match room {
        Room::Foyer    => &["what games do you make", "what is Shygazun", "what is the studio", "show me the lab"],
        Room::Garden   => &["tell me about the games", "what is the byte table", "what is Kael", "Cannabis tongue"],
        Room::Library  => &["who is Hypatia", "what is the Royal Ring", "game 7 story", "Dragon Tongue"],
        Room::Workshop => &["what is Kobra", "how does the atelier work", "voxel rendering", "Studio 42"],
        Room::Lab      => &["how does collapse routing work", "what is Hopfield", "byte table geometry", "Djinn modes"],
        Room::Info     => &["distribution policy", "what is QQVA", "what is QQDA", "how to play the games"],
    }
}

// ── Utilities ─────────────────────────────────────────────────────────────────

fn push(out: &mut Vec<u8>, s: &[u8]) { out.extend_from_slice(s); }

fn str_bytes(s: &str) -> &[u8] { s.as_bytes() }

fn url_decode(s: &str) -> String {
    let mut out = String::new();
    let bytes = s.as_bytes();
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i] == b'+' { out.push(' '); i += 1; }
        else if bytes[i] == b'%' && i+2 < bytes.len() {
            let hi = hex_val(bytes[i+1]);
            let lo = hex_val(bytes[i+2]);
            if hi < 16 && lo < 16 { out.push((hi*16+lo) as char); i += 3; }
            else { out.push('%'); i += 1; }
        } else { out.push(bytes[i] as char); i += 1; }
    }
    out
}

fn hex_val(b: u8) -> u8 {
    match b {
        b'0'..=b'9' => b - b'0',
        b'a'..=b'f' => b - b'a' + 10,
        b'A'..=b'F' => b - b'A' + 10,
        _ => 255,
    }
}

fn http_response(body: &[u8]) -> Vec<u8> {
    let mut r = Vec::new();
    r.extend_from_slice(b"HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\nContent-Length: ");
    let mut tmp = [0u8; 12];
    let mut n = body.len() as u32; let mut i = 0;
    if n == 0 { tmp[0] = b'0'; i = 1; }
    else { while n > 0 { tmp[i] = b'0'+(n%10) as u8; i+=1; n/=10; } tmp[..i].reverse(); }
    r.extend_from_slice(&tmp[..i]);
    r.extend_from_slice(b"\r\n\r\n");
    r.extend_from_slice(body);
    r
}
