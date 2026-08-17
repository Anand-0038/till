/**
 * Till night board.
 *
 * Night state accepted from GET /api/night (also POST /api/close and /api/decide).
 * GET /api/export returns the locked local audit envelope:
 * {
 *   shop, date, weekday, status,
 *   sales,
 *   drawer: { expected, counted, variance },
 *   tape: [{ id, agent, tool, text, ts }],
 *   cards: [{ id, kind, amount, why, status, actions[] }],
 *   exceptions: [{ id, kind, mode, note, status }],
 *   packet: { id, status, drawer_total, notes[], filed_by },
 *   audit: [{ agent, tool, decision, detail }],
 *   policy: [{ event, auto, ask }]
 * }
 * { format: "till-close-v1", boundary: "local-process", night: { ... } }
 */
(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);

  const ui = {
    banner: $("#banner"),
    bannerText: $("#banner-text"),
    retry: $("#btn-retry"),
    shopName: $("#shop-name"),
    nightDate: $("#night-date"),
    tapeDate: $("#tape-date"),
    tapeMeta: $("#tape-meta"),
    statusLed: $("#status-led"),
    statusText: $("#status-text"),
    lockStamp: $("#lock-stamp"),
    close: $("#btn-close"),
    reset: $("#btn-reset"),
    decide: $("#btn-decide"),
    export: $("#btn-export"),
    note: $("#toolbar-note"),
    crew: $("#crew"),
    lamp: $("#print-lamp"),
    tape: $("#tape"),
    tapeLines: $("#tape-lines"),
    tapeEmpty: $("#tape-empty"),
    cards: $("#cards"),
    inboxCount: $("#inbox-count"),
    inboxHint: $("#inbox-hint"),
    packet: $("#packet"),
    packetId: $("#packet-id"),
    packetGrid: $("#packet-grid"),
    packetNotes: $("#packet-notes"),
    packetBand: $("#packet-band"),
    packetExportNote: $("#packet-export-note"),
    policyBody: $("#policy-body"),
  };

  const POLICY = [
    ["Tender totals match POS", "file", "—"],
    ["Drawer variance ≤ $10", "accept as variance", "—"],
    ["Drawer variance > $10", "—", "accept"],
    ["Refund ≤ $50 with receipt", "post", "—"],
    ["Refund > $50", "—", "approve / deny"],
    ["Void with manager code", "accept", "—"],
    ["Void without manager code", "—", "accept / reverse"],
    ["No-sale after 21:00", "note on packet", "—"],
  ];

  const DEFAULT_ACTIONS = {
    // Recount/investigate are intentionally not shown until they have a real
    // follow-up workflow. The server only accepts actions the product applies.
    variance: ["accept"],
    refund: ["approve", "deny"],
    void: ["accept", "reverse"],
  };

  const state = {
    night: emptyNight(),
    picks: new Map(),
    printed: new Set(),
    hydrated: false,
    busy: false,
    printQueue: [],
    printing: false,
    retry: loadNight,
  };

  function emptyNight() {
    return {
      shop: "Oak & Bit Hardware",
      date: "",
      weekday: "",
      status: "open",
      sales: null,
      drawer: {},
      tape: [],
      cards: [],
      exceptions: [],
      packet: {},
      audit: [],
      policy: POLICY.map(([event, auto, ask]) => ({ event, auto, ask })),
    };
  }

  function reduceMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function unwrap(raw) {
    if (!raw || typeof raw !== "object") return {};
    if (raw.night && typeof raw.night === "object") return raw.night;
    if (raw.state && typeof raw.state === "object" && !raw.status && !raw.tape) {
      return raw.state;
    }
    if (raw.data && typeof raw.data === "object" && (raw.data.status || raw.data.tape || raw.data.cards)) {
      return raw.data;
    }
    return raw;
  }

  function asArray(v) {
    return Array.isArray(v) ? v : [];
  }

  function str(v) {
    return v == null ? "" : String(v);
  }

  function num(v) {
    if (v == null || v === "") return null;
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  }

  function lineId(line, i) {
    if (line.id != null) return String(line.id);
    if (line.key != null) return String(line.key);
    return `L${i}:${str(line.agent)}:${str(line.tool)}:${str(line.text || line.message || line.detail)}`;
  }

  function cardActions(card) {
    const given = asArray(card.actions).map((a) => String(a).toLowerCase());
    if (given.length) return given;
    const kind = str(card.kind || card.type).toLowerCase();
    if (kind.includes("refund")) return DEFAULT_ACTIONS.refund.slice();
    if (kind.includes("void")) return DEFAULT_ACTIONS.void.slice();
    if (kind.includes("var")) return DEFAULT_ACTIONS.variance.slice();
    return DEFAULT_ACTIONS.variance.slice();
  }

  function cardOpen(card) {
    const s = str(card.status || card.state).toLowerCase();
    if (!s || s === "ask" || s === "open" || s === "pending" || s === "wait") return true;
    return false;
  }

  function normalizeLine(line, i) {
    const text = str(line.text || line.message || line.detail || line.line || "");
    return {
      id: lineId(line, i),
      agent: str(line.agent || line.role || line.actor || line.source || ""),
      tool: str(line.tool || line.call || ""),
      text,
      ts: str(line.ts || line.time || line.at || ""),
    };
  }

  function inferKind(card) {
    const kind = str(card.kind || card.type || card.category);
    if (kind) return kind;
    const id = str(card.id || card.key || "").toUpperCase();
    if (id.startsWith("REF") || id.includes("REFUND")) return "refund";
    if (id.startsWith("VAR") || id.includes("TILL") || id.includes("DRAW")) return "variance";
    if (id.startsWith("VOID")) return "void";
    return "ask";
  }

  function normalizeCard(card, i) {
    const kind = inferKind(card);
    return {
      id: str(card.id || card.key || `ASK-${i + 1}`),
      kind,
      amount: num(card.amount ?? card.value ?? card.dollars),
      why: str(card.why || card.reason || card.detail || card.note || ""),
      status: str(card.status || card.state || "open"),
      actions: cardActions({ ...card, kind }),
      decision: str(card.decision || card.action || card.resolution || ""),
    };
  }

  function pickCards(raw) {
    if (Array.isArray(raw.open_asks)) return raw.open_asks;
    if (Array.isArray(raw.cards)) return raw.cards;
    if (Array.isArray(raw.inbox)) return raw.inbox;
    if (Array.isArray(raw.asks)) return raw.asks;
    if (Array.isArray(raw.open_cards)) return raw.open_cards;
    if (Array.isArray(raw.decisions) && raw.decisions.some((d) => d.kind || d.why || d.amount != null)) {
      return raw.decisions;
    }
    if (Array.isArray(raw.exceptions)) {
      return raw.exceptions.filter((e) => {
        const mode = str(e.mode || e.route || e.disposition).toLowerCase();
        const status = str(e.status || e.state).toLowerCase();
        return mode === "ask" || e.ask === true || status === "open" || status === "ask";
      });
    }
    return [];
  }

  function pickTape(raw) {
    return (
      raw.tape ||
      raw.timeline ||
      raw.log ||
      raw.events ||
      raw.journal ||
      raw.lines ||
      []
    );
  }

  function mapStatus(raw) {
    const s = str(raw.status || raw.night_status || raw.phase || raw.state).toLowerCase();
    if (["locked", "closed", "filed", "done", "complete"].includes(s)) return "locked";
    if (["ask", "interrupt", "waiting", "paused", "inbox", "hold"].includes(s)) return "ask";
    if (["running", "counting", "closing", "working", "busy"].includes(s)) return "running";
    if (["error", "failed"].includes(s)) return "error";
    if (s) return s === "idle" || s === "ready" || s === "seeded" ? "open" : s;
    const cards = pickCards(raw).map(normalizeCard);
    const packet = raw.packet || raw.deposit || {};
    const packetStatus = str(packet.status || packet.state).toLowerCase();
    if (packetStatus === "filed" || packet.id && packetStatus === "locked") return "locked";
    if (cards.some(cardOpen)) return "ask";
    if (asArray(pickTape(raw)).length) return "ask";
    return "open";
  }

  function normalizeNight(rawIn) {
    const raw = unwrap(rawIn);
    const base = emptyNight();
    const drawerRaw = raw.drawer || raw.count || raw.till || {};
    const packetRaw = raw.packet || raw.deposit || {};
    const tape = asArray(pickTape(raw)).map(normalizeLine);
    const cards = pickCards(raw).map(normalizeCard);
    const policy = asArray(raw.policy).length
      ? raw.policy.map((p) => ({
          event: str(p.event || p.rule || p.name),
          auto: str(p.auto || p.safe || "—") || "—",
          ask: str(p.ask || p.human || "—") || "—",
        }))
      : base.policy;

    const packetId =
      packetRaw.id ||
      packetRaw.packet_id ||
      raw.packet_id ||
      raw.deposit_id ||
      "";

    return {
      shop: str(raw.shop || raw.store || raw.shop_name) || base.shop,
      date: str(raw.date || raw.night_date || raw.business_date || ""),
      weekday: str(raw.weekday || raw.day || ""),
      status: mapStatus(raw),
      sales: num(raw.sales ?? raw.sales_count ?? raw.sale_count ?? raw.tickets),
      drawer: {
        expected: num(drawerRaw.expected ?? drawerRaw.pos ?? raw.expected_cash),
        counted: num(drawerRaw.counted ?? drawerRaw.actual ?? raw.counted_cash),
        variance: num(drawerRaw.variance ?? drawerRaw.short ?? raw.variance),
      },
      tape,
      cards,
      exceptions: asArray(raw.exceptions || raw.auto || []).map((e, i) => ({
        id: str(e.id || `EX-${i + 1}`),
        kind: str(e.kind || e.type || ""),
        mode: str(e.mode || e.route || e.disposition || e.lane || "auto"),
        note: str(e.note || e.detail || e.why || e.reason || ""),
        status: str(e.status || e.state || ""),
      })),
      packet: {
        id: str(packetId),
        status: str(packetRaw.status || packetRaw.state || ""),
        drawer_total: num(packetRaw.drawer_total ?? packetRaw.total ?? packetRaw.cash),
        notes: asArray(packetRaw.notes || packetRaw.lines).map((n) =>
          typeof n === "string" ? n : str(n.text || n.note || n.detail)
        ),
        filed_by: str(packetRaw.filed_by || packetRaw.clerk || ""),
      },
      audit: asArray(raw.audit || raw.audit_log || raw.trace).map((a) => ({
        agent: str(a.agent || a.role || ""),
        tool: str(a.tool || ""),
        decision: str(a.decision || a.action || ""),
        detail: str(a.detail || a.text || a.note || ""),
      })),
      policy,
      raw,
    };
  }

  function money(n) {
    if (n == null || Number.isNaN(Number(n))) return "—";
    const v = Number(n);
    const sign = v < 0 ? "−" : "";
    return `${sign}$${Math.abs(v).toFixed(2)}`;
  }

  function varianceWords(v) {
    if (v == null) return "";
    if (v === 0) return "even";
    if (v < 0) return `short ${money(Math.abs(v))}`;
    return `over ${money(v)}`;
  }

  function parseDate(iso) {
    if (!iso) return null;
    const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
    if (!m) return null;
    return new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3])));
  }

  function formatDate(night) {
    const d = parseDate(night.date);
    if (d) {
      const wk = d.toLocaleDateString("en-US", { weekday: "short", timeZone: "UTC" });
      const mon = d.toLocaleDateString("en-US", { month: "short", timeZone: "UTC" }).toUpperCase();
      const day = String(d.getUTCDate()).padStart(2, "0");
      const yr = d.getUTCFullYear();
      return { label: `${wk.toUpperCase()} ${day} ${mon} ${yr}`, iso: night.date, tape: `${wk.toUpperCase()} ${day} ${mon} ${yr}` };
    }
    if (night.weekday && night.date) {
      return { label: `${night.weekday} ${night.date}`, iso: night.date, tape: `${night.weekday} ${night.date}` };
    }
    if (night.weekday) return { label: night.weekday, iso: "", tape: night.weekday.toUpperCase() };
    if (night.date) return { label: night.date, iso: night.date, tape: night.date };
    return { label: "—", iso: "", tape: "NIGHT CLOSE" };
  }

  function detailOf(data) {
    if (!data) return "";
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) {
      return data.detail
        .map((d) => d.msg || d.message || JSON.stringify(d))
        .join("; ");
    }
    return data.error || data.message || "";
  }

  async function api(path, opts = {}) {
    let res;
    try {
      res = await fetch(path, {
        headers: {
          Accept: "application/json",
          ...(opts.body ? { "Content-Type": "application/json" } : {}),
        },
        ...opts,
      });
    } catch (err) {
      const why = err && err.message ? err.message : "network error";
      throw new Error(`Can't reach ${path}. ${why}. Is the shop server running?`);
    }

    const text = await res.text();
    let data = null;
    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        if (!res.ok) {
          throw new Error(`${path} ${res.status}: not JSON. ${text.slice(0, 160)}`);
        }
        throw new Error(`${path} returned ${res.status} (not JSON)`);
      }
    }
    if (!res.ok) {
      const extra = detailOf(data);
      throw new Error(`${path} ${res.status}${extra ? `: ${extra}` : ` ${res.statusText}`}`);
    }
    return data;
  }

  function showError(message, retryFn) {
    state.retry = retryFn || loadNight;
    ui.bannerText.textContent = message;
    ui.banner.hidden = false;
    ui.banner.setAttribute("role", "alert");
  }

  function clearError() {
    ui.banner.hidden = true;
    ui.banner.removeAttribute("role");
  }

  function closeBlocked(night = state.night) {
    if (["locked", "running"].includes(night.status)) return true;
    if (night.status === "ask" && night.cards.some(cardOpen)) return true;
    return false;
  }

  function setBusy(busy, label) {
    state.busy = busy;
    ui.close.disabled = busy || closeBlocked();
    ui.reset.disabled = busy;
    ui.decide.disabled = busy || !canStamp();
    ui.export.disabled = busy || state.night.status !== "locked";
    if (busy) {
      ui.close.setAttribute("aria-busy", "true");
      if (label) ui.note.textContent = label;
    } else {
      ui.close.removeAttribute("aria-busy");
    }
  }

  function setLamp(on) {
    ui.lamp.classList.toggle("on", on);
    ui.lamp.closest(".tape-housing")?.classList.toggle("is-printing", on);
  }

  function looksLikeNight(data) {
    if (!data || typeof data !== "object") return false;
    return Boolean(
      data.status ||
        data.tape ||
        data.cards ||
        data.night ||
        data.packet ||
        data.inbox ||
        data.timeline ||
        data.drawer ||
        data.deposit
    );
  }

  function ledWord(status) {
    if (status === "locked") return "LOCK";
    if (status === "running") return "RUN";
    if (status === "ask") return "ASK";
    if (status === "error") return "ERR";
    return "OPEN";
  }

  function agentLabel(agent) {
    const a = agent.toLowerCase();
    if (a.includes("owner")) return "OWNER";
    if (a.includes("gate")) return "GATE";
    if (a.includes("cashier")) return "CASHIER";
    if (a.includes("auditor")) return "AUDITOR";
    if (a.includes("clerk")) return "CLERK";
    return agent || "CREW";
  }

  function kindLabel(kind) {
    const k = kind.toLowerCase();
    if (k.includes("refund")) return "Refund";
    if (k.includes("void")) return "Void";
    if (k.includes("var") || k.includes("till") || k.includes("drawer")) return "Drawer variance";
    if (k.includes("no-sale") || k.includes("nosale")) return "No-sale";
    return kind || "Ask";
  }

  function actionTone(action) {
    const a = action.toLowerCase();
    if (a === "deny" || a === "reverse") return "deny";
    return "ok";
  }

  function actionLabel(action) {
    return action.replace(/_/g, " ");
  }

  function tapeHas(night, name) {
    return night.tape.some((l) => l.agent.toLowerCase().includes(name));
  }

  function crewStates(night) {
    const open = night.cards.filter(cardOpen);
    const decided = night.cards.some((c) => !cardOpen(c) || c.decision);
    const packetFiled =
      night.status === "locked" ||
      /filed|lock/.test(night.packet.status.toLowerCase()) ||
      (night.status === "locked" && night.packet.id);

    const cashierDone = tapeHas(night, "cashier") || night.drawer.counted != null || night.drawer.variance != null;
    const auditorDone =
      tapeHas(night, "auditor") ||
      night.cards.length > 0 ||
      night.exceptions.length > 0;
    const clerkDone = packetFiled || tapeHas(night, "clerk");

    if (night.status === "open" && !night.tape.length) {
      return {
        cashier: ["wait", "Wait"],
        auditor: ["wait", "Wait"],
        owner: ["wait", "Wait"],
        clerk: ["wait", "Wait"],
      };
    }

    if (night.status === "running") {
      return {
        cashier: cashierDone ? ["done", "Counted"] : ["active", "On the drawer"],
        auditor: cashierDone ? (auditorDone ? ["done", "Policy applied"] : ["active", "Reading exceptions"]) : ["wait", "Wait"],
        owner: ["wait", "Wait"],
        clerk: ["wait", "Blocked"],
      };
    }

    if (night.status === "locked") {
      return {
        cashier: ["done", "Counted"],
        auditor: ["done", "Policy applied"],
        owner: ["done", "Stamped"],
        clerk: ["done", "Filed"],
      };
    }

    return {
      cashier: [cashierDone ? "done" : "wait", cashierDone ? "Counted" : "Wait"],
      auditor: [auditorDone ? "done" : "wait", auditorDone ? "Policy applied" : "Wait"],
      owner: open.length ? ["active", `${open.length} open`] : decided ? ["done", "Stamped"] : ["wait", "Wait"],
      clerk: clerkDone ? ["done", "Filed"] : ["blocked", "Blocked"],
    };
  }

  function renderCrew(night) {
    const map = crewStates(night);
    ui.crew.querySelectorAll("[data-role]").forEach((li) => {
      const role = li.getAttribute("data-role");
      const pair = map[role] || ["wait", "Wait"];
      li.dataset.state = pair[0];
      const job = li.querySelector("[data-job]");
      if (job) job.textContent = pair[1];
    });
  }

  function renderPolicy(night) {
    const rows = night.policy.length ? night.policy : emptyNight().policy;
    ui.policyBody.innerHTML = rows
      .map(
        (r) => `<tr>
          <td data-th="Event">${escapeHtml(r.event)}</td>
          <td data-th="Auto">${escapeHtml(r.auto)}</td>
          <td data-th="Ask">${escapeHtml(r.ask)}</td>
        </tr>`
      )
      .join("");
  }

  function escapeHtml(s) {
    return str(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function appendTapeLine(line, animate) {
    ui.tapeEmpty.hidden = true;
    const row = document.createElement("article");
    row.className = "tape-line" + (animate && !reduceMotion() ? " is-new" : "");
    row.dataset.id = line.id;
    const who = agentLabel(line.agent);
    const tool = line.tool ? `<div class="tape-tool">${escapeHtml(line.tool)}</div>` : "";
    const when = line.ts ? `<div class="tape-tool">${escapeHtml(line.ts)}</div>` : "";
    const body = line.text || "—";
    row.innerHTML = `<div class="tape-agent">${escapeHtml(who)}${when}</div>
      <div class="tape-body">${tool}${escapeHtml(body)}</div>`;
    ui.tapeLines.appendChild(row);
    ui.tape.scrollTop = ui.tape.scrollHeight;
  }

  function pumpPrint() {
    if (state.printing) return;
    const next = state.printQueue.shift();
    if (!next) {
      setLamp(false);
      return;
    }
    state.printing = true;
    setLamp(true);
    appendTapeLine(next, true);
    const delay = reduceMotion() ? 0 : 320;
    window.setTimeout(() => {
      state.printing = false;
      pumpPrint();
    }, delay);
  }

  function enqueueTape(night, instant) {
    const fresh = [];
    night.tape.forEach((line) => {
      if (!state.printed.has(line.id)) {
        state.printed.add(line.id);
        fresh.push(line);
      }
    });
    if (!fresh.length) {
      ui.tapeEmpty.hidden = night.tape.length > 0 || state.printed.size > 0;
      return;
    }
    if (instant || !state.hydrated || reduceMotion()) {
      fresh.forEach((line) => appendTapeLine(line, false));
      return;
    }
    state.printQueue.push(...fresh);
    pumpPrint();
  }

  function resetTape() {
    state.printed.clear();
    state.printQueue = [];
    state.printing = false;
    state.hydrated = false;
    ui.tapeLines.innerHTML = "";
    ui.tapeEmpty.hidden = false;
    setLamp(false);
  }

  function canStamp() {
    const open = state.night.cards.filter(cardOpen);
    if (!open.length || state.busy || state.night.status === "locked") return false;
    return open.every((c) => state.picks.has(c.id));
  }

  function renderCards(night) {
    const cards = night.cards;
    const open = cards.filter(cardOpen);
    ui.inboxCount.textContent = `${open.length} open`;

    if (!cards.length) {
      const msg =
        night.status === "locked"
          ? "Night is locked. No open asks."
          : night.status === "open"
            ? "Nothing to stamp. Run night close."
            : "No asks. Clerk can file.";
      ui.cards.innerHTML = `<p class="empty-card">${msg}</p>`;
      ui.inboxHint.textContent =
        night.status === "locked"
          ? "See the packet."
          : "Safe work stays off this desk.";
      ui.decide.disabled = true;
      return;
    }

    ui.cards.innerHTML = "";
    cards.forEach((card, i) => {
      const openCard = cardOpen(card);
      const picked = state.picks.get(card.id) || "";
      const art = document.createElement("article");
      art.className = "card" + (openCard ? "" : " is-closed");
      art.dataset.id = card.id;

      const why =
        card.why ||
        (card.kind.toLowerCase().includes("refund")
          ? "Over the $50 cap. Needs a stamp."
          : "Over the $10 cap. Needs a stamp.");

      const amt = card.amount != null ? money(card.amount) : "";
      const actions = openCard
        ? `<div class="card-actions">${card.actions
            .map((a) => {
              const pressed = picked === a ? "true" : "false";
              return `<button type="button" class="btn-action" data-id="${escapeHtml(card.id)}" data-action="${escapeHtml(a)}" data-tone="${actionTone(a)}" aria-pressed="${pressed}">${escapeHtml(actionLabel(a))}</button>`;
            })
            .join("")}</div>`
        : "";
      const stamp = !openCard
        ? `<span class="card-stamp">${escapeHtml(card.decision || card.status || "stamped")}</span>`
        : picked
          ? `<span class="card-stamp">${escapeHtml(picked)}</span>`
          : "";

      art.innerHTML = `
        <div class="card-top">
          <span>${escapeHtml(card.id)}</span>
          <span>${String(i + 1).padStart(2, "0")} / ${String(cards.length).padStart(2, "0")}</span>
        </div>
        <h3>${escapeHtml(kindLabel(card.kind))}</h3>
        ${amt ? `<p class="card-amt">${escapeHtml(amt)}</p>` : ""}
        <p class="card-why">${escapeHtml(why)}</p>
        ${actions}
        ${stamp}`;
      ui.cards.appendChild(art);
    });

    if (night.status === "locked") {
      ui.inboxHint.textContent = "All stamped. Packet is below.";
    } else if (open.length && canStamp()) {
      ui.inboxHint.textContent = "Ready to stamp. Clerk files after this.";
    } else if (open.length) {
      ui.inboxHint.textContent = "Pick an action on each card. Deposit stays in the tray.";
    } else {
      ui.inboxHint.textContent = "Asks are closed. Clerk can file.";
    }

    ui.decide.disabled = state.busy || !canStamp();
  }

  function renderPacket(night) {
    const locked = night.status === "locked";
    const open = night.cards.filter(cardOpen).length;
    ui.export.disabled = state.busy || !locked;
    ui.packetExportNote.textContent = locked ? "Local JSON copy" : "Available after lock";
    const pid =
      night.packet.id ||
      (locked ? "DEP-2026-08-11" : "");

    ui.packet.classList.toggle("is-locked", locked);
    ui.packetId.textContent = pid || "Not made";

    const cells = [];
    if (night.drawer.counted != null) {
      cells.push(["Counted", money(night.drawer.counted)]);
    }
    if (night.drawer.expected != null) {
      cells.push(["Expected", money(night.drawer.expected)]);
    }
    if (night.drawer.variance != null) {
      cells.push(["Variance", varianceWords(night.drawer.variance) || money(night.drawer.variance)]);
    }
    if (night.packet.drawer_total != null) {
      cells.push(["Packet total", money(night.packet.drawer_total)]);
    }
    if (night.sales != null) {
      cells.push(["Sales", String(night.sales)]);
    }
    if (night.packet.filed_by) {
      cells.push(["Filed by", night.packet.filed_by]);
    }
    if (locked) {
      cells.push(["Status", "LOCKED"]);
    }

    ui.packetGrid.innerHTML = cells
      .map(
        ([k, v]) => `<div><dt>${escapeHtml(k)}</dt><dd>${escapeHtml(v)}</dd></div>`
      )
      .join("");

    const notes = [];
    const hasRun = night.tape.length > 0 || night.status !== "open" || Boolean(night.packet.id);
    if (hasRun) {
      night.exceptions.forEach((e) => {
        if (e.note) notes.push(e.note);
        else if (e.kind) notes.push(`${e.kind}${e.mode ? ` · ${e.mode}` : ""}`);
      });
      night.packet.notes.forEach((n) => n && notes.push(n));
      night.audit.forEach((a) => {
        const bits = [a.agent, a.tool, a.decision, a.detail].filter(Boolean);
        if (bits.length) notes.push(bits.join(" · "));
      });
      night.cards
        .filter((c) => !cardOpen(c) || c.decision)
        .forEach((c) => {
          notes.push(`${c.id} · ${c.decision || c.status}`);
        });
    }

    const unique = [];
    notes.forEach((n) => {
      if (!unique.includes(n)) unique.push(n);
    });
    ui.packetNotes.innerHTML = unique.map((n) => `<li>${escapeHtml(n)}</li>`).join("");

    if (locked) {
      ui.packetBand.textContent = pid ? `Filed · ${pid}` : "Filed · LOCKED";
    } else if (open) {
      ui.packetBand.textContent = `Held · ${open} card${open === 1 ? "" : "s"} open`;
    } else if (night.status === "ask" || night.tape.length) {
      ui.packetBand.textContent = "Held in the tray";
    } else {
      ui.packetBand.textContent = "Not made";
    }
  }

  function renderChrome(night) {
    const when = formatDate(night);
    ui.shopName.textContent = night.shop;
    ui.nightDate.textContent = when.label;
    if (when.iso) ui.nightDate.setAttribute("datetime", when.iso);
    else ui.nightDate.removeAttribute("datetime");
    ui.tapeDate.textContent = when.tape;
    const salesBit = night.sales != null ? `${night.sales} SALES · ` : "";
    ui.tapeMeta.textContent = `${salesBit}1 DRAWER`;

    ui.statusLed.dataset.status = night.status;
    ui.statusText.textContent = ledWord(night.status);
    ui.lockStamp.hidden = night.status !== "locked";

    const locked = night.status === "locked";
    const openAsks = night.cards.some(cardOpen);
    ui.close.disabled = state.busy || closeBlocked(night);
    ui.close.textContent = locked
      ? "Night locked"
      : night.status === "ask" && openAsks
        ? "Waiting on stamps"
        : "Run night close";

    if (!state.busy) {
      if (locked) ui.note.textContent = "Packet filed. Night locked.";
      else if (openAsks) ui.note.textContent = "Crew stopped. Asks need a stamp.";
      else if (night.status === "running") ui.note.textContent = "Crew is on the floor.";
      else ui.note.textContent = "Strands crew: cashier counts. Auditor applies policy. You stamp the asks. Clerk files.";
    }
  }

  function applyNight(raw, opts = {}) {
    const night = normalizeNight(raw);
    state.night = night;

    const openIds = new Set(night.cards.filter(cardOpen).map((c) => c.id));
    [...state.picks.keys()].forEach((id) => {
      if (!openIds.has(id)) state.picks.delete(id);
    });

    renderChrome(night);
    renderCrew(night);
    renderPolicy(night);
    renderCards(night);
    renderPacket(night);
    enqueueTape(night, opts.instant);
    state.hydrated = true;
    return night;
  }

  async function loadNight() {
    clearError();
    try {
      const data = await api("/api/night");
      applyNight(data, { instant: !state.hydrated });
    } catch (err) {
      showError(err.message, loadNight);
    }
  }

  async function runClose() {
    if (state.busy) return;
    clearError();
    setBusy(true, "Crew is on the floor.");
    ui.statusLed.dataset.status = "running";
    ui.statusText.textContent = "RUN";
    setLamp(true);
    try {
      const data = await api("/api/close", {
        method: "POST",
        body: JSON.stringify({}),
      });
      const night = applyNight(looksLikeNight(data) ? data : await api("/api/night"));
      if (night.status !== "locked" && night.status !== "ask") {
        applyNight(await api("/api/night"));
      }
    } catch (err) {
      showError(err.message, runClose);
      try {
        const data = await api("/api/night");
        applyNight(data);
      } catch {
        ui.statusLed.dataset.status = "error";
        ui.statusText.textContent = "ERR";
      }
    } finally {
      setBusy(false);
      if (!state.printQueue.length && !state.printing) setLamp(false);
    }
  }

  async function stampDecisions() {
    if (state.busy || !canStamp()) return;
    const decisions = state.night.cards
      .filter(cardOpen)
      .map((c) => ({ id: c.id, action: state.picks.get(c.id) }))
      .filter((d) => d.action);
    if (!decisions.length) return;

    clearError();
    setBusy(true, "Stamping. Clerk stands by.");
    try {
      const data = await api("/api/decide", {
        method: "POST",
        body: JSON.stringify({ decisions }),
      });
      applyNight(looksLikeNight(data) ? data : await api("/api/night"));
    } catch (err) {
      showError(err.message, stampDecisions);
      try {
        applyNight(await api("/api/night"));
      } catch {
        /* keep current board */
      }
    } finally {
      setBusy(false);
      if (!state.printQueue.length && !state.printing) setLamp(false);
    }
  }

  async function resetNight() {
    if (state.busy) return;
    clearError();
    setBusy(true, "Reopening the drawer.");
    try {
      await api("/api/reset", {
        method: "POST",
        body: JSON.stringify({}),
      });
      state.picks.clear();
      resetTape();
      const data = await api("/api/night");
      applyNight(data, { instant: true });
    } catch (err) {
      showError(err.message, resetNight);
    } finally {
      setBusy(false);
    }
  }

  async function exportAudit() {
    if (state.busy || state.night.status !== "locked") return;
    clearError();
    ui.export.disabled = true;
    ui.export.setAttribute("aria-busy", "true");
    ui.packetExportNote.textContent = "Preparing local copy…";
    try {
      const data = await api("/api/export");
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const href = URL.createObjectURL(blob);
      const link = document.createElement("a");
      const packetId = data?.night?.packet?.id || "close";
      link.href = href;
      link.download = `till-${packetId}.json`;
      document.body.append(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(href), 0);
      ui.packetExportNote.textContent = "Saved locally. No cloud upload.";
    } catch (err) {
      showError(err.message, exportAudit);
      ui.packetExportNote.textContent = "Export failed. Retry when ready.";
    } finally {
      ui.export.removeAttribute("aria-busy");
      ui.export.disabled = state.night.status !== "locked";
    }
  }

  ui.close.addEventListener("click", runClose);
  ui.reset.addEventListener("click", resetNight);
  ui.decide.addEventListener("click", stampDecisions);
  ui.export.addEventListener("click", exportAudit);
  ui.retry.addEventListener("click", () => {
    clearError();
    state.retry();
  });

  ui.cards.addEventListener("click", (ev) => {
    const btn = ev.target.closest("[data-action]");
    if (!btn || !ui.cards.contains(btn)) return;
    const id = btn.getAttribute("data-id");
    const action = btn.getAttribute("data-action");
    if (!id || !action) return;
    if (state.picks.get(id) === action) state.picks.delete(id);
    else state.picks.set(id, action);
    renderCards(state.night);
    renderChrome(state.night);
  });

  if (window.location.protocol === "file:") {
    showError(
      "Open this board from the Till server: uvicorn till.main:app --port 8000 then http://127.0.0.1:8000"
    );
    return;
  }

  loadNight();
})();
