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
<head><title>Quantum Quackery Divine Arts</title></head>
<body>
<h1>Quantum Quackery Divine Arts</h1>
<p>Studio 42/6  Est. 2021  quantumquackery.org</p>
<hr>
<p>To carry the flame of diverse human culture in times uncertain.</p>
<hr>
<h2>The Atelier</h2>
<p>Virtual Game Development Studio. A 3D voxel environment for building worlds
in Ko's Labyrinth and the 31-game anthology. Runs the Djinnflow Kernel,
the Kobra coding environment, and the deterministic Shygazun translation engine.</p>
<a href="local://atelier.html">Download the Atelier</a>
<h2>Ko's Labyrinth</h2>
<p>Game 7 of 31. Lapidus -- the Overworld. You are Hypatia's apprentice.
The Royal Lottery has drawn your name.</p>
<a href="local://labyrinth.html">Enter the Labyrinth</a>
<h2>Shygazun</h2>
<p>A constructed natural language. Its byte table is canonical and load-bearing.
Every word traces back to a Primordial root. 38 tongues enumerated.
Kaelshunshikeaninsuy is the authoring hub of DjinnOS.</p>
<a href="local://shygazun.html">Explore Shygazun</a>
<h2>Photonic Synthesis</h2>
<p>Ontic-Channel Isomorphism. The correspondence between the structure
of light and the structure of consciousness.</p>
<a href="local://synthesis.html">Enter Photonic Synthesis</a>
<hr>
<p>Faerie -- Kyompufwun -- the changeling browser running inside DjinnOS.</p>
</body>
</html>
"#;

const ATELIER: &[u8] = br#"<!DOCTYPE html>
<html>
<head><title>The Atelier -- Quantum Quackery Divine Arts</title></head>
<body>
<h1>The Atelier</h1>
<p>Quantum Quackery Divine Arts  Virtual Game Development Studio</p>
<hr>
<p>A 3D voxel environment for building worlds in Ko's Labyrinth and the
31-game anthology. Runs the Djinnflow Kernel, the Kobra coding environment,
and the deterministic Shygazun translation engine -- locally, on your machine.</p>
<p>v0.1.3  Latest Release</p>
<hr>
<h2>Downloads</h2>
<h3>Windows</h3>
<a href="https://github.com/quantumquackerydivinearts-cell/DjinnOS-Shyagzun/releases/download/v0.1.3/atelier-desktop-0.1.0-x64.exe">Download for Windows (.exe)</a>
<h3>Android</h3>
<a href="https://github.com/quantumquackerydivinearts-cell/DjinnOS-Shyagzun/releases/download/v0.1.3/atelier-android-v0.1.3-debug.apk">Download for Android (.apk sideload)</a>
<h3>Full Suite</h3>
<a href="https://github.com/quantumquackerydivinearts-cell/DjinnOS-Shyagzun/releases/download/v0.1.2/atelier-suite-v0.1.2-secure.zip">Full Suite (.zip, all platforms)</a>
<h3>Web App</h3>
<a href="https://atelier.quantumquackery.com">Open in Browser (no install)</a>
<hr>
<h2>What It Contains</h2>
<p>3D Voxel Renderer. Kobra Environment. Shygazun Translation Engine.
Djinnflow Kernel. Guild and Studio System. Sequential Art Tooling.
Tile Placement Network. Wand Encryption.</p>
<hr>
<a href="local://home.html">Back to QQVA</a>
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

const SYNTHESIS: &[u8] = br#"<!DOCTYPE html>
<html>
<head><title>Photonic Synthesis -- Quantum Quackery Divine Arts</title></head>
<body>
<h1>Photonic Synthesis</h1>
<p>Ontic-Channel Isomorphism  Quantum Quackery Divine Arts</p>
<hr>
<p>The isomorphism between Shygazun language and photonic computation.
Learning Shygazun and learning photonic computation are the same act
of identity resonance with the void-ian substrate, approached from
phenomenological and physical sides simultaneously.</p>
<hr>
<h2>The Correspondence</h2>
<p>Lotus elemental fields: Shak (Fire) = Strong Nuclear. Puf (Air) = Weak Nuclear.
Mel (Water) = Electromagnetic. Zot (Earth) = Gravitational.</p>
<p>Rose spectral vectors as direct spectral encoding in photonic medium.</p>
<p>Daisy photonic circuit architecture: Gates (Ro), membranes (Gl), scaffolds (To),
networks (Ne), switches (Nz), valves (Sho).</p>
<p>Aster quantum optical chirality: photon spin angular momentum is genuinely
asymmetric and cannot be derived from other properties.</p>
<p>Cannabis: the observer as formal participant in the system. The layer where
the student becomes the instrument.</p>
<hr>
<a href="local://shygazun.html">Shygazun Literary Companion</a>
<a href="local://home.html">Back to QQVA</a>
</body>
</html>
"#;

// ── Seed function ─────────────────────────────────────────────────────────────

pub fn seed() {
    write_if_absent(b"home.html",       HOME);
    write_if_absent(b"atelier.html",    ATELIER);
    write_if_absent(b"labyrinth.html",  LABYRINTH);
    write_if_absent(b"wiltoll.html",    WILTOLL);
    write_if_absent(b"azonithia.html",  AZONITHIA);
    write_if_absent(b"shygazun.html",   SHYGAZUN);
    write_if_absent(b"synthesis.html",  SYNTHESIS);
}

fn write_if_absent(name: &[u8], content: &[u8]) {
    static mut PROBE: [u8; 1] = [0u8; 1];
    let n = crate::sa::read_file(name, unsafe { &mut PROBE });
    if n == 0 {
        crate::sa::write_file(name, content);
    }
}
