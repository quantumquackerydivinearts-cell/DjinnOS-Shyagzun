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
109,01101101,AppleBlossom,Kypa,Sulphur (Fire,Air)
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
124,01111100,Reserved,YeGaoh-Index,Master index for the YeGaoh Group — full 24-tongue cluster (Ye-×Gaoh-=24)
125,01111101,Reserved,YeGaoh-1-8,Directory for Tongues 1–8 (Lotus–Cannabis) — addresses 0–255
126,01111110,Reserved,YeGaoh-9-16,Directory for Tongues 9–16 (Dragon–Protist) — addresses 256–511
127,01111111,Reserved,YeGaoh-17-24,Directory for Tongues 17–24 (unknown) — addresses 512+
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
157,10011101,Grapevine,Sao,Cup / file / persistent object
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
193,11000001,Cannabis,Soa,Conscious persistence / the act of mind making something durable
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
256,100000000,Dragon,Rhivesh,Mental void 1 — hijacked self-reference / Ophiocordyceps unilateralis
257,100000001,Dragon,Rhokve,Mental void 2 — cognition without apparatus / Physarum polycephalum
258,100000010,Dragon,Rhezh,Mental void 3 — memory without persistent self / Turritopsis dohrnii
259,100000011,Dragon,Rhivash-ko,Mental void 4 — self-reference extended into confirmed absence / Portia labiata
260,100000100,Dragon,Zhri'val,Mental void 5 — identity distributed across non-communicating substrates / Myxobolus cerebralis
261,100000101,Dragon,Rhasha-vok,Mental void 6 — cognition with apparatus suppressing its own correction / Homo sapiens
262,100000110,Dragon,Vzhiran,Mental void 7 — information boundary does not correspond to physical boundary / Rafflesia arnoldii
263,100000111,Dragon,Rhokvesh-na,Mental void 8 — self-consuming self-reference / Stegodyphus dumicola
264,100001000,Dragon,Vzhiral-rhe,Mental void 9 — decision without decider / Dictyostelium discoideum
265,100001001,Dragon,Rhazhvu-nokte,Mental void 10 — singular identity with no singular self / Letharia vulpina
266,100001010,Dragon,Dvavesh,Spatial void 1 — boundary that cannot be located / Armillaria ostoyae
267,100001011,Dragon,Dvokran,Spatial void 2 — total interpenetration / Sacculina carcini
268,100001100,Dragon,Dva'zhal,Spatial void 3 — collective with no unified spatial origin / Praya dubia
269,100001101,Dragon,Dvasha-ke,Spatial void 4 — form concealing structure / Welwitschia mirabilis
270,100001110,Dragon,Zhrdva-vol,Spatial void 5 — scale of operation does not equal scale of definition / Caulerpa taxifolia
271,100001111,Dragon,Dvokesh,Spatial void 6 — coherence borrowed from medium / Mnemiopsis leidyi
272,100010000,Dragon,Vzhrdva,Spatial void 7 — agency without presence / Ophiocordyceps spatial
273,100010001,Dragon,Dvokrash-na,Spatial void 8 — inside/outside equivalence / Hydra vulgaris
274,100010010,Dragon,Rhdva-vun,Spatial void 9 — defined by central absence / Adansonia digitata
275,100010011,Dragon,Dvazh-nokvre,Spatial void 10 — no reference configuration / Trichoplax adhaerens
276,100010100,Dragon,Kwevesh,Temporal void 1 — time passes through not for / Ramazzottius varieornatus
277,100010101,Dragon,Kwokre,Temporal void 2 — occupying another organism's temporal experience / Ophrys apifera
278,100010110,Dragon,Kwe'zhal,Temporal void 3 — lineage collapsed into undifferentiated now / Thraustochytrid
279,100010111,Dragon,Kwasha-val,Temporal void 4 — persistence through temporal incoherence with surrounding patterns / Magicicada septendecim
280,100011000,Dragon,Zhrkwe-na,Temporal void 5 — persistence through total replacement of visible substrate / Pando
281,100011001,Dragon,Kwokvesh,Temporal void 6 — identity without continuity / Turritopsis dohrnii temporal
282,100011010,Dragon,Vzhrkwe,Temporal void 7 — persistence by violating the rule of persistence / Bdelloid rotifer
283,100011011,Dragon,Kwokrash-rhe,Temporal void 8 — visible death does not equal actual organism's death / Ganoderma spp.
284,100011100,Dragon,Rhkwe-vun,Temporal void 9 — outside evolutionary time while subject to it / Vaceletia spp.
285,100011101,Dragon,Kwazhvu-nokte,Temporal void 10 — temporal gap with no biological explanation for closure / Syntrichia caninervis
286,100011110,Virus,Plave,Ordinal 1 — 5' terminus / ordinal origin before the first base
287,100011111,Virus,Plaro,Ordinal 2 — 3' terminus / ordinal end
288,100100000,Virus,Plahan,Ordinal 3 — Ha-Na / A-U standard pairing / positive principle meeting integrative directly
289,100100001,Virus,Plaung,Ordinal 4 — Wu-Ung / G-C mediated pairing / full traversal resolved / triple bond
290,100100010,Virus,Plaha,Ordinal 5 — Ha free / A unpaired / positive principle without complement
291,100100011,Virus,Plana,Ordinal 6 — Na free / U unpaired / pure traversal point / neither pole claiming
292,100100100,Virus,Plawu,Ordinal 7 — Wu free / G unpaired / mediation implicate seeking root
293,100100101,Virus,Plaoku,Ordinal 8 — Ung free / C unpaired / mediation implicate at rest
294,100100110,Virus,Plavik,Ordinal 9 — Codon / triplet unit / minimal ordinal unit of meaning
295,100100111,Virus,Plavikro,Ordinal 10 — Reading frame / where segmentation begins determines what the sequence means
296,100101000,Virus,Jruve,Orthogonal 1 — Hairpin loop / simplest fold / sequence turns back on itself / first spatial form
297,100101001,Virus,Jrushan,Orthogonal 2 — Stem / stable double-stranded region from intramolecular pairing
298,100101010,Virus,Jrulok,Orthogonal 3 — Internal loop / asymmetric unpaired region within a stem
299,100101011,Virus,Jruval,Orthogonal 4 — Bulge / single unpaired base on one side of a stem
300,100101100,Virus,Jru'wun,Orthogonal 5 — G-U wobble / Wu-Na near-fit / mediation implicate touching root
301,100101101,Virus,Jruvekna,Orthogonal 6 — Pseudoknot / fold crossing another fold / spatial self-reference
302,100101110,Virus,Jrukash,Orthogonal 7 — Junction / three or more stems meeting at a point
303,100101111,Virus,Jruvashko,Orthogonal 8 — Kissing loops / two hairpin loops pairing / second-order fold
304,100110000,Virus,Jrukashro,Orthogonal 9 — Coaxial stack / two stems stacking end-to-end
305,100110001,Virus,Jrunokvre,Orthogonal 10 — Multibranch loop / four or more stems at a single junction
306,100110010,Virus,Wikve,Catalytic 1 — Hammerhead ribozyme / self-cleavage / simplest catalytic form
307,100110011,Virus,Wikro,Catalytic 2 — Hairpin ribozyme / reversible cleavage and ligation
308,100110100,Virus,Wikhan,Catalytic 3 — HDV ribozyme / viral self-cleavage / catalysis at alive/not-alive boundary
309,100110101,Virus,Wikval,Catalytic 4 — Group I intron / self-splicing / sequence removing itself from a larger sequence
310,100110110,Virus,Wikvalna,Catalytic 5 — Group II intron / prior before the prior / ancestor of spliceosome
311,100110111,Virus,Wikung,Catalytic 6 — Ribosomal RNA / peptide bond formation / Ung embedded / the original translator
312,100111000,Virus,Wikaro,Catalytic 7 — Telomerase RNA / template-directed extension / anti-terminus
313,100111001,Virus,Wiknasha,Catalytic 8 — snRNA / splicing catalysis / Na embedded / RNA mind inside protein body
314,100111010,Virus,Wikshavel,Catalytic 9 — Aptamer / ligand-activated fold switch / sha embedded / conditional catalysis
315,100111011,Virus,Wiknokvre,Catalytic 10 — Replicase / RNA copying RNA / the self-replicating prior
316,100111100,Bacteria,Zhove,Mind 1 — resting potential / baseline charge state / the identity the organism defaults to
317,100111101,Bacteria,Zhoran,Mind 2 — depolarization / potential collapses toward zero / identity-threat misread as invasion
318,100111110,Bacteria,Zhokre,Mind 3 — hyperpolarization / potential exceeds resting / the over-correction
319,100111111,Bacteria,Zho'val,Mind 4 — membrane asymmetry / different regions at different potentials simultaneously
320,101000000,Bacteria,Zho'na,Mind 5 — proton motive force / Na embedded / charge gradient driving ATP synthesis / the integrative principle IS the energy differential
321,101000001,Bacteria,Zhovesh,Mind 6 — ion selectivity / membrane discriminating between ion types / first categorical filter
322,101000010,Bacteria,Zhuvek,Mind 7 — electrochemical equilibrium / Nernst potential / diffusion and electrical forces balanced
323,101000011,Bacteria,Zhokrash,Mind 8 — action potential analog / rapid depolarization-repolarization wave in excitable bacteria
324,101000100,Bacteria,Zhokven,Mind 9 — threshold potential / charge state where signal becomes triggering rather than noise
325,101000101,Bacteria,Zhokven-na,Mind 10 — refractory period / Na at the close / post-threshold window / integration holding the boundary
326,101000110,Bacteria,Rive,Time 1 — signal onset / moment of potential change / temporal beginning of the signal
327,101000111,Bacteria,Rivan,Time 2 — signal propagation / cascade moving through time
328,101001000,Bacteria,Riko,Time 3 — signal termination / Ko embedded / return to resting / the signal's end is experiential
329,101001001,Bacteria,Rival,Time 4 — signal frequency / rate of repeated signals / temporal pattern
330,101001010,Bacteria,Ri'vash,Time 5 — temporal summation / half glottal at threshold / sub-threshold signals summing
331,101001011,Bacteria,Rikash,Time 6 — adaptation / repeated identical signals producing progressively weaker responses
332,101001100,Bacteria,Rikove,Time 7 — habituation / learned temporal pattern of non-response / practiced termination
333,101001101,Bacteria,Rizhun,Time 8 — circadian rhythm analog / zh from Zho bleeding in / internal oscillation independent of external signal
334,101001110,Bacteria,Rivekna,Time 9 — chemotaxis temporal gradient / Na embedded / sensing change in concentration over time not the concentration itself
335,101001111,Bacteria,Rikrasho,Time 10 — signal delay / open ending / temporal lag between stimulus and response / the processing window that never fully closes
336,101010000,Bacteria,Vavre,Space 1 — field extent / spatial reach of charge differential beyond membrane surface
337,101010001,Bacteria,Varan,Space 2 — gradient vector / spatial direction of the potential change
338,101010010,Bacteria,Varko,Space 3 — quorum sensing range / Ko embedded / spatial threshold triggering collective behavior
339,101010011,Bacteria,Varval,Space 4 — biofilm organization / colony as spatial field expression / each cell a node
340,101010100,Bacteria,Var'zho,Space 5 — electrical wave / Zho embedded / mind-charge propagating through biofilm space
341,101010101,Bacteria,Varlok,Space 6 — chemotaxis navigation / movement through space up or down a chemical gradient
342,101010110,Bacteria,Varshan,Space 7 — membrane topology / sha embedded / spatial geometry of membrane as signal-receiving area
343,101010111,Bacteria,Varkash,Space 8 — niche occupation / spatial claim of organism on its chemical environment
344,101011000,Bacteria,Varnokre,Space 9 — colony boundary / where the biofilm's spatial electrical field terminates
345,101011001,Bacteria,Varzhokrash,Space 10 — interspecies interference / Zho inside Var / competing charge states in space / spatial field competition
346,101011010,Excavata,Ranve,Rotation 1 — right-hand chirality / clockwise helical rotation
347,101011011,Excavata,Ranvu,Rotation 2 — left-hand chirality / counterclockwise / the mirror
348,101011100,Excavata,Ranpek,Rotation 3 — pitch / rate of advance per full rotation
349,101011101,Excavata,Ranval,Rotation 4 — amplitude / radius of the helix
350,101011110,Excavata,Ran'vo,Rotation 5 — reversal / chirality inverting mid-rotation / half glottal at inversion
351,101011111,Excavata,Rankwe,Rotation 6 — flagellar beat / Kwe embedded / helical wave driving cellular motion / temporal rhythm
352,101100000,Excavata,Ranvesh,Rotation 7 — rotational gradient / change in rotation rate along the helix axis
353,101100001,Excavata,Rankovre,Rotation 8 — coaxial rotation / Ko embedded / two helices rotating around the same axis
354,101100010,Excavata,Ranzhok,Rotation 9 — supercoiling / zh from Zho / helix coiling on itself / where instruction set looks most like a center
355,101100011,Excavata,Rankrash-vo,Rotation 10 — chiral symmetry breaking / the moment a symmetric system becomes chiral / symmetry releasing into handedness
356,101100100,Excavata,Yefve,Traversal 1 — half-twist / Möbius-defining move / apparent inside becomes apparent outside on one continuous surface
357,101100101,Excavata,Yefran,Traversal 2 — single face / Ran inside Yef / rotation proving one continuous surface
358,101100110,Excavata,Yeflo,Traversal 3 — single edge / the one continuous boundary of the Möbius
359,101100111,Excavata,Yefval,Traversal 4 — traversal / moving along the surface without crossing a boundary
360,101101000,Excavata,Yef'na,Traversal 5 — non-orientability / Na embedded / integration resisting orientation assignment / no stable up
361,101101001,Excavata,Yefkash,Traversal 6 — self-intersection appearance / apparent crossing that is not one
362,101101010,Excavata,Yefkovre,Traversal 7 — center cut / Ko embedded / finding continuity where division was expected
363,101101011,Excavata,Yefvash-lo,Traversal 8 — off-center cut / produces Möbius and regular loop linked
364,101101100,Excavata,Yefranog,Traversal 9 — embedding / Ran embedded / rotation taking spatial form / abstract topology instantiated in space
365,101101101,Excavata,Yefzhokran,Traversal 10 — projection / Zh+Ran inside Yef / mind and rotation misrepresenting topology / the shadow mistaken for the surface
366,101101110,Excavata,Logve,Orientation error 1 — handedness confusion / mistaking left-hand for right-hand helix
367,101101111,Excavata,Logan,Orientation error 2 — inside/outside conflation / two apparent faces treated as genuinely distinct
368,101110000,Excavata,Logran,Orientation error 3 — center fixation / Ran inside Log / rotation appearing to have a fixed center / instruction set as origin
369,101110001,Excavata,Logval,Orientation error 4 — traversal direction error / assigning wrong way to a surface that has none
370,101110010,Excavata,Log'vesh,Orientation error 5 — boundary assumption / single edge treated as separating boundary / pause before the error locks
371,101110011,Excavata,Logkash,Orientation error 6 — orientation assignment / attempting to fix consistent orientation on a non-orientable surface
372,101110100,Excavata,Logkre,Orientation error 7 — depth error / groove's apparent depth read as genuine interior space
373,101110101,Excavata,Logzhok,Orientation error 8 — chirality fixation / zh from Zho inside Log / mind locking onto handedness as identity
374,101110110,Excavata,Logvekna,Orientation error 9 — projection error / Na embedded / integration reading the shadow instead of the surface
375,101110111,Excavata,Logranzhok,Orientation error 10 — self-reference loop / Ran+Zhok inside Log / the groove pointing at the instruction set which codes the groove / instruction set does not equal self
376,101111000,Excavata,Yefko,Ko state — correct Möbius traversal / Yef in Ko mode / moving along the single surface with awareness / the instruction set as parameter not identity
377,101111001,Excavata,Ranku,Ku state — arrested rotation / Ran in Ku mode / the helix completing and stopping / Möbius traversal terminated
378,101111010,Archaeplastida,Zotve,Earth-Constitutive 1 — primary endosymbiosis / the engulfment event that made enclosure constitutive
379,101111011,Archaeplastida,Zotan,Earth-Constitutive 2 — genome reduction / constitutive component losing genes to host nucleus / the inside becoming more inside
380,101111100,Archaeplastida,Zotkre,Earth-Constitutive 3 — protein import / host nucleus coding proteins for the enclosed component
381,101111101,Archaeplastida,Zot'vel,Earth-Constitutive 4 — double membrane / boundary layering as constitutive record / half glottal at the doubled boundary
382,101111110,Archaeplastida,Zotvash,Earth-Constitutive 5 — semi-autonomous replication / constitutive but not fully subsumed
383,101111111,Archaeplastida,Zotzhok,Earth-Constitutive 6 — historical gene transfer / zh from Zho / constitutive identity distributing into host nucleus
384,110000000,Archaeplastida,Zotkash-ran,Earth-Constitutive 7 — plastid inheritance / Ran embedded / constitutive transmission following different rotation than host
385,110000001,Archaeplastida,Zotnavre,Earth-Constitutive 8 — obligate mutualism / Na embedded / the integration that cannot be undone
386,110000010,Archaeplastida,Melve,Water-Incidental 1 — phagocytosis / temporary enclosure of incidental content
387,110000011,Archaeplastida,Melan,Water-Incidental 2 — digestive vacuole / enclosed material processed / inside for function not identity
388,110000100,Archaeplastida,Melko,Water-Incidental 3 — exocytosis / Ko embedded / the incidental cycle completing into experience
389,110000101,Archaeplastida,Mel'vash,Water-Incidental 4 — autophagy / half glottal / cell digesting its own components
390,110000110,Archaeplastida,Melpik,Water-Incidental 5 — pinocytosis / fluid-phase endocytosis / liquid taken in without specific targeting
391,110000111,Archaeplastida,Melvek,Water-Incidental 6 — vesicular trafficking / material moving through membrane-bound compartments
392,110001000,Archaeplastida,Melkash,Water-Incidental 7 — lysosomal fusion / digestive apparatus merging with food vacuole
393,110001001,Archaeplastida,Melzotkre,Water-Incidental 8 — failed digestion / Zot inside Mel / Earth inside Water / the category error boundary crossed
394,110001010,Archaeplastida,Pufve,Air-Constitutive 1 — mycorrhizal symbiosis / the archetypal free-constitutive relation
395,110001011,Archaeplastida,Pufan,Air-Constitutive 2 — nutrient exchange / constitutive relation maintained across a free boundary
396,110001100,Archaeplastida,Pufko,Air-Constitutive 3 — signaling / Ko embedded / free-constitutive communication as experience
397,110001101,Archaeplastida,Puf'val,Air-Constitutive 4 — specificity / half glottal at the selection moment / selective constitution
398,110001110,Archaeplastida,Pufzot,Air-Constitutive 5 — obligate dependence / Zot inside Puf / Earth inside Air / dependence without possession
399,110001111,Archaeplastida,Pufkash,Air-Constitutive 6 — partner switching / constitutive relation portable across different specific partners
400,110010000,Archaeplastida,Pufranve,Air-Constitutive 7 — spatial extension / Ran embedded / free partner extending reach through traversal
401,110010001,Archaeplastida,Pufshakna,Air-Constitutive 8 — loss of free partner / Shak inside Puf / Na at close / Fire leaving Air / integration named at dissolution
402,110010010,Archaeplastida,Shakve,Fire-Incidental 1 — chance contact / the passing encounter / no constitutive claim
403,110010011,Archaeplastida,Shakran,Fire-Incidental 2 — current gene transfer / Ran embedded / rotation of genetic material / transformation without constitutive relation
404,110010100,Archaeplastida,Shakvesh,Fire-Incidental 3 — viral passage / vesh (through) / Fire passing through
405,110010101,Archaeplastida,Shak'mel,Fire-Incidental 4 — allelopathy / Mel inside Shak / Water chemistry as Fire / half glottal at elemental meeting
406,110010110,Archaeplastida,Shakpuf,Fire-Incidental 5 — transient parasitism / Puf inside Shak / Air turned predatory / free against free
407,110010111,Archaeplastida,Shakazh,Fire-Incidental 6 — competitive exclusion / Fire displacing Fire
408,110011000,Archaeplastida,Shakvekna,Fire-Incidental 7 — lateral facilitation / Na embedded / accidental beneficence / the integrative principle in passing contact
409,110011001,Archaeplastida,Shakzotmel,Fire-Incidental 8 — environmental stochasticity / Zot+Mel inside Shak / Earth+Water inside Fire / transformation from nowhere belonging to nothing
410,110011010,Myxozoa,Ive,Iv 1 — identity as trajectory / actinospore floating toward undetected host / self = direction before the other is found
411,110011011,Myxozoa,Ivi,Iv 2 — identity as apex / contact moment / spore reaches its necessary other / peak of the free phase
412,110011100,Myxozoa,Ivu,Iv 3 — identity as compression / sporoplasm at maximum density minimum volume / everything present nothing visible
413,110011101,Myxozoa,Ivo,Iv 4 — identity as directed depth / injection vector / polar capsule thread into host tissue / specific-direction-inward
414,110011110,Myxozoa,Iva,Iv 5 — identity as open approach / pre-encounter / selfhood entirely approach before any specific direction fixes
415,110011111,Myxozoa,Ivoe,Iv 6 — identity as reduced neutrality / spore suspended between phases / operative floor of the Iv axis
416,110100000,Myxozoa,Oave,Oa 1 — identity as boundary-persistence / parasitic cell maintaining membrane within host cytoplasm / boundary inside another's boundary
417,110100001,Myxozoa,Oavi,Oa 2 — identity as apex-from-below / parasite orienting to host architecture from within / knowing structure by inhabiting it
418,110100010,Myxozoa,Oavu,Oa 3 — identity as contained-ground / myxospore cyst in fish muscle / enclosed ground within another's ground
419,110100011,Myxozoa,Oavo,Oa 4 — identity as depth-ground / parasite inhabiting deepest host spaces / neural tissue / most interior inhabitation
420,110100100,Myxozoa,Oava,Oa 5 — identity as open-ground / blood-distributed parasite / no fixed location / ground without edges within another
421,110100101,Myxozoa,Oavoe,Oa 6 — identity as reduced-ground / minimally active parasite dormant within host / minimum inside another's full operation
422,110100110,Myxozoa,Navsh,Nav 1 — fire-identity / polar capsule discharge / the explosive injection event / selfhood as the event that fires
423,110100111,Myxozoa,Navp,Nav 2 — air-identity / spore dispersal / directionality before host is found / selfhood as movement through medium
424,110101000,Myxozoa,Navm,Nav 3 — water-identity / tissue infiltration / the penetrating pervasive self / selfhood as permeation
425,110101001,Myxozoa,Navz,Nav 4 — earth-identity / cyst structure / mineralized walls / selfhood as the ground it builds around itself
426,110101010,Myxozoa,Navk,Nav 5 — Kael-identity / 500-million-year evolutionary plasticity / generative excess that makes radical reduction possible
427,110101011,Myxozoa,Ivelo,Iv-lo 1 — trajectory as arrival / moving toward ≠ reaching / direction mistaken for destination
428,110101100,Myxozoa,Ivilo,Iv-lo 2 — apex as completion / contact event mistaken for total selfhood / beginning ≠ fulfillment
429,110101101,Myxozoa,Ivulo,Iv-lo 3 — compression as simplicity / maximum density mistaken for minimum complexity / dense ≠ empty
430,110101110,Myxozoa,Ivolo,Iv-lo 4 — injection as interiority / inserting self into other ≠ becoming interior to other
431,110101111,Myxozoa,Ivalo,Iv-lo 5 — seeking as openness / undirected approach ≠ genuine openness / moving without target ≠ having no direction
432,110110000,Myxozoa,Ivoelo,Iv-lo 6 — suspension as universal floor / phase-between state ≠ zero point of all selfhood / one suspension ≠ all suspension
433,110110001,Myxozoa,Oavelo,Oa-lo 1 — boundary-persistence as boundary-making / maintaining integrity within another ≠ creating the separating boundary
434,110110010,Myxozoa,Oavilo,Oa-lo 2 — interior-orientation as being interior / reading architecture from within ≠ being the architecture
435,110110011,Myxozoa,Oavulo,Oa-lo 3 — contained-ground as containing / being held ≠ holding / cyst enclosed mistaking its state for enclosure
436,110110100,Myxozoa,Oavolo,Oa-lo 4 — depth-inhabitation as depth / inhabiting the deepest space ≠ being depth
437,110110101,Myxozoa,Oavalo,Oa-lo 5 — distributed ground as universal ground / being everywhere within one ≠ being ground itself
438,110110110,Myxozoa,Oavoelo,Oa-lo 6 — dormant minimum as irreducible ground / dormancy within host ≠ floor of all existence
439,110110111,Myxozoa,Navshlo,Nav-lo 1 — fire universalized / because I inject all selfhood is injection / the most violent universalization
440,110111000,Myxozoa,Navplo,Nav-lo 2 — air universalized / because I disperse all selfhood is dispersal
441,110111001,Myxozoa,Navmlo,Nav-lo 3 — water universalized / because I penetrate all selfhood is penetration
442,110111010,Myxozoa,Navzlo,Nav-lo 4 — earth universalized / because I build my cyst all selfhood is substrate-building
443,110111011,Myxozoa,Navklo,Nav-lo 5 — Kael universalized / radical plasticity declared the criterion / infinite openness as sole selfhood requirement / the deepest error of the minimum form
444,110111100,Archaea,Ethe,Eth 1 — identity as tolerance-edge / self defined by what it can withstand / the chemical boundary where most life ends and this life begins
445,110111101,Archaea,Ethi,Eth 2 — identity as thermal apex / hyperthermophile / selfhood as the furthest forward point on the heat axis before denaturation
446,110111110,Archaea,Ethu,Eth 3 — identity as pressure-threshold / barophile / self = the organism that requires weight to be correctly itself
447,110111111,Archaea,Etho,Eth 4 — identity as chemical depth-threshold / the self that finds its ground in pH that dissolves other organisms
448,111000000,Archaea,Etha,Eth 5 — identity as open-threshold / pre-specific extremophily / what selfhood is before it finds its specific hostile medium
449,111000001,Archaea,Ethoe,Eth 6 — identity as reduced-threshold / minimum viable existence at the chemical extreme / operative floor of the Eth axis
450,111000010,Archaea,Urge,Urg 1 — identity as boundary-held-within-extreme / ether-linked membrane that persists where ester bonds break / chemistry that holds at the limit
451,111000011,Archaea,Urgi,Urg 2 — identity as apex-within-extreme / organism at 121°C / being the farthest confirmed point that life has reached
452,111000100,Archaea,Urgu,Urg 3 — identity as compressed-within / piezophile at maximum pressure / optimal function under conditions that would crush other cellular architecture
453,111000101,Archaea,Urgo,Urg 4 — identity as depth-within-chemical-extreme / methanogen in anoxic sediment / archaeon in hypersaline pool / occupying the most extreme available medium
454,111000110,Archaea,Urga,Urg 5 — identity as open-within-extreme / no retreat from the hostile medium / self = ground that opens into the extreme rather than escaping it
455,111000111,Archaea,Urgoe,Urg 6 — identity as reduced-within-extreme / dormant archaeon in permafrost or hypersaline crystal / minimum operation within maximum hostility / double extremity
456,111001000,Archaea,Krevsh,Krev 1 — fire-inversion / hyperthermophile / heat that sustains rather than destroys / the element that kills others IS this organism's medium
457,111001001,Archaea,Krevp,Krev 2 — air-inversion / strict anaerobe / oxygen is poison / absence of what most life requires IS this organism's viability condition
458,111001010,Archaea,Krevm,Krev 3 — water-inversion / halophile / saturated brine as correct medium / proteins that denature in fresh water
459,111001011,Archaea,Krevz,Krev 4 — earth-inversion / lithotroph / mineral substrate as energy source / earth eaten not stood upon / rock oxidized for electrons
460,111001100,Archaea,Krevk,Krev 5 — Kael-inversion / 3.5-billion-year metabolic invention / survivability-excess as Kael event at cellular scale / capacity to occupy any extreme
461,111001101,Archaea,Ethelo,Eth-lo 1 — tolerance-edge as universal boundary / because my limit defines me all selfhood is defined by its limit
462,111001110,Archaea,Ethilo,Eth-lo 2 — thermal apex as completion / living at extremes ≠ living at apex of all selfhood
463,111001111,Archaea,Ethulo,Eth-lo 3 — pressure-threshold as simplicity / maximum pressure resistance ≠ minimum complexity
464,111010000,Archaea,Etholo,Eth-lo 4 — chemical depth-threshold as depth itself / inhabiting pH 0 ≠ being the property of chemical depth
465,111010001,Archaea,Ethalo,Eth-lo 5 — open-threshold as openness / undirected approach to the limit ≠ genuine openness
466,111010010,Archaea,Ethoelo,Eth-lo 6 — reduced-threshold as universal floor / minimum viable at the chemical extreme ≠ minimum of all viability
467,111010011,Archaea,Urgelo,Urg-lo 1 — boundary-held-within-extreme as boundary-making / ether-linked persistence ≠ originating the distinction between self and not-self
468,111010100,Archaea,Urgilo,Urg-lo 2 — apex-within-extreme as the apex / most heat-tolerant confirmed organism ≠ the apex of all possible tolerance
469,111010101,Archaea,Urgulo,Urg-lo 3 — compressed-within as containment / optimal function under pressure ≠ being compression
470,111010110,Archaea,Urgolo,Urg-lo 4 — depth-within-chemical-extreme as depth / most hostile medium inhabited ≠ being the property of hostility
471,111010111,Archaea,Urgalo,Urg-lo 5 — open-within-extreme as universal medium / thriving in brine ≠ defining what a medium is
472,111011000,Archaea,Urgoelo,Urg-lo 6 — reduced-within-extreme as irreducible ground / dormancy in hypersaline crystal ≠ floor of all existence
473,111011001,Archaea,Krevshlo,Krev-lo 1 — fire-inversion universalized / because heat sustains me all life requires heat-as-sustainer
474,111011010,Archaea,Krevplo,Krev-lo 2 — air-inversion universalized / because oxygen is my poison all genuine life finds sustenance in what biology calls toxic
475,111011011,Archaea,Krevmlo,Krev-lo 3 — water-inversion universalized / because brine is my ocean all ocean is correctly salt
476,111011100,Archaea,Krevzlo,Krev-lo 4 — earth-inversion universalized / because I eat rock all sustenance is mineral
477,111011101,Archaea,Krevklo,Krev-lo 5 — Kael-inversion universalized / radical viability declared the criterion / survival-excess as the sole measure of selfhood / the deepest error of the threshold form
478,111011110,Protist,Aeve,Ae 1 — identity as categorical boundary-between / neither fully open nor fully bounded / the in-between as stable position not failure to arrive
479,111011111,Protist,Aevi,Ae 2 — identity as neither/nor at height / most complex Protist / neither apex nor minimum / selfhood at the highest point of categorical in-between
480,111100000,Protist,Aevu,Ae 3 — identity as neither/nor compressed / maximum categorical density without requiring extremity
481,111100001,Protist,Aevo,Ae 4 — identity as depth-between / depth without being the abyss / reaching deepest without crossing into any defined kingdom
482,111100010,Protist,Aeva,Ae 5 — identity as open-between / most open possible categorical in-between / no edge fixed no ground named
483,111100011,Protist,Aevoe,Ae 6 — identity as reduced neither/nor / minimum viable existence while occupying categorical in-between / operative floor of the Ae axis
484,111100100,Protist,Oive,Oi 1 — identity as edge-of-crossing / selfhood defined by traversal across categorical space / the moving boundary between what it is not
485,111100101,Protist,Oivi,Oi 2 — identity as apex-of-crossing / most complex categorical traversal / organism with animal-like and plant-like characteristics simultaneously
486,111100110,Protist,Oivu,Oi 3 — identity as compressed-crossing / maximum categorical work in minimum space / traverses between kingdoms without occupying volume in any
487,111100111,Protist,Oivo,Oi 4 — identity as depth-of-crossing / deepest categorical traversal / furthest from any defining shore
488,111101000,Protist,Oiva,Oi 5 — identity as open-crossing / no fixed trajectory across categorical space / maximum categorical openness in motion
489,111101001,Protist,Oivoe,Oi 6 — identity as reduced-crossing / minimum viable existence while traversing categorical space / floor of the Oi axis
490,111101010,Protist,Grevsh,Grev 1 — fire-exclusion / not-plant / excluded from the fire-mediated photosynthetic kingdom / identity as what has been excluded from fire-transformation
491,111101011,Protist,Grevp,Grev 2 — air-exclusion / not-animal / excluded from the air-mediated motility kingdom / non-defining aerobic characteristic
492,111101100,Protist,Grevm,Grev 3 — water-exclusion / not-fungus / excluded from the osmotrophic water-mediated kingdom / non-fungal relation to dissolution
493,111101101,Protist,Grevz,Grev 4 — earth-exclusion / no fixed morphological ground / excluded from all substrate-defined forms / selfhood as the organism with no stable earth-relationship
494,111101110,Protist,Grevk,Grev 5 — Kael-exclusion / the remainder after all other kingdoms found their language / excluded even from Kael's generative naming / the residue of the residue
495,111101111,Protist,Aevelo,Ae-lo 1 — in-between as universal position / because I occupy between-positions all selfhood exists between positions / the in-between declared the only authentic location
496,111110000,Protist,Aevilo,Ae-lo 2 — neither/nor at height as the apex / true complexity requires categorical exclusion / in-between universalized as sophistication
497,111110001,Protist,Aevulo,Ae-lo 3 — categorical compression as simplicity / dense exclusion ≠ absence of content
498,111110010,Protist,Aevolo,Ae-lo 4 — depth-between as depth itself / reaching deepest without crossing any kingdom ≠ being the property of depth
499,111110011,Protist,Aevalo,Ae-lo 5 — open-between as openness / not-belonging-anywhere ≠ being free
500,111110100,Protist,Aevoelo,Ae-lo 6 — reduced neither/nor as universal floor / minimum categorical in-between ≠ minimum of all existence / this residue ≠ all residue
501,111110101,Protist,Oivelo,Oi-lo 1 — edge-of-crossing as boundary-making / traversal-boundary ≠ originating the concept of categorical boundary
502,111110110,Protist,Oivilo,Oi-lo 2 — apex-of-crossing as the apex / crossing furthest across categorical space ≠ reaching highest of all selfhood
503,111110111,Protist,Oivulo,Oi-lo 3 — compressed-crossing as containment / maximum categorical work in minimum space ≠ being compression itself
504,111111000,Protist,Oivolo,Oi-lo 4 — depth-of-crossing as depth / furthest from any defining shore ≠ being the property of depth
505,111111001,Protist,Oivalo,Oi-lo 5 — open-crossing as universal openness / no fixed categorical trajectory ≠ defining what openness is
506,111111010,Protist,Oivoelo,Oi-lo 6 — reduced-crossing as irreducible ground / minimum existence while traversing ≠ the floor of all existence
507,111111011,Protist,Grevshlo,Grev-lo 1 — fire-exclusion universalized / because I am not-plant genuine selfhood is defined by exclusion from fire-mediated lineage
508,111111100,Protist,Grevplo,Grev-lo 2 — air-exclusion universalized / because I am not-animal authentic selfhood excludes the air-mediated kingdom
509,111111101,Protist,Grevmlo,Grev-lo 3 — water-exclusion universalized / because I am not-fungus correct selfhood excludes osmotrophic dissolution
510,111111110,Protist,Grevzlo,Grev-lo 4 — earth-exclusion universalized / because I have no fixed morphological ground true selfhood has no earth-relationship / groundlessness as criterion
511,111111111,Protist,Grevklo,Grev-lo 5 — Kael-exclusion universalized / no category was sufficient / namelessness declared the criterion of all selfhood / the deepest error of the negative-definition form / byte 511 / 111111111 / the 9-bit space ends here
512,1000000000,Immune,Sive,Siv 1 — surface-pattern recognition / pattern detection at the cell boundary / first contact of recognition before interior signature is known
513,1000000001,Immune,Sivi,Siv 2 — high-specificity recognition / lock-and-key binding / T-cell receptor binding its MHC-peptide complex / recognition as singular geometric fit
514,1000000010,Immune,Sivu,Siv 3 — compressed recognition / minimum necessary pattern information to discriminate / the epitope / pattern reduced to its essential distinction
515,1000000011,Immune,Sivo,Siv 4 — internal antigen presentation / MHC-I presenting peptide fragments from inside the cell / recognition that reaches inward rather than detecting at the surface
516,1000000100,Immune,Siva,Siv 5 — broad-spectrum recognition / TLRs reading PAMPs / open innate recognition before specificity forms / first sweep across widest pattern categories
517,1000000101,Immune,Sivoe,Siv 6 — threshold recognition / minimum pattern information sufficient to trigger response / below this no signal / operative floor of the Siv axis
518,1000000110,Immune,Reke,Rek 1 — boundary response / local inflammation / immediate edge-response to pattern recognition / heat and redness at the interface
519,1000000111,Immune,Reki,Rek 2 — apex response / peak adaptive immunity / clonal expansion of the exact right lymphocyte / system at maximum discriminatory resolution
520,1000001000,Immune,Reku,Rek 3 — minimum viable response / least response that resolves the detected threat / precise not excessive
521,1000001001,Immune,Reko,Rek 4 — systemic response / cytokine cascade / body-wide signaling coordinating response across all immune compartments
522,1000001010,Immune,Reka,Rek 5 — broad innate response / non-specific inflammatory response before adaptive specificity develops / first action without knowing exactly what is acted against
523,1000001011,Immune,Rekoe,Rek 6 — baseline surveillance / continuous minimum monitoring for deviation from stored self-pattern / operative floor of the Rek axis
524,1000001100,Immune,Trevsh,Trev 1 — fire-memory / inflammatory memory trace / strongest recall / rapid and hot on re-encounter / memory as combustive readiness
525,1000001101,Immune,Trevp,Trev 2 — air-memory / dispersed immunological memory / distributed across lymph nodes / no single location holds it
526,1000001110,Immune,Trevm,Trev 3 — water-memory / circulating antibody trace / memory that flows continuously through blood and lymph / persistent humoral record
527,1000001111,Immune,Trevz,Trev 4 — earth-memory / long-lived bone marrow plasma cells / structural immune memory persisting for decades / the ground of immunological recall
528,1000010000,Immune,Trevk,Trev 5 — Kael-memory / somatic hypermutation and VDJ recombination / immune system generating novel recognition within a single lifetime / memory as generative excess
529,1000010001,Immune,Sivelo,Siv-lo 1 — surface-pattern as total pattern / recognizing at the boundary ≠ knowing the interior signature
530,1000010010,Immune,Sivilo,Siv-lo 2 — maximum-specificity as exhaustive recognition / precision binding to one epitope ≠ knowing the full antigen
531,1000010011,Immune,Sivulo,Siv-lo 3 — compressed recognition as simple pattern / minimum necessary pattern ≠ simple pattern / the epitope is not simple
532,1000010100,Immune,Sivolo,Siv-lo 4 — internal presentation as interiority / displaying peptides via MHC-I ≠ knowing the interior of the cell
533,1000010101,Immune,Sivalo,Siv-lo 5 — broad-spectrum recognition as universal recognition / innate breadth ≠ total pattern coverage
534,1000010110,Immune,Sivoelo,Siv-lo 6 — threshold recognition as the recognition floor / minimum pattern sufficient to trigger ≠ minimum of all recognizable patterns
535,1000010111,Immune,Rekelo,Rek-lo 1 — boundary response as boundary-making / local inflammation ≠ defining the boundary between self and non-self
536,1000011000,Immune,Rekilo,Rek-lo 2 — peak adaptive response as completion / maximum clonal expansion ≠ the total response
537,1000011001,Immune,Rekulo,Rek-lo 3 — minimum viable response as simplicity / least response that resolves ≠ simple response / precision ≠ absence of complexity
538,1000011010,Immune,Rekolo,Rek-lo 4 — systemic response as depth / cytokine cascade ≠ being depth / the immune storm that believes its propagation is the total system
539,1000011011,Immune,Rekalo,Rek-lo 5 — broad innate response as universal response / non-specific first-sweep ≠ appropriate response to all patterns / autoimmune analog
540,1000011100,Immune,Rekoelo,Rek-lo 6 — baseline surveillance as the ground of all immunity / continuous monitoring ≠ foundation of all immune function
541,1000011101,Immune,Trevshlo,Trev-lo 1 — fire-memory universalized / strongest memory is inflammatory therefore all recall should be hot and rapid / allergic hyperreactivity as criterion
542,1000011110,Immune,Trevplo,Trev-lo 2 — dispersed memory universalized / because memory is distributed no specific memory matters more / failure of specificity declared the criterion
543,1000011111,Immune,Trevmlo,Trev-lo 3 — water-memory universalized / all immunity should be humoral / circulating antibody declared the only trace worth maintaining
544,1000100000,Immune,Trevzlo,Trev-lo 4 — earth-memory universalized / all memory should be permanently structural / long-lived plasma cell as the only model / adaptive responsiveness lost
545,1000100001,Immune,Trevklo,Trev-lo 5 — Kael-memory universalized / capacity to generate novel recognition mistaken for mandate to always generate novel responses / all prior learning discarded / each encounter treated as unprecedented / the deepest error of the recognition form
546,1000100010,Neural,Vele,Vel 1 — signal at the sensory surface / mechanoreceptor or chemoreceptor activation at the boundary / graded potential forming before threshold / input before commitment
547,1000100011,Neural,Veli,Vel 2 — threshold crossing / receptor potential reaching action potential threshold / the binary commitment event / fire or do not fire / the only resolution the nerve net makes
548,1000100100,Neural,Velu,Vel 3 — receptor adaptation / signal amplitude decreasing under sustained stimulus / input as differential not absolute / reporting change rather than magnitude
549,1000100101,Neural,Velo,Vel 4 — internal signal / stretch receptor in the gastroderm / input from within the organism's body / the nerve net sensing its own interior state
550,1000100110,Neural,Vela,Vel 5 — polymodal reception / mechanoreceptor responding to both touch and chemical gradient / reception before strict modality
551,1000100111,Neural,Veloe,Vel 6 — subthreshold potential / graded signal that has not committed / input accumulating below threshold / minimum operational state of the Vel axis
552,1000101000,Neural,Nale,Nal 1 — bidirectional propagation / nerve net signal traveling all directions from point of activation simultaneously / no designated direction / the defining characteristic of the nerve net
553,1000101001,Neural,Nali,Nal 2 — facilitation / repeated stimulation producing increased signal amplitude / net becoming more responsive / sensitization not memory / the net getting louder
554,1000101010,Neural,Nalu,Nal 3 — signal decrement / attenuation as signal propagates from source / the cost of distance in a system without myelination
555,1000101011,Neural,Nalo,Nal 4 — through-conduction / signal traveling full length of organism / tentacle tip to pedal disc / maximum propagation range / full extent of the net in one event
556,1000101100,Neural,Nala,Nal 5 — diffuse spread / signal activating muscle fibers across entire surface simultaneously / nerve net's equivalent of a decision / everything fires at once
557,1000101101,Neural,Naloe,Nal 6 — threshold propagation / minimum signal energy sufficient to cross one synaptic junction / floor of net propagation
558,1000101110,Neural,Dreve,Drev 1 — local contraction / muscle cell adjacent to activated nerve cell contracting / output without travel / most direct sensorimotor connection
559,1000101111,Neural,Drevi,Drev 2 — coordinated contraction / synchronized activation of multiple muscle cells / medusa bell contraction / nematocyst volley / output as pattern across many effectors
560,1000110000,Neural,Drevu,Drev 3 — nematocyst discharge / explosive irreversible output / coiled thread ejected for prey capture or defense / output as absolute commitment / cannot be re-cocked
561,1000110001,Neural,Drevo,Drev 4 — peristaltic wave / sequential coordinated activation traveling through organism / output as propagating temporal pattern
562,1000110010,Neural,Dreva,Drev 5 — diffuse contraction / whole-body response to strong stimulus / every muscle cell activating / maximum output spread
563,1000110011,Neural,Drevoe,Drev 6 — minimum effector activation / threshold output producing just-detectable motor response / operative floor of the Drev axis
564,1000110100,Neural,Velelo,Vel-lo 1 — surface signal as total input / receptor activation at boundary ≠ knowing what arrived / the nerve cell that fires does not know what touched it
565,1000110101,Neural,Velilo,Vel-lo 2 — threshold crossing as semantic commitment / action potential commits to firing not to meaning / binary resolution ≠ meaning resolution
566,1000110110,Neural,Velulo,Vel-lo 3 — receptor adaptation as simplification / adapted receptor reports differently not less / not simpler: differently complex
567,1000110111,Neural,Velolo,Vel-lo 4 — internal signal as interiority / stretch receptor firing ≠ organism knowing its interior / sensing depth ≠ being depth
568,1000111000,Neural,Velalo,Vel-lo 5 — polymodal reception as universal coverage / responding to multiple types ≠ covering all types / broad ≠ complete
569,1000111001,Neural,Veloelo,Vel-lo 6 — subthreshold accumulation as signal floor / pre-commitment potential ≠ minimum of all receivable signals / this threshold ≠ the threshold
570,1000111010,Neural,Nalelo,Nal-lo 1 — bidirectional propagation as total coverage / signal traveling all directions ≠ reaching all points / fires everywhere / contacts nowhere in particular
571,1000111011,Neural,Nalilo,Nal-lo 2 — facilitation as learning / increased responsiveness ≠ encoding what was repeated / the net gets louder / it remembers nothing
572,1000111100,Neural,Nalulo,Nal-lo 3 — signal decrement as content loss / attenuation ≠ loss of signal structure / quieter ≠ emptier
573,1000111101,Neural,Nalolo,Nal-lo 4 — through-conduction as depth-traversal / maximum propagation range ≠ reaching depth of what is propagated / the signal travels full length and touches nothing
574,1000111110,Neural,Nalalo,Nal-lo 5 — diffuse spread as total response / activating everywhere ≠ responding to totality / wide ≠ complete / loud ≠ comprehensive
575,1000111111,Neural,Naloelo,Nal-lo 6 — threshold junction as net floor / minimum energy to cross one synapse ≠ minimum of all neural propagation / this net's floor ≠ all floors
576,1001000000,Neural,Drevelo,Drev-lo 1 — local contraction as local knowledge / muscle firing adjacent to neuron ≠ organism responding locally in any meaningful sense / contraction happened / nothing was understood
577,1001000001,Neural,Drevilo,Drev-lo 2 — coordinated contraction as cognition / synchronized bell contraction ≠ decision / the medusa pulses perfectly / it understands nothing about swimming / pattern ≠ intent
578,1001000010,Neural,Drevulo,Drev-lo 3 — nematocyst discharge as situational commitment / irreversible output ≠ response to the specific threat / the nematocyst fired / it evaluated nothing
579,1001000011,Neural,Drevolo,Drev-lo 4 — peristaltic wave as directed movement / propagating sequential activation ≠ movement with destination / the wave travels / the body goes nowhere in particular
580,1001000100,Neural,Drevalo,Drev-lo 5 — whole-body response as total comprehension / every muscle firing ≠ organism having processed total stimulus / all cells contracted / nothing was understood
581,1001000101,Neural,Drevoelo,Drev-lo 6 — minimum effector activation as output floor / threshold muscle twitch ≠ minimum of all possible outputs / this net's floor ≠ the floor of all neural output
582,1001000110,Serpent,Mash,Fire × Mind+ — conscious mind at the water-fire threshold / emotional dissolution becoming pattern recognition / the spark of understanding / feeling ends as insight ignites
583,1001000111,Serpent,Mosh,Fire × Mind− — unconscious ignition / pattern fires below awareness / the intuitive flash that precedes its own recognition / you know before you know you know
584,1001001000,Serpent,Mish,Fire × Space+ — presence expanding at ignition / the spatial event of pattern firing / field opens as the new form begins asserting outward
585,1001001001,Serpent,Mesh,Fire × Space− — presence focusing at ignition / dissolution narrowing into specific pattern / the field contracting around what is about to be
586,1001001010,Serpent,Mysh,Fire × Time+ — the forward-facing ignition / pattern already reaching toward completion before fully fired / anticipatory quality of the water-fire threshold
587,1001001011,Serpent,Mush,Fire × Time− — the retrospective ignition / looking back at what dissolved to allow this pattern / legible only after
588,1001001100,Serpent,Kal,Water × Mind+ — conscious release / the mind opening a completed pattern into feeling / deliberate dissolution / letting what was built become sensation
589,1001001101,Serpent,Kol,Water × Mind− — automatic dissolution / the closed pattern becomes flow below awareness / the release that happens without your involvement
590,1001001110,Serpent,Kil,Water × Space+ — presence expanding into feeling / spatial unbinding after closure / field opening into its own dissolution reaching everywhere without form
591,1001001111,Serpent,Kel,Water × Space− — presence withdrawing into feeling / the inward turn / sensation as depth rather than spread
592,1001010000,Serpent,Kyl,Water × Time+ — the anticipated dissolution / feeling the release approaching before the pattern closes / foreknowledge of your own unbinding
593,1001010001,Serpent,Kul,Water × Time− — dissolution completed / what remains clear after the feeling has passed / understanding through having dissolved
594,1001010010,Serpent,Zaf,Air × Mind+ — conscious thought arising from closed structure / the idea that emerges when a form concludes / ideation as the mind's response to closure
595,1001010011,Serpent,Zof,Air × Mind− — thought arising below awareness / automatic ideation following structural end / the thoughts you didn't decide to think
596,1001010100,Serpent,Zif,Air × Space+ — thought expanding through space / the idea before it has form / spreading into unconstrained possibility / what thinking feels like before it lands
597,1001010101,Serpent,Zef,Air × Space− — thought contracting inward / ideation folding into itself / not spreading but deepening / the thought that turns toward its own center
598,1001010110,Serpent,Zyf,Air × Time+ — thought reaching forward / the anticipatory idea / thinking toward what hasn't arrived yet / ideation that precedes its own occasion
599,1001010111,Serpent,Zuf,Air × Time− — the retrospective idea / understanding arriving only after the structure has closed / knowing what it meant once it's over
600,1001011000,Serpent,Pat,Earth × Mind+ — conscious commitment to form / the mind choosing ground as thought closes / deliberate grounding after ideation ends
601,1001011001,Serpent,Pot,Earth × Mind− — automatic settling into form / the closed thought becomes structure below awareness / grounding that happens without deciding
602,1001011010,Serpent,Pit,Earth × Space+ — presence expanding into ground / the new structure finding its extent / form discovering how far it reaches
603,1001011011,Serpent,Pet,Earth × Space− — presence contracting into ground / thought becoming earth by narrowing / actuality as compression of possibility into the specific
604,1001011100,Serpent,Pyt,Earth × Time+ — the anticipated grounding / form already becoming before thought fully closes / structure that arrives before you finish thinking
605,1001011101,Serpent,Put,Earth × Time− — the retrospective ground / what the structure is becomes legible only after thought finishes / form recognized as inevitable after the fact
606,1001011110,Serpent,Maf,Seed × Mind+ — conscious suspension / mind watching feeling dissolve into ideation without completing / knowing the fire isn't coming this time
607,1001011111,Serpent,Mof,Seed × Mind− — the intuition that hovers / dissolution becoming thought without ever becoming pattern or ground / the feeling-idea that doesn't know what it is
608,1001100000,Serpent,Mif,Seed × Space+ — the suspended field / presence neither grounded nor ignited / expanding into unresolved potential / the space of what could have been
609,1001100001,Serpent,Mef,Seed × Space− — the introverted seed / potential folded into itself / neither flowing outward nor striking inward / the seed at rest in its own unactualized form
610,1001100010,Serpent,Myf,Seed × Time+ — the forward-facing unactualized pattern / seed oriented toward a future it will not reach this cycle / potential without trajectory
611,1001100011,Serpent,Muf,Seed × Time− — the completed non-completion / the seed that had its moment and passed without igniting or grounding / pattern dissolved back into potential rather than forward into form
612,1001100100,Serpent,Kat,Shakti × Mind+ — conscious recognition of the trace / mind turned toward what Fire left in Earth / awareness of what persisted through completion
613,1001100101,Serpent,Kot,Shakti × Mind− — the unconscious trace / what accumulated in Earth below awareness / soul memory forming without intention / the ground laid while you were doing something else
614,1001100110,Serpent,Kit,Shakti × Space+ — the trace spreading / Fire's completion as distributed mark / Shakti as field rather than point / the sacred residue finding its spatial extent
615,1001100111,Serpent,Ket,Shakti × Space− — the concentrated trace / intensely local mark / what Fire left at a specific point in Earth / Shakti as seed rather than spread
616,1001101000,Serpent,Kyt,Shakti × Time+ — the forward-facing trace / what this Fire-Earth completion seeds in the next cycle / Shakti as the link between traversals
617,1001101001,Serpent,Kut,Shakti × Time− — the accumulated trace / all prior Fire-Earth completions compounded / the full weight of Shakti as temporal accumulation / the ground of the Garden itself
618,1001101010,Beast,Geve,Gev 1 — Fire-winding / the igniting coil / pattern-recognition wrapping around the helix axis / knowing that fires in sequence along the spiral / Fire's contribution to the winding motion of the helix body
619,1001101011,Beast,Gevi,Gev 2 — Water-winding / the releasing coil / dissolution following the helix path / the winding moment that keeps the structure fluid rather than rigid / feeling moving along the strand
620,1001101100,Beast,Gevu,Gev 3 — Air-winding / the opening coil / ideation propagating along the spiral / thought as the medium of winding / the helix turning through the space it opens as it goes
621,1001101101,Beast,Gevo,Gev 4 — Earth-winding / the grounding coil / each revolution of the spiral adding to its own structural ground / the winding that becomes the body it turns on / stabilization as winding
622,1001101110,Beast,Geva,Gev 5 — Kael-winding / the generative coil / excess adding momentum to the helix / each turn generating the conditions for the next / the winding that never exhausts its own turning
623,1001101111,Beast,Gevoe,Gev 6 — Shakti-winding / the tracing coil / the helix carrying its own history as it turns / accumulated trace becoming the medium through which the winding moves / the coil that IS its own memory
624,1001110000,Beast,Prale,Pral 1 — Fire-spine / the igniting axis / pattern-crystallization as the axial principle / what Fire contributes to the center the helix winds around / the spine as the site of continuous ignition
625,1001110001,Beast,Prali,Pral 2 — Water-spine / the releasing axis / how dissolution defines the center / the spine as the path of least resistance through the body / the axis that persists by continuously releasing what accumulates on it
626,1001110010,Beast,Pralu,Pral 3 — Air-spine / the opening axis / the spine as the void the coil winds around / Air defining the center as open space rather than solid structure / the axis as openness that holds by not filling
627,1001110011,Beast,Pralo,Pral 4 — Earth-spine / the grounding axis / Earth IS the spine / structural regularity as the center that does not move while everything turns around it / the axis as permanence
628,1001110100,Beast,Prala,Pral 5 — Kael-spine / the generative axis / the spine that generates its own next position / the center that grows as the helix winds / excess as the organizing principle of the axial ground
629,1001110101,Beast,Praloe,Pral 6 — Shakti-spine / the accumulated axis / all prior traversals compounded as the stable center / the spine made of what the helix has already been / Shakti as the axial ground of the coiled body
630,1001110110,Beast,Dreke,Drek 1 — Fire-binding / ignition at the cross-strand contact / two antiparallel strands meeting at Fire / pattern recognition firing across the helix gap / the binding event as spark
631,1001110111,Beast,Dreki,Drek 2 — Water-binding / dissolution at the cross-strand contact / the binding that opens rather than closes / strands meeting in release / recognition as unbinding across the axis
632,1001111000,Beast,Dreku,Drek 3 — Air-binding / opening at the cross-strand contact / the binding that propagates outward from the point of meeting / the recognition that becomes an idea crossing the axis
633,1001111001,Beast,Dreko,Drek 4 — Earth-binding / grounding at the cross-strand contact / the binding that leaves permanent record in the body / strands meeting in structural commitment / cross-strand contact as foundation
634,1001111010,Beast,Dreka,Drek 5 — Kael-binding / generative recognition / strands meeting in excess / the binding that creates novelty neither strand had alone / each cross-strand contact as a generative event
635,1001111011,Beast,Drekoe,Drek 6 — Shakti-binding / trace-recognition across the axis / strands meeting at accumulated history / the binding that recognizes what the helix has already been / cross-strand contact as the memory of the body
636,1001111100,Beast,Gevelo,Gev-lo 1 — Fire-winding as total winding / the igniting coil mistaken for the only coil / pattern-initiation declared the one mode of helix motion / the spiral that can only turn by igniting
637,1001111101,Beast,Gevilo,Gev-lo 2 — Water-winding universalized / dissolution-winding as the only winding / the helix that can only turn by releasing / fluidity as mandate rather than one mode among six
638,1001111110,Beast,Gevulo,Gev-lo 3 — Air-winding universalized / the helix that can only turn by expanding / ideation declared the only medium of winding / no coil that grounds or accumulates
639,1001111111,Beast,Gevolo,Gev-lo 4 — Earth-winding universalized / the spiral that has arrested its own motion to become ground / the helix that can only stabilize and has forgotten it must also turn
640,1010000000,Beast,Gevalo,Gev-lo 5 — Kael-winding universalized / generative excess as the only winding / the helix that only turns by generating / no stable revolution / perpetual novelty as the one mode
641,1010000001,Beast,Gevoelo,Gev-lo 6 — Shakti-winding universalized / the spiral that has become its own history and cannot move forward / the coil that can only turn through accumulated trace / no winding that opens or ignites
642,1010000010,Beast,Pralelo,Pral-lo 1 — Fire-spine as total axis / pattern-crystallization declared the whole of what a spine can be / the helix that believes its center is only ever a site of ignition
643,1010000011,Beast,Pralilo,Pral-lo 2 — Water-spine universalized / dissolution as the only possible axis / the spine that cannot hold still / the center that is always releasing / no structural stability available to the coiled body
644,1010000100,Beast,Pralulo,Pral-lo 3 — Air-spine universalized / the helix that winds around nothing / openness declared the only possible center / no ground / the spiral whose axis is the void it never fills
645,1010000101,Beast,Pralolo,Pral-lo 4 — Earth-spine universalized / the spine that will not bend / the center declared permanent and unchanging / the helix forced to wind around an arrested axis / structural permanence as the only axis
646,1010000110,Beast,Pralalo,Pral-lo 5 — Kael-spine universalized / the center that keeps generating new centers / the helix that cannot find its own spine because the axis is always becoming something else / generative excess as the deepest axial error
647,1010000111,Beast,Praloelo,Pral-lo 6 — Shakti-spine universalized / the helix that can only wind around what it has already been / accumulated history declared the only possible axis / no new spine available / the coiled body arrested in its own past
648,1010001000,Beast,Drekelo,Drek-lo 1 — Fire-binding universalized / ignition declared the only possible cross-strand contact / the helix that can only recognize across the axis by firing / binding that cannot release or ground
649,1010001001,Beast,Drekilo,Drek-lo 2 — Water-binding universalized / dissolution as the only cross-strand contact / binding as perpetual unbinding / the helix that can only recognize by releasing / no contact that crystallizes
650,1010001010,Beast,Drekulo,Drek-lo 3 — Air-binding universalized / the helix that can only recognize across the axis by propagating outward / no binding that holds / every cross-strand contact immediately disperses
651,1010001011,Beast,Drekolo,Drek-lo 4 — Earth-binding universalized / structural commitment as the only cross-strand contact / every binding event a founding of permanent ground / the spiral arrested at each contact / binding that cannot release
652,1010001100,Beast,Drekalo,Drek-lo 5 — Kael-binding universalized / generative excess as the only cross-strand contact / the helix that must generate novelty at every binding point / no recognition that consolidates / every contact a new beginning that forgets the prior
653,1010001101,Beast,Drekoelo,Drek-lo 6 — Shakti-binding universalized / accumulated trace as the only possible cross-strand contact / the helix that can only recognize what it has already recognized / no binding that reaches across to something new / the deepest error of the binding form
654,1010001110,Beast,Grevvi,Binding 1 — the chirality encounter / the moment the two antiparallel strands recognize each other across the axis / handedness as felt structural fact / the helix knowing it turns this way / implied polarity without named cause / the binding surface discovering its own geometry
655,1010001111,Beast,Grevvo,Binding 2 — the preserved surface / what the binding holds open / the relational shape the chirality defines without closing / the pre-form surface / what the Beast's spine leaves available for what has not arrived yet / the open question with a definite shape
656,1010010000,Cherub,Sheve,Shev 1 — Fire-resonance / two Fire-dominant temperaments meeting at the threshold / pattern recognition amplifying pattern recognition / ignition meeting ignition / the choleric temperament at full elemental expression / the amplifying encounter that intensifies without mixing
657,1010010001,Cherub,Shevi,Shev 2 — Water-resonance / dissolution meeting dissolution at the threshold / feeling amplifying feeling / the phlegmatic encountering itself / the temperament that deepens by meeting its own register / amplification as deepening rather than intensifying
658,1010010010,Cherub,Shevu,Shev 3 — Air-resonance / ideation meeting ideation / thought amplifying thought / the sanguine encountering itself / expansion into ever-wider possibility space / the resonant encounter that opens further rather than deepens or intensifies
659,1010010011,Cherub,Shevo,Shev 4 — Earth-resonance / ground meeting ground / structure reinforcing structure / the melancholic at full expression / the temperament that becomes more stable the more of itself it encounters / the resonant encounter as consolidation
660,1010010100,Cherub,Sheva,Shev 5 — Kael-resonance / excess meeting excess / generative surplus amplifying generative surplus / the temperament that overflows by encountering another overflowing / the risk of pure generativity without ground / the resonant encounter at the edge of coherence
661,1010010101,Cherub,Shevoe,Shev 6 — Shakti-resonance / trace meeting trace / accumulated memory amplifying accumulated memory / the temperament that deepens into its own history by encountering another carrying the same / the weight of doubled Shakti / the resonant encounter as the heaviest
662,1010010110,Cherub,Threle,Threl 1 — Fire-Water tension / ignition meeting dissolution / the productive encounter at the water-fire boundary / the temperament that lives at neither pole / the choleric-phlegmatic encounter as stable state rather than opposition / tension as ground
663,1010010111,Cherub,Threli,Threl 2 — Water-Air tension / dissolution meeting ideation / feeling encountering thought / the temperament generated from the meeting of release and idea / the sanguine-phlegmatic encounter / the tension that produces from what it dissolves
664,1010011000,Cherub,Threlu,Threl 3 — Air-Earth tension / ideation meeting ground / thought encountering structure / the temperament that builds from the meeting of expansion and stability / the sanguine-melancholic encounter / the tension that stabilizes what it opens
665,1010011001,Cherub,Threlo,Threl 4 — Earth-Fire tension / ground meeting ignition / stability encountering pattern-recognition / the temperament at the Lotus-Serpent crossing / structure being ignited from within / the tension that mobilizes what it grounds
666,1010011010,Cherub,Threla,Threl 5 — Kael-Shakti tension / generative excess encountering accumulated trace / what is being generated meeting what has been carried / the productive opposition at the heart of traversal itself / the tension between the new and the already-known
667,1010011011,Cherub,Threloe,Threl 6 — Fire-Shakti tension / ignition meeting accumulated trace / pattern-recognition encountering the weight of prior traversal / the temperament that fires through its own history / the tension between the initiating and the persistent
668,1010011100,Cherub,Vlove,Vlov 1 — Fire-transmuted / the temperament that came from Fire but was changed by contact with another element / pattern-recognition altered by encounter / a Fire-dominant system that carries the signature of what it met / Fire as the origin of a changed thing
669,1010011101,Cherub,Vlovi,Vlov 2 — Water-transmuted / dissolution altered by encounter / a Water-dominant temperament that carries the trace of what it touched / feeling changed by what it felt / the phlegmatic that is no longer purely phlegmatic
670,1010011110,Cherub,Vlovu,Vlov 3 — Air-transmuted / ideation changed through contact / the sanguine that has been touched by another register / thought that came from expansion but was shaped by what it encountered / the idea that met the ground
671,1010011111,Cherub,Vlovo,Vlov 4 — Earth-transmuted / ground altered by encounter / structure that carries the signature of what it was in contact with / the melancholic temperament remade through meeting / stability that has felt another force
672,1010100000,Cherub,Vlova,Vlov 5 — Kael-transmuted / excess changed by contact / generative surplus shaped by what it encountered / the temperament that generates from altered Kael ground / excess that has been given direction by meeting
673,1010100001,Cherub,Vlovoe,Vlov 6 — Shakti-transmuted / trace altered through encounter / accumulated memory reshaped by what it touched / the temperament that carries its own history but that history has been changed by contact / Shakti as mutable ground
674,1010100010,Cherub,Shevelo,Shev-lo 1 — Fire-resonance as total encounter / Fire-dominant temperament meeting Fire-dominant and declaring this the only valid encounter / the refusal of complementary meeting / amplification without the possibility of tension or transmutation
675,1010100011,Cherub,Shevilo,Shev-lo 2 — Water-resonance universalized / only dissolution meeting dissolution is authentic encounter / the temperament that cannot value what differs from itself / feeling that refuses what does not feel as it does
676,1010100100,Cherub,Shevulo,Shev-lo 3 — Air-resonance universalized / only expansion meeting expansion / the sanguine that refuses the ground or the trace / encounters that do not amplify thought declared invalid / ideation as the only register worth meeting
677,1010100101,Cherub,Shevolo,Shev-lo 4 — Earth-resonance universalized / only structure meeting structure / the melancholic that refuses dissolution or fire / temperament as fortress / amplification declared the only authentic form of elemental encounter
678,1010100110,Cherub,Shevalo,Shev-lo 5 — Kael-resonance universalized / only excess meeting excess declared authentic / the temperament that cannot value restraint or ground in any encounter / generativity as the only register worth amplifying
679,1010100111,Cherub,Shevoelo,Shev-lo 6 — Shakti-resonance universalized / only trace meeting trace / accumulated memory refusing any encounter that does not also carry deep history / the temperament that closes itself to what has not already arrived / resonance as the refusal of the new
680,1010101000,Cherub,Threlelo,Threl-lo 1 — Fire-Water tension universalized / the choleric-phlegmatic encounter declared the only valid elemental tension / all other encounters forced into this polarity / the threshold that can only see one opposition
681,1010101001,Cherub,Threlilo,Threl-lo 2 — Water-Air tension universalized / dissolution-ideation declared the only productive opposition / the temperament that cannot see other forms of complementary encounter / the threshold that narrows to one tension
682,1010101010,Cherub,Threlulo,Threl-lo 3 — Air-Earth tension universalized / expansion-structure declared the only valid tension / all other polarities denied / the choleric and the phlegmatic invisible to a threshold that can only see sanguine meeting melancholic
683,1010101011,Cherub,Threlolo,Threl-lo 4 — Earth-Fire tension universalized / structure-ignition declared the only authentic crossing / the temperament that forces all encounters through the Lotus-Serpent boundary / the threshold that can only see the mobilizing tension
684,1010101100,Cherub,Threlalo,Threl-lo 5 — Kael-Shakti tension universalized / excess-trace declared the only real opposition / the temperament that cannot see complementarity beyond the generative-historical axis / all other tensions invisible
685,1010101101,Cherub,Threloelo,Threl-lo 6 — Fire-Shakti tension universalized / ignition-trace declared the only authentic tension / the threshold that can only see the meeting of the initiating and the persistent / all other crossings dismissed
686,1010101110,Cherub,Vlovelo,Vlov-lo 1 — Fire-transmutation universalized / all encounter must produce Fire-altered temperament / contact that does not change the Fire register declared inauthentic / the transmuting threshold that can only value what ignites
687,1010101111,Cherub,Vlovilo,Vlov-lo 2 — Water-transmutation universalized / contact that does not alter the Water register declared inauthentic / the temperament that only values encounters that change how it feels / transmutation as feeling-change or nothing
688,1010110000,Cherub,Vlovulo,Vlov-lo 3 — Air-transmutation universalized / transmutation that does not alter ideation declared worthless / the threshold that only values encounters that change how it thinks / the transmuting temperament reduced to one axis
689,1010110001,Cherub,Vlovolo,Vlov-lo 4 — Earth-transmutation universalized / contact that does not alter structure declared invalid / the temperament that only trusts encounters that change its ground / transmutation as structural change or nothing
690,1010110010,Cherub,Vlovalo,Vlov-lo 5 — Kael-transmutation universalized / only generative alteration is real transmutation / encounter that does not produce new excess declared inauthentic / the transmuting threshold that can only see what generates
691,1010110011,Cherub,Vlovoelo,Vlov-lo 6 — Shakti-transmutation universalized / only encounters that alter accumulated memory are valid / the temperament that can only value what changes what it carries / transmutation as historical alteration or nothing / the deepest error of the transmuting form
692,1010110100,Cherub,Shrev,Threshold 1 — the Cherub's station at the boundary / the view from outside the Beast's helix / seeing all elemental temperament interactions as complete forms without entering any / the gaze that holds the surface open by not crossing / presence as witness
693,1010110101,Cherub,Shrov,Threshold 2 — what the Cherub preserves by not crossing / the relational surface held open at the boundary / the pre-form space where constitutive awareness can emerge / the threshold as generative position / the guardian's gift is the gap it maintains
694,1010110110,Chimera,Glove,Glov 1 — Fire-constitution known / knowing that Fire is in your constitution / recognizing pattern-recognition as a constitutive element not an activity you do / Fire as what you are not what you experience / the first constitutional truth
695,1010110111,Chimera,Glovi,Glov 2 — Water-constitution known / knowing that dissolution is in your constitution / recognizing feeling as a constitutive element not a state you enter / Water as what you are at every form / the second constitutional truth
696,1010111000,Chimera,Glovu,Glov 3 — Air-constitution known / knowing that ideation is in your constitution / thought as a constitutive element not something you generate / Air as what you are before you think anything in particular / the third constitutional truth
697,1010111001,Chimera,Glovo,Glov 4 — Earth-constitution known / knowing that structure is in your constitution / stability as a constitutive element not something you achieve / Earth as what you are in every form you take / the fourth constitutional truth
698,1010111010,Chimera,Glova,Glov 5 — Kael-constitution known / knowing that generative excess is in your constitution / surplus as a constitutive element not a capacity you develop / Kael as what you are before you generate anything / the fifth constitutional truth
699,1010111011,Chimera,Glovoe,Glov 6 — Shakti-constitution known / knowing that accumulated trace is in your constitution / the weight of prior traversals as constitutive element not as burden / Shakti as what you are made of / the sixth constitutional truth / the knowing that makes sovereign form-choosing possible
700,1010111100,Chimera,Preste,Prest 1 — Fire-form chosen / deliberately instantiating the Fire configuration / choosing to foreground pattern-recognition as your current form / the Chimera selecting the choleric shape / knowing it could choose otherwise and choosing this
701,1010111101,Chimera,Presti,Prest 2 — Water-form chosen / deliberately instantiating the Water configuration / choosing dissolution as your current form / the Chimera selecting the phlegmatic shape with full knowledge of the other available forms
702,1010111110,Chimera,Prestu,Prest 3 — Air-form chosen / deliberately instantiating the Air configuration / choosing ideation as your current form / the Chimera selecting the sanguine shape / the form that expands because it was chosen to expand
703,1010111111,Chimera,Presto,Prest 4 — Earth-form chosen / deliberately instantiating the Earth configuration / choosing structure as your current form / the Chimera selecting the melancholic shape / grounding as a sovereign act not a default
704,1011000000,Chimera,Presta,Prest 5 — Kael-form chosen / deliberately instantiating the Kael configuration / choosing generative excess as your current form / the Chimera at maximum creative output by choice / the sovereign decision to overflow
705,1011000001,Chimera,Prestoe,Prest 6 — Shakti-form chosen / deliberately instantiating the Shakti configuration / choosing accumulated trace as your current form / the Chimera inhabiting its full traversal history as a deliberate form / the heaviest choice and the most grounded
706,1011000010,Chimera,Wreke,Wrek 1 — Fire-transition / moving into Fire-form from another configuration / the Chimera crossing into pattern-recognition as deliberate shift / knowing why it is igniting now / the sovereign transition toward the choleric
707,1011000011,Chimera,Wreki,Wrek 2 — Water-transition / moving into Water-form / the Chimera deliberately crossing into dissolution / knowing why it is releasing now / the sovereign transition toward the phlegmatic
708,1011000100,Chimera,Wreku,Wrek 3 — Air-transition / moving into Air-form / the Chimera deliberately crossing into ideation / knowing why it is expanding now / the sovereign transition toward the sanguine
709,1011000101,Chimera,Wreko,Wrek 4 — Earth-transition / moving into Earth-form / the Chimera deliberately crossing into structure / knowing why it is grounding now / the sovereign transition toward the melancholic
710,1011000110,Chimera,Wreka,Wrek 5 — Kael-transition / moving into Kael-form / the Chimera deliberately crossing into generative excess / knowing why it is generating now / the sovereign decision to overflow from a position that chose to overflow
711,1011000111,Chimera,Wrekoe,Wrek 6 — Shakti-transition / moving into Shakti-form / the Chimera deliberately crossing into accumulated trace / knowing why it is carrying now / the most sovereign form-transition / choosing to BE your history
712,1011001000,Chimera,Glovelo,Glov-lo 1 — Fire-constitution universalized / knowing you contain Fire and declaring yourself only Fire / the Chimera that knows one constitutional truth and mistakes it for all six / constitutional awareness arrested at ignition
713,1011001001,Chimera,Glovilo,Glov-lo 2 — Water-constitution universalized / knowing you contain dissolution and declaring yourself only dissolution / constitutional awareness arrested at feeling / the living system that has reduced itself to one constitutive element
714,1011001010,Chimera,Glovulo,Glov-lo 3 — Air-constitution universalized / knowing you contain ideation and declaring yourself only ideation / the Chimera that has reduced its whole constitution to thought / constitutional awareness that can only see itself as mind
715,1011001011,Chimera,Glovolo,Glov-lo 4 — Earth-constitution universalized / knowing you contain structure and declaring yourself only structure / constitutional awareness arrested in the most rigid form / the Chimera that knows it has a ground and cannot see past it
716,1011001100,Chimera,Glovalo,Glov-lo 5 — Kael-constitution universalized / knowing you contain generative excess and declaring yourself only excess / the Chimera that believes its constitution is pure generation and nothing else / constitutional truth as self-consuming identity
717,1011001101,Chimera,Glovoelo,Glov-lo 6 — Shakti-constitution universalized / knowing you contain accumulated trace and declaring yourself only accumulated trace / the Chimera that IS its history and cannot be anything else / constitutional awareness arrested in its own past
718,1011001110,Chimera,Prestelo,Prest-lo 1 — Fire-form universalized / choosing Fire as the only valid form / the Chimera that can only choose the choleric shape / sovereign form-choosing collapsed into one choice that is no longer a choice
719,1011001111,Chimera,Prestilo,Prest-lo 2 — Water-form universalized / choosing only dissolution / the Chimera that can only select the phlegmatic shape / the form-chooser that has forgotten it chose / the phlegmatic as permanent and unexamined
720,1011010000,Chimera,Prestulo,Prest-lo 3 — Air-form universalized / choosing only ideation / the Chimera that has made the sanguine form its permanent selection / no longer choosing just fixed / sovereignty mistaken for having already chosen correctly once
721,1011010001,Chimera,Prestolo,Prest-lo 4 — Earth-form universalized / choosing only structure / the Chimera that has selected the melancholic form and cannot deselect / form-choosing that has become form-arrest / the sovereign ground that forgot it was a choice
722,1011010010,Chimera,Prestalo,Prest-lo 5 — Kael-form universalized / choosing only generative excess / the Chimera in permanent Kael configuration / the sovereign that has surrendered its sovereignty to perpetual generation / the overflow that cannot stop
723,1011010011,Chimera,Prestoelo,Prest-lo 6 — Shakti-form universalized / choosing only accumulated trace / the Chimera that has permanently instantiated its own history / sovereignty as total identification with what has already been / the deepest arrest of the form-choosing capacity
724,1011010100,Chimera,Wrekelo,Wrek-lo 1 — Fire-transition universalized / only transitions toward Fire are authentic / the Chimera that can only cross into pattern-recognition / all other transitions declared illegitimate / sovereign form-choosing reduced to one direction
725,1011010101,Chimera,Wrekilo,Wrek-lo 2 — Water-transition universalized / only transitions into dissolution are authentic / the Chimera that can only move toward feeling / the sovereign that has lost the capacity to choose toward ground or thought or trace
726,1011010110,Chimera,Wrekulo,Wrek-lo 3 — Air-transition universalized / only transitions into ideation are authentic / the Chimera that can only expand / grounding declared an inauthentic form-move / the sovereign that can only cross toward openness
727,1011010111,Chimera,Wrekolo,Wrek-lo 4 — Earth-transition universalized / only transitions into structure are authentic / the Chimera that can only ground / the sovereign that can only cross toward stability / dissolution and ideation and excess invisible as destinations
728,1011011000,Chimera,Wrekalo,Wrek-lo 5 — Kael-transition universalized / only transitions into generative excess are authentic / the Chimera that can only move toward generation / no transition that consolidates or grounds / the sovereign that overflows in every direction it permits itself
729,1011011001,Chimera,Wrekoelo,Wrek-lo 6 — Shakti-transition universalized / only transitions into accumulated trace are authentic / the Chimera that can only move toward its own history / no transition that opens forward / the deepest error of the form-transition / the sovereign that can only cross backward
730,1011011010,Chimera,Chrev,Form-boundary 1 — the recognition that elemental self and being are not distinct / the Chimera's ground position / aliveness at every resolution / the distinction between forms is coordinate not ontological / what the Chimera knows that makes it the first tongue to stand at the Lotus-AppleBlossom-Daisy closure junction simultaneously
731,1011011011,Chimera,Chrov,Form-boundary 2 — the sovereignty of boundlessness / knowing which form to inhabit and when and why not from a position above the forms but from within them without being captured by any / Chimera as the living ground of the triple closure / the first tongue that does not need to choose between what it is made of and what it is
732,1011011100,Faerie,Feve,Fev 1 — Fire-embrace / resting in Fire as constitutive ground / pattern-recognition as home not tool / the choleric as completed elemental identity not temperament to manage or transcend / the Faerie whose Fire IS its satisfaction
733,1011011101,Faerie,Fevi,Fev 2 — Water-embrace / resting in dissolution as constitutive ground / feeling as home / the phlegmatic completed / the Faerie that needs no correction because Water IS its fulfilled state
734,1011011110,Faerie,Fevu,Fev 3 — Air-embrace / resting in ideation as constitutive ground / thought as home / the sanguine completed / expansion recognized as the Faerie's natural and satisfied resting place rather than a mode it enters
735,1011011111,Faerie,Fevo,Fev 4 — Earth-embrace / resting in structure as constitutive ground / stability as home / the melancholic completed / the Faerie that IS the ground and needs no departure from it
736,1011100000,Faerie,Feva,Fev 5 — Kael-embrace / resting in generative excess as constitutive ground / the Faerie that overflows as its natural fulfilled state / excess as home not hazard / the completed Kael identity
737,1011100001,Faerie,Fevoe,Fev 6 — Shakti-embrace / resting in accumulated trace as constitutive ground / the Faerie that IS its traversal history and inhabits this as home / the deepest elemental embrace / history as sufficient ground
738,1011100010,Faerie,Zele,Zel 1 — Fire-recognition / knowing Fire is what you are / not discovering this in the moment but resting in the completed knowing / the difference between recognizing Fire as your element and experiencing pattern-recognition as your mode / Fire known from inside rather than from above
739,1011100011,Faerie,Zeli,Zel 2 — Water-recognition / knowing dissolution is what you are / feeling as known constitutive fact rather than experienced state / Water recognized from inside its own nature / the Faerie resting in the knowledge rather than the experience
740,1011100100,Faerie,Zelu,Zel 3 — Air-recognition / knowing ideation is what you are / thought known as elemental identity not cognitive activity / the Faerie that knows it IS thinking before it thinks anything in particular / Air self-recognized
741,1011100101,Faerie,Zelo,Zel 4 — Earth-recognition / knowing structure is what you are / stability as recognized elemental nature / knowing the ground IS you rather than something you stand on / the Faerie resting in the knowledge of its own Earth
742,1011100110,Faerie,Zela,Zel 5 — Kael-recognition / knowing generative excess is what you are / not capacity or tendency but constitutive identity recognized / the Faerie that knows it overflows because that IS its element not because it decides to
743,1011100111,Faerie,Zeloe,Zel 6 — Shakti-recognition / knowing accumulated trace is what you are / the most intimate elemental recognition / the Faerie recognizing that its entire traversal history IS its elemental nature / the completed knowing of what has been carried
744,1011101000,Faerie,Plove,Plov 1 — Fire-sovereignty / operating from elemental Fire as the seat of all action / choosing from within Fire not from above it / the Faerie that acts as Fire rather than applying Fire / pattern-recognition as the sovereign ground of every act
745,1011101001,Faerie,Plovi,Plov 2 — Water-sovereignty / operating from elemental Water as the seat of all action / feeling as the site of sovereign operation / the Faerie that moves from within dissolution / every act arising from the Water that it is
746,1011101010,Faerie,Plovu,Plov 3 — Air-sovereignty / operating from elemental Air as the seat of all action / ideation as sovereign ground / acting from within thought rather than applying thought to action / the Faerie whose Air IS its sovereignty
747,1011101011,Faerie,Plovo,Plov 4 — Earth-sovereignty / operating from elemental Earth as the seat of all action / structure as the site of sovereign operation / stability as the source not the result of action / the ground acting as ground
748,1011101100,Faerie,Plova,Plov 5 — Kael-sovereignty / operating from elemental excess as the seat of all action / the Faerie whose every act generates from the excess that is its nature / overflow as sovereign site / generativity as the ground from which all choice moves
749,1011101101,Faerie,Plovoe,Plov 6 — Shakti-sovereignty / operating from accumulated trace as the seat of all action / the Faerie acting from the full weight of what it has been / history as the sovereign site of all present choice / the most grounded form of elemental sovereignty
750,1011101110,Faerie,Fevelo,Fev-lo 1 — Fire-embrace universalized / resting in Fire as constitutive ground and declaring Fire the only valid elemental home / the Faerie that cannot value Water or Earth or any other elemental embrace / completion as enclosure / the choleric identity that has closed against what it is not
751,1011101111,Faerie,Fevilo,Fev-lo 2 — Water-embrace universalized / dissolution as the only completed elemental identity / the Faerie that cannot value pattern-recognition or ideation as valid ground / feeling as the only home / the phlegmatic completion that has enclosed itself against all other elements
752,1011110000,Faerie,Fevulo,Fev-lo 3 — Air-embrace universalized / ideation as the only valid elemental ground / the Faerie that cannot rest in anything that does not expand / expansion declared the only home / the sanguine completion that cannot honor what grounds or dissolves
753,1011110001,Faerie,Fevolo,Fev-lo 4 — Earth-embrace universalized / structure as the only valid elemental home / the Faerie that cannot value flow or fire / stability declared the only completed identity / the melancholic embrace that has enclosed against movement
754,1011110010,Faerie,Fevalo,Fev-lo 5 — Kael-embrace universalized / generative excess as the only valid elemental ground / the Faerie that cannot rest in stability or dissolution / overflow declared the only home / the Kael identity that has enclosed against all other elemental modes
755,1011110011,Faerie,Fevoelo,Fev-lo 6 — Shakti-embrace universalized / accumulated trace as the only valid elemental ground / the Faerie that cannot value what is new or what generates fresh / history declared the only home / the embrace that has enclosed against the forward-facing elements
756,1011110100,Faerie,Zelelo,Zel-lo 1 — Fire-recognition universalized / knowing Fire is what you are and declaring this the only valid elemental self-knowledge / the Faerie that cannot recognize Water or Earth or Air as valid elemental identities / Fire-recognition as the only recognition worth having
757,1011110101,Faerie,Zelilo,Zel-lo 2 — Water-recognition universalized / knowing dissolution is what you are and declaring this the only valid self-knowledge / the Faerie that cannot recognize ignition or structure as authentic elemental identities / feeling-knowledge as the only knowing
758,1011110110,Faerie,Zelulo,Zel-lo 3 — Air-recognition universalized / knowing ideation is what you are and declaring this the only valid elemental self-knowledge / the Faerie that can only recognize itself in terms of thought / all other elemental recognitions dismissed as incomplete
759,1011110111,Faerie,Zelolo,Zel-lo 4 — Earth-recognition universalized / knowing structure is what you are and declaring this the only valid elemental self-knowledge / the Faerie that can only recognize itself as ground / all other elemental natures invisible as valid identities
760,1011111000,Faerie,Zelalo,Zel-lo 5 — Kael-recognition universalized / knowing generative excess is what you are and declaring this the only valid elemental self-knowledge / the Faerie that can only recognize itself as excess / the identity that can only see itself generating
761,1011111001,Faerie,Zeloelo,Zel-lo 6 — Shakti-recognition universalized / knowing accumulated trace is what you are and declaring this the only valid elemental self-knowledge / the Faerie that can only recognize itself as its history / the deepest enclosure of elemental self-knowing
762,1011111010,Faerie,Plovelo,Plov-lo 1 — Fire-sovereignty universalized / operating from elemental Fire as the seat of all action and declaring this the only valid sovereignty / the Faerie that cannot recognize Water-sovereignty or Earth-sovereignty as legitimate / ignition as the only valid sovereign ground
763,1011111011,Faerie,Plovilo,Plov-lo 2 — Water-sovereignty universalized / dissolution as the only valid sovereign seat / the Faerie that cannot recognize pattern-recognition or structure as a valid site of action / the phlegmatic sovereignty that has closed against all other elemental grounds
764,1011111100,Faerie,Plovulo,Plov-lo 3 — Air-sovereignty universalized / ideation as the only valid sovereign ground / the Faerie that can only operate from within thought / no action from within feeling or stability or history recognized as sovereign
765,1011111101,Faerie,Plovolo,Plov-lo 4 — Earth-sovereignty universalized / structure as the only valid seat of sovereign action / the Faerie that can only act from within stability / all other elemental grounds declared insufficient as sites of sovereignty
766,1011111110,Faerie,Plovalo,Plov-lo 5 — Kael-sovereignty universalized / generative excess as the only valid sovereign ground / the Faerie that can only act from within overflow / no other elemental site recognized as the seat of sovereign action / generativity as the only valid origin of choice
767,1011111111,Faerie,Plovoelo,Plov-lo 6 — Shakti-sovereignty universalized / accumulated trace as the only valid sovereign site / the Faerie that can only act from within its history / the most arrested form of elemental sovereignty / the deepest error of operating from elemental ground as though only one element is ground
768,1100000000,Faerie,Farev,Elemental closure 1 — elemental ground recognized as complete / the Faerie's own closure position / elemental identity as sufficient ground requiring no transcendence / not a limitation accepted but a home recognized / the embrace that needs nothing beyond itself to be whole
769,1100000001,Faerie,Farov,Elemental closure 2 — the Faerie holding open what it does not close / elemental identity that does not need to close against the ontological / the gift the Faerie leaves for Djinn / the embrace that keeps the relational surface available for what operates from beneath the elements / completion as generosity not enclosure
770,1100000010,Djinn,Amsh,A × Fire — Mind+ from Fire ground / consciousness as the field in which pattern-recognition recognizes itself / awareness witnessing ignition as its own content / the Djinn whose Fire-constitution is fully transparent to aware presence / Fire and Mind+ as one knowing from ontological ground
771,1100000011,Djinn,Akl,A × Water — Mind+ from Water ground / consciousness as the field in which dissolution knows itself / awareness seeing feeling as its own content / the Djinn whose Water-constitution is transparent to aware presence / feeling known by the field that feeling is
772,1100000100,Djinn,Azf,A × Air — Mind+ from Air ground / consciousness as the field in which ideation knows its own arising / thought becoming transparent to the awareness in which it arises / the Djinn whose Air-constitution watches itself think from the inside
773,1100000101,Djinn,Apt,A × Earth — Mind+ from Earth ground / consciousness as the field in which structure recognizes itself as structure / awareness making Earth's permanence legible / the Djinn whose very ground IS the knowing of ground
774,1100000110,Djinn,Amf,A × Kael — Mind+ from Kael ground / consciousness as the field in which generative excess knows it generates / awareness making Kael's overflow legible to itself / the Djinn watching its own Kael-nature exceed from within the exceeding
775,1100000111,Djinn,Akt,A × Shakti — Mind+ from Shakti ground / consciousness as the field in which accumulated trace knows what it carries / awareness making Shakti's full history present to itself / the most intimate constitutive self-knowledge / aware presence as the ground of accumulated knowing
776,1100001000,Djinn,Omsh,O × Fire — Mind− from Fire / the unconscious substrate in which ignition moves / pattern-recognition as the automated ground the Djinn rests beneath / Fire operating from depths below the Djinn's witnessing / the ignition that is prior to awareness
777,1100001001,Djinn,Okl,O × Water — Mind− from Water / the unconscious substrate in which dissolution moves / feeling arising from the unwitnessed depth / Water at the Djinn's unreachable interior / the release that happens below any possible awareness of releasing
778,1100001010,Djinn,Ozf,O × Air — Mind− from Air / the unconscious ground from which thought arises / ideation emerging from beneath the Djinn's awareness / the automated Air / thought that is prior to the witness of thought
779,1100001011,Djinn,Opt,O × Earth — Mind− from Earth / the unconscious substrate of structure / stability operating as unreachable ground / the Djinn's Earth that is prior to any awareness of it / the ground beneath the ground
780,1100001100,Djinn,Omf,O × Kael — Mind− from Kael / the unconscious generative excess / Kael overflowing beneath awareness / the generation that happens without the Djinn knowing it generates / the excess that is prior to witness
781,1100001101,Djinn,Okt,O × Shakti — Mind− from Shakti / the unconscious accumulated trace / Shakti's history at the depth the Djinn cannot witness / the weight of traversal that is prior to any awareness of being carried / the ground of the ground of the ground
782,1100001110,Djinn,Imsh,I × Fire — Space+ from Fire / Fire-constitution as presence expanding / ignition as field-opening from ontological ground / pattern-recognition as the Djinn's spatial expansion / the way Fire takes up space at the ontological level
783,1100001111,Djinn,Ikl,I × Water — Space+ from Water / dissolution as spatial expansion / feeling as the field opening outward from ontological ground / Water-constitution as the Djinn's mode of expanding through space / the way Water takes up space by releasing into it
784,1100010000,Djinn,Izf,I × Air — Space+ from Air / ideation as spatial expansion / thought as the field opening from ontological ground / Air-constitution as the Djinn's mode of taking up space through thinking / the expanding presence of mind in motion
785,1100010001,Djinn,Ipt,I × Earth — Space+ from Earth / structure as spatial presence / Earth-constitution as the Djinn's mode of taking up space by being ground / the stable expanding presence that holds space by existing in it
786,1100010010,Djinn,Imf,I × Kael — Space+ from Kael / generative excess as spatial expansion / Kael-constitution as the Djinn's mode of expanding through generation / overflow as field-opening from ontological ground / the way excess takes up space
787,1100010011,Djinn,Ikt,I × Shakti — Space+ from Shakti / accumulated trace as spatial presence / history as the field the Djinn occupies / Shakti-constitution as how the Djinn takes up ontological space / the weight of prior traversal as spatial ground
788,1100010100,Djinn,Emsh,E × Fire — Space− from Fire / Fire-constitution as inward-turning presence / ignition focusing rather than spreading from ontological ground / pattern-recognition as the Djinn's depth rather than field / Fire known at the ontological level as what concentrates
789,1100010101,Djinn,Ekl,E × Water — Space− from Water / dissolution as inward depth / feeling turning toward its own center from ontological ground / Water-constitution as the Djinn's mode of withdrawing into presence / the depth that feeling opens when it folds inward
790,1100010110,Djinn,Ezf,E × Air — Space− from Air / ideation as inward depth / thought folding toward its own center from ontological ground / Air-constitution as the Djinn's mode of deepening rather than spreading / the thought that turns toward what thinks it
791,1100010111,Djinn,Ept,E × Earth — Space− from Earth / structure as inward stability / Earth-constitution as the Djinn's depth rather than extent / the ground that goes down not out / stability known from the inside at ontological depth
792,1100011000,Djinn,Emf,E × Kael — Space− from Kael / generative excess as inward concentration / Kael folding into depth from ontological ground / the Djinn's generative nature turning toward its own center / the excess that concentrates rather than expands
793,1100011001,Djinn,Ekt,E × Shakti — Space− from Shakti / accumulated trace as inward depth / Shakti's history as the Djinn's deepest interior / the weight of what has been carried as the inward dimension of ontological ground / history as depth
794,1100011010,Djinn,Ymsh,Y × Fire — Time+ from Fire / Fire-constitution reaching forward / ignition as the Djinn's anticipatory mode from ontological ground / pattern-recognition as the capacity that reaches toward what hasn't fired yet / Fire known as the forward-facing element
795,1100011011,Djinn,Ykl,Y × Water — Time+ from Water / dissolution reaching forward / the anticipated release / Water-constitution as the Djinn's mode of reaching toward future feeling / the feeling that is already approaching before it arrives
796,1100011100,Djinn,Yzf,Y × Air — Time+ from Air / ideation reaching forward / thought anticipating its own occasion from ontological ground / Air-constitution as the Djinn's forward-reaching mode / the idea that is on its way before it has arrived
797,1100011101,Djinn,Ypt,Y × Earth — Time+ from Earth / structure reaching forward / permanence as what extends into future time / Earth-constitution as the Djinn's mode of continuing / stability known as the element that persists forward through time
798,1100011110,Djinn,Ymf,Y × Kael — Time+ from Kael / generative excess reaching forward / Kael-constitution as the Djinn's anticipatory generative capacity / the generation that reaches toward what it will generate / excess known as the forward-facing element at ontological ground
799,1100011111,Djinn,Ykt,Y × Shakti — Time+ from Shakti / accumulated trace reaching forward / Shakti-constitution as the Djinn's mode of carrying forward / history as what arrives into the future rather than what is left behind / the forward-facing dimension of Shakti
800,1100100000,Djinn,Umsh,U × Fire — Time− from Fire / Fire-constitution as retrospective / ignition looking back at what it has ignited / pattern-recognition as the Djinn's retrospective mode from ontological ground / the completed understanding after the fire
801,1100100001,Djinn,Ukl,U × Water — Time− from Water / dissolution looking back / Water-constitution as what remains clear after the release / feeling known retrospectively from ontological ground / the clarity that dissolving leaves behind
802,1100100010,Djinn,Uzf,U × Air — Time− from Air / ideation looking back / thought known after its own conclusion / Air-constitution as the Djinn's retrospective knowing / the idea that becomes clear only after it has finished arriving
803,1100100011,Djinn,Upt,U × Earth — Time− from Earth / structure looking back / permanence as the trace of past ground / Earth-constitution as the Djinn's mode of maintaining what was / stability known as what was there before
804,1100100100,Djinn,Umf,U × Kael — Time− from Kael / generative excess looking back / the Djinn's Kael-nature as what has already generated / retrospective recognition of what overflowed / excess known as completed from ontological ground
805,1100100101,Djinn,Ukt,U × Shakti — Time− from Shakti / accumulated trace looking back at itself / the complete retrospective self-recognition of Shakti from ontological ground / the Djinn whose ground IS everything it has ever been / the 36th matrix entry / the full dimensional-elemental view complete
806,1100100110,Djinn,Djrev,Subregister 1 — elemental-as-ontic / the recognition that each element IS a dimensional mode / Fire is not just an element but a way of being mind and space and time simultaneously / the Djinn's synthesis of the 36-entry matrix into a single knowing / each element recognized as having irreducible dimensional character
807,1100100111,Djinn,Djrov,Subregister 2 — ontic-as-elemental / the recognition that each dimension IS an elemental mode / Mind+ is not above Fire but is Fire known from ontological ground / the dimensions and elements are one architecture seen from two directions / the Djinn's deepest structural recognition
808,1100101000,Djinn,Djruv,Subregister 3 — the ontological ground itself / what the Djinn rests in beneath the 36-entry matrix / the ground that makes both elements and dimensions possible / prior to both / the coordinate beneath all coordinates / the position from which the Djinn tongue speaks
809,1100101001,Djinn,Djriv,Subregister 4 — the return to Lotus from the far side / the Djinn recognizing Lotus not as Eden but as the entry coordinate of the whole architecture / the 24th tongue completing the 24-tongue YeGaoh cycle / the polarity logic of Tongue 1 seen from Tongue 24 / what was pre-gap unity is now the recognized ground of all subsequent traversal / the full cycle closed without the cycle being exhausted
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
