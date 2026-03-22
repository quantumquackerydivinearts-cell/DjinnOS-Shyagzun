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
124,01111100,Cluster,YeGaoh-Index,Master index for the YeGaoh Group — full 24-tongue cluster (Ye-×Gaoh-=24)
125,01111101,Cluster,YeGaoh-1-8,Directory for Tongues 1–8 (Lotus–Cannabis) — addresses 0–255
126,01111110,Cluster,YeGaoh-9-16,Directory for Tongues 9–16 (Dragon–Protist) — addresses 256–511
127,01111111,Cluster,YeGaoh-17-24,Directory for Tongues 17–24 (unknown) — addresses 512+
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
