// faerie_pages.rs -- Initial Faerie-safe local:// pages for DjinnOS.
//
// Seeded into the Sa volume at first boot.  Accessible via local:// URLs.
// Format: Faerie-safe HTML -- a subset of HTML understood by the browser,
// extended with ko: link prefixes for Kobra expression dispatch.
//
// Page format:
//   Standard HTML tags: h1 h2 p a ul li hr
//   Link href="local://page.html"   -- navigate to Sa-local page
//   Link href="ko:expression"       -- evaluate Kobra, render result or navigate
//   Link href="http(s)://..."       -- Kyom proxy fetch
//   No CSS, no <script>, no images.
//
// Canonical local:// pages:
//   home.html         -- DjinnOS / QQVA welcome
//   labyrinth.html    -- Ko's Labyrinth portal (7_KLGS)
//   wiltoll.html      -- Wiltoll Lane (game 7 starting zone)
//   azonithia.html    -- Azonithia Avenue

// ── Page definitions ──────────────────────────────────────────────────────────

const HOME: &[u8] = br#"<!DOCTYPE html>
<html>
<head><title>Quantum Quackery Virtual Atelier</title></head>
<body>
<h1>Quantum Quackery Virtual Atelier</h1>
<p>Studio 42/6. Games, sequential art, constructed language.</p>
<hr>
<h2>Ko's Labyrinth</h2>
<p>A 31-game anthology. You are Hypatia's apprentice.
The Royal Lottery has drawn your name.</p>
<a href="local://labyrinth.html">Enter the Labyrinth</a>
<hr>
<h2>Shygazun</h2>
<p>A constructed natural language. Its byte table is canonical and load-bearing.
Every word traces back to a Primordial root.</p>
<a href="local://shygazun.html">Browse the byte table</a>
<hr>
<p>Faerie Browser -- Kyompufwun -- the changeling that brings you what lives elsewhere.</p>
</body>
</html>
"#;

const LABYRINTH: &[u8] = br#"<!DOCTYPE html>
<html>
<head><title>Ko's Labyrinth -- 7_KLGS</title></head>
<body>
<h1>Ko's Labyrinth</h1>
<p>Game 7 of 31. Lapidus -- the Overworld. You are in the labyrinth now.</p>
<hr>
<h2>Where are you?</h2>
<a href="local://wiltoll.html">Wiltoll Lane -- your home</a>
<a href="local://azonithia.html">Azonithia Avenue</a>
<hr>
<h2>Situation</h2>
<p>The Royal Lottery has selected your name. You have until the next
drawing to clear the Sulphera rings or be conscripted to Castle Azoth.</p>
<p>Hypatia is somewhere in the labyrinth. You are her apprentice.
Find her before the Alfir's window closes.</p>
<hr>
<a href="local://home.html">Back to QQVA</a>
</body>
</html>
"#;

const WILTOLL: &[u8] = br#"<!DOCTYPE html>
<html>
<head><title>Wiltoll Lane -- 7_KLGS</title></head>
<body>
<h1>Wiltoll Lane</h1>
<p>The eastern end of Lapidus, where the lane meets the foot of Mt. Elaene.
Lush near the mountain, spare near Azonithia Avenue. Morning fog.</p>
<hr>
<h2>You can see</h2>
<p>Your house. The lane stretching west toward the city.
A figure by the treeline -- Sidhal, carrying something.</p>
<hr>
<h2>What do you do?</h2>
<a href="ko:quest status 0003_KLST">Check on Sidhal</a>
<a href="local://azonithia.html">Walk toward Azonithia Avenue</a>
<a href="local://labyrinth.html">Back to situation</a>
</body>
</html>
"#;

const AZONITHIA: &[u8] = br#"<!DOCTYPE html>
<html>
<head><title>Azonithia Avenue -- 7_KLGS</title></head>
<body>
<h1>Azonithia Avenue</h1>
<p>The main artery of Lapidus. Castle Azoth to the west, Wiltoll Lane
to the east. 4.5 miles. The city breathes here.</p>
<hr>
<h2>Districts along the avenue (west to east)</h2>
<p>Heartvein Heights and Youthspring -- the wealthy quarter near the castle.</p>
<p>Temple district and Goldshoot -- commerce and faith intertwined.</p>
<p>Markets and June -- where people actually live.</p>
<p>Slums: Hopefare, Orebustle, Mt. Hieronymus at the far eastern end.</p>
<hr>
<h2>You can go</h2>
<a href="local://wiltoll.html">East -- back to Wiltoll Lane</a>
<a href="local://labyrinth.html">Back to situation</a>
</body>
</html>
"#;

const SHYGAZUN: &[u8] = br#"<!DOCTYPE html>
<html>
<head><title>Shygazun -- the language</title></head>
<body>
<h1>Shygazun</h1>
<p>A constructed natural language. Its byte table is canonical and load-bearing.
Not flavor text. The word for the existence of the series itself is Wunashako.</p>
<hr>
<h2>First cluster -- Tongues 1-8</h2>
<p>Lotus (T1) -- Earth/Water/Air/Fire/presence/being. The elemental register.</p>
<p>Rose (T2) -- Numbers 0-11 base-12 and Primordial priors.</p>
<p>Sakura (T3) -- Spatial. The six voxel faces. Structural types Va/Vo/Vi/Vy.</p>
<p>Daisy (T4) -- Structural/mechanical. Scaffold, membrane, network, bond.</p>
<p>AppleBlossom (T5) -- Elemental compounds. Mind+/Space+/Time+.</p>
<p>Aster (T6) -- Temporal/spatial operations. Linear/loop/fold/frozen time.</p>
<p>Grapevine (T7) -- Data, networking, files. Sa/Sao/Seth/Samos/Myrun/Kyom.</p>
<p>Cannabis (T8) -- Consciousness and awareness. Soa/Sei/Suy/An/In.</p>
<hr>
<a href="local://home.html">Back to QQVA</a>
</body>
</html>
"#;

// ── Seed function ─────────────────────────────────────────────────────────────

pub fn seed() {
    write_if_absent(b"home.html",      HOME);
    write_if_absent(b"labyrinth.html", LABYRINTH);
    write_if_absent(b"wiltoll.html",   WILTOLL);
    write_if_absent(b"azonithia.html", AZONITHIA);
    write_if_absent(b"shygazun.html",  SHYGAZUN);
}

fn write_if_absent(name: &[u8], content: &[u8]) {
    static mut PROBE: [u8; 1] = [0u8; 1];
    let n = crate::sa::read_file(name, unsafe { &mut PROBE });
    if n == 0 {
        crate::sa::write_file(name, content);
    }
}
