import React, { useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:9000";

const NAV_ITEMS = [
  "Foyer",
  "Workshop",
  "Temple and Gardens",
  "Guild Hall",
  "Messages",
  "Studio Hub",
  "Lesson Creation",
  "Module Creation",
  "Learning Hall",
  "CRM",
  "Booking System",
  "Leads",
  "Clients",
  "Quotes",
  "Orders",
  "Commission Hall",
  "Suppliers",
  "Inventory",
  "Renderer Lab",
  "Privacy"
];

function capabilitiesForRole(role) {
  if (role === "steward") {
    return [
      "kernel.place",
      "kernel.observe",
      "kernel.timeline",
      "kernel.frontiers",
      "kernel.edges",
      "kernel.attest",
      "crm.contacts.read",
      "crm.contacts.write",
      "booking.read",
      "booking.write",
      "lesson.read",
      "lesson.write",
      "module.read",
      "module.write",
      "lead.read",
      "lead.write",
      "client.read",
      "client.write",
      "quote.read",
      "quote.write",
      "order.read",
      "order.write",
      "supplier.read",
      "supplier.write",
      "inventory.read",
      "inventory.write"
    ];
  }
  if (role === "senior_artisan") {
    return [
      "kernel.observe",
      "kernel.timeline",
      "kernel.frontiers",
      "kernel.edges",
      "kernel.attest",
      "crm.contacts.read",
      "crm.contacts.write",
      "booking.read",
      "booking.write",
      "lesson.read",
      "lesson.write",
      "module.read",
      "module.write",
      "lead.read",
      "lead.write",
      "client.read",
      "client.write",
      "quote.read",
      "quote.write",
      "order.read",
      "order.write",
      "supplier.read",
      "supplier.write",
      "inventory.read",
      "inventory.write"
    ];
  }
  if (role === "artisan") {
    return [
      "kernel.observe",
      "kernel.timeline",
      "kernel.frontiers",
      "kernel.edges",
      "crm.contacts.read",
      "crm.contacts.write",
      "booking.read",
      "lesson.read",
      "lesson.write",
      "module.read",
      "module.write",
      "lead.read",
      "lead.write",
      "client.read",
      "client.write",
      "quote.read",
      "quote.write",
      "order.read",
      "supplier.read",
      "supplier.write",
      "inventory.read",
      "inventory.write"
    ];
  }
  return [
    "kernel.observe",
    "kernel.timeline",
    "kernel.frontiers",
    "crm.contacts.read",
    "booking.read",
    "lesson.read",
    "module.read",
    "lead.read",
    "client.read",
    "quote.read",
    "order.read",
    "supplier.read",
    "inventory.read"
  ];
}

function buildHeaders(role, capsCsv, adminGateToken) {
  const headers = {
    "Content-Type": "application/json",
    "X-Atelier-Actor": "desktop-user",
    "X-Atelier-Capabilities": capsCsv,
    "X-Artisan-Id": "artisan-desktop",
    "X-Artisan-Role": role,
    "X-Workshop-Id": "workshop-primary",
    "X-Workshop-Scopes": "scene:*,workspace:*"
  };
  if (adminGateToken) {
    headers["X-Admin-Gate-Token"] = adminGateToken;
  }
  return headers;
}

function parseSafeJson(text) {
  if (!text) {
    return {};
  }
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text };
  }
}

function downloadJson(filename, data) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function GraphBars({ title, items }) {
  const max = items.reduce((m, it) => (it.value > m ? it.value : m), 0);
  return (
    <section className="panel">
      <h2>{title}</h2>
      <div className="graph">
        {items.map((item) => {
          const pct = max === 0 ? 0 : Math.round((item.value / max) * 100);
          return (
            <div className="graph-row" key={item.label}>
              <span>{item.label}</span>
              <div className="graph-track">
                <div className="graph-fill" style={{ width: `${pct}%` }} />
              </div>
              <strong>{item.value}</strong>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function monthLabel(year, month) {
  return new Date(year, month, 1).toLocaleDateString(undefined, { month: "long", year: "numeric" });
}

function buildCalendarDays(year, month) {
  const first = new Date(year, month, 1);
  const startWeekday = first.getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells = [];
  for (let i = 0; i < startWeekday; i += 1) {
    cells.push({ key: `pad-${i}`, day: null, iso: null });
  }
  for (let day = 1; day <= daysInMonth; day += 1) {
    const iso = new Date(year, month, day).toISOString().slice(0, 10);
    cells.push({ key: iso, day, iso });
  }
  return cells;
}

function compareIso(a, b) {
  if (a < b) {
    return -1;
  }
  if (a > b) {
    return 1;
  }
  return 0;
}

function makeStudioFileId() {
  return `studio_${Date.now()}_${Math.floor(Math.random() * 10000)}`;
}

function rangesOverlap(startA, endA, startB, endB) {
  return startA < endB && startB < endA;
}

function renderInlineMarkdown(text) {
  const parts = [];
  const pattern = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  let last = 0;
  let idx = 0;
  let match = pattern.exec(text);
  while (match) {
    if (match.index > last) {
      parts.push(<span key={`plain-${idx}`}>{text.slice(last, match.index)}</span>);
      idx += 1;
    }
    const token = match[0];
    if (token.startsWith("**") && token.endsWith("**")) {
      parts.push(<strong key={`strong-${idx}`}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith("*") && token.endsWith("*")) {
      parts.push(<em key={`em-${idx}`}>{token.slice(1, -1)}</em>);
    } else if (token.startsWith("`") && token.endsWith("`")) {
      parts.push(<code key={`code-${idx}`}>{token.slice(1, -1)}</code>);
    }
    idx += 1;
    last = pattern.lastIndex;
    match = pattern.exec(text);
  }
  if (last < text.length) {
    parts.push(<span key={`tail-${idx}`}>{text.slice(last)}</span>);
  }
  return parts;
}

function renderMarkdownBlocks(text) {
  const lines = text.split("\n");
  const blocks = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();
    if (!trimmed) {
      i += 1;
      continue;
    }
    if (trimmed.startsWith("### ")) {
      blocks.push(<h3 key={`h3-${i}`}>{renderInlineMarkdown(trimmed.slice(4))}</h3>);
      i += 1;
      continue;
    }
    if (trimmed.startsWith("## ")) {
      blocks.push(<h2 key={`h2-${i}`}>{renderInlineMarkdown(trimmed.slice(3))}</h2>);
      i += 1;
      continue;
    }
    if (trimmed.startsWith("# ")) {
      blocks.push(<h1 key={`h1-${i}`}>{renderInlineMarkdown(trimmed.slice(2))}</h1>);
      i += 1;
      continue;
    }
    if (trimmed.startsWith("> ")) {
      blocks.push(<blockquote key={`quote-${i}`}>{renderInlineMarkdown(trimmed.slice(2))}</blockquote>);
      i += 1;
      continue;
    }
    if (trimmed.startsWith("- ")) {
      const items = [];
      let j = i;
      while (j < lines.length && lines[j].trim().startsWith("- ")) {
        items.push(lines[j].trim().slice(2));
        j += 1;
      }
      blocks.push(
        <ul key={`ul-${i}`}>
          {items.map((item, k) => (
            <li key={`uli-${i}-${k}`}>{renderInlineMarkdown(item)}</li>
          ))}
        </ul>
      );
      i = j;
      continue;
    }
    if (/^\d+\.\s+/.test(trimmed)) {
      const items = [];
      let j = i;
      while (j < lines.length && /^\d+\.\s+/.test(lines[j].trim())) {
        items.push(lines[j].trim().replace(/^\d+\.\s+/, ""));
        j += 1;
      }
      blocks.push(
        <ol key={`ol-${i}`}>
          {items.map((item, k) => (
            <li key={`oli-${i}-${k}`}>{renderInlineMarkdown(item)}</li>
          ))}
        </ol>
      );
      i = j;
      continue;
    }
    const para = [];
    let j = i;
    while (j < lines.length && lines[j].trim() && !/^(#|>|- |\d+\.\s+)/.test(lines[j].trim())) {
      para.push(lines[j].trim());
      j += 1;
    }
    blocks.push(<p key={`p-${i}`}>{renderInlineMarkdown(para.join(" "))}</p>);
    i = j;
  }
  if (blocks.length === 0) {
    return <p>Lesson preview appears here as you type.</p>;
  }
  return blocks;
}

const LESSON_MARKDOWN_CHEATSHEET = [
  "# Title",
  "## Section",
  "### Subsection",
  "- Bullet item",
  "1. Numbered step",
  "> Callout block",
  "**bold** *italic* `code`"
];

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function buildRendererFrameHtml(kind, source, engineState) {
  const escapedSource = JSON.stringify(String(source));
  const escapedState = JSON.stringify(engineState);
  return `<!doctype html>
<html>
  <head>
    <meta charset="UTF-8" />
    <style>
      body { margin: 0; font: 13px monospace; background: #0f1729; color: #cde0ff; }
      #root { padding: 10px; white-space: pre-wrap; }
      .entity { margin: 6px 0; padding: 6px; border: 1px solid #284063; border-radius: 6px; background: #111b2f; }
      .ok { color: #8be9a8; }
      .err { color: #ff8f8f; }
    </style>
  </head>
  <body>
    <div id="root"></div>
    <script>
      const root = document.getElementById("root");
      const source = ${escapedSource};
      const engine = ${escapedState};
      function line(text, cls) {
        const div = document.createElement("div");
        if (cls) div.className = cls;
        div.textContent = text;
        root.appendChild(div);
      }
      function renderEntities(entities) {
        entities.forEach((entity, idx) => {
          const div = document.createElement("div");
          div.className = "entity";
          div.textContent = \`#\${idx + 1} \${JSON.stringify(entity)}\`;
          root.appendChild(div);
        });
      }
      try {
        line("engine.tick=" + String(engine.tick || 0), "ok");
        if ("${kind}" === "javascript") {
          const fn = new Function("engine", "root", source + "\\n; return (typeof render === 'function' ? render(engine, root) : null);");
          const result = fn(engine, root);
          if (result !== null && result !== undefined) line("return: " + JSON.stringify(result), "ok");
        } else if ("${kind}" === "json") {
          const parsed = JSON.parse(source || "{}");
          line("json parsed ok", "ok");
          renderEntities(Array.isArray(parsed.entities) ? parsed.entities : []);
          line(JSON.stringify(parsed, null, 2));
        } else if ("${kind}" === "cobra") {
          const lines = source.split(/\\r?\\n/).map((v) => v.trim()).filter(Boolean);
          const entities = [];
          lines.forEach((ln) => {
            if (ln.startsWith("entity ")) {
              const parts = ln.split(" ");
              entities.push({ id: parts[1] || "anon", x: Number(parts[2] || 0), y: Number(parts[3] || 0), tag: parts[4] || "none" });
            }
          });
          line("cobra entities=" + entities.length, "ok");
          renderEntities(entities);
        } else if ("${kind}" === "python") {
          const lines = source.split(/\\r?\\n/).map((v) => v.trim());
          const drawLines = lines.filter((ln) => ln.startsWith("#draw "));
          line("python directives=" + drawLines.length, "ok");
          drawLines.forEach((ln) => line(ln.slice(6)));
        }
      } catch (err) {
        line(String(err && err.message ? err.message : err), "err");
      }
    </script>
  </body>
</html>`;
}

export function App() {
  const [section, setSection] = useState(() => localStorage.getItem("atelier.section") || "Foyer");
  const [role, setRole] = useState(() => localStorage.getItem("atelier.role") || "senior_artisan");
  const [workspaceId, setWorkspaceId] = useState(() => localStorage.getItem("atelier.workspace") || "main");
  const [output, setOutput] = useState("{}");
  const [notice, setNotice] = useState("Ready");
  const [busyAction, setBusyAction] = useState(null);
  const [activityLog, setActivityLog] = useState([]);

  const [gateCode, setGateCode] = useState("");
  const [adminGateToken, setAdminGateToken] = useState(null);
  const [adminVerified, setAdminVerified] = useState(false);
  const [gateMessage, setGateMessage] = useState("Placement tooling is locked.");
  const [raw, setRaw] = useState("");
  const [timelineLast, setTimelineLast] = useState("25");

  const [contactName, setContactName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contacts, setContacts] = useState([]);
  const [contactFilter, setContactFilter] = useState("");

  const [bookingStart, setBookingStart] = useState("");
  const [bookingEnd, setBookingEnd] = useState("");
  const [bookings, setBookings] = useState([]);
  const [bookingFilter, setBookingFilter] = useState("");
  const [profileName, setProfileName] = useState(() => localStorage.getItem("atelier.profile_name") || "Artisan");
  const [profileEmail, setProfileEmail] = useState(() => localStorage.getItem("atelier.profile_email") || "");
  const [profileTimezone, setProfileTimezone] = useState(
    () => localStorage.getItem("atelier.profile_tz") || Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"
  );
  const [artisanAccessInput, setArtisanAccessInput] = useState("");
  const [artisanAccessVerified, setArtisanAccessVerified] = useState(false);
  const [artisanIssuedCode, setArtisanIssuedCode] = useState("");
  const today = new Date();
  const [calendarYear, setCalendarYear] = useState(today.getFullYear());
  const [calendarMonth, setCalendarMonth] = useState(today.getMonth());
  const [calendarDragStart, setCalendarDragStart] = useState(null);
  const [calendarDragEnd, setCalendarDragEnd] = useState(null);
  const [calendarDragging, setCalendarDragging] = useState(false);
  const [quickStartHour, setQuickStartHour] = useState("10:00");
  const [quickEndHour, setQuickEndHour] = useState("11:00");
  const [calendarModalOpen, setCalendarModalOpen] = useState(false);
  const [calendarModalDay, setCalendarModalDay] = useState(null);
  const [calendarModalStart, setCalendarModalStart] = useState("10:00");
  const [calendarModalEnd, setCalendarModalEnd] = useState("11:00");
  const [calendarModalStatus, setCalendarModalStatus] = useState("scheduled");
  const [calendarModalNotes, setCalendarModalNotes] = useState("");

  const [lessonTitle, setLessonTitle] = useState("");
  const [lessonBody, setLessonBody] = useState("");
  const [lessons, setLessons] = useState([]);
  const [lessonFilter, setLessonFilter] = useState("");
  const LESSON_SOFT_LIMIT = 12000;

  const [moduleTitle, setModuleTitle] = useState("");
  const [moduleDescription, setModuleDescription] = useState("");
  const [modules, setModules] = useState([]);
  const [moduleFilter, setModuleFilter] = useState("");

  const [leadName, setLeadName] = useState("");
  const [leadEmail, setLeadEmail] = useState("");
  const [leadDetails, setLeadDetails] = useState("");
  const [leads, setLeads] = useState([]);
  const [leadFilter, setLeadFilter] = useState("");

  const [clientName, setClientName] = useState("");
  const [clientEmail, setClientEmail] = useState("");
  const [clientPhone, setClientPhone] = useState("");
  const [clients, setClients] = useState([]);
  const [clientFilter, setClientFilter] = useState("");

  const [quoteTitle, setQuoteTitle] = useState("");
  const [quoteAmount, setQuoteAmount] = useState("");
  const [quoteCurrency, setQuoteCurrency] = useState("USD");
  const [quotePublic, setQuotePublic] = useState(false);
  const [quotes, setQuotes] = useState([]);
  const [quoteFilter, setQuoteFilter] = useState("");

  const [orderTitle, setOrderTitle] = useState("");
  const [orderAmount, setOrderAmount] = useState("");
  const [orderCurrency, setOrderCurrency] = useState("USD");
  const [orders, setOrders] = useState([]);
  const [orderFilter, setOrderFilter] = useState("");

  const [supplierName, setSupplierName] = useState("");
  const [supplierContact, setSupplierContact] = useState("");
  const [supplierEmail, setSupplierEmail] = useState("");
  const [suppliers, setSuppliers] = useState([]);
  const [supplierFilter, setSupplierFilter] = useState("");

  const [inventorySku, setInventorySku] = useState("");
  const [inventoryName, setInventoryName] = useState("");
  const [inventoryQty, setInventoryQty] = useState("0");
  const [inventoryReorder, setInventoryReorder] = useState("0");
  const [inventoryCost, setInventoryCost] = useState("0");
  const [inventorySupplierId, setInventorySupplierId] = useState("");
  const [inventoryItems, setInventoryItems] = useState([]);
  const [inventoryFilter, setInventoryFilter] = useState("");

  const [rendererPython, setRendererPython] = useState("#draw title=Workshop Renderer");
  const [rendererCobra, setRendererCobra] = useState("entity cube 12 8 amber");
  const [rendererJs, setRendererJs] = useState("function render(engine, root) { root.append('js tick=' + engine.tick); return { ok: true, tick: engine.tick }; }");
  const [rendererJson, setRendererJson] = useState("{\"entities\":[{\"id\":\"light-1\",\"x\":3,\"y\":5,\"kind\":\"lamp\"}]}");
  const [rendererEngineStateText, setRendererEngineStateText] = useState("{\"tick\":0,\"camera\":{\"x\":0,\"y\":0}}");

  const [publicName, setPublicName] = useState("");
  const [publicEmail, setPublicEmail] = useState("");
  const [publicDetails, setPublicDetails] = useState("");
  const [publicQuotes, setPublicQuotes] = useState([]);
  const [privacyManifest, setPrivacyManifest] = useState(null);

  const [messageDraft, setMessageDraft] = useState("");
  const [messageLog, setMessageLog] = useState([]);
  const [studioFolders, setStudioFolders] = useState(() => {
    const raw = localStorage.getItem("atelier.studio_folders");
    if (!raw) {
      return ["notes", "scripts", "templates"];
    }
    try {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.every((item) => typeof item === "string")) {
        return parsed;
      }
      return ["notes", "scripts", "templates"];
    } catch {
      return ["notes", "scripts", "templates"];
    }
  });
  const [studioFiles, setStudioFiles] = useState(() => {
    const raw = localStorage.getItem("atelier.studio_files");
    if (!raw) {
      return [
        { id: "file_notes", name: "daily-notes.md", folder: "notes", content: "" },
        { id: "file_script", name: "automation.py", folder: "scripts", content: "" },
        { id: "file_template", name: "proposal-template.txt", folder: "templates", content: "" }
      ];
    }
    try {
      const parsed = JSON.parse(raw);
      if (
        Array.isArray(parsed) &&
        parsed.every(
          (item) =>
            item &&
            typeof item.id === "string" &&
            typeof item.name === "string" &&
            typeof item.folder === "string" &&
            typeof item.content === "string"
        )
      ) {
        return parsed;
      }
      return [
        { id: "file_notes", name: "daily-notes.md", folder: "notes", content: "" },
        { id: "file_script", name: "automation.py", folder: "scripts", content: "" },
        { id: "file_template", name: "proposal-template.txt", folder: "templates", content: "" }
      ];
    } catch {
      return [
        { id: "file_notes", name: "daily-notes.md", folder: "notes", content: "" },
        { id: "file_script", name: "automation.py", folder: "scripts", content: "" },
        { id: "file_template", name: "proposal-template.txt", folder: "templates", content: "" }
      ];
    }
  });
  const [studioSelectedFileId, setStudioSelectedFileId] = useState(() => localStorage.getItem("atelier.studio_selected") || "file_notes");
  const [studioNewFolder, setStudioNewFolder] = useState("");
  const [studioNewFileName, setStudioNewFileName] = useState("");
  const [studioTargetFolder, setStudioTargetFolder] = useState("notes");
  const [studioRenameFileName, setStudioRenameFileName] = useState("");
  const [studioRenameFolderFrom, setStudioRenameFolderFrom] = useState("notes");
  const [studioRenameFolderTo, setStudioRenameFolderTo] = useState("");
  const [studioMoveTargetFolder, setStudioMoveTargetFolder] = useState("notes");
  const [studioDraggedFileId, setStudioDraggedFileId] = useState(null);

  const caps = useMemo(() => capabilitiesForRole(role).join(","), [role]);
  const datasetSummary = useMemo(
    () => [
      { label: "Contacts", value: contacts.length },
      { label: "Bookings", value: bookings.length },
      { label: "Lessons", value: lessons.length },
      { label: "Modules", value: modules.length },
      { label: "Leads", value: leads.length },
      { label: "Clients", value: clients.length },
      { label: "Quotes", value: quotes.length },
      { label: "Orders", value: orders.length },
      { label: "Suppliers", value: suppliers.length },
      { label: "Inventory", value: inventoryItems.length }
    ],
    [contacts, bookings, lessons, modules, leads, clients, quotes, orders, suppliers, inventoryItems]
  );
  const studioSelectedFile = useMemo(
    () => studioFiles.find((file) => file.id === studioSelectedFileId) || null,
    [studioFiles, studioSelectedFileId]
  );

  useEffect(() => localStorage.setItem("atelier.section", section), [section]);
  useEffect(() => localStorage.setItem("atelier.role", role), [role]);
  useEffect(() => localStorage.setItem("atelier.workspace", workspaceId), [workspaceId]);
  useEffect(() => localStorage.setItem("atelier.profile_name", profileName), [profileName]);
  useEffect(() => localStorage.setItem("atelier.profile_email", profileEmail), [profileEmail]);
  useEffect(() => localStorage.setItem("atelier.profile_tz", profileTimezone), [profileTimezone]);
  useEffect(() => localStorage.setItem("atelier.studio_folders", JSON.stringify(studioFolders)), [studioFolders]);
  useEffect(() => localStorage.setItem("atelier.studio_files", JSON.stringify(studioFiles)), [studioFiles]);
  useEffect(() => localStorage.setItem("atelier.studio_selected", studioSelectedFileId), [studioSelectedFileId]);
  useEffect(() => {
    function stopDrag() {
      setCalendarDragging(false);
    }
    window.addEventListener("mouseup", stopDrag);
    return () => window.removeEventListener("mouseup", stopDrag);
  }, []);
  useEffect(() => {
    if (studioFiles.length === 0) {
      return;
    }
    if (!studioFiles.some((file) => file.id === studioSelectedFileId)) {
      setStudioSelectedFileId(studioFiles[0].id);
    }
  }, [studioFiles, studioSelectedFileId]);
  useEffect(() => {
    if (studioFolders.length === 0) {
      return;
    }
    if (!studioFolders.includes(studioTargetFolder)) {
      setStudioTargetFolder(studioFolders[0]);
    }
    if (!studioFolders.includes(studioRenameFolderFrom)) {
      setStudioRenameFolderFrom(studioFolders[0]);
    }
    if (!studioFolders.includes(studioMoveTargetFolder)) {
      setStudioMoveTargetFolder(studioFolders[0]);
    }
  }, [studioFolders, studioTargetFolder, studioRenameFolderFrom, studioMoveTargetFolder]);
  useEffect(() => {
    setArtisanAccessVerified(false);
    setArtisanAccessInput("");
    setArtisanIssuedCode("");
  }, [profileName, profileEmail, role, workspaceId]);
  useEffect(() => {
    void fetchArtisanAccessStatus();
  }, [profileName, profileEmail, role, workspaceId]);
  useEffect(() => {
    if (!studioSelectedFile) {
      setStudioRenameFileName("");
      return;
    }
    setStudioRenameFileName(studioSelectedFile.name);
  }, [studioSelectedFile]);

  function pushActivity(action, ok, detail) {
    setActivityLog((prev) =>
      [{ at: new Date().toISOString(), section, workspace_id: workspaceId, action, ok, detail }, ...prev].slice(0, 60)
    );
  }

  async function runAction(actionName, fn) {
    setBusyAction(actionName);
    try {
      const data = await fn();
      setNotice(`${actionName}: success`);
      pushActivity(actionName, true, "ok");
      return data;
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setNotice(`${actionName}: failed`);
      pushActivity(actionName, false, msg);
      return null;
    } finally {
      setBusyAction(null);
    }
  }

  async function apiCall(path, method, body, tokenOverride) {
    const token = tokenOverride === undefined ? adminGateToken : tokenOverride;
    const response = await fetch(`${API_BASE}${path}`, {
      method,
      headers: buildHeaders(role, caps, token),
      body: body === null ? undefined : JSON.stringify(body)
    });
    const data = parseSafeJson(await response.text());
    setOutput(JSON.stringify(data, null, 2));
    if (!response.ok) {
      throw new Error(JSON.stringify(data));
    }
    return data;
  }

  async function publicApiCall(path, method, body) {
    const response = await fetch(`${API_BASE}${path}`, {
      method,
      headers: { "Content-Type": "application/json" },
      body: body === null ? undefined : JSON.stringify(body)
    });
    const data = parseSafeJson(await response.text());
    setOutput(JSON.stringify(data, null, 2));
    if (!response.ok) {
      throw new Error(JSON.stringify(data));
    }
    return data;
  }

  async function refreshGateStatus(tokenOverride) {
    await runAction("admin_gate_status", async () => {
      const data = await apiCall("/v1/atelier/admin/gate/status", "GET", null, tokenOverride);
      const verified = Boolean(data.verified_admin);
      setAdminVerified(verified);
      setGateMessage(verified ? "Placement tooling unlocked." : "Placement tooling is locked.");
      return data;
    });
  }

  useEffect(() => {
    setAdminGateToken(null);
    setAdminVerified(false);
    setGateCode("");
    setGateMessage("Placement tooling is locked.");
    void refreshGateStatus(null);
  }, [role, caps]);

  const makeList = (path, setter, action) => async () =>
    runAction(action, async () => {
      const data = await apiCall(path, "GET", null);
      setter(data);
      return data;
    });

  const listContacts = makeList(`/v1/crm/contacts?workspace_id=${encodeURIComponent(workspaceId)}`, setContacts, "contacts_list");
  const listBookings = makeList(`/v1/booking?workspace_id=${encodeURIComponent(workspaceId)}`, setBookings, "bookings_list");
  const listLessons = makeList(`/v1/lessons?workspace_id=${encodeURIComponent(workspaceId)}`, setLessons, "lessons_list");
  const listModules = makeList(`/v1/modules?workspace_id=${encodeURIComponent(workspaceId)}`, setModules, "modules_list");
  const listLeads = makeList(`/v1/leads?workspace_id=${encodeURIComponent(workspaceId)}`, setLeads, "leads_list");
  const listClients = makeList(`/v1/clients?workspace_id=${encodeURIComponent(workspaceId)}`, setClients, "clients_list");
  const listQuotes = makeList(`/v1/quotes?workspace_id=${encodeURIComponent(workspaceId)}`, setQuotes, "quotes_list");
  const listOrders = makeList(`/v1/orders?workspace_id=${encodeURIComponent(workspaceId)}`, setOrders, "orders_list");
  const listSuppliers = makeList(`/v1/suppliers?workspace_id=${encodeURIComponent(workspaceId)}`, setSuppliers, "suppliers_list");
  const listInventory = makeList(`/v1/inventory?workspace_id=${encodeURIComponent(workspaceId)}`, setInventoryItems, "inventory_list");
  const loadPublicQuotes = async () =>
    runAction("public_quotes_list", async () => {
      const data = await publicApiCall(`/public/commission-hall/quotes?workspace_id=${encodeURIComponent(workspaceId)}`, "GET", null);
      setPublicQuotes(data);
      return data;
    });
  const loadPrivacyManifest = async () =>
    runAction("privacy_manifest_load", async () => {
      const data = await publicApiCall("/public/privacy/manifest", "GET", null);
      setPrivacyManifest(data);
      return data;
    });

  async function loadOrganizationOverview() {
    await runAction("organization_overview", async () => {
      await Promise.all([
        listContacts(),
        listBookings(),
        listLessons(),
        listModules(),
        listLeads(),
        listClients(),
        listQuotes(),
        listOrders(),
        listSuppliers(),
        listInventory()
      ]);
      return {};
    });
  }

  async function verifyAdminGate() {
    await runAction("admin_gate_verify", async () => {
      const data = await apiCall("/v1/atelier/admin/gate/verify", "POST", { gate_code: gateCode }, null);
      const token = typeof data.admin_gate_token === "string" ? data.admin_gate_token : null;
      setAdminGateToken(token);
      setAdminVerified(Boolean(data.verified_admin) && token !== null);
      setGateMessage("Placement tooling unlocked.");
      return data;
    });
  }

  async function observe() {
    await runAction("observe", () => apiCall("/v1/atelier/observe", "POST", {}));
  }
  async function timeline() {
    await runAction("timeline", () => apiCall(`/v1/atelier/timeline?last=${encodeURIComponent(timelineLast)}`, "GET", null));
  }
  async function frontiers() {
    await runAction("frontiers", () => apiCall("/v1/atelier/frontiers", "GET", null));
  }
  async function place() {
    await runAction("place", () => apiCall("/v1/atelier/place", "POST", { raw, context: { scene_id: section.toLowerCase(), workspace_id: workspaceId } }));
  }

  async function createEntity(action, path, payload, reset, refresh) {
    await runAction(action, async () => {
      await apiCall(path, "POST", payload);
      reset();
      await refresh();
      return {};
    });
  }

  async function quickCreateCalendarBooking() {
    if (!selectedCalendarRange) {
      setNotice("calendar_booking_create: select one or more calendar days first");
      return;
    }
    if (!quickStartHour || !quickEndHour) {
      setNotice("calendar_booking_create: start and end time required");
      return;
    }
    const startIso = `${selectedCalendarRange.start}T${quickStartHour}:00`;
    const endIso = `${selectedCalendarRange.end}T${quickEndHour}:00`;
    if (new Date(endIso).getTime() <= new Date(startIso).getTime()) {
      setNotice("calendar_booking_create: end must be after start");
      return;
    }
    await createEntity(
      "calendar_booking_create",
      "/v1/booking",
      {
        workspace_id: workspaceId,
        starts_at: startIso,
        ends_at: endIso,
        status: "scheduled",
        notes: `profile:${profileName || "Artisan"}`
      },
      () => {},
      listBookings
    );
  }

  function openCalendarModalForDay(dayIso) {
    setCalendarModalDay(dayIso);
    setCalendarModalStart("10:00");
    setCalendarModalEnd("11:00");
    setCalendarModalStatus("scheduled");
    setCalendarModalNotes(`profile:${profileName || "Artisan"}`);
    setCalendarModalOpen(true);
  }

  async function createCalendarModalBooking() {
    if (!calendarModalDay) {
      setNotice("calendar_modal_create: no day selected");
      return;
    }
    const startIso = `${calendarModalDay}T${calendarModalStart}:00`;
    const endIso = `${calendarModalDay}T${calendarModalEnd}:00`;
    if (new Date(endIso).getTime() <= new Date(startIso).getTime()) {
      setNotice("calendar_modal_create: end must be after start");
      return;
    }
    if (calendarModalConflicts.length > 0) {
      setNotice("calendar_modal_create: conflict detected, adjust time or proceed intentionally");
      return;
    }
    await createEntity(
      "calendar_modal_create",
      "/v1/booking",
      {
        workspace_id: workspaceId,
        starts_at: startIso,
        ends_at: endIso,
        status: calendarModalStatus,
        notes: calendarModalNotes
      },
      () => {
        setCalendarModalOpen(false);
        setCalendarModalDay(null);
      },
      listBookings
    );
  }

  function createStudioFolder() {
    const name = studioNewFolder.trim();
    if (!name) {
      setNotice("studio_folder_create: name required");
      return;
    }
    if (studioFolders.includes(name)) {
      setNotice("studio_folder_create: folder already exists");
      return;
    }
    setStudioFolders((prev) => [...prev, name]);
    setStudioTargetFolder(name);
    setStudioNewFolder("");
  }

  function createStudioFile() {
    const name = studioNewFileName.trim();
    if (!name) {
      setNotice("studio_file_create: name required");
      return;
    }
    if (!studioTargetFolder) {
      setNotice("studio_file_create: folder required");
      return;
    }
    const next = {
      id: makeStudioFileId(),
      name,
      folder: studioTargetFolder,
      content: ""
    };
    setStudioFiles((prev) => [...prev, next]);
    setStudioSelectedFileId(next.id);
    setStudioNewFileName("");
  }

  function updateStudioSelectedContent(value) {
    if (!studioSelectedFile) {
      return;
    }
    setStudioFiles((prev) =>
      prev.map((file) => (file.id === studioSelectedFile.id ? { ...file, content: value } : file))
    );
  }

  function deleteStudioSelectedFile() {
    if (!studioSelectedFile) {
      return;
    }
    setStudioFiles((prev) => prev.filter((file) => file.id !== studioSelectedFile.id));
  }

  function renameStudioSelectedFile() {
    if (!studioSelectedFile) {
      setNotice("studio_file_rename: no file selected");
      return;
    }
    const nextName = studioRenameFileName.trim();
    if (!nextName) {
      setNotice("studio_file_rename: name required");
      return;
    }
    setStudioFiles((prev) => prev.map((file) => (file.id === studioSelectedFile.id ? { ...file, name: nextName } : file)));
  }

  function moveStudioSelectedFile() {
    if (!studioSelectedFile) {
      setNotice("studio_file_move: no file selected");
      return;
    }
    if (!studioMoveTargetFolder) {
      setNotice("studio_file_move: target folder required");
      return;
    }
    setStudioFiles((prev) =>
      prev.map((file) => (file.id === studioSelectedFile.id ? { ...file, folder: studioMoveTargetFolder } : file))
    );
  }

  function renameStudioFolder() {
    const from = studioRenameFolderFrom.trim();
    const to = studioRenameFolderTo.trim();
    if (!from || !to) {
      setNotice("studio_folder_rename: source and target required");
      return;
    }
    if (!studioFolders.includes(from)) {
      setNotice("studio_folder_rename: source not found");
      return;
    }
    if (studioFolders.includes(to)) {
      setNotice("studio_folder_rename: target already exists");
      return;
    }
    setStudioFolders((prev) => prev.map((folder) => (folder === from ? to : folder)));
    setStudioFiles((prev) => prev.map((file) => (file.folder === from ? { ...file, folder: to } : file)));
    setStudioTargetFolder(to);
    setStudioMoveTargetFolder(to);
    setStudioRenameFolderFrom(to);
    setStudioRenameFolderTo("");
  }

  async function fetchArtisanAccessStatus() {
    await runAction("artisan_access_status", async () => {
      const data = await apiCall("/v1/access/artisan-id/status", "GET", null);
      setArtisanAccessVerified(Boolean(data.artisan_access_verified));
      return data;
    });
  }

  async function issueArtisanAccessCode() {
    await runAction("artisan_access_issue", async () => {
      const data = await apiCall("/v1/access/artisan-id/issue", "POST", {
        profile_name: profileName,
        profile_email: profileEmail
      });
      const issued = typeof data.artisan_code === "string" ? data.artisan_code : "";
      setArtisanIssuedCode(issued);
      setArtisanAccessInput(issued);
      setArtisanAccessVerified(Boolean(data.status?.artisan_access_verified));
      return data;
    });
  }

  async function verifyArtisanAccess() {
    await runAction("artisan_access_verify", async () => {
      const data = await apiCall("/v1/access/artisan-id/verify", "POST", {
        profile_name: profileName,
        profile_email: profileEmail,
        artisan_code: artisanAccessInput
      });
      setArtisanAccessVerified(Boolean(data.artisan_access_verified));
      return data;
    });
  }

  function duplicateStudioSelectedFile() {
    if (!studioSelectedFile) {
      setNotice("studio_file_duplicate: no file selected");
      return;
    }
    const copy = {
      ...studioSelectedFile,
      id: makeStudioFileId(),
      name: `${studioSelectedFile.name}.copy`
    };
    setStudioFiles((prev) => [...prev, copy]);
    setStudioSelectedFileId(copy.id);
  }

  function duplicateStudioFolder() {
    const from = studioRenameFolderFrom.trim();
    if (!from || !studioFolders.includes(from)) {
      setNotice("studio_folder_duplicate: source folder required");
      return;
    }
    const duplicated = `${from}_copy`;
    if (studioFolders.includes(duplicated)) {
      setNotice("studio_folder_duplicate: copy already exists");
      return;
    }
    const filesToCopy = studioFiles.filter((file) => file.folder === from);
    setStudioFolders((prev) => [...prev, duplicated]);
    setStudioFiles((prev) => [
      ...prev,
      ...filesToCopy.map((file) => ({
        ...file,
        id: makeStudioFileId(),
        folder: duplicated,
        name: `${file.name}.copy`
      }))
    ]);
  }

  function moveFileToFolder(fileId, folder) {
    if (!fileId || !folder) {
      return;
    }
    setStudioFiles((prev) => prev.map((file) => (file.id === fileId ? { ...file, folder } : file)));
  }

  function appendLessonBlock(block) {
    setLessonBody((prev) => `${prev}${prev ? "\n\n" : ""}${block}`);
  }

  function surroundSelection(textarea, open, close) {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const before = lessonBody.slice(0, start);
    const selected = lessonBody.slice(start, end);
    const after = lessonBody.slice(end);
    const next = `${before}${open}${selected}${close}${after}`;
    setLessonBody(next);
    requestAnimationFrame(() => {
      const cursorStart = start + open.length;
      const cursorEnd = cursorStart + selected.length;
      textarea.setSelectionRange(cursorStart, cursorEnd);
      textarea.focus();
    });
  }

  function prefixSelectedLines(textarea, prefix) {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const before = lessonBody.slice(0, start);
    const selected = lessonBody.slice(start, end);
    const after = lessonBody.slice(end);
    const lines = selected ? selected.split("\n") : [""];
    const prefixed = lines.map((line) => `${prefix}${line}`).join("\n");
    const next = `${before}${prefixed}${after}`;
    setLessonBody(next);
    requestAnimationFrame(() => {
      textarea.setSelectionRange(start, start + prefixed.length);
      textarea.focus();
    });
  }

  function handleLessonEditorKeyDown(event) {
    const textarea = event.currentTarget;
    const mod = event.ctrlKey || event.metaKey;
    if (event.key === "Tab") {
      event.preventDefault();
      const pos = textarea.selectionStart;
      const next = `${lessonBody.slice(0, pos)}  ${lessonBody.slice(textarea.selectionEnd)}`;
      setLessonBody(next);
      requestAnimationFrame(() => {
        textarea.setSelectionRange(pos + 2, pos + 2);
      });
      return;
    }
    if (!mod) {
      return;
    }
    if (event.key.toLowerCase() === "b") {
      event.preventDefault();
      surroundSelection(textarea, "**", "**");
      return;
    }
    if (event.key.toLowerCase() === "i") {
      event.preventDefault();
      surroundSelection(textarea, "*", "*");
      return;
    }
    if (event.key.toLowerCase() === "k") {
      event.preventDefault();
      surroundSelection(textarea, "`", "`");
      return;
    }
    if (event.shiftKey && event.key === "7") {
      event.preventDefault();
      prefixSelectedLines(textarea, "1. ");
      return;
    }
    if (event.shiftKey && event.key === "8") {
      event.preventDefault();
      prefixSelectedLines(textarea, "- ");
      return;
    }
    if (event.shiftKey && event.key.toLowerCase() === "c") {
      event.preventDefault();
      prefixSelectedLines(textarea, "> ");
    }
  }

  const filtered = (items, text, keys) =>
    items.filter((it) => (text ? keys.map((k) => String(it[k] || "")).join(" ").toLowerCase().includes(text.toLowerCase()) : true));

  const filteredContacts = filtered(contacts, contactFilter, ["full_name", "email"]);
  const filteredBookings = filtered(bookings, bookingFilter, ["status", "starts_at", "ends_at"]);
  const filteredLessons = filtered(lessons, lessonFilter, ["title", "status"]);
  const filteredModules = filtered(modules, moduleFilter, ["title", "status"]);
  const filteredLeads = filtered(leads, leadFilter, ["full_name", "email", "status"]);
  const filteredClients = filtered(clients, clientFilter, ["full_name", "email", "status"]);
  const filteredQuotes = filtered(quotes, quoteFilter, ["title", "status", "currency"]);
  const filteredOrders = filtered(orders, orderFilter, ["title", "status", "currency"]);
  const filteredSuppliers = filtered(suppliers, supplierFilter, ["supplier_name", "contact_name", "contact_email"]);
  const filteredInventory = filtered(inventoryItems, inventoryFilter, ["sku", "name", "currency"]);
  const rendererEngineState = useMemo(() => {
    try {
      const parsed = JSON.parse(rendererEngineStateText || "{}");
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        return parsed;
      }
      return { tick: 0 };
    } catch {
      return { tick: 0 };
    }
  }, [rendererEngineStateText]);
  const pythonFrameDoc = useMemo(() => buildRendererFrameHtml("python", rendererPython, rendererEngineState), [rendererPython, rendererEngineState]);
  const cobraFrameDoc = useMemo(() => buildRendererFrameHtml("cobra", rendererCobra, rendererEngineState), [rendererCobra, rendererEngineState]);
  const jsFrameDoc = useMemo(() => buildRendererFrameHtml("javascript", rendererJs, rendererEngineState), [rendererJs, rendererEngineState]);
  const jsonFrameDoc = useMemo(() => buildRendererFrameHtml("json", rendererJson, rendererEngineState), [rendererJson, rendererEngineState]);
  const calendarCells = useMemo(() => buildCalendarDays(calendarYear, calendarMonth), [calendarYear, calendarMonth]);
  const selectedCalendarRange = useMemo(() => {
    if (!calendarDragStart || !calendarDragEnd) {
      return null;
    }
    const start = compareIso(calendarDragStart, calendarDragEnd) <= 0 ? calendarDragStart : calendarDragEnd;
    const end = compareIso(calendarDragStart, calendarDragEnd) <= 0 ? calendarDragEnd : calendarDragStart;
    return { start, end };
  }, [calendarDragStart, calendarDragEnd]);
  const bookingsByDay = useMemo(() => {
    const byDay = {};
    for (const booking of bookings) {
      const start = String(booking.starts_at || "").slice(0, 10);
      if (!start) {
        continue;
      }
      if (!byDay[start]) {
        byDay[start] = [];
      }
      byDay[start].push(booking);
    }
    return byDay;
  }, [bookings]);
  const calendarModalConflicts = useMemo(() => {
    if (!calendarModalDay) {
      return [];
    }
    const startIso = `${calendarModalDay}T${calendarModalStart}:00`;
    const endIso = `${calendarModalDay}T${calendarModalEnd}:00`;
    const start = new Date(startIso).getTime();
    const end = new Date(endIso).getTime();
    if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) {
      return [];
    }
    return bookings.filter((booking) => {
      const bStart = new Date(String(booking.starts_at || "")).getTime();
      const bEnd = new Date(String(booking.ends_at || "")).getTime();
      if (!Number.isFinite(bStart) || !Number.isFinite(bEnd)) {
        return false;
      }
      return rangesOverlap(start, end, bStart, bEnd);
    });
  }, [bookings, calendarModalDay, calendarModalStart, calendarModalEnd]);

  function isDaySelected(iso) {
    if (!iso || !selectedCalendarRange) {
      return false;
    }
    return compareIso(iso, selectedCalendarRange.start) >= 0 && compareIso(iso, selectedCalendarRange.end) <= 0;
  }

  function stepRendererEngine() {
    const next = {
      ...rendererEngineState,
      tick: Number(rendererEngineState.tick || 0) + 1
    };
    setRendererEngineStateText(JSON.stringify(next, null, 2));
  }

  function renderSectionTools() {
    const restrictedSections = new Set(["Workshop", "Temple and Gardens", "Guild Hall"]);
    if (restrictedSections.has(section) && !artisanAccessVerified) {
      return (
        <section className="panel">
          <h2>Artisan Access Gate</h2>
          <p>This space requires a verified ArtisanID bound to your profile and station.</p>
          <div className="row">
            <input value={artisanAccessInput} onChange={(e) => setArtisanAccessInput(e.target.value)} placeholder="enter artisan ID code" />
            <button className="action" onClick={verifyArtisanAccess}>Verify Access</button>
          </div>
          <p>{`Profile: ${profileName || "Artisan"} | Station: ${role} | Workspace: ${workspaceId}`}</p>
          <div className="row">
            <button className="action" onClick={issueArtisanAccessCode}>Issue Server Code</button>
            <button className="action" onClick={fetchArtisanAccessStatus}>Refresh Status</button>
          </div>
          {artisanIssuedCode ? <p>{`Issued code: ${artisanIssuedCode}`}</p> : null}
        </section>
      );
    }

    if (section === "Foyer") {
      return (
        <>
          <section className="panel">
            <h2>Session Control</h2>
            <div className="row">
              <select value={role} onChange={(e) => setRole(e.target.value)}>
                <option value="apprentice">Apprentice</option>
                <option value="artisan">Artisan</option>
                <option value="senior_artisan">Senior Artisan</option>
                <option value="steward">Steward</option>
              </select>
              <input value={workspaceId} onChange={(e) => setWorkspaceId(e.target.value)} placeholder="workspace id" />
              <button className="action" onClick={loadOrganizationOverview}>Load Overview</button>
            </div>
            <div className="kpis">
              {datasetSummary.map((it) => (
                <div className="kpi" key={it.label}><span>{it.label}</span><strong>{it.value}</strong></div>
              ))}
            </div>
          </section>
          <section className="panel">
            <h2>User Profile</h2>
            <div className="row">
              <input value={profileName} onChange={(e) => setProfileName(e.target.value)} placeholder="display name" />
              <input value={profileEmail} onChange={(e) => setProfileEmail(e.target.value)} placeholder="email" />
              <input value={profileTimezone} onChange={(e) => setProfileTimezone(e.target.value)} placeholder="timezone (IANA)" />
            </div>
            <p>{`Bookings and calendar views are scoped to workspace "${workspaceId}" and profile "${profileName || "Artisan"}".`}</p>
            <div className="row">
              <input value={artisanAccessInput} onChange={(e) => setArtisanAccessInput(e.target.value)} placeholder="artisan ID access code" />
              <button className="action" onClick={verifyArtisanAccess}>Verify Workshop/Temple/Guild Access</button>
              <button className="action" onClick={issueArtisanAccessCode}>Issue Server Code</button>
              <button className="action" onClick={fetchArtisanAccessStatus}>Refresh Status</button>
            </div>
            <p>{`Access status: ${artisanAccessVerified ? "verified" : "locked"}`}</p>
            {artisanIssuedCode ? <p>{`Issued code: ${artisanIssuedCode}`}</p> : null}
          </section>
          <section className="panel">
            <h2>Booking Calendar</h2>
            <div className="row">
              <button className="action" onClick={() => {
                if (calendarMonth === 0) {
                  setCalendarMonth(11);
                  setCalendarYear((y) => y - 1);
                } else {
                  setCalendarMonth((m) => m - 1);
                }
              }}>Prev Month</button>
              <strong className="calendar-label">{monthLabel(calendarYear, calendarMonth)}</strong>
              <button className="action" onClick={() => {
                if (calendarMonth === 11) {
                  setCalendarMonth(0);
                  setCalendarYear((y) => y + 1);
                } else {
                  setCalendarMonth((m) => m + 1);
                }
              }}>Next Month</button>
              <button className="action" onClick={listBookings}>Refresh Bookings</button>
            </div>
            <div className="row">
              <input value={quickStartHour} onChange={(e) => setQuickStartHour(e.target.value)} placeholder="start HH:MM" />
              <input value={quickEndHour} onChange={(e) => setQuickEndHour(e.target.value)} placeholder="end HH:MM" />
              <button className="action" onClick={quickCreateCalendarBooking}>Create Booking From Selection</button>
              <button className="action" onClick={() => { setCalendarDragStart(null); setCalendarDragEnd(null); }}>Clear Selection</button>
            </div>
            <p>
              {selectedCalendarRange
                ? `Selected range: ${selectedCalendarRange.start} to ${selectedCalendarRange.end}`
                : "Drag across days to select a booking range."}
            </p>
            <div className="calendar-grid">
              {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((name) => (
                <div key={name} className="calendar-head">{name}</div>
              ))}
              {calendarCells.map((cell) => {
                const count = cell.iso ? (bookingsByDay[cell.iso] || []).length : 0;
                return (
                  <div
                    key={cell.key}
                    className={`calendar-cell ${cell.day ? "" : "calendar-cell-empty"} ${isDaySelected(cell.iso) ? "calendar-cell-selected" : ""}`}
                    onMouseDown={() => {
                      if (!cell.iso) {
                        return;
                      }
                      setCalendarDragStart(cell.iso);
                      setCalendarDragEnd(cell.iso);
                      setCalendarDragging(true);
                    }}
                    onMouseEnter={() => {
                      if (!cell.iso || !calendarDragging) {
                        return;
                      }
                      setCalendarDragEnd(cell.iso);
                    }}
                    onMouseUp={() => {
                      if (!cell.iso) {
                        setCalendarDragging(false);
                        return;
                      }
                      if (calendarDragging) {
                        setCalendarDragEnd(cell.iso);
                      }
                      setCalendarDragging(false);
                    }}
                  >
                    {cell.day ? (
                      <>
                        <div className="calendar-day-row">
                          <span>{cell.day}</span>
                          <button
                            className="calendar-add-btn"
                            onMouseDown={(e) => e.stopPropagation()}
                            onClick={(e) => {
                              e.stopPropagation();
                              if (cell.iso) {
                                openCalendarModalForDay(cell.iso);
                              }
                            }}
                          >
                            +
                          </button>
                        </div>
                        {count > 0 ? <em>{`${count} booking${count === 1 ? "" : "s"}`}</em> : null}
                      </>
                    ) : null}
                  </div>
                );
              })}
            </div>
            {calendarModalOpen ? (
              <div className="modal-backdrop">
                <div className="modal-card">
                  <h3>{`Create Booking - ${calendarModalDay}`}</h3>
                  <div className="row">
                    <input value={calendarModalStart} onChange={(e) => setCalendarModalStart(e.target.value)} placeholder="start HH:MM" />
                    <input value={calendarModalEnd} onChange={(e) => setCalendarModalEnd(e.target.value)} placeholder="end HH:MM" />
                  </div>
                  <div className="row">
                    <input value={calendarModalStatus} onChange={(e) => setCalendarModalStatus(e.target.value)} placeholder="status" />
                    <input value={calendarModalNotes} onChange={(e) => setCalendarModalNotes(e.target.value)} placeholder="notes" />
                  </div>
                  {calendarModalConflicts.length > 0 ? (
                    <div className="conflict-box">
                      <strong>{`${calendarModalConflicts.length} conflict${calendarModalConflicts.length === 1 ? "" : "s"} detected`}</strong>
                      <ul>
                        {calendarModalConflicts.map((booking) => (
                          <li key={booking.id || `${booking.starts_at}-${booking.ends_at}`}>
                            {`${String(booking.starts_at)} -> ${String(booking.ends_at)} (${String(booking.status || "scheduled")})`}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  <div className="row">
                    <button className="action" onClick={createCalendarModalBooking}>Create</button>
                    <button
                      className="action"
                      onClick={() =>
                        createEntity(
                          "calendar_modal_force_create",
                          "/v1/booking",
                          {
                            workspace_id: workspaceId,
                            starts_at: `${calendarModalDay}T${calendarModalStart}:00`,
                            ends_at: `${calendarModalDay}T${calendarModalEnd}:00`,
                            status: calendarModalStatus,
                            notes: `${calendarModalNotes} [conflict_override]`
                          },
                          () => {
                            setCalendarModalOpen(false);
                            setCalendarModalDay(null);
                          },
                          listBookings
                        )
                      }
                      disabled={calendarModalConflicts.length === 0}
                    >
                      Force Create
                    </button>
                    <button className="action" onClick={() => setCalendarModalOpen(false)}>Cancel</button>
                  </div>
                </div>
              </div>
            ) : null}
          </section>
          <GraphBars title="Organization Graph" items={datasetSummary} />
        </>
      );
    }
    if (section === "Workshop") {
      return (
        <>
          <section className="panel">
            <h2>Admin Gate</h2>
            <p>{gateMessage}</p>
            <div className="row">
              <input value={gateCode} onChange={(e) => setGateCode(e.target.value)} placeholder="steward gate code" disabled={role !== "steward"} />
              <button className="action" onClick={verifyAdminGate} disabled={role !== "steward"}>Verify Gate</button>
              <button className="action" onClick={() => void refreshGateStatus(undefined)}>Refresh</button>
            </div>
          </section>
          {adminVerified && role === "steward" ? (
            <section className="panel">
              <h2>Placement Emitter</h2>
              <div className="row">
                <input value={raw} onChange={(e) => setRaw(e.target.value)} placeholder="emit placement line" />
                <button className="action" onClick={place}>Emit Placement</button>
              </div>
            </section>
          ) : null}
        </>
      );
    }
    if (section === "CRM") {
      return (
        <section className="panel">
          <h2>CRM</h2>
          <div className="row">
            <input value={contactName} onChange={(e) => setContactName(e.target.value)} placeholder="contact name" />
            <input value={contactEmail} onChange={(e) => setContactEmail(e.target.value)} placeholder="contact email" />
            <button className="action" onClick={() => createEntity("contacts_create", "/v1/crm/contacts", { workspace_id: workspaceId, full_name: contactName, email: contactEmail || null, notes: "" }, () => { setContactName(""); setContactEmail(""); }, listContacts)}>Create</button>
            <button className="action" onClick={listContacts}>Refresh</button>
          </div>
          <div className="row"><input value={contactFilter} onChange={(e) => setContactFilter(e.target.value)} placeholder="filter contacts" /><button className="action" onClick={() => downloadJson(`contacts-${workspaceId}.json`, filteredContacts)}>Export</button></div>
          <pre>{JSON.stringify(filteredContacts, null, 2)}</pre>
        </section>
      );
    }
    if (section === "Booking System") {
      return (
        <section className="panel">
          <h2>Booking System</h2>
          <div className="row">
            <input value={bookingStart} onChange={(e) => setBookingStart(e.target.value)} placeholder="start ISO datetime" />
            <input value={bookingEnd} onChange={(e) => setBookingEnd(e.target.value)} placeholder="end ISO datetime" />
            <button className="action" onClick={() => createEntity("bookings_create", "/v1/booking", { workspace_id: workspaceId, starts_at: bookingStart, ends_at: bookingEnd, status: "scheduled", notes: "" }, () => {}, listBookings)}>Create</button>
            <button className="action" onClick={listBookings}>Refresh</button>
          </div>
          <div className="row"><input value={bookingFilter} onChange={(e) => setBookingFilter(e.target.value)} placeholder="filter bookings" /><button className="action" onClick={() => downloadJson(`bookings-${workspaceId}.json`, filteredBookings)}>Export</button></div>
          <pre>{JSON.stringify(filteredBookings, null, 2)}</pre>
        </section>
      );
    }
    if (section === "Lesson Creation") {
      return (
        <section className="panel">
          <h2>Lesson Builder</h2>
          <div className="row">
            <input value={lessonTitle} onChange={(e) => setLessonTitle(e.target.value)} placeholder="lesson title" />
            <button className="action" onClick={() => createEntity("lessons_create", "/v1/lessons", { workspace_id: workspaceId, title: lessonTitle, body: lessonBody, status: "draft" }, () => { setLessonTitle(""); setLessonBody(""); }, listLessons)}>Create</button>
            <button className="action" onClick={listLessons}>Refresh</button>
          </div>
          <div className="row">
            <button className="action" onClick={() => appendLessonBlock("## Learning Objective\n- ")}>Add Objective Block</button>
            <button className="action" onClick={() => appendLessonBlock("### Exercise\n1. ")}>Add Exercise Block</button>
            <button className="action" onClick={() => appendLessonBlock("### Reflection\n- ")}>Add Reflection Block</button>
            <button className="action" onClick={() => appendLessonBlock("> Key Insight")}>Add Callout</button>
            <input value={lessonFilter} onChange={(e) => setLessonFilter(e.target.value)} placeholder="filter lessons" />
          </div>
          <div className="lesson-workbench">
            <div>
              <textarea
                className="editor lesson-editor"
                value={lessonBody}
                onChange={(e) => setLessonBody(e.target.value)}
                onKeyDown={handleLessonEditorKeyDown}
                placeholder="Write full lesson content with sections, spacing, bullets, and examples."
              />
              <div className="cheatsheet">
                <h4>Markdown Cheatsheet</h4>
                <ul>
                  {LESSON_MARKDOWN_CHEATSHEET.map((item) => (
                    <li key={item}><code>{item}</code></li>
                  ))}
                </ul>
                <p>Shortcuts: Ctrl/Cmd+B bold, Ctrl/Cmd+I italic, Ctrl/Cmd+K code, Ctrl/Cmd+Shift+8 bullet, Ctrl/Cmd+Shift+7 numbered, Ctrl/Cmd+Shift+C quote.</p>
              </div>
              <p className={`char-count ${lessonBody.length > LESSON_SOFT_LIMIT ? "char-count-warn" : ""}`}>
                {`Characters: ${lessonBody.length}${lessonBody.length > LESSON_SOFT_LIMIT ? ` (above soft limit ${LESSON_SOFT_LIMIT})` : ""}`}
              </p>
            </div>
            <div className="lesson-preview">
              <h3>Live Preview</h3>
              <div className="preview-body">{renderMarkdownBlocks(lessonBody)}</div>
            </div>
          </div>
          <pre>{JSON.stringify(filteredLessons, null, 2)}</pre>
        </section>
      );
    }
    if (section === "Module Creation") {
      return (
        <section className="panel">
          <h2>Module Builder</h2>
          <div className="row">
            <input value={moduleTitle} onChange={(e) => setModuleTitle(e.target.value)} placeholder="module title" />
            <button className="action" onClick={() => createEntity("modules_create", "/v1/modules", { workspace_id: workspaceId, title: moduleTitle, description: moduleDescription, status: "draft" }, () => { setModuleTitle(""); setModuleDescription(""); }, listModules)}>Create</button>
            <button className="action" onClick={listModules}>Refresh</button>
          </div>
          <div className="row"><input value={moduleDescription} onChange={(e) => setModuleDescription(e.target.value)} placeholder="module description" /><input value={moduleFilter} onChange={(e) => setModuleFilter(e.target.value)} placeholder="filter modules" /></div>
          <pre>{JSON.stringify(filteredModules, null, 2)}</pre>
        </section>
      );
    }
    if (section === "Leads") {
      return (
        <section className="panel">
          <h2>Leads</h2>
          <div className="row">
            <input value={leadName} onChange={(e) => setLeadName(e.target.value)} placeholder="lead name" />
            <input value={leadEmail} onChange={(e) => setLeadEmail(e.target.value)} placeholder="lead email" />
            <button className="action" onClick={() => createEntity("leads_create", "/v1/leads", { workspace_id: workspaceId, full_name: leadName, email: leadEmail || null, details: leadDetails, status: "new", source: "internal" }, () => { setLeadName(""); setLeadEmail(""); setLeadDetails(""); }, listLeads)}>Create</button>
            <button className="action" onClick={listLeads}>Refresh</button>
          </div>
          <div className="row"><input value={leadDetails} onChange={(e) => setLeadDetails(e.target.value)} placeholder="lead details" /><input value={leadFilter} onChange={(e) => setLeadFilter(e.target.value)} placeholder="filter leads" /></div>
          <pre>{JSON.stringify(filteredLeads, null, 2)}</pre>
        </section>
      );
    }
    if (section === "Clients") {
      return (
        <section className="panel">
          <h2>Clients</h2>
          <div className="row">
            <input value={clientName} onChange={(e) => setClientName(e.target.value)} placeholder="client name" />
            <input value={clientEmail} onChange={(e) => setClientEmail(e.target.value)} placeholder="client email" />
            <input value={clientPhone} onChange={(e) => setClientPhone(e.target.value)} placeholder="client phone" />
            <button className="action" onClick={() => createEntity("clients_create", "/v1/clients", { workspace_id: workspaceId, full_name: clientName, email: clientEmail || null, phone: clientPhone || null, status: "active" }, () => { setClientName(""); setClientEmail(""); setClientPhone(""); }, listClients)}>Create</button>
            <button className="action" onClick={listClients}>Refresh</button>
          </div>
          <div className="row"><input value={clientFilter} onChange={(e) => setClientFilter(e.target.value)} placeholder="filter clients" /></div>
          <pre>{JSON.stringify(filteredClients, null, 2)}</pre>
        </section>
      );
    }
    if (section === "Quotes") {
      return (
        <>
          <section className="panel">
            <h2>Quotes</h2>
            <div className="row">
              <input value={quoteTitle} onChange={(e) => setQuoteTitle(e.target.value)} placeholder="quote title" />
              <input value={quoteAmount} onChange={(e) => setQuoteAmount(e.target.value)} placeholder="amount cents" />
              <input value={quoteCurrency} onChange={(e) => setQuoteCurrency(e.target.value)} placeholder="currency" />
              <label><input type="checkbox" checked={quotePublic} onChange={(e) => setQuotePublic(e.target.checked)} /> Public</label>
              <button className="action" onClick={() => createEntity("quotes_create", "/v1/quotes", { workspace_id: workspaceId, title: quoteTitle, amount_cents: Number.parseInt(quoteAmount || "0", 10), currency: quoteCurrency, status: quotePublic ? "published" : "draft", is_public: quotePublic, notes: "" }, () => { setQuoteTitle(""); setQuoteAmount(""); setQuotePublic(false); }, listQuotes)}>Create</button>
              <button className="action" onClick={listQuotes}>Refresh</button>
            </div>
            <div className="row"><input value={quoteFilter} onChange={(e) => setQuoteFilter(e.target.value)} placeholder="filter quotes" /></div>
            <pre>{JSON.stringify(filteredQuotes, null, 2)}</pre>
          </section>
          <GraphBars
            title="Quote Status Graph"
            items={[
              { label: "Draft", value: quotes.filter((q) => q.status === "draft").length },
              { label: "Published", value: quotes.filter((q) => q.status === "published").length },
              { label: "Public", value: quotes.filter((q) => q.is_public).length }
            ]}
          />
        </>
      );
    }
    if (section === "Orders") {
      return (
        <section className="panel">
          <h2>Orders</h2>
          <div className="row">
            <input value={orderTitle} onChange={(e) => setOrderTitle(e.target.value)} placeholder="order title" />
            <input value={orderAmount} onChange={(e) => setOrderAmount(e.target.value)} placeholder="amount cents" />
            <input value={orderCurrency} onChange={(e) => setOrderCurrency(e.target.value)} placeholder="currency" />
            <button className="action" onClick={() => createEntity("orders_create", "/v1/orders", { workspace_id: workspaceId, title: orderTitle, amount_cents: Number.parseInt(orderAmount || "0", 10), currency: orderCurrency, status: "open", notes: "" }, () => { setOrderTitle(""); setOrderAmount(""); }, listOrders)}>Create</button>
            <button className="action" onClick={listOrders}>Refresh</button>
          </div>
          <div className="row"><input value={orderFilter} onChange={(e) => setOrderFilter(e.target.value)} placeholder="filter orders" /></div>
          <pre>{JSON.stringify(filteredOrders, null, 2)}</pre>
        </section>
      );
    }
    if (section === "Suppliers") {
      return (
        <section className="panel">
          <h2>Suppliers</h2>
          <div className="row">
            <input value={supplierName} onChange={(e) => setSupplierName(e.target.value)} placeholder="supplier name" />
            <input value={supplierContact} onChange={(e) => setSupplierContact(e.target.value)} placeholder="contact name" />
            <input value={supplierEmail} onChange={(e) => setSupplierEmail(e.target.value)} placeholder="contact email" />
            <button
              className="action"
              onClick={() =>
                createEntity(
                  "suppliers_create",
                  "/v1/suppliers",
                  {
                    workspace_id: workspaceId,
                    supplier_name: supplierName,
                    contact_name: supplierContact,
                    contact_email: supplierEmail || null,
                    contact_phone: null,
                    notes: ""
                  },
                  () => {
                    setSupplierName("");
                    setSupplierContact("");
                    setSupplierEmail("");
                  },
                  listSuppliers
                )
              }
            >
              Create
            </button>
            <button className="action" onClick={listSuppliers}>Refresh</button>
          </div>
          <div className="row">
            <input value={supplierFilter} onChange={(e) => setSupplierFilter(e.target.value)} placeholder="filter suppliers" />
            <button className="action" onClick={() => downloadJson(`suppliers-${workspaceId}.json`, filteredSuppliers)}>Export</button>
          </div>
          <pre>{JSON.stringify(filteredSuppliers, null, 2)}</pre>
        </section>
      );
    }
    if (section === "Inventory") {
      return (
        <section className="panel">
          <h2>Inventory</h2>
          <div className="row">
            <input value={inventorySku} onChange={(e) => setInventorySku(e.target.value)} placeholder="SKU" />
            <input value={inventoryName} onChange={(e) => setInventoryName(e.target.value)} placeholder="item name" />
            <input value={inventoryQty} onChange={(e) => setInventoryQty(e.target.value)} placeholder="qty on hand" />
            <input value={inventoryReorder} onChange={(e) => setInventoryReorder(e.target.value)} placeholder="reorder level" />
            <input value={inventoryCost} onChange={(e) => setInventoryCost(e.target.value)} placeholder="unit cost cents" />
          </div>
          <div className="row">
            <select value={inventorySupplierId} onChange={(e) => setInventorySupplierId(e.target.value)}>
              <option value="">no supplier</option>
              {suppliers.map((supplier) => (
                <option key={supplier.id} value={supplier.id}>{supplier.supplier_name}</option>
              ))}
            </select>
            <button
              className="action"
              onClick={() =>
                createEntity(
                  "inventory_create",
                  "/v1/inventory",
                  {
                    workspace_id: workspaceId,
                    sku: inventorySku,
                    name: inventoryName,
                    quantity_on_hand: Number.parseInt(inventoryQty || "0", 10),
                    reorder_level: Number.parseInt(inventoryReorder || "0", 10),
                    unit_cost_cents: Number.parseInt(inventoryCost || "0", 10),
                    currency: "USD",
                    supplier_id: inventorySupplierId || null,
                    notes: ""
                  },
                  () => {
                    setInventorySku("");
                    setInventoryName("");
                    setInventoryQty("0");
                    setInventoryReorder("0");
                    setInventoryCost("0");
                    setInventorySupplierId("");
                  },
                  listInventory
                )
              }
            >
              Create
            </button>
            <button className="action" onClick={listSuppliers}>Load Suppliers</button>
            <button className="action" onClick={listInventory}>Refresh Inventory</button>
          </div>
          <div className="row">
            <input value={inventoryFilter} onChange={(e) => setInventoryFilter(e.target.value)} placeholder="filter inventory" />
            <button className="action" onClick={() => downloadJson(`inventory-${workspaceId}.json`, filteredInventory)}>Export</button>
          </div>
          <pre>{JSON.stringify(filteredInventory, null, 2)}</pre>
        </section>
      );
    }
    if (section === "Renderer Lab") {
      return (
        <>
          <section className="panel">
            <h2>Multi-Frame Renderer</h2>
            <p>Programmable structural renderer with independent Python, Cobra, JavaScript, and JSON frames.</p>
            <div className="row">
              <button className="action" onClick={stepRendererEngine}>Step Engine Tick</button>
              <button className="action" onClick={() => setRendererEngineStateText(JSON.stringify({ tick: 0, camera: { x: 0, y: 0 } }, null, 2))}>Reset Engine</button>
            </div>
            <div className="renderer-grid">
              <div className="renderer-cell">
                <h3>Python Layer</h3>
                <textarea className="editor editor-mono renderer-editor" value={rendererPython} onChange={(e) => setRendererPython(e.target.value)} />
                <iframe className="renderer-frame" sandbox="allow-scripts" srcDoc={pythonFrameDoc} title="python-renderer" />
              </div>
              <div className="renderer-cell">
                <h3>Cobra Layer</h3>
                <textarea className="editor editor-mono renderer-editor" value={rendererCobra} onChange={(e) => setRendererCobra(e.target.value)} />
                <iframe className="renderer-frame" sandbox="allow-scripts" srcDoc={cobraFrameDoc} title="cobra-renderer" />
              </div>
              <div className="renderer-cell">
                <h3>JavaScript Layer</h3>
                <textarea className="editor editor-mono renderer-editor" value={rendererJs} onChange={(e) => setRendererJs(e.target.value)} />
                <iframe className="renderer-frame" sandbox="allow-scripts" srcDoc={jsFrameDoc} title="js-renderer" />
              </div>
              <div className="renderer-cell">
                <h3>JSON Scene Layer</h3>
                <textarea className="editor editor-mono renderer-editor" value={rendererJson} onChange={(e) => setRendererJson(e.target.value)} />
                <iframe className="renderer-frame" sandbox="allow-scripts" srcDoc={jsonFrameDoc} title="json-renderer" />
              </div>
            </div>
          </section>
          <section className="panel">
            <h2>Engine State</h2>
            <textarea className="editor editor-mono renderer-state" value={rendererEngineStateText} onChange={(e) => setRendererEngineStateText(e.target.value)} />
          </section>
        </>
      );
    }
    if (section === "Privacy") {
      return (
        <section className="panel">
          <h2>Privacy Policy Manifest</h2>
          <p>Machine-readable disclosure bundle for app/web/electron/android distribution.</p>
          <div className="row">
            <button className="action" onClick={loadPrivacyManifest}>Load from API</button>
            <button className="action" onClick={() => downloadJson("privacy-policy-manifest.json", privacyManifest || {})}>Export</button>
          </div>
          <pre>{JSON.stringify(privacyManifest || {}, null, 2)}</pre>
        </section>
      );
    }
    if (section === "Commission Hall") {
      return (
        <section className="panel">
          <h2>Public Commission Hall</h2>
          <p>Public surface for published quote visibility and inquiry intake.</p>
          <div className="row"><button className="action" onClick={loadPublicQuotes}>Load Public Quotes</button><button className="action" onClick={() => downloadJson(`public-quotes-${workspaceId}.json`, publicQuotes)}>Export</button></div>
          <div className="row"><input value={publicName} onChange={(e) => setPublicName(e.target.value)} placeholder="your name" /><input value={publicEmail} onChange={(e) => setPublicEmail(e.target.value)} placeholder="your email" /><button className="action" onClick={() => runAction("public_inquiry_create", () => publicApiCall("/public/commission-hall/inquiries", "POST", { workspace_id: workspaceId, full_name: publicName, email: publicEmail || null, details: publicDetails }))}>Submit Inquiry</button></div>
          <div className="row"><input value={publicDetails} onChange={(e) => setPublicDetails(e.target.value)} placeholder="commission details" /></div>
          <pre>{JSON.stringify(publicQuotes, null, 2)}</pre>
        </section>
      );
    }
    if (section === "Temple and Gardens") {
      return <section className="panel"><h2>Frontier Reflection</h2><div className="row"><button className="action" onClick={frontiers}>Load Frontiers</button><button className="action" onClick={observe}>Run Observe</button><button className="action" onClick={timeline}>Timeline</button></div></section>;
    }
    if (section === "Guild Hall") {
      return <section className="panel"><h2>Guild Activity</h2><div className="row"><button className="action" onClick={listLessons}>Refresh Lessons</button><button className="action" onClick={listModules}>Refresh Modules</button></div></section>;
    }
    if (section === "Messages") {
      return <section className="panel"><h2>Messages</h2><div className="row"><input value={messageDraft} onChange={(e) => setMessageDraft(e.target.value)} placeholder="message text" /><button className="action" onClick={() => setMessageLog((prev) => [{ section, text: messageDraft, at: new Date().toISOString() }, ...prev].slice(0, 40))}>Post</button></div><pre>{JSON.stringify(messageLog, null, 2)}</pre></section>;
    }
    if (section === "Studio Hub") {
      return (
        <>
          <section className="panel">
            <h2>Studio Workspace</h2>
            <div className="row">
              <input value={studioNewFolder} onChange={(e) => setStudioNewFolder(e.target.value)} placeholder="new folder name" />
              <button className="action" onClick={createStudioFolder}>Add Folder</button>
            </div>
            <div className="row">
              <select value={studioRenameFolderFrom} onChange={(e) => setStudioRenameFolderFrom(e.target.value)}>
                {studioFolders.map((folder) => (
                  <option key={`rename-${folder}`} value={folder}>{folder}</option>
                ))}
              </select>
              <input value={studioRenameFolderTo} onChange={(e) => setStudioRenameFolderTo(e.target.value)} placeholder="rename folder to" />
              <button className="action" onClick={renameStudioFolder}>Rename Folder</button>
              <button className="action" onClick={duplicateStudioFolder}>Duplicate Folder</button>
            </div>
            <div className="row">
              <select value={studioTargetFolder} onChange={(e) => setStudioTargetFolder(e.target.value)}>
                {studioFolders.map((folder) => (
                  <option key={folder} value={folder}>{folder}</option>
                ))}
              </select>
              <input value={studioNewFileName} onChange={(e) => setStudioNewFileName(e.target.value)} placeholder="new file name" />
              <button className="action" onClick={createStudioFile}>Add File</button>
            </div>
            <div className="studio-grid">
              <aside className="studio-tree">
                {studioFolders.map((folder) => (
                  <div key={folder} className="studio-folder">
                    <strong>{folder}</strong>
                    <div
                      className={`studio-dropzone ${studioDraggedFileId ? "studio-dropzone-active" : ""}`}
                      onDragOver={(e) => e.preventDefault()}
                      onDrop={(e) => {
                        e.preventDefault();
                        moveFileToFolder(studioDraggedFileId, folder);
                        setStudioDraggedFileId(null);
                      }}
                    >
                      Drop file here to move
                    </div>
                    {studioFiles
                      .filter((file) => file.folder === folder)
                      .map((file) => (
                        <button
                          key={file.id}
                          className={`studio-file ${studioSelectedFileId === file.id ? "studio-file-active" : ""}`}
                          onClick={() => setStudioSelectedFileId(file.id)}
                          draggable
                          onDragStart={() => setStudioDraggedFileId(file.id)}
                          onDragEnd={() => setStudioDraggedFileId(null)}
                        >
                          {file.name}
                        </button>
                      ))}
                  </div>
                ))}
              </aside>
              <div className="studio-editor-wrap">
                <div className="row">
                  <strong>{studioSelectedFile ? `${studioSelectedFile.folder}/${studioSelectedFile.name}` : "No file selected"}</strong>
                </div>
                <div className="row">
                  <input value={studioRenameFileName} onChange={(e) => setStudioRenameFileName(e.target.value)} placeholder="rename selected file" />
                  <button className="action" onClick={renameStudioSelectedFile}>Rename File</button>
                  <select value={studioMoveTargetFolder} onChange={(e) => setStudioMoveTargetFolder(e.target.value)}>
                    {studioFolders.map((folder) => (
                      <option key={`move-${folder}`} value={folder}>{folder}</option>
                    ))}
                  </select>
                  <button className="action" onClick={moveStudioSelectedFile}>Move File</button>
                  <button className="action" onClick={duplicateStudioSelectedFile}>Duplicate File</button>
                </div>
                <div className="row">
                  <button
                    className="action"
                    onClick={() =>
                      downloadJson(`studio-file-${workspaceId}.json`, {
                        file: studioSelectedFile || null
                      })
                    }
                  >
                    Export Current
                  </button>
                  <button className="action" onClick={() => downloadJson(`studio-files-${workspaceId}.json`, studioFiles)}>Export All</button>
                  <button className="action" onClick={deleteStudioSelectedFile}>Delete File</button>
                </div>
                <textarea
                  className={`editor ${studioSelectedFile && studioSelectedFile.name.endsWith(".py") ? "editor-mono" : ""}`}
                  value={studioSelectedFile ? studioSelectedFile.content : ""}
                  onChange={(e) => updateStudioSelectedContent(e.target.value)}
                  placeholder="Select or create a file to begin editing."
                />
              </div>
            </div>
          </section>
          <section className="panel">
            <h2>Studio Operations</h2>
            <div className="row">
              <button className="action" onClick={observe}>Sync Kernel State</button>
              <button className="action" onClick={() => downloadJson(`activity-${workspaceId}.json`, activityLog)}>Export Audit</button>
            </div>
            <pre>{JSON.stringify(activityLog, null, 2)}</pre>
          </section>
        </>
      );
    }
    if (section === "Learning Hall") {
      return (
        <section className="panel">
          <h2>Learning Hall</h2>
          <div className="row">
            <button className="action" onClick={listLessons}>Load Lessons</button>
            <button className="action" onClick={listModules}>Load Modules</button>
          </div>
          {filteredLessons.length > 0 ? (
            <div className="lesson-preview">
              <h3>{filteredLessons[0].title}</h3>
              <div className="preview-body">{renderMarkdownBlocks(filteredLessons[0].body || "")}</div>
            </div>
          ) : (
            <p>No lessons loaded yet.</p>
          )}
        </section>
      );
    }
    return <section className="panel"><h2>Tooling</h2><p>Select a section.</p></section>;
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">Quantum Quackery Atelier<small>FOYER NAVIGATOR</small></div>
        <div className="nav">{NAV_ITEMS.map((item) => <button key={item} className={section === item ? "active" : ""} onClick={() => setSection(item)}>{item}</button>)}</div>
      </aside>
      <main className="content">
        <div className="hero">
          <h1>{section}</h1>
          <p>Operational tooling first. Kernel placement remains workshop-gated for verified steward sessions.</p>
          <div className="statusbar">
            <span className="badge">Role: {role}</span>
            <span className="badge">Workspace: {workspaceId}</span>
            <span className="badge">Admin Gate: {adminVerified ? "verified" : "locked"}</span>
            <span className="badge">Artisan Access: {artisanAccessVerified ? "verified" : "locked"}</span>
            <span className="badge">{busyAction ? `Running: ${busyAction}` : notice}</span>
          </div>
        </div>
        <div className="tools-grid">{renderSectionTools()}</div>
        <section className="panel"><h2>API Output</h2><pre>{output}</pre></section>
      </main>
    </div>
  );
}

