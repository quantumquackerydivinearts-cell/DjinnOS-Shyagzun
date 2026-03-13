from __future__ import annotations

from typing import Final, Mapping, Sequence, TypedDict


class ShygazunByteEntry(TypedDict):
    decimal: int
    binary: str
    tongue: str
    symbol: str
    meaning: str


# Canonical language table source (authoritative).
# Format: Decimal,Binary,Tongue,Symbol,Meaning
# Note: rows are parsed with split(',', 4) so commas inside Meaning are preserved.
_BYTE_TABLE_CSV: Final[str] = """Decimal,Binary,Tongue,Symbol,Meaning
0,00000000,Lotus,Ty,Earth Initiator / material beginning
1,00000001,Lotus,Zu,Earth Terminator / empirical closure
2,00000010,Lotus,Ly,Water Initiator / feeling toward
3,00000011,Lotus,Mu,Water Terminator / memory from
4,00000100,Lotus,Fy,Air Initiator / thought toward
5,00000101,Lotus,Pu,Air Terminator / stasis / stuck
6,00000110,Lotus,Shy,Fire Initiator / pattern toward
7,00000111,Lotus,Ku,Fire Terminator / death / end
8,00001000,Lotus,Ti,Here / near presence
9,00001001,Lotus,Ta,Active being / presence
10,00001010,Lotus,Li,New / odd
11,00001011,Lotus,La,Tense / excited
12,00001100,Lotus,Fi,Known / context-sensitive
13,00001101,Lotus,Fa,Complex / old
14,00001110,Lotus,Shi,Related / clear
15,00001111,Lotus,Sha,Intellect of spirit
16,00010000,Lotus,Zo,Absence / passive non-being
17,00010001,Lotus,Mo,Relaxed / silent
18,00010010,Lotus,Po,Simple / new
19,00010011,Lotus,Ko,Experience / intuition
20,00010100,Lotus,Ze,There / far
21,00010101,Lotus,Me,Familiar / home
22,00010110,Lotus,Pe,Unknown / insensitive
23,00010111,Lotus,Ke,Incoherent / ill
24,00011000,Rose,Ru,Vector Lowest Red
25,00011001,Rose,Ot,Vector Orange
26,00011010,Rose,El,Vector Yellow
27,00011011,Rose,Ki,Vector Green
28,00011100,Rose,Fu,Vector Blue
29,00011101,Rose,Ka,Vector Indigo
30,00011110,Rose,AE,Vector Highest Violet
31,00011111,Rose,Gaoh,Number 12 / 0
32,00100000,Rose,Ao,Number 1
33,00100001,Rose,Ye,Number 2
34,00100010,Rose,Ui,Number 3
35,00100011,Rose,Shu,Number 4
36,00100100,Rose,Kiel,Number 5
37,00100101,Rose,Yeshu,Number 6
38,00100110,Rose,Lao,Number 7
39,00100111,Rose,Shushy,Number 8
40,00101000,Rose,Uinshu,Number 9
41,00101001,Rose,Kokiel,Number 10
42,00101010,Rose,Aonkiel,Number 11
43,00101011,Rose,Ha,Absolute Positive
44,00101100,Rose,Ga,Absolute Negative
45,00101101,Rose,Wu,Process / Way
46,00101110,Rose,Na,Neutral / Integration
47,00101111,Rose,Ung,Piece / Point
48,00110000,Sakura,Jy,Top
49,00110001,Sakura,Ji,Starboard
50,00110010,Sakura,Ja,Front
51,00110011,Sakura,Jo,Back
52,00110100,Sakura,Je,Port
53,00110101,Sakura,Ju,Bottom
54,00110110,Sakura,Dy,Hence / Heretofore
55,00110111,Sakura,Di,Traveling / Distancing
56,00111000,Sakura,Da,Meeting / Conjoined
57,00111001,Sakura,Do,Parting / Divorced
58,00111010,Sakura,De,Domesticating / Staying
59,00111011,Sakura,Du,Whither / Status of
60,00111100,Sakura,By,When-hence / Eventual
61,00111101,Sakura,Bi,Crowned / Owning
62,00111110,Sakura,Ba,Plain / Explicit
63,00111111,Sakura,Bo,Hidden / Occulted
64,01000000,Sakura,Be,Common / Outer / Wild
65,01000001,Sakura,Bu,Since / Relational
66,01000010,Sakura,Va,Order / Structure / Life
67,01000011,Sakura,Vo,Chaos / Boundary-breakage / Mutation
68,01000100,Sakura,Ve,Pieces / Not-wherever / Where
69,01000101,Sakura,Vu,Death-moment / Never / Now
70,01000110,Sakura,Vi,Body / Wherever / What
71,01000111,Sakura,Vy,Lifespan / Whenever / How
72,01001000,Daisy,Lo,Segments / Identity
73,01001001,Daisy,Yei,Component / Integrator
74,01001010,Daisy,Ol,Deadzone / Relative Void
75,01001011,Daisy,X,Joint / Interlock
76,01001100,Daisy,Yx,Fulcrum / Crux
77,01001101,Daisy,Go,Plug / Blocker
78,01001110,Daisy,Foa,Degree / Space
79,01001111,Daisy,Oy,Depths / Layers
80,01010000,Daisy,W,Freefall / Socket Space
81,01010001,Daisy,Th,Cuff / Indentation
82,01010010,Daisy,Kael,Cluster / Fruit / Flower
83,01010011,Daisy,Ro,Ion-channel / Gate / Receptor
84,01010100,Daisy,Gl,Membrane / Muscle
85,01010101,Daisy,To,Scaffold / Framework
86,01010110,Daisy,Ma,Web / Interchange
87,01010111,Daisy,Ne,Network / System
88,01011000,Daisy,Ym,Radial Space
89,01011001,Daisy,Nz,Switch / Circuit Actuator
90,01011010,Daisy,Sho,Valve / Fluid Actuator
91,01011011,Daisy,Hi,Lever / Radial Actuator
92,01011100,Daisy,Mh,Bond
93,01011101,Daisy,Zhi,Eye / Vortex
94,01011110,Daisy,Vr,Rotor / Tensor
95,01011111,Daisy,St,Surface
96,01100000,Daisy,Fn,Passage / Pathway
97,01100001,Daisy,N,Seed / Sheet / Fiber
98,01100010,AppleBlossom,A,Mind +
99,01100011,AppleBlossom,O,Mind -
100,01100100,AppleBlossom,I,Space +
101,01100101,AppleBlossom,E,Space -
102,01100110,AppleBlossom,Y,Time +
103,01100111,AppleBlossom,U,Time -
104,01101000,AppleBlossom,Shak,Fire
105,01101001,AppleBlossom,Puf,Air
106,01101010,AppleBlossom,Mel,Water
107,01101011,AppleBlossom,Zot,Earth
108,01101100,AppleBlossom,Zhuk,Plasma (Fire,Fire)
109,01101101,AppleBlossom,Kyzu,Sulphur (Fire,Air)
110,01101110,AppleBlossom,Alky,Alkahest / Alcohol (Fire,Water)
111,01101111,AppleBlossom,Kazho,Magma / Lava (Fire,Earth)
112,01110000,AppleBlossom,Puky,Smoke (Air,Fire)
113,01110001,AppleBlossom,Pyfu,Gas (Air,Air)
114,01110010,AppleBlossom,Mipa,Carbonation / Trapped Gas (Air,Water)
115,01110011,AppleBlossom,Zitef,Mercury (Air,Earth)
116,01110100,AppleBlossom,Shem,Steam (Water,Fire)
117,01110101,AppleBlossom,Lefu,Vapor (Water,Air)
118,01110110,AppleBlossom,Milo,Mixed fluids / Mixtures (Water,Water)
119,01110111,AppleBlossom,Myza,Erosion (Water,Earth)
120,01111000,AppleBlossom,Zashu,Radiation / Radioactive stones (Earth,Fire)
121,01111001,AppleBlossom,Fozt,Dust (Earth,Air)
122,01111010,AppleBlossom,Mazi,Sediment (Earth,Water)
123,01111011,AppleBlossom,Zaot,Salt (Earth,Earth)
128,10000000,Aster,Ry,Right-chiral red
129,10000001,Aster,Oth,Right-chiral orange
130,10000010,Aster,Le,Right-chiral yellow
131,10000011,Aster,Gi,Right-chiral green
132,10000100,Aster,Fe,Right-chiral blue
133,10000101,Aster,Ky,Right-chiral indigo
134,10000110,Aster,Alz,Right-chiral violet
135,10000111,Aster,Ra,Left-chiral red
136,10001000,Aster,Tho,Left-chiral orange
137,10001001,Aster,Lu,Left-chiral yellow
138,10001010,Aster,Ge,Left-chiral green
139,10001011,Aster,Fo,Left-chiral blue
140,10001100,Aster,Kw,Left-chiral indigo
141,10001101,Aster,Dr,Left-chiral violet
142,10001110,Aster,Si,Linear time
143,10001111,Aster,Su,Loop time
144,10010000,Aster,Os,Exponential time
145,10010001,Aster,Se,Logarithmic time
146,10010010,Aster,Sy,Fold time
147,10010011,Aster,As,Frozen time
148,10010100,Aster,Ep,Assign space
149,10010101,Aster,Gwev,Save space
150,10010110,Aster,Ifa,Parse space
151,10010111,Aster,Ier,Loop space
152,10011000,Aster,San,Push space
153,10011001,Aster,Enno,Delete space
154,10011010,Aster,Yl,Run space
155,10011011,Aster,Hoz,Unbind space
156,10011100,Grapevine,Sa,Feast table / root volume
157,10011101,Grapevine,Soa,Cup / file / persistent object
158,10011110,Grapevine,Syr,Wine / volatile buffer
159,10011111,Grapevine,Seth,Platter / directory / bundle
160,10100000,Grapevine,Samos,Banquet hall / database cluster
161,10100001,Grapevine,Sava,Amphora / snapshot archive
162,10100010,Grapevine,Sael,Leftovers / cache
163,10100011,Grapevine,Myk,Messenger / packet
164,10100100,Grapevine,Myr,Procession path / route
165,10100101,Grapevine,Mio,Stride / hop
166,10100110,Grapevine,Mek,Call / emit event
167,10100111,Grapevine,Mavo,Banner / metadata
168,10101000,Grapevine,Mekha,Herald / gateway
169,10101001,Grapevine,Myrun,Sacred march / stream
170,10101010,Grapevine,Dyf,Jitter / nondeterminism
171,10101011,Grapevine,Dyo,Burst / load spike
172,10101100,Grapevine,Dyth,Packet loss / corruption
173,10101101,Grapevine,Dyska,Concurrency / thread dance
174,10101110,Grapevine,Dyne,Broadcast / flood
175,10101111,Grapevine,Dyran,Overflow / memory full
176,10110000,Grapevine,Dyso,Overload threshold
177,10110001,Grapevine,Kyf,Cluster node
178,10110010,Grapevine,Kyl,Steward / coordinator
179,10110011,Grapevine,Kyra,Control token / semaphore
180,10110100,Grapevine,Kyvos,Ring topology
181,10110101,Grapevine,Kysha,Consensus choir
182,10110110,Grapevine,Kyom,Replica / masked follower
183,10110111,Grapevine,Kysael,Authoritative commit
184,10111000,Cannabis,At,Grounded awareness / consciousness of material presence (Lotus seen through Mind — the felt sense of being here, embodied, in a specific moment of earth)
185,10111001,Cannabis,Ar,Chromatic perception / awareness of energetic quality (Rose through Mind — the direct experience of frequency, color as felt rather than measured)
186,10111010,Cannabis,Av,Relational consciousness / awareness of connection and structure (Sakura through Mind — knowing where you stand in relation to other things)
187,10111011,Cannabis,Azr,Structural intuition / felt sense of how things are assembled (Daisy through Mind — the bodily knowledge of mechanism and form)
188,10111100,Cannabis,Af,Transformative awareness / consciousness of change in process (AppleBlossom through Mind — feeling a phase transition as it happens)
189,10111101,Cannabis,An,Chiral discernment / awareness of handedness and temporal direction (Aster through Mind — the sense of which way time is turning)
190,10111110,Cannabis,Od,Unspecified mental signal / noise without narrative (Grapevine dark through Mind)
191,10111111,Cannabis,Ox,Of the quality of unconscious transmission (operator shadow as adjective)
192,11000000,Cannabis,Om,In the manner of unconscious transmission (operator shadow as adverb)
193,11000001,Cannabis,Soa*,Conscious persistence / the act of mind making something durable
194,11000010,Cannabis,It,Grounded locality / the spatial fact of material presence (Lotus through Space — where something is in the most concrete sense, its place in the earth)
195,11000011,Cannabis,Ir,Spectral field / the spatial distribution of energetic frequency (Rose through Space — color and energy as they occupy and define space around them)
196,11000100,Cannabis,Iv,Relational geometry / the spatial structure of connection (Sakura through Space — the actual distances and orientations between things in relation)
197,11000101,Cannabis,Izr,Structural volume / the space a form occupies and articulates (Daisy through Space — the three dimensional reality of how something is assembled)
198,11000110,Cannabis,If,Transitional space / the spatial site of transformation (AppleBlossom through Space — the place where phase change happens, the crucible, the threshold)
199,11000111,Cannabis,In,Chiral orientation / handedness as spatial phenomenon (Aster through Space — which way something faces in space, its mirror distinction)
200,11001000,Cannabis,Ed,Unspecified spatial signal / network without location (Grapevine dark through Space)
201,11001001,Cannabis,Ex,Of the quality of unlocated transmission (operator shadow as adjective)
202,11001010,Cannabis,Em,In the manner of unlocated transmission (operator shadow as adverb)
203,11001011,Cannabis,Sei,Conscious spatial action / the act of mind deliberately occupying or shaping space
204,11001100,Cannabis,Yt,Grounded duration / the temporal weight of material existence (Lotus through Time — how long something has been here, its age as felt reality)
205,11001101,Cannabis,Yr,Spectral timing / the frequency and rhythm of energetic cycles (Rose through Time — color and energy as they pulse and recur)
206,11001110,Cannabis,Yv,Relational temporality / the timing of meeting and parting (Sakura through Time — when things come together and separate, the rhythm of relation)
207,11001111,Cannabis,Yzr,Structural time / the temporal unfolding of form and assembly (Daisy through Time — how a structure develops, grows, completes itself)
208,11010000,Cannabis,Yf,Transformative time / the duration of phase change (AppleBlossom through Time — how long transformation takes, the timing of alchemical process)
209,11010001,Cannabis,Yn,Chiral time / the direction and handedness of temporal flow (Aster through Time — which way time is moving, linear or looped, folded or frozen)
210,11010010,Cannabis,Ud,Unspecified temporal signal / propagation without sequence (Grapevine dark through Time)
211,11010011,Cannabis,Ux,Of the quality of unsequenced transmission (operator shadow as adjective)
212,11010100,Cannabis,Um,In the manner of unsequenced transmission (operator shadow as adverb)
213,11010101,Cannabis,Suy,Conscious temporal action / the act of mind deliberately moving through or shaping time
"""

def _parse_rows(csv_text: str) -> tuple[ShygazunByteEntry, ...]:
    rows: list[ShygazunByteEntry] = []
    lines = [line.strip() for line in csv_text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("byte table is empty")
    if lines[0] != "Decimal,Binary,Tongue,Symbol,Meaning":
        raise ValueError("invalid byte table header")

    for raw_line in lines[1:]:
        parts = raw_line.split(",", 4)
        if len(parts) != 5:
            raise ValueError(f"invalid row: {raw_line}")

        decimal_text, binary, tongue, symbol, meaning = parts
        decimal = int(decimal_text)
        rows.append(
            {
                "decimal": decimal,
                "binary": binary,
                "tongue": tongue,
                "symbol": symbol,
                "meaning": meaning,
            }
        )

    return tuple(rows)


SHYGAZUN_BYTE_ROWS: Final[tuple[ShygazunByteEntry, ...]] = _parse_rows(_BYTE_TABLE_CSV)
SHYGAZUN_BYTE_ORDER: Final[tuple[int, ...]] = tuple(row["decimal"] for row in SHYGAZUN_BYTE_ROWS)
SHYGAZUN_BYTE_TABLE: Final[dict[int, ShygazunByteEntry]] = {
    row["decimal"]: row for row in SHYGAZUN_BYTE_ROWS
}


def _build_tongue_index(rows: Sequence[ShygazunByteEntry]) -> dict[str, tuple[ShygazunByteEntry, ...]]:
    grouped: dict[str, list[ShygazunByteEntry]] = {}
    for row in rows:
        tongue = row["tongue"]
        if tongue not in grouped:
            grouped[tongue] = []
        grouped[tongue].append(row)
    return {tongue: tuple(entries) for tongue, entries in grouped.items()}


def _build_symbol_index(rows: Sequence[ShygazunByteEntry]) -> dict[str, tuple[ShygazunByteEntry, ...]]:
    grouped: dict[str, list[ShygazunByteEntry]] = {}
    for row in rows:
        symbol = row["symbol"]
        if symbol not in grouped:
            grouped[symbol] = []
        grouped[symbol].append(row)
    return {symbol: tuple(entries) for symbol, entries in grouped.items()}


SHYGAZUN_TONGUE_INDEX: Final[dict[str, tuple[ShygazunByteEntry, ...]]] = _build_tongue_index(
    SHYGAZUN_BYTE_ROWS
)
SHYGAZUN_SYMBOL_INDEX: Final[dict[str, tuple[ShygazunByteEntry, ...]]] = _build_symbol_index(
    SHYGAZUN_BYTE_ROWS
)


def byte_entry(decimal: int) -> ShygazunByteEntry:
    return SHYGAZUN_BYTE_TABLE[decimal]


def symbol_entry(symbol: str) -> ShygazunByteEntry:
    entries = SHYGAZUN_SYMBOL_INDEX[symbol]
    if len(entries) != 1:
        raise ValueError(f"symbol '{symbol}' is declensional; use symbol_entries()")
    return entries[0]


def symbol_entries(symbol: str) -> Sequence[ShygazunByteEntry]:
    return SHYGAZUN_SYMBOL_INDEX[symbol]


def tongue_rows(tongue: str) -> Sequence[ShygazunByteEntry]:
    return SHYGAZUN_TONGUE_INDEX[tongue]


def tongues() -> Sequence[str]:
    return tuple(SHYGAZUN_TONGUE_INDEX.keys())


def byte_table_snapshot() -> Mapping[int, ShygazunByteEntry]:
    return dict(SHYGAZUN_BYTE_TABLE)


def byte_rows() -> Sequence[ShygazunByteEntry]:
    return SHYGAZUN_BYTE_ROWS