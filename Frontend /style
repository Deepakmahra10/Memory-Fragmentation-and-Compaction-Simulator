/* =========================================================
   Memory Fragmentation & Compaction Simulator — script.js

   Python is authoritative for process state and all memory algorithms.
   This file only sends actions to the API and renders returned state.
   ========================================================= */

(() => {
  "use strict";

  /* ---------- Config ---------- */
  const STEP_MS = 650; // delay between processes moving during compaction
  const MAX_LOG = 80; // max entries kept in the event log
  const MIN_TOTAL = 64;
  const MAX_TOTAL = 4096;
  const API_BASE =
    window.location.port === "5501" ? "http://127.0.0.1:8000" : "";

  const ALGOS = {
    first: {
      label: "First fit",
      hint: "Takes the first hole (scanning from address 0) that is big enough. Fast, but it keeps chipping small holes into the front of memory.",
    },
    best: {
      label: "Best fit",
      hint: "Takes the smallest hole that still fits. Wastes the least per request, but leaves many tiny slivers nobody can use.",
    },
    worst: {
      label: "Worst fit",
      hint: "Takes the largest hole, hoping the leftover stays big enough to reuse. Often breaks up the big hole you need later.",
    },
  };

  /* ---------- State ---------- */
  const state = {
    total: 512,
    procs: [], // [{ pid, name, start, size, color }]
    holes: [],
    stats: { used: 0, free: 512, largest: 512, frag: 0 },
    preview: null,
    previewSize: null,
    algo: "first",
    busy: false, // true while compaction is animating
    lastCompaction: null, // { moved, kb, holesBefore, holesAfter }
    log: [], // [{ time, type, msg }]
  };

  /* ---------- DOM ---------- */
  const $ = (id) => document.getElementById(id);
  const els = {
    total: $("totalMem"),
    setSize: $("btnSetSize"),
    algoGroup: $("algoGroup"),
    algoHint: $("algoHint"),
    name: $("procName"),
    size: $("procSize"),
    chips: $("sizeChips"),
    alloc: $("btnAlloc"),
    auto: $("autoCompact"),
    compact: $("btnCompact"),
    demo: $("btnDemo"),
    reset: $("btnReset"),
    strip: $("memStrip"),
    ruler: $("ruler"),
    caption: $("mapCaption"),
    banner: $("banner"),
    statTotal: $("statTotal"),
    statUsed: $("statUsed"),
    statUsedPct: $("statUsedPct"),
    statFree: $("statFree"),
    statFreePct: $("statFreePct"),
    statHoles: $("statHoles"),
    statLargest: $("statLargest"),
    meter: $("meter"),
    meterTrack: $("meterTrack"),
    meterFill: $("meterFill"),
    fragValue: $("fragValue"),
    fragFormula: $("fragFormula"),
    fragNote: $("fragNote"),
    procBody: $("procBody"),
    holeBody: $("holeBody"),
    log: $("log"),
    clearLog: $("btnClearLog"),
  };

  // pid -> DOM node for process blocks (kept so CSS transitions can animate moves)
  const blockEls = new Map();

  /* ---------- Small helpers ---------- */
  const esc = (s) =>
    String(s).replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    );
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const sortedProcs = () => [...state.procs].sort((a, b) => a.start - b.start);
  const colorFor = (pid) =>
    `hsl(${Math.round((pid * 137.508) % 360)}, 62%, 66%)`; // golden angle = distinct hues
  const plural = (n, word) =>
    `${n} ${n === 1 ? word : word === "process" ? "processes" : `${word}s`}`;
  const readJson = async (response) => {
    const body = await response.text();
    let result;
    try {
      result = JSON.parse(body);
    } catch {
      throw new Error(
        body
          ? `API returned a non-JSON response (HTTP ${response.status}). Start the Python server with "python -m backend.server".`
          : `API returned an empty response (HTTP ${response.status}). Start the Python server with "python -m backend.server".`,
      );
    }
    if (!response.ok)
      throw new Error(result.error || `Request failed (${response.status}).`);
    return result;
  };
  const fetchApi = async (url, options) => {
    try {
      return await fetch(url, options);
    } catch (error) {
      if (error instanceof TypeError) {
        throw new Error(
          'Cannot reach the Python API. Start it with "python -m backend.server" from the project folder.',
        );
      }
      throw error;
    }
  };
  const api = async (action, data = {}) => {
    const response = await fetchApi(`${API_BASE}/api/action`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, ...data }),
    });
    return readJson(response);
  };
  const applyState = (memory) => {
    state.total = memory.total;
    els.total.value = memory.total;
    state.algo = memory.strategy;
    state.procs = memory.processes.map((proc) => ({
      ...proc,
      color: colorFor(proc.pid),
    }));
    state.holes = memory.holes;
    state.stats = memory.stats;
    state.preview = memory.preview;
    state.previewSize = null;
  };
  const safe = async (run) => {
    try {
      await run();
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      addLog("err", `Python API error: ${message}`);
      showBanner("warn", `Could not complete the request: ${message}`);
      render();
    }
  };

  /* ---------- Allocation preview ---------- */
  function previewHole() {
    if (state.busy) return null;
    const size = parseInt(els.size.value, 10);
    if (!Number.isInteger(size) || size < 1) return null;
    return state.previewSize === size ? state.preview : null;
  }

  async function refreshPreview() {
    if (state.busy) return;
    const size = parseInt(els.size.value, 10);
    if (!Number.isInteger(size) || size < 1) {
      state.preview = null;
      state.previewSize = null;
      render();
      return;
    }
    const response = await fetchApi(
      `${API_BASE}/api/state?size=${encodeURIComponent(size)}`,
    );
    const result = await readJson(response);
    if (state.busy || parseInt(els.size.value, 10) !== size) return;
    applyState(result.state);
    state.previewSize = size;
    render();
  }

  /* =========================================================
     2. ACTIONS
     ========================================================= */

  async function initMemory(total) {
    const response = await api("reset", { total });
    applyState(response.state);
    state.lastCompaction = null;
    state.log = [];
    for (const node of blockEls.values()) node.remove();
    blockEls.clear();
    hideBanner();
    renderRuler();
    addLog("info", `Memory ready: ${state.total} KB, one free hole.`);
    render();
  }

  function setTotalFromInput() {
    if (state.busy) return;
    let v = parseInt(els.total.value, 10);
    if (!Number.isInteger(v)) v = 512;
    v = Math.min(MAX_TOTAL, Math.max(MIN_TOTAL, v));
    els.total.value = v;
    void safe(() => initMemory(v));
  }

  async function allocate(size, name) {
    if (state.busy) return;
    hideBanner();

    const response = await api("allocate", { size, name });
    applyState(response.state);
    state.previewSize = size;
    const outcome = response.outcome;
    if (outcome.result === "allocated") {
      const proc = outcome.process;
      addLog(
        "ok",
        `${ALGOS[state.algo].label}: placed ${proc.name} (${size} KB) at address ${proc.start}.`,
      );
      render();
      return;
    }

    const s = outcome.stats;

    if (outcome.result === "fragmented") {
      addLog(
        "err",
        `Request of ${size} KB failed. ${s.free} KB is free in total, but the largest hole is only ${s.largest} KB.`,
      );

      if (els.auto.checked) {
        addLog("info", "Auto-compact is on: compacting, then retrying.");
        await compact();
        await allocate(size, name);
        return;
      }

      showBanner(
        "error",
        `External fragmentation: ${size} KB requested, ${s.free} KB free in total, but the largest hole is only ${s.largest} KB. Compaction merges the holes so this request can fit.`,
        {
          label: "Compact and retry",
          run: async () => {
            await compact();
            hideBanner();
            await allocate(size, name);
          },
        },
      );
    } else {
      addLog(
        "err",
        `Out of memory: ${size} KB needed, only ${s.free} KB free. Compaction cannot help; free a process first.`,
      );
      showBanner(
        "warn",
        `Not enough memory: ${size} KB needed but only ${s.free} KB is free in total. Free a process to make room.`,
      );
    }
    render();
  }

  async function freeProcess(pid) {
    if (state.busy) return;
    const response = await api("free", { pid });
    const proc = response.process;
    applyState(response.state);
    hideBanner();
    addLog(
      "info",
      `Freed ${proc.name} (${proc.size} KB) from address ${proc.start}.`,
    );
    render();
  }

  /** Slide every process to the low end of memory, one at a time (animated). */
  async function compact() {
    if (state.busy) return;
    hideBanner();

    if (state.procs.length === 0) {
      addLog("warn", "Nothing to compact: memory is empty.");
      showBanner(
        "info",
        "Nothing to compact yet. Allocate a few processes first.",
      );
      return;
    }
    const response = await api("compact");
    const moves = response.outcome.moves;
    if (moves.length === 0) {
      addLog("info", "Memory is already compact: no gaps between processes.");
      showBanner(
        "info",
        "Memory is already compact. There are no gaps between processes.",
      );
      return;
    }

    setBusy(true);
    renderStrip();
    addLog(
      "info",
      `Compaction started: ${plural(moves.length, "process")} to move.`,
    );

    for (const m of moves) {
      const proc = state.procs.find((item) => item.pid === m.pid);
      if (proc) proc.start = m.to;
      addLog("info", `Moved ${m.name} (${m.size} KB): ${m.from} to ${m.to}.`);
      renderStrip();
      await sleep(STEP_MS);
    }

    applyState(response.state);
    const outcome = response.outcome;
    state.lastCompaction = {
      moved: outcome.moved,
      kb: outcome.copied_kb,
      holesBefore: outcome.holes_before,
      holesAfter: outcome.holes_after,
    };
    addLog(
      "ok",
      `Compaction finished: ${plural(outcome.holes_before, "hole")} became ${plural(outcome.holes_after, "hole")}. Copied ${outcome.copied_kb} KB.`,
    );
    setBusy(false);
    await refreshPreview();
  }

  async function loadDemo() {
    if (state.busy) return;
    const response = await api("demo");
    applyState(response.state);
    state.previewSize = response.outcome.suggested_size;
    state.lastCompaction = null;
    state.log = [];
    els.size.value = response.outcome.suggested_size;
    const finished = response.outcome.finished;
    const createdCount = state.procs.length + finished.length;
    addLog(
      "info",
      `Example loaded: ${createdCount} processes placed, then ${finished.join(", ")} finished.`,
    );
    addLog(
      "warn",
      `Try allocating ${response.outcome.suggested_size} KB. ${state.stats.free} KB is free in total, but no single hole is that big.`,
    );
    render();
  }

  function setBusy(flag) {
    state.busy = flag;
    document.body.classList.toggle("busy", flag);
  }

  /* =========================================================
     3. RENDERING
     ========================================================= */

  function render() {
    renderStrip();
    renderStats();
    renderTables();
    renderLog();
  }

  function renderRuler() {
    els.ruler.innerHTML = "";
    const divisions = 8;
    for (let i = 0; i <= divisions; i++) {
      const tick = document.createElement("span");
      tick.className =
        "tick" + (i === 0 ? " first" : i === divisions ? " last" : "");
      tick.style.left = `${(i / divisions) * 100}%`;
      tick.textContent = Math.round((state.total * i) / divisions);
      els.ruler.appendChild(tick);
    }
  }

  function sizeClass(pct) {
    if (pct < 4) return " tiny";
    if (pct < 9) return " narrow";
    return "";
  }

  function renderStrip() {
    const total = state.total;

    // 1) Remove blocks for processes that no longer exist
    const alive = new Set(state.procs.map((p) => p.pid));
    for (const [pid, node] of blockEls) {
      if (!alive.has(pid)) {
        node.remove();
        blockEls.delete(pid);
      }
    }

    // 2) Create / update process blocks (persistent nodes => smooth CSS transitions)
    for (const p of state.procs) {
      const leftPct = (p.start / total) * 100;
      const widthPct = (p.size / total) * 100;
      let node = blockEls.get(p.pid);

      if (!node) {
        node = document.createElement("div");
        node.setAttribute("role", "button");
        node.tabIndex = 0;
        node.innerHTML =
          '<span class="b-name"></span><span class="b-size"></span>';
        node.addEventListener("click", () => {
          void safe(() => freeProcess(p.pid));
        });
        node.addEventListener("keydown", (e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            void safe(() => freeProcess(p.pid));
          }
        });
        // set position BEFORE inserting so a new block doesn't slide in from 0
        node.style.left = `${leftPct}%`;
        node.style.width = `${widthPct}%`;
        els.strip.appendChild(node);
        blockEls.set(p.pid, node);
      }

      node.className = "block proc" + sizeClass(widthPct);
      node.style.setProperty("--c", p.color);
      node.style.left = `${leftPct}%`;
      node.style.width = `${widthPct}%`;
      node.title = `${p.name}: ${p.size} KB at ${p.start}–${p.start + p.size - 1}. Click to free.`;
      node.setAttribute(
        "aria-label",
        `Free ${p.name}, ${p.size} KB at address ${p.start}`,
      );
      node.children[0].textContent = p.name;
      node.children[1].textContent = `${p.size} KB`;
    }

    // 3) Holes are redrawn every time (they are just gaps)
    els.strip.querySelectorAll(".hole").forEach((n) => n.remove());
    if (!state.busy) {
      const target = previewHole();
      for (const h of state.holes) {
        const widthPct = (h.size / total) * 100;
        const node = document.createElement("div");
        const isTarget = target && target.start === h.start;
        node.className =
          "block hole" + (isTarget ? " target" : "") + sizeClass(widthPct);
        node.style.left = `${(h.start / total) * 100}%`;
        node.style.width = `${widthPct}%`;
        node.title = `Free hole: ${h.size} KB at ${h.start}–${h.start + h.size - 1}`;
        node.innerHTML = `<span class="b-name">free</span><span class="b-size">${h.size} KB</span>`;
        els.strip.appendChild(node);
      }
    }
  }

  function renderStats() {
    const s = state.stats;
    const usedPct = Math.round((s.used / state.total) * 100);

    els.caption.textContent = `${state.total} KB · ${plural(state.procs.length, "process")} · ${plural(state.holes.length, "hole")} · ${ALGOS[state.algo].label}`;

    els.statTotal.textContent = `${state.total} KB`;
    els.statUsed.textContent = `${s.used} KB`;
    els.statUsedPct.textContent = `${usedPct}% of total`;
    els.statFree.textContent = `${s.free} KB`;
    els.statFreePct.textContent = `${100 - usedPct}% of total`;
    els.statHoles.textContent = state.holes.length;
    els.statLargest.textContent = `${s.largest} KB`;

    // Fragmentation meter
    const frag = s.frag;
    els.fragValue.textContent = `${frag.toFixed(1)}%`;
    els.meterFill.style.width = `${frag}%`;
    els.meterTrack.setAttribute("aria-valuenow", frag.toFixed(0));
    els.meter.classList.remove("lvl-ok", "lvl-warn", "lvl-danger");
    els.meter.classList.add(
      frag < 20 ? "lvl-ok" : frag < 50 ? "lvl-warn" : "lvl-danger",
    );

    if (s.free > 0) {
      els.fragFormula.textContent = `(1 − ${s.largest} ÷ ${s.free}) × 100 = ${frag.toFixed(1)}%`;
    } else {
      els.fragFormula.textContent =
        "No free memory, so fragmentation is 0% by definition.";
    }

    let note;
    if (s.free === 0) {
      note = "Memory is completely full.";
    } else if (state.holes.length === 1) {
      note = `All ${s.free} KB of free memory is in one hole, so any request up to ${s.free} KB can succeed.`;
    } else {
      note = `Free memory is split across ${state.holes.length} holes. Only requests up to ${s.largest} KB can succeed, even though ${s.free} KB is free.`;
    }
    if (state.lastCompaction) {
      const c = state.lastCompaction;
      note += ` Last compaction moved ${plural(c.moved, "process")} and copied ${c.kb} KB.`;
    }
    els.fragNote.textContent = note;
  }

  function renderTables() {
    // Processes
    const procs = sortedProcs();
    els.procBody.innerHTML = procs.length
      ? procs
          .map(
            (p) => `
          <tr>
            <td><span class="dot" style="background:${p.color}"></span>${esc(p.name)}</td>
            <td class="num">${p.start}</td>
            <td class="num">${p.start + p.size - 1}</td>
            <td class="num">${p.size}</td>
            <td class="num"><button class="free-btn" type="button" data-pid="${p.pid}">Free</button></td>
          </tr>`,
          )
          .join("")
      : '<tr><td class="empty" colspan="5">No processes yet. Allocate one to begin.</td></tr>';

    // Holes
    const holes = state.holes;
    const target = previewHole();
    const largest = holes.reduce((m, h) => Math.max(m, h.size), 0);
    els.holeBody.innerHTML = holes.length
      ? holes
          .map(
            (h, i) => `
          <tr>
            <td>${i + 1}${h.size === largest && holes.length > 1 ? '<span class="tag">largest</span>' : ""}${target && target.start === h.start ? '<span class="tag">next</span>' : ""}</td>
            <td class="num">${h.start}</td>
            <td class="num">${h.start + h.size - 1}</td>
            <td class="num">${h.size}</td>
          </tr>`,
          )
          .join("")
      : '<tr><td class="empty" colspan="4">No free memory.</td></tr>';
  }

  /* ---------- Log ---------- */
  function addLog(type, msg) {
    const time = new Date().toLocaleTimeString([], { hour12: false });
    state.log.unshift({ time, type, msg });
    if (state.log.length > MAX_LOG) state.log.length = MAX_LOG;
  }

  function renderLog() {
    els.log.innerHTML = "";
    for (const entry of state.log) {
      const li = document.createElement("li");
      li.className = entry.type;
      const t = document.createElement("time");
      t.textContent = entry.time;
      const span = document.createElement("span");
      span.textContent = entry.msg;
      li.append(t, span);
      els.log.appendChild(li);
    }
  }

  /* ---------- Banner ---------- */
  function showBanner(kind, message, action) {
    const cls = kind === "error" ? "" : kind; // 'error' uses the default red style
    els.banner.className = `banner ${cls}`.trim();
    els.banner.innerHTML = "";
    const p = document.createElement("p");
    p.textContent = message;
    els.banner.appendChild(p);
    if (action) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "btn primary";
      b.style.width = "auto";
      b.textContent = action.label;
      b.addEventListener("click", () => {
        void safe(action.run);
      });
      els.banner.appendChild(b);
    }
  }

  function hideBanner() {
    els.banner.className = "banner hidden";
    els.banner.innerHTML = "";
  }

  /* =========================================================
     4. EVENT WIRING
     ========================================================= */

  function onAllocateClick() {
    if (state.busy) return;
    const size = parseInt(els.size.value, 10);

    if (!Number.isInteger(size) || size < 1) {
      showBanner("warn", "Enter a whole number of KB, 1 or more.");
      els.size.focus();
      return;
    }
    if (size > state.total) {
      showBanner(
        "warn",
        `A process can't be larger than total memory (${state.total} KB).`,
      );
      return;
    }

    const name = els.name.value.trim().slice(0, 10);
    els.name.value = "";
    void safe(() => allocate(size, name));
  }

  els.alloc.addEventListener("click", onAllocateClick);
  els.size.addEventListener("keydown", (e) => {
    if (e.key === "Enter") onAllocateClick();
  });
  els.name.addEventListener("keydown", (e) => {
    if (e.key === "Enter") onAllocateClick();
  });
  els.size.addEventListener("input", () => {
    void safe(refreshPreview);
  });

  els.chips.addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (!chip) return;
    els.size.value = chip.dataset.size;
    void safe(refreshPreview);
  });

  els.algoGroup.addEventListener("click", (e) => {
    const btn = e.target.closest(".seg");
    if (!btn || state.busy) return;
    void safe(async () => {
      const size = parseInt(els.size.value, 10);
      const response = await api("strategy", {
        strategy: btn.dataset.algo,
        size: Number.isInteger(size) && size > 0 ? size : null,
      });
      applyState(response.state);
      state.previewSize = Number.isInteger(size) && size > 0 ? size : null;
      els.algoGroup.querySelectorAll(".seg").forEach((button) => {
        const active = button.dataset.algo === state.algo;
        button.classList.toggle("active", active);
        button.setAttribute("aria-pressed", String(active));
      });
      els.algoHint.textContent = ALGOS[state.algo].hint;
      render();
    });
  });

  els.procBody.addEventListener("click", (e) => {
    const btn = e.target.closest(".free-btn");
    if (btn) void safe(() => freeProcess(Number(btn.dataset.pid)));
  });

  els.setSize.addEventListener("click", setTotalFromInput);
  els.total.addEventListener("keydown", (e) => {
    if (e.key === "Enter") setTotalFromInput();
  });
  els.compact.addEventListener("click", () => {
    void safe(compact);
  });
  els.demo.addEventListener("click", () => {
    void safe(loadDemo);
  });
  els.reset.addEventListener("click", () => {
    if (!state.busy) void safe(() => initMemory(state.total));
  });
  els.clearLog.addEventListener("click", () => {
    state.log = [];
    renderLog();
  });

  /* ---------- Start ---------- */
  els.algoHint.textContent = ALGOS[state.algo].hint;
  els.algoGroup.querySelectorAll(".seg").forEach((button) => {
    const active = button.dataset.algo === state.algo;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  void safe(() => initMemory(state.total));
})();
