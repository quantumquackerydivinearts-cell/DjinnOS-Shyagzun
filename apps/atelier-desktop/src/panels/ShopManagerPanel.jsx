import React, { useCallback, useEffect, useRef, useState } from "react";

const SECTION_IDS = [
  "digital-products",
  "custom-orders",
  "physical-goods",
  "licenses",
  "consultations",
  "land-assessments",
];

const ITEM_TYPES = ["digital", "service", "physical"];

function formatCents(cents) {
  if (cents == null) return "—";
  return `$${(cents / 100).toFixed(2)}`;
}

// ---------------------------------------------------------------------------
// Artisan view — item list + upload form
// ---------------------------------------------------------------------------

function ArtisanView({ apiBase, authToken, artisanId }) {
  const [items, setItems] = useState([]);
  const [balance, setBalance] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [submitStatus, setSubmitStatus] = useState(null);

  // Upload form state
  const [formTitle, setFormTitle] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [formSection, setFormSection] = useState(SECTION_IDS[0]);
  const [formType, setFormType] = useState(ITEM_TYPES[0]);
  const [formPriceCents, setFormPriceCents] = useState("");
  const [formCurrency, setFormCurrency] = useState("usd");
  const [formTags, setFormTags] = useState("");
  const [formInventory, setFormInventory] = useState("");
  const [formThumbnail, setFormThumbnail] = useState(null);
  const [formFile, setFormFile] = useState(null);

  const thumbnailRef = useRef(null);
  const fileRef = useRef(null);

  const headers = { Authorization: `Bearer ${authToken}` };

  const loadItems = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/artisan/shop/items`, { headers });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setItems(data.items || []);
      setBalance(data.stripe_balance || null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [apiBase, authToken]);

  useEffect(() => {
    if (authToken) loadItems();
  }, [authToken, loadItems]);

  function resetForm() {
    setFormTitle("");
    setFormDescription("");
    setFormSection(SECTION_IDS[0]);
    setFormType(ITEM_TYPES[0]);
    setFormPriceCents("");
    setFormCurrency("usd");
    setFormTags("");
    setFormInventory("");
    setFormThumbnail(null);
    setFormFile(null);
    if (thumbnailRef.current) thumbnailRef.current.value = "";
    if (fileRef.current) fileRef.current.value = "";
    setEditingItem(null);
  }

  function startEdit(item) {
    setFormTitle(item.title);
    setFormDescription(item.description || "");
    setFormSection(item.section_id);
    setFormType(item.item_type);
    setFormPriceCents(String(item.price_cents));
    setFormCurrency(item.currency || "usd");
    setFormTags((item.tags || []).join(", "));
    setFormInventory(item.inventory_count != null ? String(item.inventory_count) : "");
    setEditingItem(item);
    setShowForm(true);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitStatus(null);

    const priceCents = parseInt(formPriceCents, 10);
    if (isNaN(priceCents) || priceCents < 0) {
      setSubmitStatus({ error: "Price must be a non-negative integer (in cents)." });
      return;
    }

    if (editingItem) {
      // PATCH
      const body = {
        title: formTitle,
        description: formDescription,
        price_cents: priceCents,
        tags: formTags.split(",").map((t) => t.trim()).filter(Boolean),
      };
      if (formInventory !== "") body.inventory_count = parseInt(formInventory, 10);
      try {
        const res = await fetch(`${apiBase}/artisan/shop/items/${editingItem.id}`, {
          method: "PATCH",
          headers: { ...headers, "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
        setSubmitStatus({ ok: "Item updated." });
        resetForm();
        setShowForm(false);
        loadItems();
      } catch (err) {
        setSubmitStatus({ error: err.message });
      }
    } else {
      // POST multipart
      const fd = new FormData();
      fd.append("title", formTitle);
      fd.append("description", formDescription);
      fd.append("section_id", formSection);
      fd.append("item_type", formType);
      fd.append("price_cents", priceCents);
      fd.append("currency", formCurrency);
      fd.append(
        "tags_json",
        JSON.stringify(formTags.split(",").map((t) => t.trim()).filter(Boolean))
      );
      if (formInventory !== "") fd.append("inventory_count", parseInt(formInventory, 10));
      if (formThumbnail) fd.append("thumbnail", formThumbnail);
      if (formFile && formType === "digital") fd.append("file", formFile);
      try {
        const res = await fetch(`${apiBase}/artisan/shop/items`, {
          method: "POST",
          headers,
          body: fd,
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
        setSubmitStatus({ ok: "Item created." });
        resetForm();
        setShowForm(false);
        loadItems();
      } catch (err) {
        setSubmitStatus({ error: err.message });
      }
    }
  }

  async function handleToggleActive(item) {
    if (item.is_active) {
      // soft delete
      try {
        const res = await fetch(`${apiBase}/artisan/shop/items/${item.id}`, {
          method: "DELETE",
          headers,
        });
        if (!res.ok) {
          const d = await res.json();
          setError(d.detail || `HTTP ${res.status}`);
          return;
        }
        loadItems();
      } catch (err) {
        setError(err.message);
      }
    } else {
      try {
        const res = await fetch(`${apiBase}/artisan/shop/items/${item.id}`, {
          method: "PATCH",
          headers: { ...headers, "Content-Type": "application/json" },
          body: JSON.stringify({ is_active: true }),
        });
        if (!res.ok) {
          const d = await res.json();
          setError(d.detail || `HTTP ${res.status}`);
          return;
        }
        loadItems();
      } catch (err) {
        setError(err.message);
      }
    }
  }

  async function handleFeaturedToggle(item) {
    try {
      const res = await fetch(`${apiBase}/artisan/shop/items/${item.id}`, {
        method: "PATCH",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ is_featured: !item.is_featured }),
      });
      if (!res.ok) {
        const d = await res.json();
        setError(d.detail || `HTTP ${res.status}`);
        return;
      }
      loadItems();
    } catch (err) {
      setError(err.message);
    }
  }

  const activeItems = items.filter((i) => i.is_active);
  const inactiveItems = items.filter((i) => !i.is_active);

  return (
    <div className="panel-section">
      <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "0.75rem" }}>
        <h3 style={{ margin: 0 }}>Your Shop Items</h3>
        <button
          className="btn"
          onClick={() => {
            resetForm();
            setShowForm((v) => !v);
          }}
        >
          {showForm ? "Cancel" : "+ New Item"}
        </button>
        <button className="btn" onClick={loadItems} disabled={loading}>
          {loading ? "Loading…" : "Refresh"}
        </button>
      </div>

      {error && <div className="output error">{error}</div>}
      {submitStatus?.ok && <div className="output ok">{submitStatus.ok}</div>}
      {submitStatus?.error && <div className="output error">{submitStatus.error}</div>}

      {balance && (
        <div className="output" style={{ marginBottom: "0.75rem" }}>
          <strong>Stripe Balance</strong>
          {(balance.available || []).map((a, i) => (
            <span key={i} style={{ marginLeft: "0.5rem" }}>
              Available: {formatCents(a.amount)} {a.currency?.toUpperCase()}
            </span>
          ))}
          {(balance.pending || []).map((p, i) => (
            <span key={i} style={{ marginLeft: "0.5rem" }}>
              Pending: {formatCents(p.amount)} {p.currency?.toUpperCase()}
            </span>
          ))}
          {balance.error && <span style={{ marginLeft: "0.5rem", color: "var(--warn)" }}>{balance.error}</span>}
        </div>
      )}

      {showForm && (
        <form
          onSubmit={handleSubmit}
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "0.5rem",
            marginBottom: "1rem",
            background: "var(--surface-2, #f5f5f4)",
            padding: "0.75rem",
            borderRadius: "6px",
          }}
        >
          <label style={{ gridColumn: "1 / -1" }}>
            <span>Title *</span>
            <input
              className="input"
              required
              value={formTitle}
              onChange={(e) => setFormTitle(e.target.value)}
            />
          </label>
          <label style={{ gridColumn: "1 / -1" }}>
            <span>Description *</span>
            <textarea
              className="input"
              required
              rows={3}
              value={formDescription}
              onChange={(e) => setFormDescription(e.target.value)}
              style={{ width: "100%", resize: "vertical" }}
            />
          </label>
          {!editingItem && (
            <>
              <label>
                <span>Section</span>
                <select
                  className="input"
                  value={formSection}
                  onChange={(e) => setFormSection(e.target.value)}
                >
                  {SECTION_IDS.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>Type</span>
                <select
                  className="input"
                  value={formType}
                  onChange={(e) => setFormType(e.target.value)}
                >
                  {ITEM_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </label>
            </>
          )}
          <label>
            <span>Price (cents) *</span>
            <input
              className="input"
              type="number"
              min="0"
              required
              value={formPriceCents}
              onChange={(e) => setFormPriceCents(e.target.value)}
              placeholder="e.g. 2500 = $25.00"
            />
          </label>
          {!editingItem && (
            <label>
              <span>Currency</span>
              <input
                className="input"
                value={formCurrency}
                onChange={(e) => setFormCurrency(e.target.value)}
                placeholder="usd"
              />
            </label>
          )}
          <label style={{ gridColumn: "1 / -1" }}>
            <span>Tags (comma-separated)</span>
            <input
              className="input"
              value={formTags}
              onChange={(e) => setFormTags(e.target.value)}
              placeholder="art, print, original"
            />
          </label>
          <label>
            <span>Inventory count (blank = unlimited)</span>
            <input
              className="input"
              type="number"
              min="0"
              value={formInventory}
              onChange={(e) => setFormInventory(e.target.value)}
              placeholder="leave blank for unlimited"
            />
          </label>
          <label>
            <span>Thumbnail</span>
            <input
              ref={thumbnailRef}
              type="file"
              accept="image/*"
              onChange={(e) => setFormThumbnail(e.target.files?.[0] || null)}
            />
          </label>
          {(!editingItem && formType === "digital") && (
            <label style={{ gridColumn: "1 / -1" }}>
              <span>Digital File</span>
              <input
                ref={fileRef}
                type="file"
                onChange={(e) => setFormFile(e.target.files?.[0] || null)}
              />
            </label>
          )}
          <div style={{ gridColumn: "1 / -1" }}>
            <button className="btn" type="submit">
              {editingItem ? "Save Changes" : "Create Item"}
            </button>
          </div>
        </form>
      )}

      {items.length === 0 && !loading && (
        <p style={{ color: "var(--muted, #6b7280)" }}>No items yet. Create your first listing.</p>
      )}

      {activeItems.length > 0 && (
        <>
          <h4 style={{ marginBottom: "0.4rem" }}>Active ({activeItems.length})</h4>
          <ItemTable
            items={activeItems}
            onEdit={startEdit}
            onToggleActive={handleToggleActive}
            onFeaturedToggle={handleFeaturedToggle}
          />
        </>
      )}

      {inactiveItems.length > 0 && (
        <>
          <h4 style={{ marginBottom: "0.4rem", marginTop: "1rem" }}>Inactive ({inactiveItems.length})</h4>
          <ItemTable
            items={inactiveItems}
            onEdit={startEdit}
            onToggleActive={handleToggleActive}
            onFeaturedToggle={handleFeaturedToggle}
          />
        </>
      )}
    </div>
  );
}

function ItemTable({ items, onEdit, onToggleActive, onFeaturedToggle }) {
  return (
    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
      <thead>
        <tr style={{ borderBottom: "1px solid var(--border, #e5e7eb)" }}>
          <th style={{ textAlign: "left", padding: "0.25rem 0.5rem" }}>Title</th>
          <th style={{ textAlign: "left", padding: "0.25rem 0.5rem" }}>Section</th>
          <th style={{ textAlign: "left", padding: "0.25rem 0.5rem" }}>Type</th>
          <th style={{ textAlign: "right", padding: "0.25rem 0.5rem" }}>Price</th>
          <th style={{ textAlign: "center", padding: "0.25rem 0.5rem" }}>Featured</th>
          <th style={{ textAlign: "center", padding: "0.25rem 0.5rem" }}>Inventory</th>
          <th style={{ padding: "0.25rem 0.5rem" }}>Actions</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.id} style={{ borderBottom: "1px solid var(--border, #e5e7eb)" }}>
            <td style={{ padding: "0.3rem 0.5rem" }}>{item.title}</td>
            <td style={{ padding: "0.3rem 0.5rem" }}>{item.section_id}</td>
            <td style={{ padding: "0.3rem 0.5rem" }}>{item.item_type}</td>
            <td style={{ padding: "0.3rem 0.5rem", textAlign: "right" }}>
              {formatCents(item.price_cents)} {item.currency?.toUpperCase()}
            </td>
            <td style={{ padding: "0.3rem 0.5rem", textAlign: "center" }}>
              <input
                type="checkbox"
                checked={!!item.is_featured}
                onChange={() => onFeaturedToggle(item)}
              />
            </td>
            <td style={{ padding: "0.3rem 0.5rem", textAlign: "center" }}>
              {item.inventory_count != null ? item.inventory_count : "∞"}
            </td>
            <td style={{ padding: "0.3rem 0.5rem" }}>
              <button className="btn" style={{ marginRight: "0.4rem" }} onClick={() => onEdit(item)}>
                Edit
              </button>
              <button className="btn" onClick={() => onToggleActive(item)}>
                {item.is_active ? "Deactivate" : "Activate"}
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// ---------------------------------------------------------------------------
// Buyer view — section tabs + item grid + checkout
// ---------------------------------------------------------------------------

function BuyerView({ apiBase }) {
  const [activeSection, setActiveSection] = useState(SECTION_IDS[0]);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedItem, setSelectedItem] = useState(null);
  const [buyerEmail, setBuyerEmail] = useState("");
  const [checkoutStatus, setCheckoutStatus] = useState(null);
  const [quantity, setQuantity] = useState(1);

  const loadSection = useCallback(
    async (section) => {
      setLoading(true);
      setError(null);
      setSelectedItem(null);
      try {
        const url = new URL(`${apiBase}/public/shop/items`);
        url.searchParams.set("workspace_id", "all");
        url.searchParams.set("section_id", section);
        const res = await fetch(url.toString());
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setItems(data.items || []);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    },
    [apiBase]
  );

  useEffect(() => {
    loadSection(activeSection);
  }, [activeSection, loadSection]);

  async function handleCheckout() {
    if (!selectedItem || !buyerEmail) return;
    setCheckoutStatus(null);

    const origin = window.location.origin || "http://localhost:5173";
    try {
      const res = await fetch(`${apiBase}/public/shop/checkout-session`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          item_id: selectedItem.id,
          quantity,
          buyer_email: buyerEmail,
          success_url: `${origin}?shop=success`,
          cancel_url: `${origin}?shop=cancel`,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);

      // In Electron: use shell.openExternal; in browser: window.open
      const checkoutUrl = data.checkout_url;
      if (window.electronAPI?.openExternal) {
        window.electronAPI.openExternal(checkoutUrl);
      } else {
        window.open(checkoutUrl, "_blank", "noopener,noreferrer");
      }
      setCheckoutStatus({ ok: "Checkout opened in your browser." });
    } catch (err) {
      setCheckoutStatus({ error: err.message });
    }
  }

  return (
    <div className="panel-section">
      {/* Section tabs */}
      <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap", marginBottom: "0.75rem" }}>
        {SECTION_IDS.map((s) => (
          <button
            key={s}
            className={`btn ${activeSection === s ? "btn-active" : ""}`}
            onClick={() => setActiveSection(s)}
            style={{ textTransform: "capitalize" }}
          >
            {s.replace(/-/g, " ")}
          </button>
        ))}
      </div>

      {error && <div className="output error">{error}</div>}
      {loading && <div className="output">Loading…</div>}

      {!loading && items.length === 0 && (
        <p style={{ color: "var(--muted, #6b7280)" }}>No items available in this section.</p>
      )}

      {/* Item grid */}
      {!selectedItem && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
            gap: "0.75rem",
          }}
        >
          {items.map((item) => (
            <div
              key={item.id}
              onClick={() => setSelectedItem(item)}
              style={{
                border: "1px solid var(--border, #e5e7eb)",
                borderRadius: "6px",
                padding: "0.75rem",
                cursor: "pointer",
                background: "var(--surface, #fff)",
              }}
            >
              {item.thumbnail_url && (
                <img
                  src={item.thumbnail_url}
                  alt={item.title}
                  style={{ width: "100%", height: "120px", objectFit: "cover", borderRadius: "4px", marginBottom: "0.5rem" }}
                />
              )}
              {item.is_featured && (
                <span style={{ fontSize: "0.7rem", background: "var(--accent, #0f766e)", color: "#fff", padding: "0 4px", borderRadius: "3px", marginBottom: "0.25rem", display: "inline-block" }}>
                  Featured
                </span>
              )}
              <div style={{ fontWeight: "600", marginBottom: "0.25rem" }}>{item.title}</div>
              <div style={{ fontSize: "0.85rem", color: "var(--muted, #6b7280)", marginBottom: "0.25rem" }}>
                {item.section_id}
              </div>
              <div style={{ fontWeight: "700" }}>{formatCents(item.price_cents)}</div>
            </div>
          ))}
        </div>
      )}

      {/* Item detail + checkout */}
      {selectedItem && (
        <div
          style={{
            border: "1px solid var(--border, #e5e7eb)",
            borderRadius: "6px",
            padding: "1rem",
            maxWidth: "500px",
          }}
        >
          <button className="btn" onClick={() => setSelectedItem(null)} style={{ marginBottom: "0.75rem" }}>
            ← Back
          </button>
          {selectedItem.thumbnail_url && (
            <img
              src={selectedItem.thumbnail_url}
              alt={selectedItem.title}
              style={{ width: "100%", maxHeight: "200px", objectFit: "cover", borderRadius: "4px", marginBottom: "0.75rem" }}
            />
          )}
          <h3 style={{ margin: "0 0 0.5rem" }}>{selectedItem.title}</h3>
          <p style={{ color: "var(--muted, #6b7280)", marginBottom: "0.5rem" }}>{selectedItem.description}</p>
          <div style={{ fontWeight: "700", fontSize: "1.1rem", marginBottom: "0.75rem" }}>
            {formatCents(selectedItem.price_cents)} {(selectedItem.currency || "usd").toUpperCase()}
          </div>
          {selectedItem.inventory_count != null && (
            <div style={{ marginBottom: "0.5rem", fontSize: "0.85rem" }}>
              In stock: {selectedItem.inventory_count}
            </div>
          )}
          {(selectedItem.tags || []).length > 0 && (
            <div style={{ marginBottom: "0.75rem" }}>
              {selectedItem.tags.map((t) => (
                <span
                  key={t}
                  style={{
                    display: "inline-block",
                    background: "var(--surface-2, #f5f5f4)",
                    borderRadius: "3px",
                    padding: "0 6px",
                    marginRight: "4px",
                    fontSize: "0.78rem",
                  }}
                >
                  {t}
                </span>
              ))}
            </div>
          )}

          <label style={{ display: "block", marginBottom: "0.5rem" }}>
            <span>Quantity</span>
            <input
              className="input"
              type="number"
              min="1"
              value={quantity}
              onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value, 10) || 1))}
              style={{ width: "80px", marginLeft: "0.5rem" }}
            />
          </label>
          <label style={{ display: "block", marginBottom: "0.75rem" }}>
            <span>Your email *</span>
            <input
              className="input"
              type="email"
              required
              value={buyerEmail}
              onChange={(e) => setBuyerEmail(e.target.value)}
              placeholder="you@example.com"
              style={{ marginLeft: "0.5rem", width: "240px" }}
            />
          </label>

          <button
            className="btn"
            onClick={handleCheckout}
            disabled={!buyerEmail}
          >
            Buy — {formatCents(selectedItem.price_cents * quantity)}
          </button>

          {checkoutStatus?.ok && (
            <div className="output ok" style={{ marginTop: "0.5rem" }}>
              {checkoutStatus.ok}
            </div>
          )}
          {checkoutStatus?.error && (
            <div className="output error" style={{ marginTop: "0.5rem" }}>
              {checkoutStatus.error}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main panel — toggles artisan vs buyer view
// ---------------------------------------------------------------------------

export function ShopManagerPanel({ apiBase, authToken, artisanId }) {
  const isArtisan = Boolean(authToken && artisanId);
  const [mode, setMode] = useState(isArtisan ? "artisan" : "buyer");

  return (
    <div className="panel-section">
      <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "1rem" }}>
        <h2 style={{ margin: 0 }}>QQDA Artisan Marketplace</h2>
        {isArtisan && (
          <div style={{ display: "flex", gap: "0.4rem" }}>
            <button
              className={`btn ${mode === "artisan" ? "btn-active" : ""}`}
              onClick={() => setMode("artisan")}
            >
              My Items
            </button>
            <button
              className={`btn ${mode === "buyer" ? "btn-active" : ""}`}
              onClick={() => setMode("buyer")}
            >
              Browse Shop
            </button>
          </div>
        )}
      </div>

      {mode === "artisan" && isArtisan ? (
        <ArtisanView apiBase={apiBase} authToken={authToken} artisanId={artisanId} />
      ) : (
        <BuyerView apiBase={apiBase} />
      )}

      {!isArtisan && (
        <p style={{ color: "var(--muted, #6b7280)", marginTop: "0.5rem", fontSize: "0.85rem" }}>
          Sign in as a Guild artisan to manage your listings.
        </p>
      )}
    </div>
  );
}
