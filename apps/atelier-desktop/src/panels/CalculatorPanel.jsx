/**
 * CalculatorPanel.jsx — Shygazun Semantic Calculator
 * ===================================================
 *
 * A base-12 dimensional calculator grounded in the Shygazun byte table.
 *
 * FONT RENDERING:
 *   When Alexi's glyph SVGs are compiled and the font is built
 *   (run: python tools/build_shygazun_font.py), swap every
 *   <SymbolFallback> usage to <Glyph> by following the TODO comments below.
 *
 *   The Glyph component and toShygazun function are already defined here —
 *   only the @font-face CSS and the swap below are needed.
 *
 * STATE:
 *   Arithmetic state is managed in React, mirroring the canonical
 *   Python logic in shygazun/sanctum/calculator.py.
 *   The Python module is the spec; this is the view layer.
 */

import { useState, useCallback } from "react";

// ---------------------------------------------------------------------------
// Byte table (embedded — matches shygazun_byte_table.py exactly)
// Derived at import time, never hardcoded ranges.
// ---------------------------------------------------------------------------

// prettier-ignore
const BYTE_TABLE = [
  // decimal, tongue, symbol, meaning
  [0,"Lotus","Ty","Earth Initiator / material beginning"],
  [1,"Lotus","Zu","Earth Terminator / empirical closure"],
  [2,"Lotus","Ly","Water Initiator / feeling toward"],
  [3,"Lotus","Mu","Water Terminator / memory from"],
  [4,"Lotus","Fy","Air Initiator / thought toward"],
  [5,"Lotus","Pu","Air Terminator / stasis / stuck"],
  [6,"Lotus","Shy","Fire Initiator / pattern toward"],
  [7,"Lotus","Ku","Fire Terminator / death / end"],
  [8,"Lotus","Ti","Here / near presence"],
  [9,"Lotus","Ta","Active being / presence"],
  [10,"Lotus","Li","New / odd"],
  [11,"Lotus","La","Tense / excited"],
  [12,"Lotus","Fi","Known / context-sensitive"],
  [13,"Lotus","Fa","Complex / old"],
  [14,"Lotus","Shi","Related / clear"],
  [15,"Lotus","Sha","Intellect of spirit"],
  [16,"Lotus","Zo","Absence / passive non-being"],
  [17,"Lotus","Mo","Relaxed / silent"],
  [18,"Lotus","Po","Simple / new"],
  [19,"Lotus","Ko","Experience / intuition"],
  [20,"Lotus","Ze","There / far"],
  [21,"Lotus","Me","Familiar / home"],
  [22,"Lotus","Pe","Unknown / insensitive"],
  [23,"Lotus","Ke","Incoherent / ill"],
  [24,"Rose","Ru","Vector Lowest Red"],
  [25,"Rose","Ot","Vector Orange"],
  [26,"Rose","El","Vector Yellow"],
  [27,"Rose","Ki","Vector Green"],
  [28,"Rose","Fu","Vector Blue"],
  [29,"Rose","Ka","Vector Indigo"],
  [30,"Rose","AE","Vector Highest Violet"],
  [31,"Rose","Gaoh","Number 12 / 0"],
  [32,"Rose","Ao","Number 1"],
  [33,"Rose","Ye","Number 2"],
  [34,"Rose","Ui","Number 3"],
  [35,"Rose","Shu","Number 4"],
  [36,"Rose","Kiel","Number 5"],
  [37,"Rose","Yeshu","Number 6"],
  [38,"Rose","Lao","Number 7"],
  [39,"Rose","Shushy","Number 8"],
  [40,"Rose","Uinshu","Number 9"],
  [41,"Rose","Kokiel","Number 10"],
  [42,"Rose","Aonkiel","Number 11"],
  [43,"Rose","Ha","Absolute Positive"],
  [44,"Rose","Ga","Absolute Negative"],
  [45,"Rose","Wu","Process / Way"],
  [46,"Rose","Na","Neutral / Integration"],
  [47,"Rose","Ung","Piece / Point"],
  [48,"Sakura","Jy","Top"],
  [49,"Sakura","Ji","Starboard"],
  [50,"Sakura","Ja","Front"],
  [51,"Sakura","Jo","Back"],
  [52,"Sakura","Je","Port"],
  [53,"Sakura","Ju","Bottom"],
  [54,"Sakura","Dy","Hence / Heretofore"],
  [55,"Sakura","Di","Traveling / Distancing"],
  [56,"Sakura","Da","Meeting / Conjoined"],
  [57,"Sakura","Do","Parting / Divorced"],
  [58,"Sakura","De","Domesticating / Staying"],
  [59,"Sakura","Du","Whither / Status of"],
  [60,"Sakura","By","When-hence / Eventual"],
  [61,"Sakura","Bi","Crowned / Owning"],
  [62,"Sakura","Ba","Plain / Explicit"],
  [63,"Sakura","Bo","Hidden / Occulted"],
  [64,"Sakura","Be","Common / Outer / Wild"],
  [65,"Sakura","Bu","Since / Relational"],
  [66,"Sakura","Va","Order / Structure / Life"],
  [67,"Sakura","Vo","Chaos / Boundary-breakage / Mutation"],
  [68,"Sakura","Ve","Pieces / Not-wherever / Where"],
  [69,"Sakura","Vu","Death-moment / Never / Now"],
  [70,"Sakura","Vi","Body / Wherever / What"],
  [71,"Sakura","Vy","Lifespan / Whenever / How"],
  [72,"Daisy","Lo","Segments / Identity"],
  [73,"Daisy","Yei","Component / Integrator"],
  [74,"Daisy","Ol","Deadzone / Relative Void"],
  [75,"Daisy","X","Joint / Interlock"],
  [76,"Daisy","Yx","Fulcrum / Crux"],
  [77,"Daisy","Go","Plug / Blocker"],
  [78,"Daisy","Foa","Degree / Space"],
  [79,"Daisy","Oy","Depths / Layers"],
  [80,"Daisy","W","Freefall / Socket Space"],
  [81,"Daisy","Th","Cuff / Indentation"],
  [82,"Daisy","Kael","Cluster / Fruit / Flower"],
  [83,"Daisy","Ro","Ion-channel / Gate / Receptor"],
  [84,"Daisy","Gl","Membrane / Muscle"],
  [85,"Daisy","To","Scaffold / Framework"],
  [86,"Daisy","Ma","Web / Interchange"],
  [87,"Daisy","Ne","Network / System"],
  [88,"Daisy","Ym","Radial Space"],
  [89,"Daisy","Nz","Switch / Circuit Actuator"],
  [90,"Daisy","Sho","Valve / Fluid Actuator"],
  [91,"Daisy","Hi","Lever / Radial Actuator"],
  [92,"Daisy","Mh","Bond"],
  [93,"Daisy","Zhi","Eye / Vortex"],
  [94,"Daisy","Vr","Rotor / Tensor"],
  [95,"Daisy","St","Surface"],
  [96,"Daisy","Fn","Passage / Pathway"],
  [97,"Daisy","N","Seed / Sheet / Fiber"],
  [98,"AppleBlossom","A","Mind +"],
  [99,"AppleBlossom","O","Mind -"],
  [100,"AppleBlossom","I","Space +"],
  [101,"AppleBlossom","E","Space -"],
  [102,"AppleBlossom","Y","Time +"],
  [103,"AppleBlossom","U","Time -"],
  [104,"AppleBlossom","Shak","Fire"],
  [105,"AppleBlossom","Puf","Air"],
  [106,"AppleBlossom","Mel","Water"],
  [107,"AppleBlossom","Zot","Earth"],
  [108,"AppleBlossom","Zhuk","Plasma (Fire,Fire)"],
  [109,"AppleBlossom","Kypa","Sulphur (Fire,Air)"],
  [110,"AppleBlossom","Alky","Alkahest / Alcohol (Fire,Water)"],
  [111,"AppleBlossom","Kazho","Magma / Lava (Fire,Earth)"],
  [112,"AppleBlossom","Puky","Smoke (Air,Fire)"],
  [113,"AppleBlossom","Pyfu","Gas (Air,Air)"],
  [114,"AppleBlossom","Mipa","Carbonation / Trapped Gas (Air,Water)"],
  [115,"AppleBlossom","Zitef","Mercury (Air,Earth)"],
  [116,"AppleBlossom","Shem","Steam (Water,Fire)"],
  [117,"AppleBlossom","Lefu","Vapor (Water,Air)"],
  [118,"AppleBlossom","Milo","Mixed fluids / Mixtures (Water,Water)"],
  [119,"AppleBlossom","Myza","Erosion (Water,Earth)"],
  [120,"AppleBlossom","Zashu","Radiation / Radioactive stones (Earth,Fire)"],
  [121,"AppleBlossom","Fozt","Dust (Earth,Air)"],
  [122,"AppleBlossom","Zosh","Sediment / Stone in Liquid (Earth,Water)"],
  [123,"AppleBlossom","Kael","Quintessence / Chaos / Life"],
  // 124–127 reserved — intentionally absent
  [128,"Aster","Ry","Chiral Lowest Red (Left)"],
  [129,"Aster","Ra","Chiral Lowest Red (Right)"],
  [130,"Aster","Oty","Chiral Orange (Left)"],
  [131,"Aster","Ota","Chiral Orange (Right)"],
  [132,"Aster","Ely","Chiral Yellow (Left)"],
  [133,"Aster","Ela","Chiral Yellow (Right)"],
  [134,"Aster","Kiy","Chiral Green (Left)"],
  [135,"Aster","Kia","Chiral Green (Right)"],
  [136,"Aster","Fuy","Chiral Blue (Left)"],
  [137,"Aster","Fua","Chiral Blue (Right)"],
  [138,"Aster","Kay","Chiral Indigo (Left)"],
  [139,"Aster","Kaa","Chiral Indigo (Right)"],
  [140,"Aster","AEy","Chiral Highest Violet (Left)"],
  [141,"Aster","AEa","Chiral Highest Violet (Right)"],
  [142,"Aster","Si","Linear time"],
  [143,"Aster","Su","Loop time"],
  [144,"Aster","Os","Exponential time"],
  [145,"Aster","Se","Logarithmic time"],
  [146,"Aster","Sy","Fold time"],
  [147,"Aster","As","Frozen time"],
  [148,"Aster","Mavo","Banner / Flag / Metadata"],
  [149,"Aster","Dyf","Jitter / Nondeterminism"],
  [150,"Aster","Vyl","Run-space op: assign"],
  [151,"Aster","Mek","Call / Emit event"],
  [152,"Aster","Soa","Cup / File / Persistent Object"],
  [153,"Aster","Ylo","Run-space op: loop"],
  [154,"Aster","Yl","Run-space"],
  [155,"Aster","Goel","Run-space op: unbind"],
  [156,"Grapevine","Sa","Feast table / Root volume"],
  [157,"Grapevine","Sao","Cup / File / Persistent object"],
  [158,"Grapevine","Syr","Wine / Volatile buffer"],
  [159,"Grapevine","Seth","Platter / Directory / Bundle"],
  [160,"Grapevine","Samos","Banquet hall / Database cluster"],
  [161,"Grapevine","Myk","Messenger / Packet"],
  [162,"Grapevine","Myka","Herald / Packet with address"],
  [163,"Grapevine","Myke","Courier / Signed packet"],
  [164,"Grapevine","Mykao","Ambassador / Credentialed packet"],
  [165,"Grapevine","Kyl","Wineskin / Encrypted container"],
  [166,"Grapevine","Kyls","Sealed wineskin / Encrypted at rest"],
  [167,"Grapevine","Kylm","Locked wineskin / Encrypted in transit"],
  [168,"Grapevine","Mekha","Herald / Gateway"],
  [169,"Grapevine","Myrun","Sacred march / Stream"],
  [170,"Grapevine","Nosh","Feast / Broadcast"],
  [171,"Grapevine","Noshka","Grand feast / Multicast"],
  [172,"Grapevine","Tav","Table setting / Schema"],
  [173,"Grapevine","Tavro","Schema with relations"],
  [174,"Grapevine","Syn","Vintage / Version"],
  [175,"Grapevine","Synth","Archive vintage / Immutable version"],
  [176,"Grapevine","Koph","Goblet / View"],
  [177,"Grapevine","Kophi","Crystal goblet / Materialized view"],
  [178,"Grapevine","Loch","Cellar / Cold storage"],
  [179,"Grapevine","Lochm","Deep cellar / Archival storage"],
  [180,"Grapevine","Rosh","Toast / Acknowledgment"],
  [181,"Grapevine","Kysha","Consensus choir"],
  [182,"Grapevine","Kyshe","Partial quorum"],
  [183,"Grapevine","Kysael","Authoritative commit"],
  [184,"Cannabis","Tyk","Conscious material action / awareness of Earth"],
  [185,"Cannabis","Zuk","Conscious material closure / awareness of ending"],
  [186,"Cannabis","Lyk","Conscious feeling / awareness of water"],
  [187,"Cannabis","Muk","Conscious memory / awareness of past feeling"],
  [188,"Cannabis","Fyk","Conscious thought / awareness of air"],
  [189,"Cannabis","Puk","Conscious stasis / awareness of stuck thought"],
  [190,"Cannabis","Shyk","Conscious pattern / awareness of fire"],
  [191,"Cannabis","Kuk","Conscious ending / awareness of death-pattern"],
  [192,"Cannabis","Tik","Conscious presence / awareness of here"],
  [193,"Cannabis","Tak","Conscious being / awareness of active presence"],
  [194,"Cannabis","Lik","Conscious newness / awareness of odd"],
  [195,"Cannabis","Lak","Conscious tension / awareness of excitement"],
  [196,"Cannabis","Fik","Conscious knowing / context-aware awareness"],
  [197,"Cannabis","Fak","Conscious complexity / awareness of age"],
  [198,"Cannabis","Shik","Conscious relation / awareness of clarity"],
  [199,"Cannabis","Shak","Conscious intellect / awareness of spirit-mind"],
  [200,"Cannabis","Zok","Conscious absence / awareness of non-being"],
  [201,"Cannabis","Mok","Conscious relaxation / awareness of silence"],
  [202,"Cannabis","Pok","Conscious simplicity / awareness of newness"],
  [203,"Cannabis","Kok","Conscious experience / awareness of intuition"],
  [204,"Cannabis","Zek","Conscious distance / awareness of there"],
  [205,"Cannabis","Mek","Conscious familiarity / awareness of home"],
  [206,"Cannabis","Pek","Conscious unknown / awareness of insensitivity"],
  [207,"Cannabis","Kek","Conscious incoherence / awareness of ill"],
  [208,"Cannabis","Tys","Spatial material action / distribution of Earth"],
  [209,"Cannabis","Zus","Spatial material closure / distribution of ending"],
  [210,"Cannabis","Lys","Spatial feeling / distribution of water"],
  [211,"Cannabis","Mus","Spatial memory / distribution of past feeling"],
  [212,"Cannabis","Fys","Spatial thought / distribution of air"],
  [213,"Cannabis","Suy","Conscious temporal action / the act of mind deliberately moving through or shaping time"],
];

// ---------------------------------------------------------------------------
// Derived structures (built once at module load)
// ---------------------------------------------------------------------------

const TONGUE_ORDER = [];
const TONGUE_MAP = {};  // tongue → [{decimal, symbol, meaning}]

for (const [decimal, tongue, symbol, meaning] of BYTE_TABLE) {
  if (!TONGUE_MAP[tongue]) {
    TONGUE_MAP[tongue] = [];
    TONGUE_ORDER.push(tongue);
  }
  TONGUE_MAP[tongue].push({ decimal, tongue, symbol, meaning });
}

// Rose spine: entries whose meaning starts with "Number"
const SPINE_ROWS = TONGUE_MAP["Rose"].filter(r => r.meaning.startsWith("Number"));

function spineValue(row) {
  if (row.meaning.includes("12 / 0") || row.meaning.includes("12/0")) return 0;
  for (const tok of row.meaning.split(/\s+/)) {
    const n = parseInt(tok, 10);
    if (!isNaN(n)) return n;
  }
  return 0;
}

const SPINE_BY_VALUE = {};
for (const r of SPINE_ROWS) {
  SPINE_BY_VALUE[spineValue(r)] = r;
}
const SPINE_BY_DECIMAL = {};
for (const r of SPINE_ROWS) {
  SPINE_BY_DECIMAL[r.decimal] = r;
}
const SPINE_SORTED = [...SPINE_ROWS].sort((a, b) => spineValue(a) - spineValue(b));

const PRIMORDIAL_SYMBOLS = new Set(["Ha", "Ga", "Wu", "Na", "Ung"]);
const PRIMORDIAL_ROWS = TONGUE_MAP["Rose"].filter(r => PRIMORDIAL_SYMBOLS.has(r.symbol));
const SPECTRAL_ROWS = TONGUE_MAP["Rose"].filter(
  r => !PRIMORDIAL_SYMBOLS.has(r.symbol) && r.symbol !== "Gaoh" && !SPINE_BY_DECIMAL[r.decimal]
);

// Gaoh fold is a named operation using Gaoh's symbol
const OPERATIONS = ["Ha", "Ga", "Wu", "Na", "Ung", "Gaoh"];
const OP_DISPLAY = { Ha: "+", Ga: "−", Wu: "×", Na: "÷", Ung: "⟲", Gaoh: "◉" };

// ---------------------------------------------------------------------------
// Codepoint mapping (font — when compiled)
// TODO: swap SymbolFallback → Glyph everywhere once font is built
// ---------------------------------------------------------------------------

/** Maps decimal address → Unicode PUA character U+E000+decimal */
const toShygazun = (decimal) => String.fromCodePoint(0xE000 + decimal);

/**
 * Glyph component — renders a single Shygazun character via the compiled font.
 * Requires the @font-face to be loaded (see index.css TODO below).
 *
 * TODO (font swap): uncomment the @font-face block in index.css, then replace
 * every <SymbolFallback> with <Glyph> throughout this file.
 */
const Glyph = ({ decimal, size = 20, style }) => (
  <span style={{ fontFamily: "Shygazun", fontSize: size, lineHeight: 1, ...style }}>
    {toShygazun(decimal)}
  </span>
);

/**
 * Fallback component — renders the Latin symbol string from the byte table.
 * Drop-in replacement for <Glyph>. Same props interface.
 *
 * TODO (font swap): replace <SymbolFallback> with <Glyph> once font is built.
 */
const SymbolFallback = ({ decimal, size = 14, style }) => {
  const row = BYTE_TABLE.find(r => r[0] === decimal);
  const sym = row ? row[2] : `?${decimal}`;
  return (
    <span style={{ fontFamily: "monospace", fontSize: size, fontWeight: 600, ...style }}>
      {sym}
    </span>
  );
};

// ---------------------------------------------------------------------------
// Möbius coil distance (mirrors Layers.py coil_distance)
// Kept here so the JS view layer is self-contained.
// The Python module is canonical — this mirrors it exactly.
// ---------------------------------------------------------------------------

function coilDistance(a, b) {
  // a and b are layer indices 1–12
  const la = ((a - 1 + 12) % 12) + 1;
  const lb = ((b - 1 + 12) % 12) + 1;
  const direct = Math.abs(la - lb);
  const wrapped = 12 - direct;
  return Math.min(direct, wrapped);
}

// ---------------------------------------------------------------------------
// Pure state functions (mirror shygazun/sanctum/calculator.py)
// ---------------------------------------------------------------------------

function makeCalculator() {
  const gaohRow = SPINE_BY_VALUE[0];
  return {
    current: { spine: { ...gaohRow, value: 0 }, dims: [] },
    pendingOp: null,
    pendingValue: null,
    expr: gaohRow.symbol,
    vocab: [],  // [{name, compound}]
  };
}

function enterValue(state, decimal) {
  const row = SPINE_BY_DECIMAL[decimal];
  if (!row) return state;
  const val = spineValue(row);
  const spine = { ...row, value: val };
  const expr = state.pendingOp
    ? state.expr + row.symbol
    : row.symbol;
  return { ...state, current: { ...state.current, spine }, expr };
}

function toggleDim(state, decimal) {
  const row = BYTE_TABLE.find(r => r[0] === decimal);
  if (!row) return state;
  const op = { decimal: row[0], tongue: row[1], symbol: row[2], meaning: row[3] };
  const dims = state.current.dims;
  const exists = dims.some(d => d.decimal === decimal);
  const newDims = exists
    ? dims.filter(d => d.decimal !== decimal)
    : [...dims, op];
  return { ...state, current: { ...state.current, dims: newDims } };
}

function setOp(state, opSymbol) {
  if (!OPERATIONS.includes(opSymbol)) return state;
  const expr = state.expr + " " + opSymbol + " ";
  return {
    ...state,
    pendingOp: opSymbol,
    pendingValue: state.current.spine,
    expr,
  };
}

function executeOp(state) {
  if (!state.pendingOp || !state.pendingValue) return state;
  const a = state.pendingValue.value;
  const b = state.current.spine.value;
  const op = state.pendingOp;
  let result;

  if (op === "Ha")   result = (a + b) % 12;
  else if (op === "Ga")   result = ((a - b) % 12 + 12) % 12;
  else if (op === "Wu")   result = (a * b) % 12;
  else if (op === "Na")   result = b !== 0 ? Math.floor(a / b) % 12 : 0;
  else if (op === "Ung") {
    const la = a !== 0 ? a : 12;
    const lb = b !== 0 ? b : 12;
    result = coilDistance(la, lb);
  }
  else if (op === "Gaoh") result = (a + b) % 12;
  else result = b;

  const resultRow = SPINE_BY_VALUE[result];
  const resultSpine = { ...resultRow, value: result };
  const expr = state.expr + state.current.spine.symbol + " = " + resultRow.symbol;
  return {
    ...state,
    current: { ...state.current, spine: resultSpine },
    pendingOp: null,
    pendingValue: null,
    expr,
  };
}

function saveToVocab(state, name) {
  const filtered = state.vocab.filter(v => v.name !== name);
  return {
    ...state,
    vocab: [...filtered, { name, compound: state.current }],
  };
}

function recallVocab(state, name) {
  const entry = state.vocab.find(v => v.name === name);
  if (!entry) return state;
  return {
    ...state,
    current: entry.compound,
    pendingOp: null,
    pendingValue: null,
    expr: compoundString(entry.compound),
  };
}

// ---------------------------------------------------------------------------
// Dimensional projection (mirrors calculator.py ProjectedAxis.project)
// ---------------------------------------------------------------------------

function projectAxis(op, value) {
  const tongueRows = TONGUE_MAP[op.tongue] || [];
  if (!tongueRows.length) return { op, projectedDecimal: op.decimal, projectedSymbol: op.symbol, projectedMeaning: op.meaning };
  const idx = value % tongueRows.length;
  const entry = tongueRows[idx];
  return { op, projectedDecimal: entry.decimal, projectedSymbol: entry.symbol, projectedMeaning: entry.meaning };
}

function compoundString(compound) {
  return compound.spine.symbol + compound.dims.map(d => d.symbol).join("");
}

function compoundProjections(compound) {
  return compound.dims.map(op => projectAxis(op, compound.spine.value));
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const S = {
  root: {
    display: "grid",
    gridTemplateRows: "auto 1fr",
    gap: 0,
    height: "100%",
  },
  panel: {
    border: "1px solid var(--line)",
    borderRadius: 12,
    background: "#fffdf8",
    padding: 16,
    marginBottom: 14,
  },
  row: {
    display: "flex",
    flexWrap: "wrap",
    gap: 8,
    alignItems: "center",
  },
  display: {
    border: "1px solid var(--line)",
    borderRadius: 10,
    background: "#fff",
    padding: "12px 16px",
    marginBottom: 12,
    fontFamily: "monospace",
  },
  bigValue: {
    fontSize: 42,
    fontWeight: 700,
    letterSpacing: "-0.02em",
    color: "var(--accent)",
    lineHeight: 1,
  },
  exprLine: {
    fontSize: 12,
    color: "#8a7e6e",
    marginTop: 4,
    whiteSpace: "pre-wrap",
    wordBreak: "break-all",
  },
  chip: (active) => ({
    display: "inline-flex",
    alignItems: "center",
    gap: 4,
    padding: "3px 8px",
    borderRadius: 999,
    border: `1px solid ${active ? "var(--accent)" : "var(--line)"}`,
    background: active ? "var(--accent-soft)" : "#fff",
    color: active ? "#173a34" : "#5e564b",
    fontSize: 11,
    fontWeight: active ? 700 : 400,
    cursor: "pointer",
    userSelect: "none",
  }),
  opBtn: (active) => ({
    padding: "6px 14px",
    borderRadius: 8,
    border: `1px solid ${active ? "var(--accent)" : "var(--line)"}`,
    background: active ? "var(--accent-soft)" : "#fff9ef",
    color: active ? "#173a34" : "#2a261f",
    fontWeight: 700,
    cursor: "pointer",
    fontSize: 16,
    minWidth: 42,
  }),
  spineBtn: (active) => ({
    padding: "6px 10px",
    borderRadius: 8,
    border: `1px solid ${active ? "var(--accent)" : "var(--line)"}`,
    background: active ? "var(--accent-soft)" : "#fff9ef",
    color: active ? "#173a34" : "#2a261f",
    fontWeight: 600,
    cursor: "pointer",
    fontSize: 13,
    minWidth: 52,
    textAlign: "center",
  }),
  dimBtn: (active) => ({
    padding: "4px 8px",
    borderRadius: 6,
    border: `1px solid ${active ? "#8bb39d" : "var(--line)"}`,
    background: active ? "#edf8f0" : "#fff",
    color: active ? "#23583a" : "#5e564b",
    fontSize: 11,
    cursor: "pointer",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 1,
  }),
  tabBar: {
    display: "flex",
    flexWrap: "wrap",
    gap: 4,
    marginBottom: 8,
  },
  tab: (active) => ({
    padding: "4px 10px",
    borderRadius: 6,
    border: `1px solid ${active ? "var(--accent)" : "var(--line)"}`,
    background: active ? "var(--accent-soft)" : "#fff",
    color: active ? "#173a34" : "#5e564b",
    fontSize: 11,
    fontWeight: active ? 700 : 400,
    cursor: "pointer",
  }),
  sectionLabel: {
    fontSize: 10,
    fontWeight: 700,
    letterSpacing: "0.08em",
    color: "#8a7e6e",
    textTransform: "uppercase",
    margin: "8px 0 4px",
  },
  projBox: {
    border: "1px solid var(--line)",
    borderRadius: 8,
    padding: "8px 12px",
    background: "#fafaf7",
    fontSize: 12,
  },
  projLabel: {
    fontSize: 10,
    color: "#8a7e6e",
    fontWeight: 700,
    letterSpacing: "0.06em",
    textTransform: "uppercase",
  },
  vocabEntry: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "6px 10px",
    borderRadius: 8,
    border: "1px solid var(--line)",
    background: "#fff",
    fontSize: 12,
    cursor: "pointer",
  },
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function CalculatorPanel() {
  const [calc, setCalc] = useState(() => makeCalculator());
  const [kbTab, setKbTab] = useState("Rose");
  const [vocabName, setVocabName] = useState("");

  const dispatch = useCallback((fn, ...args) => {
    setCalc(prev => fn(prev, ...args));
  }, []);

  const { current, pendingOp, expr, vocab } = calc;
  const { spine, dims } = current;
  const projections = compoundProjections(current);
  const activeDimDecimals = new Set(dims.map(d => d.decimal));

  // ---- Display ----
  const displaySymbol = spine.symbol;
  const displayValue  = spine.value;
  const displayBase12 = displayValue.toString(12).toUpperCase();
  const compound      = compoundString(current);

  return (
    <section className="panel">
      <h2>Shygazun Calculator</h2>
      <p style={{ color: "#5e564b", fontSize: 13, marginTop: -8, marginBottom: 14 }}>
        Base-12 semantic arithmetic engine. Rose spine values · Dimensional operators · Möbius-wrapped results.
      </p>

      {/* === DISPLAY === */}
      <div style={S.display}>
        <div style={S.row}>
          {/* TODO (font swap): replace SymbolFallback with Glyph here */}
          <SymbolFallback decimal={spine.decimal} size={36} style={{ color: "var(--accent)", marginRight: 8 }} />
          <div>
            <div style={S.bigValue}>{displayBase12}<sub style={{ fontSize: 18, opacity: 0.5 }}>₁₂</sub></div>
            <div style={{ fontSize: 11, color: "#8a7e6e" }}>{displaySymbol} — {spine.meaning}</div>
          </div>
        </div>

        {/* Active dim chips */}
        {dims.length > 0 && (
          <div style={{ ...S.row, marginTop: 8 }}>
            {dims.map(op => (
              <span key={op.decimal} style={S.chip(true)} onClick={() => dispatch(toggleDim, op.decimal)}>
                {/* TODO (font swap): replace span below with <Glyph decimal={op.decimal} size={12} /> */}
                <span style={{ fontFamily: "monospace", fontSize: 11 }}>{op.symbol}</span>
                {op.meaning.slice(0, 28)}{op.meaning.length > 28 ? "…" : ""}
                <span style={{ opacity: 0.5, marginLeft: 2 }}>×</span>
              </span>
            ))}
          </div>
        )}

        {/* Compound address */}
        {compound.length > spine.symbol.length && (
          <div style={{ marginTop: 8, fontSize: 13, fontFamily: "monospace", color: "#4a7a68" }}>
            {compound}
          </div>
        )}

        {/* Expression */}
        <div style={S.exprLine}>{expr || "—"}</div>
        {pendingOp && (
          <div style={{ fontSize: 11, color: "#9a7e28", marginTop: 4 }}>
            waiting: {calc.pendingValue?.symbol} {OP_DISPLAY[pendingOp]} …
          </div>
        )}
      </div>

      {/* === ARITHMETIC CONTROLS === */}
      <div style={S.panel}>
        <div style={S.sectionLabel}>Arithmetic</div>
        <div style={S.row}>
          {OPERATIONS.map(op => {
            const row = TONGUE_MAP["Rose"].find(r => r.symbol === op) ||
                        { decimal: 31, symbol: "Gaoh" };
            return (
              <button key={op} style={S.opBtn(pendingOp === op)} onClick={() => dispatch(setOp, op)}>
                {/* TODO (font swap): replace span below with <Glyph decimal={row.decimal} size={16} /> */}
                <span style={{ fontFamily: "monospace", fontSize: 12, display: "block" }}>{op}</span>
                <span style={{ fontSize: 10, opacity: 0.6 }}>{OP_DISPLAY[op]}</span>
              </button>
            );
          })}
          <button
            style={{ ...S.opBtn(false), background: "#eff8f6", borderColor: "#8bb39d", color: "#173a34" }}
            onClick={() => dispatch(executeOp)}
          >=</button>
          <button
            style={{ ...S.opBtn(false), background: "#fff0f0", borderColor: "#cb8e8e", color: "#7a2323" }}
            onClick={() => setCalc(makeCalculator())}
          >C</button>
        </div>
      </div>

      {/* === PROJECTIONS === */}
      {projections.length > 0 && (
        <div style={S.panel}>
          <div style={S.sectionLabel}>Dimensional Projections</div>
          <div style={{ display: "grid", gap: 8 }}>
            {projections.map((proj, i) => (
              <div key={i} style={S.projBox}>
                <div style={S.projLabel}>
                  {/* TODO (font swap): replace symbol spans with <Glyph> */}
                  <span style={{ fontFamily: "monospace" }}>{proj.op.symbol}</span>
                  {" "}({proj.op.tongue}) — {proj.op.meaning}
                </div>
                <div style={{ marginTop: 4, fontSize: 13 }}>
                  <span style={{ fontFamily: "monospace", fontWeight: 700, color: "var(--accent)" }}>
                    {proj.projectedSymbol}
                  </span>
                  {" — "}{proj.projectedMeaning}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* === KEYBOARD === */}
      <div style={S.panel}>
        <div style={S.sectionLabel}>Keyboard</div>
        <div style={S.tabBar}>
          {TONGUE_ORDER.map(t => (
            <button key={t} style={S.tab(kbTab === t)} onClick={() => setKbTab(t)}>{t}</button>
          ))}
        </div>

        {kbTab === "Rose" ? (
          <>
            <div style={S.sectionLabel}>Spine (values)</div>
            <div style={S.row}>
              {SPINE_SORTED.map(r => (
                <button
                  key={r.decimal}
                  style={S.spineBtn(spine.decimal === r.decimal)}
                  onClick={() => dispatch(enterValue, r.decimal)}
                  title={r.meaning}
                >
                  {/* TODO (font swap): replace span below with <Glyph decimal={r.decimal} size={14} /> */}
                  <span style={{ fontFamily: "monospace", fontSize: 12, display: "block" }}>{r.symbol}</span>
                  <span style={{ fontSize: 9, opacity: 0.6 }}>{spineValue(r)}</span>
                </button>
              ))}
            </div>

            <div style={S.sectionLabel}>Spectral (dim operators)</div>
            <div style={S.row}>
              {SPECTRAL_ROWS.map(r => (
                <button
                  key={r.decimal}
                  style={S.dimBtn(activeDimDecimals.has(r.decimal))}
                  onClick={() => dispatch(toggleDim, r.decimal)}
                  title={r.meaning}
                >
                  {/* TODO (font swap): replace span below with <Glyph decimal={r.decimal} size={13} /> */}
                  <span style={{ fontFamily: "monospace", fontSize: 11 }}>{r.symbol}</span>
                  <span style={{ fontSize: 9, opacity: 0.7, maxWidth: 60, textAlign: "center" }}>
                    {r.meaning.slice(0, 14)}
                  </span>
                </button>
              ))}
            </div>

            <div style={S.sectionLabel}>Primordials (dim operators)</div>
            <div style={S.row}>
              {PRIMORDIAL_ROWS.map(r => (
                <button
                  key={r.decimal}
                  style={S.dimBtn(activeDimDecimals.has(r.decimal))}
                  onClick={() => dispatch(toggleDim, r.decimal)}
                  title={r.meaning}
                >
                  {/* TODO (font swap): replace span below with <Glyph decimal={r.decimal} size={13} /> */}
                  <span style={{ fontFamily: "monospace", fontSize: 11 }}>{r.symbol}</span>
                  <span style={{ fontSize: 9, opacity: 0.7 }}>{r.meaning.slice(0, 14)}</span>
                </button>
              ))}
            </div>
          </>
        ) : (
          <>
            <div style={S.row}>
              {(TONGUE_MAP[kbTab] || []).map(r => (
                <button
                  key={r.decimal}
                  style={S.dimBtn(activeDimDecimals.has(r.decimal))}
                  onClick={() => dispatch(toggleDim, r.decimal)}
                  title={r.meaning}
                >
                  {/* TODO (font swap): replace span below with <Glyph decimal={r.decimal} size={13} /> */}
                  <span style={{ fontFamily: "monospace", fontSize: 11 }}>{r.symbol}</span>
                  <span style={{ fontSize: 9, opacity: 0.7, maxWidth: 64, textAlign: "center" }}>
                    {r.meaning.slice(0, 16)}
                  </span>
                </button>
              ))}
            </div>
          </>
        )}
      </div>

      {/* === VOCABULARY REGISTER === */}
      <div style={S.panel}>
        <div style={S.sectionLabel}>Vocabulary Register</div>
        <div style={S.row}>
          <input
            value={vocabName}
            onChange={e => setVocabName(e.target.value)}
            placeholder="name this compound"
            style={{
              flex: 1,
              padding: "6px 10px",
              border: "1px solid var(--line)",
              borderRadius: 8,
              fontSize: 13,
              background: "#fff",
            }}
            onKeyDown={e => {
              if (e.key === "Enter" && vocabName.trim()) {
                dispatch(saveToVocab, vocabName.trim());
                setVocabName("");
              }
            }}
          />
          <button
            className="action"
            onClick={() => {
              if (vocabName.trim()) {
                dispatch(saveToVocab, vocabName.trim());
                setVocabName("");
              }
            }}
          >Save</button>
        </div>

        {vocab.length > 0 && (
          <div style={{ marginTop: 10, display: "grid", gap: 6 }}>
            {vocab.map(({ name, compound: c }) => (
              <div
                key={name}
                style={S.vocabEntry}
                onClick={() => dispatch(recallVocab, name)}
                title="Click to recall"
              >
                {/* TODO (font swap): replace monospace span with glyph string */}
                <span style={{ fontFamily: "monospace", fontWeight: 700, color: "var(--accent)" }}>
                  {compoundString(c)}
                </span>
                <span style={{ color: "#8a7e6e" }}>—</span>
                <span style={{ fontWeight: 600 }}>{name}</span>
                <span style={{ marginLeft: "auto", fontSize: 10, color: "#8a7e6e" }}>
                  {c.spine.symbol}·{c.spine.value}
                  {c.dims.length > 0 ? ` [${c.dims.map(d => d.symbol).join(" ")}]` : ""}
                </span>
              </div>
            ))}
          </div>
        )}
        {vocab.length === 0 && (
          <p style={{ fontSize: 12, color: "#8a7e6e", margin: "8px 0 0" }}>
            No saved compounds. Enter a name and press Save (or Enter).
          </p>
        )}
      </div>

    </section>
  );
}
