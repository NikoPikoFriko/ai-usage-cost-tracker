(function () {
  const state = {
    channel: "all",
    gapOnly: false,
    unpricedOnly: false,
    q: "",
    pin: null,
  };
  let data = { sessions: [], events: [], gaps: [], totals: {}, meta: {} };

  const fmtInt = (n) => (n == null ? "—" : Number(n).toLocaleString());
  const sessionTitle = (id) =>
    (data.sessions.find((s) => s.session_id === id) || {}).title || id;

  function filteredEvents() {
    return (data.events || []).filter((e) => {
      if (state.channel !== "all" && e.channel !== state.channel) return false;
      if (state.gapOnly && e.grade !== "GAP") return false;
      if (state.unpricedOnly && e.cost_usd != null) return false;
      if (state.pin && e.session_id !== state.pin) return false;
      if (state.q) {
        const hay = [
          e.label,
          e.model,
          e.session_id,
          e.channel,
          sessionTitle(e.session_id),
        ]
          .join(" ")
          .toLowerCase();
        if (!hay.includes(state.q.toLowerCase())) return false;
      }
      return true;
    });
  }

  function filteredSessions() {
    const ev = filteredEvents();
    let sessions = (data.sessions || []).filter((s) => {
      if (state.channel !== "all" && s.channel !== state.channel) return false;
      if (state.pin && s.session_id !== state.pin) return false;
      if (state.q) {
        const hay = [s.title, s.session_id, s.channel, (s.model_mix || []).join(" ")]
          .join(" ")
          .toLowerCase();
        if (!hay.includes(state.q.toLowerCase()) && !ev.some((e) => e.session_id === s.session_id))
          return false;
      }
      if ((state.gapOnly || state.unpricedOnly || state.q) && !state.pin) {
        return ev.some((e) => e.session_id === s.session_id);
      }
      return true;
    });

    sessions = sessions.map((s) => {
      const vis = filteredEvents().filter((e) => e.session_id === s.session_id);
      const use =
        state.gapOnly || state.unpricedOnly || state.q || state.pin
          ? vis
          : (data.events || []).filter((e) => e.session_id === s.session_id);
      const priced = use.filter((e) => e.cost_usd != null);
      const cost = priced.reduce((a, e) => a + e.cost_usd, 0);
      return {
        ...s,
        tokens_total: use.reduce(
          (a, e) => a + (e.tokens_in || 0) + (e.tokens_out || 0),
          0
        ),
        events_n: use.length,
        cost_usd: priced.length ? cost : use.length ? null : s.cost_usd,
        coverage: priced.length + "/" + use.length,
        grade: use.some((e) => e.grade === "GAP") ? "GAP" : s.grade,
      };
    });

    sessions.sort((a, b) => {
      if (a.cost_usd == null && b.cost_usd == null) return 0;
      if (a.cost_usd == null) return 1;
      if (b.cost_usd == null) return -1;
      return b.cost_usd - a.cost_usd;
    });
    return sessions;
  }

  function badge(ch) {
    const label = ch === "chatgpt" ? "ChatGPT" : "Codex";
    return '<span class="badge badge-' + ch + '">' + label + "</span>";
  }

  function renderTotals(events, sessions) {
    const cost = events.reduce((a, e) => a + (e.cost_usd == null ? 0 : e.cost_usd), 0);
    const tin = events.reduce((a, e) => a + (e.tokens_in || 0), 0);
    const tout = events.reduce((a, e) => a + (e.tokens_out || 0), 0);
    const unpriced = events.filter((e) => e.cost_usd == null).length;
    const pct = events.length ? Math.round((100 * unpriced) / events.length) : 0;
    document.querySelector("#stat-cost b").textContent = "$" + cost.toFixed(4);
    document.querySelector("#stat-tokens b").textContent = fmtInt(tin + tout);
    document.querySelector("#stat-split b").textContent =
      fmtInt(tin) + " / " + fmtInt(tout);
    document.querySelector("#stat-sessions b").textContent = String(sessions.length);
    document.querySelector("#stat-events b").textContent = String(events.length);
    document.querySelector("#stat-gap b").textContent = pct + "%";
    const cov = events.length
      ? Math.round((100 * (events.length - unpriced)) / events.length)
      : 0;
    document.querySelector("#coverage-bar i").style.width = cov + "%";
  }

  function renderSessions(sessions) {
    const tb = document.getElementById("session-tbody");
    document.getElementById("session-count").textContent = sessions.length + " shown";
    document.getElementById("session-empty").hidden = sessions.length > 0;
    tb.innerHTML = sessions
      .map((s) => {
        const costCell =
          s.cost_usd == null
            ? '<td class="gap-cell">GAP</td>'
            : "<td>$" + Number(s.cost_usd).toFixed(4) + "</td>";
        const sel = state.pin === s.session_id ? " is-selected" : "";
        return (
          '<tr class="session-row' +
          sel +
          '" data-session-id="' +
          s.session_id +
          '">' +
          "<td>" +
          badge(s.channel) +
          "</td>" +
          "<td>" +
          (s.title || "") +
          ' <span class="mono muted">' +
          s.session_id.slice(0, 8) +
          "</span></td>" +
          '<td class="hi-only mono">' +
          ((s.started_at || "").replace("T", " ").slice(0, 16) || "—") +
          "</td>" +
          "<td>" +
          s.events_n +
          "</td>" +
          "<td>" +
          fmtInt(s.tokens_total) +
          "</td>" +
          costCell +
          '<td class="grade-' +
          s.grade +
          '">' +
          s.grade +
          "</td>" +
          '<td class="hi-only">' +
          (s.model_mix || []).join(" · ") +
          "</td>" +
          '<td class="hi-only">' +
          (s.coverage || "") +
          "</td>" +
          "</tr>"
        );
      })
      .join("");
    tb.querySelectorAll(".session-row").forEach((row) => {
      row.addEventListener("click", () => {
        state.pin = row.getAttribute("data-session-id");
        render();
      });
    });
    const pinBanner = document.getElementById("session-pin-banner");
    if (state.pin) {
      pinBanner.hidden = false;
      document.getElementById("pin-label").textContent = sessionTitle(state.pin);
    } else pinBanner.hidden = true;
  }

  function renderEvents(events) {
    const tb = document.getElementById("event-tbody");
    document.getElementById("event-scope").textContent = state.pin
      ? "Session: " + sessionTitle(state.pin)
      : "Showing: all events (filtered)";
    document.getElementById("event-empty").hidden = events.length > 0;
    const sorted = events.slice().sort((a, b) => (b.ts || "").localeCompare(a.ts || ""));
    tb.innerHTML = sorted
      .map((e) => {
        const costCell =
          e.cost_usd == null
            ? '<td class="gap-cell">GAP</td>'
            : "<td>$" + Number(e.cost_usd).toFixed(4) + "</td>";
        return (
          "<tr>" +
          '<td class="mono">' +
          ((e.ts || "").replace("T", " ").slice(0, 19) || "—") +
          "</td>" +
          "<td>" +
          badge(e.channel) +
          "</td>" +
          '<td class="unpin-only">' +
          (state.pin ? "" : sessionTitle(e.session_id)) +
          "</td>" +
          "<td>" +
          (e.label || "") +
          "</td>" +
          '<td class="hi-only">' +
          (e.role || "") +
          "</td>" +
          '<td class="mono">' +
          (e.model || "") +
          "</td>" +
          "<td>" +
          fmtInt(e.tokens_in) +
          "</td>" +
          "<td>" +
          fmtInt(e.tokens_out) +
          "</td>" +
          '<td class="hi-only">' +
          fmtInt(e.tokens_cached) +
          "</td>" +
          costCell +
          '<td class="grade-' +
          e.grade +
          '">' +
          e.grade +
          "</td>" +
          "</tr>"
        );
      })
      .join("");
    document.querySelectorAll(".unpin-only").forEach((el) => {
      if (el.tagName === "TH" || el.tagName === "TD")
        el.style.display = state.pin ? "none" : "";
    });
  }

  function renderGaps(events) {
    const unpriced = events.filter((e) => e.cost_usd == null);
    const ul = document.getElementById("gap-list");
    const ok = document.getElementById("gaps-ok");
    const serial = document.getElementById("gap-serial-action");
    document.getElementById("gap-count").textContent = unpriced.length
      ? unpriced.length + " unpriced"
      : "clear";
    if (!unpriced.length) {
      ul.innerHTML = "";
      ok.hidden = false;
      serial.textContent = "";
      return;
    }
    ok.hidden = true;
    const action =
      (data.gaps && data.gaps[0] && data.gaps[0].action) ||
      "Add model rates then reprice";
    ul.innerHTML =
      '<li><strong class="gap-cell">G-NO-PRICE</strong> × ' +
      unpriced.length +
      " — " +
      action +
      "</li>";
    serial.textContent = "One next step: " + action;
  }

  function render() {
    const events = filteredEvents();
    const sessions = filteredSessions();
    renderTotals(events, sessions);
    renderSessions(sessions);
    renderEvents(events);
    renderGaps(events);
    const bits = [data.meta && data.meta.data_class ? data.meta.data_class : "DATA"];
    if (state.channel !== "all") bits.push(state.channel);
    if (state.gapOnly) bits.push("GAP");
    if (state.unpricedOnly) bits.push("unpriced");
    if (state.pin) bits.push("pin");
    if (state.q) bits.push('"' + state.q + '"');
    document.getElementById("filter-summary").textContent = bits.join(" · ");
  }

  function bind() {
    document.querySelectorAll('input[name="ch"]').forEach((r) => {
      r.addEventListener("change", () => {
        state.channel = r.value;
        render();
      });
    });
    document.getElementById("gap-only").addEventListener("change", (e) => {
      state.gapOnly = e.target.checked;
      render();
    });
    document.getElementById("unpriced-only").addEventListener("change", (e) => {
      state.unpricedOnly = e.target.checked;
      render();
    });
    document.getElementById("filter-search").addEventListener("input", (e) => {
      state.q = e.target.value.trim();
      render();
    });
    document.getElementById("btn-clear-filters").addEventListener("click", () => {
      state.channel = "all";
      state.gapOnly = false;
      state.unpricedOnly = false;
      state.q = "";
      state.pin = null;
      document.querySelector('input[name="ch"][value="all"]').checked = true;
      document.getElementById("gap-only").checked = false;
      document.getElementById("unpriced-only").checked = false;
      document.getElementById("filter-search").value = "";
      render();
    });
    document.getElementById("btn-clear-pin").addEventListener("click", () => {
      state.pin = null;
      render();
    });
    document.getElementById("toggle-low-res").addEventListener("change", (e) => {
      document.body.classList.toggle("low-res", e.target.checked);
    });
    document.getElementById("stat-gap").addEventListener("click", () => {
      document.getElementById("gap-only").checked = true;
      state.gapOnly = true;
      document.getElementById("panel-gaps").scrollIntoView({ behavior: "smooth" });
      render();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        state.pin = null;
        render();
      }
    });
  }

  async function load() {
    const badge = document.getElementById("data-badge");
    const sync = document.getElementById("sync-line");
    try {
      const res = await fetch("data.json", { cache: "no-store" });
      if (!res.ok) throw new Error("HTTP " + res.status);
      data = await res.json();
      const cls = (data.meta && data.meta.data_class) || "LIVE";
      badge.className = cls === "LIVE" ? "live-badge" : "mock-badge";
      badge.textContent = cls;
      sync.textContent =
        "Last export: " +
        ((data.meta && data.meta.generated_at) || "—") +
        " · " +
        ((data.meta && data.meta.note) || "local-first");
      render();
    } catch (err) {
      document.getElementById("load-error").hidden = false;
      document.getElementById("load-error").textContent =
        "Could not load data.json. Run: python -m src.cli ingest codex-jsonl  then open via python -m src.cli serve  (file:// may block fetch). " +
        err;
    }
  }

  bind();
  load();
})();
