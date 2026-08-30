/* Pulse — Runs UI (Phase 1: Create, Discover, Join, My Runs) */
(() => {
  "use strict";

  const RUN_TYPES = [
    { id: "easy", label: "Easy Run" },
    { id: "long", label: "Long Run" },
    { id: "tempo", label: "Tempo" },
    { id: "intervals", label: "Intervals" },
    { id: "recovery", label: "Recovery" },
    { id: "trail", label: "Trail" },
    { id: "social", label: "Social" },
  ];

  const DISTANCE_PRESETS = [5, 8, 10, 15, 20];
  const PACE_PRESETS = [
    { label: "Easy", min: "5:30", max: "6:30" },
    { label: "4:30–5:00", min: "4:30", max: "5:00" },
    { label: "5:00–5:30", min: "5:00", max: "5:30" },
    { label: "5:30–6:00", min: "5:30", max: "6:00" },
  ];

  let hooks = null;

  const runsState = {
    nearby: { status: "idle", items: [], error: null },
    discover: { status: "idle", items: [], error: null, tab: "runs" },
    people: { status: "idle", items: [], error: null },
    myRuns: { status: "idle", items: [], error: null, tab: "upcoming" },
    detail: { status: "idle", run: null, error: null, runId: null },
    create: {
      step: 1,
      location_name: "",
      meeting_time: "",
      distance_km: 10,
      pace_min: "5:00",
      pace_max: "5:30",
      run_type: "easy",
      visibility: "everyone",
      title: "",
      description: "",
      max_participants: null,
      submitting: false,
      peer: null,
    },
  };

  function h(str) {
    return hooks.escapeHtml(str);
  }

  function formatRunWhen(iso) {
    if (!iso) return "—";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "—";
    const now = new Date();
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);
    const time = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    if (d.toDateString() === now.toDateString()) return `Today · ${time}`;
    if (d.toDateString() === tomorrow.toDateString()) return `Tomorrow · ${time}`;
    const day = d.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });
    return `${day} · ${time}`;
  }

  function runTypeLabel(id) {
    return RUN_TYPES.find((t) => t.id === id)?.label || id || "Run";
  }

  function compatClass(level) {
    if (level === "great_match") return "is-great";
    if (level === "possible_match") return "is-maybe";
    if (level === "challenging") return "is-hard";
    return "is-unknown";
  }

  function renderRunCard(run, { compact = false } = {}) {
    const compat = run.compatibility || {};
    const joinBtn = run.is_going
      ? `<span class="run-card-going">Going</span>`
      : run.can_join
        ? `<button type="button" class="btn btn-primary btn-sm" data-action="open-run" data-run-id="${h(run.id)}">Join</button>`
        : `<span class="run-card-full">Full</span>`;
    return `
      <article class="run-card ${compact ? "is-compact" : ""}" data-action="open-run" data-run-id="${h(run.id)}">
        <div class="run-card-top">
          <h3>${h(run.title)}</h3>
          <span class="run-card-type">${h(runTypeLabel(run.run_type))}</span>
        </div>
        <p class="run-card-when">📅 ${h(formatRunWhen(run.meeting_time))}</p>
        <p class="run-card-loc">📍 ${h(run.location_name)}</p>
        <div class="run-card-metrics">
          <span>${h(String(run.distance_km))} km</span>
          ${run.pace_range ? `<span>${h(run.pace_range)}</span>` : ""}
        </div>
        <div class="run-card-foot">
          <span class="run-card-count">👥 ${h(run.participant_count || 0)} going</span>
          ${compat.emoji ? `<span class="run-compat-pill ${compatClass(compat.level)}">${h(compat.emoji)} ${h(compat.label || "")}</span>` : ""}
          ${joinBtn}
        </div>
      </article>`;
  }

  function renderHomeRunsStrip() {
    const block = runsState.nearby;
    if (block.status === "loading" || block.status === "idle") {
      return `<section class="runs-strip-section"><h2 class="runs-section-title">Runs near you</h2><p class="runs-section-sub">Loading upcoming runs…</p></section>`;
    }
    if (block.status === "error") {
      return `<section class="runs-strip-section"><h2 class="runs-section-title">Runs near you</h2><p class="runs-section-sub">${h(block.error)}</p></section>`;
    }
    if (!block.items.length) {
      return `
        <section class="runs-strip-section">
          <div class="runs-section-head">
            <h2 class="runs-section-title">Runs near you</h2>
            <button type="button" class="btn btn-ghost btn-sm" data-nav="discover">See all</button>
          </div>
          <p class="runs-section-sub">No runs yet. Be the first — create one and invite your pace group.</p>
          <button type="button" class="btn btn-primary" data-nav="create-run">Create a Run</button>
        </section>`;
    }
    return `
      <section class="runs-strip-section">
        <div class="runs-section-head">
          <h2 class="runs-section-title">Run now / upcoming near you</h2>
          <button type="button" class="btn btn-ghost btn-sm" data-nav="discover">See all</button>
        </div>
        <div class="runs-strip">${block.items.slice(0, 8).map((r) => renderRunCard(r, { compact: true })).join("")}</div>
      </section>`;
  }

  function matchLevelClass(level) {
    if (level === "great_match") return "is-great";
    if (level === "good_match") return "is-maybe";
    if (level === "possible_match") return "is-hard";
    return "is-unknown";
  }

  function renderPeopleCard(person) {
    const match = person.match || {};
    const followBtn = person.is_following
      ? `<button type="button" class="btn btn-ghost btn-sm" data-action="confirm-unfollow" data-athlete-id="${h(person.athlete_id)}" data-handle="${h(person.handle || "")}">Following</button>`
      : `<button type="button" class="btn btn-primary btn-sm" data-action="follow-user" data-athlete-id="${h(person.athlete_id)}" data-handle="${h(person.handle || "")}">Follow</button>`;
    return `
      <article class="people-match-card">
        <button type="button" class="people-match-main" data-action="open-user" data-athlete-id="${h(person.athlete_id)}" data-handle="${h(person.handle || "")}">
          <span class="pulse-avatar is-md">${person.avatar_url ? `<img src="${h(person.avatar_url)}" alt="">` : h(person.initials || "P")}</span>
          <div class="people-match-meta">
            <strong>${h(person.name)}</strong>
            <span class="people-match-handle">${person.handle ? `@${h(person.handle)}` : ""}</span>
            <span class="people-match-score ${matchLevelClass(match.level)}">${h(match.emoji || "")} ${h(String(match.score ?? "—"))}% · ${h(match.label || "")}</span>
          </div>
        </button>
        <div class="people-match-stats">
          ${person.easy_pace_range ? `<span>Easy ${h(person.easy_pace_range)}</span>` : ""}
          ${person.typical_distance ? `<span>Usually ${h(person.typical_distance)}</span>` : ""}
          ${person.location_label ? `<span>📍 ${h(person.location_label)}</span>` : ""}
        </div>
        <div class="people-match-actions">
          ${followBtn}
          <button type="button" class="btn btn-primary btn-sm" data-action="run-together" data-athlete-id="${h(person.athlete_id)}">Run together</button>
        </div>
      </article>`;
  }

  function renderPeopleMatches() {
    const p = runsState.people;
    if (p.status === "loading" || p.status === "idle") {
      return `<p class="runs-section-sub">Finding compatible runners…</p>`;
    }
    if (p.status === "error") {
      return `<p class="runs-section-sub">${h(p.error)} <button type="button" class="btn btn-ghost btn-sm" data-action="retry-people-matches">Retry</button></p>`;
    }
    if (!p.items.length) {
      return `
        <div class="coming-soon is-inline">
          <h2>No matches yet</h2>
          <p>Make your profile public and sync Strava so we can find runners near your pace. Location stays approximate — never exact.</p>
          <button type="button" class="btn btn-primary" data-action="open-settings">Open Settings</button>
        </div>`;
    }
    return `<div class="people-match-list">${p.items.map(renderPeopleCard).join("")}</div>`;
  }

  function renderDiscover() {
    const tab = runsState.discover.tab || "runs";
    const tabs = [
      { id: "runs", label: "Runs" },
      { id: "people", label: "People" },
      { id: "clubs", label: "Clubs" },
      { id: "routes", label: "Routes" },
    ];
    let body = "";
    if (tab === "people") {
      body = renderPeopleMatches();
    } else if (tab !== "runs") {
      body = `
        <div class="coming-soon is-inline">
          <h2>${h(tabs.find((t) => t.id === tab)?.label || tab)}</h2>
          <p>Coming in Phase 3. Clubs and routes are next.</p>
        </div>`;
    } else {
      const d = runsState.discover;
      if (d.status === "loading") body = `<p class="runs-section-sub">Finding runs near you…</p>`;
      else if (d.status === "error")
        body = `<p class="runs-section-sub">${h(d.error)} <button type="button" class="btn btn-ghost btn-sm" data-action="retry-discover-runs">Retry</button></p>`;
      else if (!d.items.length)
        body = `<p class="runs-section-sub">No upcoming runs. Create one and bring your people.</p><button type="button" class="btn btn-primary" data-nav="create-run">Create a Run</button>`;
      else body = `<div class="runs-list">${d.items.map((r) => renderRunCard(r)).join("")}</div>`;
    }
    return `
      <section class="pulse-page runs-page" data-page="discover">
        <header class="runs-page-head">
          <h1>Discover</h1>
          <p class="runs-tagline">Find your people. Find your pace. Run together.</p>
        </header>
        <div class="discover-tabs" role="tablist">
          ${tabs
            .map(
              (t) =>
                `<button type="button" class="discover-tab ${tab === t.id ? "is-active" : ""}" data-action="discover-tab" data-tab="${h(t.id)}">${h(t.label)}</button>`
            )
            .join("")}
        </div>
        ${body}
      </section>`;
  }

  function renderMyRuns() {
    const tab = runsState.myRuns.tab || "upcoming";
    const tabs = [
      { id: "upcoming", label: "Upcoming" },
      { id: "hosting", label: "Hosting" },
      { id: "past", label: "Past" },
    ];
    const d = runsState.myRuns;
    let body = "";
    if (d.status === "loading") body = `<p class="runs-section-sub">Loading your runs…</p>`;
    else if (d.status === "error")
      body = `<p class="runs-section-sub">${h(d.error)}</p>`;
    else if (!d.items.length)
      body = `<p class="runs-section-sub">Nothing here yet.${tab === "upcoming" ? " Join a run from Discover." : ""}</p>`;
    else
      body = `<div class="runs-list">${d.items.map((r) => renderRunCard(r)).join("")}</div>`;

    return `
      <section class="pulse-page runs-page" data-page="my-runs">
        <header class="runs-page-head"><h1>My Runs</h1></header>
        <div class="discover-tabs">
          ${tabs
            .map(
              (t) =>
                `<button type="button" class="discover-tab ${tab === t.id ? "is-active" : ""}" data-action="my-runs-tab" data-tab="${h(t.id)}">${h(t.label)}</button>`
            )
            .join("")}
        </div>
        ${body}
      </section>`;
  }

  function renderRunDetail() {
    const d = runsState.detail;
    if (d.status === "loading" || d.status === "idle") {
      return `<section class="pulse-page run-detail-page"><p class="runs-section-sub">Loading run…</p></section>`;
    }
    if (d.status === "error" || !d.run) {
      return `
        <section class="pulse-page run-detail-page">
          <p class="runs-section-sub">${h(d.error || "Run not found.")}</p>
          <button type="button" class="btn btn-primary" data-nav="discover">Back to Discover</button>
        </section>`;
    }
    const run = d.run;
    const compat = run.compatibility || {};
    const participants = Array.isArray(run.participants) ? run.participants : [];
    const host = run.host || {};
    const joinCta = run.is_going
      ? `<button type="button" class="btn btn-ghost run-detail-cta" data-action="leave-run" data-run-id="${h(run.id)}">Leave Run</button>`
      : `<button type="button" class="btn btn-primary run-detail-cta" data-action="join-run" data-run-id="${h(run.id)}" ${run.can_join ? "" : "disabled"}>Join Run</button>`;

    return `
      <section class="pulse-page run-detail-page" data-page="run">
        <header class="run-detail-head">
          <button type="button" class="ig-action-btn" data-action="back-from-run" aria-label="Back">←</button>
          <h1>${h(run.title)}</h1>
          <span></span>
        </header>
        <div class="run-detail-hero">
          <p class="run-detail-when">${h(formatRunWhen(run.meeting_time))}</p>
          <p class="run-detail-loc">📍 ${h(run.location_name)}</p>
          <div class="run-detail-metrics">
            <span>${h(String(run.distance_km))} km</span>
            ${run.pace_range ? `<span>${h(run.pace_range)}</span>` : ""}
            <span>${h(runTypeLabel(run.run_type))}</span>
          </div>
        </div>
        <div class="run-compat-block ${compatClass(compat.level)}">
          <strong>${h(compat.emoji || "")} ${h(compat.label || "Compatibility")}</strong>
          <p>${h(compat.message || "")}</p>
        </div>
        <section class="run-detail-block">
          <h2>${h(run.participant_count || 0)} going</h2>
          <div class="run-participant-avatars">
            ${participants
              .slice(0, 6)
              .map(
                (p) =>
                  `<button type="button" class="pulse-avatar" data-action="open-user" data-athlete-id="${h(p.athlete_id)}" title="${h(p.name)}">${p.avatar_url ? `<img src="${h(p.avatar_url)}" alt="">` : h(p.initials || "P")}</button>`
              )
              .join("")}
          </div>
        </section>
        <section class="run-detail-block">
          <h2>Hosted by</h2>
          <button type="button" class="run-host-row" data-action="open-user" data-athlete-id="${h(host.athlete_id || "")}">
            <span class="pulse-avatar">${host.avatar_url ? `<img src="${h(host.avatar_url)}" alt="">` : h(host.initials || "P")}</span>
            <strong>${h(host.name || "Runner")}</strong>
          </button>
        </section>
        ${run.description ? `<section class="run-detail-block"><h2>About</h2><p>${h(run.description)}</p></section>` : ""}
        <div class="run-detail-actions">${joinCta}${run.is_going ? `<p class="run-going-note">✓ You're going</p>` : ""}</div>
      </section>`;
  }

  function defaultMeetingTime() {
    const d = new Date();
    d.setDate(d.getDate() + 1);
    d.setHours(9, 0, 0, 0);
    return d.toISOString().slice(0, 16);
  }

  function renderCreateRun() {
    const c = runsState.create;
    const step = c.step;
    let stepBody = "";

    if (step === 1) {
      stepBody = `
        <label class="run-form-label">Where are you running?
          <input type="text" id="createRunLocation" value="${h(c.location_name)}" placeholder="Search location or area" autocomplete="off">
        </label>
        <p class="form-hint">Use a meeting point — park, café, bridge. No exact home addresses.</p>`;
    } else if (step === 2) {
      stepBody = `
        <label class="run-form-label">When?
          <input type="datetime-local" id="createRunWhen" value="${h(c.meeting_time || defaultMeetingTime())}">
        </label>`;
    } else if (step === 3) {
      stepBody = `
        <p class="run-form-label">Distance</p>
        <div class="run-chip-row">
          ${DISTANCE_PRESETS.map(
            (km) =>
              `<button type="button" class="run-chip ${c.distance_km === km ? "is-active" : ""}" data-action="create-distance" data-km="${km}">${km} km</button>`
          ).join("")}
          <button type="button" class="run-chip ${!DISTANCE_PRESETS.includes(c.distance_km) ? "is-active" : ""}" data-action="create-distance" data-km="custom">Custom</button>
        </div>
        <label class="run-form-label">Custom km
          <input type="number" id="createRunDistance" min="1" max="200" step="0.1" value="${h(c.distance_km)}">
        </label>`;
    } else if (step === 4) {
      stepBody = `
        <p class="run-form-label">What pace?</p>
        <div class="run-chip-row">
          ${PACE_PRESETS.map(
            (p, i) =>
              `<button type="button" class="run-chip" data-action="create-pace-preset" data-idx="${i}">${h(p.label)}</button>`
          ).join("")}
        </div>
        <div class="form-row-2">
          <label>Min /km<input type="text" id="createRunPaceMin" value="${h(c.pace_min)}" placeholder="5:00"></label>
          <label>Max /km<input type="text" id="createRunPaceMax" value="${h(c.pace_max)}" placeholder="5:30"></label>
        </div>
        <label class="run-form-label">Run type
          <select id="createRunType">
            ${RUN_TYPES.map((t) => `<option value="${h(t.id)}" ${c.run_type === t.id ? "selected" : ""}>${h(t.label)}</option>`).join("")}
          </select>
        </label>`;
    } else if (step === 5) {
      stepBody = `
        <p class="run-form-label">Who can join?</p>
        <div class="run-visibility-list">
          <label><input type="radio" name="runVis" value="everyone" ${c.visibility === "everyone" ? "checked" : ""}> 🌍 Everyone</label>
          <label><input type="radio" name="runVis" value="followers" ${c.visibility === "followers" ? "checked" : ""}> 👥 Followers</label>
          <label><input type="radio" name="runVis" value="invite_only" ${c.visibility === "invite_only" ? "checked" : ""}> 🔒 Invite only</label>
        </div>`;
    } else {
      stepBody = `
        <label class="run-form-label">Title
          <input type="text" id="createRunTitle" value="${h(c.title)}" placeholder="Sunday Long Run">
        </label>
        <label class="run-form-label">Description (optional)
          <textarea id="createRunDesc" rows="3" placeholder="Meeting at the statue. Easy pace, all welcome.">${h(c.description)}</textarea>
        </label>
        <label class="run-form-label">Max runners (optional)
          <input type="number" id="createRunMax" min="2" max="500" value="${c.max_participants || ""}" placeholder="No limit">
        </label>
        <div class="run-create-summary">
          <p>📍 ${h(c.location_name || "—")}</p>
          <p>📅 ${h(formatRunWhen(c.meeting_time))}</p>
          <p>${h(String(c.distance_km))} km · ${h(c.pace_min)}–${h(c.pace_max)}/km</p>
        </div>`;
    }

    const isLast = step >= 6;
    const peerBanner = c.peer
      ? `<div class="run-together-banner">
           <span class="pulse-avatar">${c.peer.avatar_url ? `<img src="${h(c.peer.avatar_url)}" alt="">` : h(c.peer.initials || "P")}</span>
           <div><strong>Running with ${h(c.peer.name)}</strong><span>Suggested match — tweak anything before creating.</span></div>
         </div>`
      : "";
    return `
      <section class="pulse-page runs-page create-run-page" data-page="create-run">
        <header class="runs-page-head">
          <button type="button" class="ig-action-btn" data-action="create-run-back" aria-label="Back">←</button>
          <h1>Create a Run</h1>
          <span class="create-step-label">Step ${step}/6</span>
        </header>
        <div class="create-run-progress"><div class="create-run-progress-bar" style="width:${(step / 6) * 100}%"></div></div>
        ${peerBanner}
        ${stepBody}
        <div class="create-run-nav">
          ${step > 1 ? `<button type="button" class="btn btn-ghost" data-action="create-run-prev">Back</button>` : ""}
          <button type="button" class="btn btn-primary" data-action="${isLast ? "create-run-submit" : "create-run-next"}" ${c.submitting ? "disabled" : ""}>
            ${isLast ? (c.submitting ? "Creating…" : "Create Run") : "Continue"}
          </button>
        </div>
      </section>`;
  }

  async function loadNearby(force = false) {
    if (runsState.nearby.status === "ready" && !force) return;
    runsState.nearby.status = "loading";
    try {
      const res = await hooks.apiFetch("/api/runs/nearby?limit=12");
      if (!res.ok) throw new Error("Could not load runs.");
      const data = await res.json();
      runsState.nearby.items = Array.isArray(data.items) ? data.items : [];
      runsState.nearby.status = "ready";
      runsState.nearby.error = null;
    } catch (err) {
      runsState.nearby.status = "error";
      runsState.nearby.error = err.message || "Try again.";
    }
  }

  async function loadDiscover(force = false) {
    if (runsState.discover.status === "ready" && !force) return;
    runsState.discover.status = "loading";
    try {
      const res = await hooks.apiFetch("/api/runs?tab=discover&limit=40");
      if (!res.ok) throw new Error("Could not load runs.");
      const data = await res.json();
      runsState.discover.items = Array.isArray(data.items) ? data.items : [];
      runsState.discover.status = "ready";
      runsState.discover.error = null;
    } catch (err) {
      runsState.discover.status = "error";
      runsState.discover.error = err.message || "Try again.";
    }
  }

  async function loadPeopleMatches(force = false) {
    if (runsState.people.status === "ready" && !force) return;
    runsState.people.status = "loading";
    try {
      const res = await hooks.apiFetch("/api/people/matches?limit=24");
      if (!res.ok) throw new Error("Could not load matches.");
      const data = await res.json();
      runsState.people.items = Array.isArray(data.items) ? data.items : [];
      runsState.people.status = "ready";
      runsState.people.error = null;
    } catch (err) {
      runsState.people.status = "error";
      runsState.people.error = err.message || "Try again.";
    }
  }

  async function loadMyRuns(force = false) {
    const tab = runsState.myRuns.tab || "upcoming";
    runsState.myRuns.status = "loading";
    try {
      const res = await hooks.apiFetch(`/api/runs?tab=${encodeURIComponent(tab)}&limit=40`);
      if (!res.ok) throw new Error("Could not load your runs.");
      const data = await res.json();
      runsState.myRuns.items = Array.isArray(data.items) ? data.items : [];
      runsState.myRuns.status = "ready";
      runsState.myRuns.error = null;
    } catch (err) {
      runsState.myRuns.status = "error";
      runsState.myRuns.error = err.message || "Try again.";
    }
  }

  async function loadRunDetail(runId, force = false) {
    if (!force && runsState.detail.runId === runId && runsState.detail.status === "ready") return;
    runsState.detail.runId = runId;
    runsState.detail.status = "loading";
    try {
      const res = await hooks.apiFetch(`/api/runs/${encodeURIComponent(runId)}`);
      if (!res.ok) throw new Error("Run not found.");
      runsState.detail.run = await res.json();
      runsState.detail.status = "ready";
      runsState.detail.error = null;
    } catch (err) {
      runsState.detail.status = "error";
      runsState.detail.error = err.message || "Try again.";
      runsState.detail.run = null;
    }
  }

  function syncCreateFormFromDom() {
    const c = runsState.create;
    const loc = document.getElementById("createRunLocation");
    if (loc) c.location_name = loc.value.trim();
    const when = document.getElementById("createRunWhen");
    if (when) c.meeting_time = when.value ? new Date(when.value).toISOString() : c.meeting_time;
    const dist = document.getElementById("createRunDistance");
    if (dist) c.distance_km = Number(dist.value) || c.distance_km;
    const pmin = document.getElementById("createRunPaceMin");
    if (pmin) c.pace_min = pmin.value.trim();
    const pmax = document.getElementById("createRunPaceMax");
    if (pmax) c.pace_max = pmax.value.trim();
    const rtype = document.getElementById("createRunType");
    if (rtype) c.run_type = rtype.value;
    const title = document.getElementById("createRunTitle");
    if (title) c.title = title.value.trim();
    const desc = document.getElementById("createRunDesc");
    if (desc) c.description = desc.value.trim();
    const maxp = document.getElementById("createRunMax");
    if (maxp && maxp.value) c.max_participants = Number(maxp.value);
    const vis = document.querySelector('input[name="runVis"]:checked');
    if (vis) c.visibility = vis.value;
  }

  async function submitCreateRun() {
    syncCreateFormFromDom();
    const c = runsState.create;
    if (!c.location_name) {
      hooks.showToast("Add a meeting location.");
      c.step = 1;
      hooks.render();
      return;
    }
    if (!c.title) {
      c.title = `${runTypeLabel(c.run_type)} · ${c.distance_km} km`;
    }
    c.submitting = true;
    hooks.render();
    try {
      const res = await hooks.apiFetch("/api/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: c.title,
          description: c.description || null,
          location_name: c.location_name,
          meeting_time: c.meeting_time || defaultMeetingTime(),
          distance_km: c.distance_km,
          pace_min: c.pace_min,
          pace_max: c.pace_max,
          run_type: c.run_type,
          max_participants: c.max_participants,
          visibility: c.visibility,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Could not create run.");
      hooks.showToast("Run created. See you out there.");
      runsState.create = {
        step: 1,
        location_name: "",
        meeting_time: "",
        distance_km: 10,
        pace_min: "5:00",
        pace_max: "5:30",
        run_type: "easy",
        visibility: "everyone",
        title: "",
        description: "",
        max_participants: null,
        submitting: false,
      };
      runsState.nearby.status = "idle";
      runsState.discover.status = "idle";
      openRun(data.id);
    } catch (err) {
      c.submitting = false;
      hooks.showToast(err.message || "Try again.");
      hooks.render();
    }
  }

  function openRun(runId) {
    hooks.navigate("run", { runId: String(runId) });
  }

  async function joinRun(runId) {
    const res = await hooks.apiFetch(`/api/runs/${runId}/join`, { method: "POST" });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      hooks.showToast(data.detail || "Could not join.");
      return;
    }
    runsState.detail.run = data;
    runsState.detail.status = "ready";
    runsState.nearby.status = "idle";
    runsState.discover.status = "idle";
    runsState.myRuns.status = "idle";
    hooks.showToast("You're going. Lace up.");
    hooks.render();
  }

  async function leaveRun(runId) {
    const res = await hooks.apiFetch(`/api/runs/${runId}/leave`, { method: "POST" });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      hooks.showToast(data.detail || "Could not leave.");
      return;
    }
    runsState.detail.run = data;
    hooks.showToast("You left this run.");
    hooks.render();
  }

  async function startRunTogether(athleteId) {
    if (!athleteId) return;
    try {
      const res = await hooks.apiFetch(`/api/people/${encodeURIComponent(athleteId)}/run-together`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Could not prepare run.");
      const c = runsState.create;
      c.step = 1;
      c.peer = data.peer || null;
      c.title = data.suggested_title || "";
      c.location_name = data.suggested_location || c.location_name || "";
      if (data.suggested_distance_km) c.distance_km = data.suggested_distance_km;
      if (data.suggested_pace_min) c.pace_min = data.suggested_pace_min;
      if (data.suggested_pace_max) c.pace_max = data.suggested_pace_max;
      if (!c.meeting_time) c.meeting_time = defaultMeetingTime();
      if (c.peer?.name) {
        c.description = `Run together with ${c.peer.name}. Suggested: ${
          (data.match && data.match.suggested_pace) || "easy pace"
        }.`;
      }
      hooks.navigate("create-run");
      hooks.showToast(
        data.match?.label
          ? `${data.match.emoji || ""} ${data.match.score}% · ${data.match.label}`
          : "Adjust the run and invite them."
      );
    } catch (err) {
      hooks.showToast(err.message || "Try again.");
    }
  }

  function handleAction(action, el) {
    if (action === "open-run") {
      openRun(el?.dataset?.runId);
      return true;
    }
    if (action === "back-from-run") {
      hooks.navigate("discover");
      return true;
    }
    if (action === "discover-tab") {
      runsState.discover.tab = el?.dataset?.tab || "runs";
      if (runsState.discover.tab === "people") {
        loadPeopleMatches(false).then(() => hooks.render());
      } else {
        hooks.render();
      }
      return true;
    }
    if (action === "retry-people-matches") {
      loadPeopleMatches(true).then(() => hooks.render());
      return true;
    }
    if (action === "run-together") {
      startRunTogether(el?.dataset?.athleteId);
      return true;
    }
    if (action === "my-runs-tab") {
      runsState.myRuns.tab = el?.dataset?.tab || "upcoming";
      loadMyRuns(true).then(() => hooks.render());
      return true;
    }
    if (action === "retry-discover-runs") {
      loadDiscover(true).then(() => hooks.render());
      return true;
    }
    if (action === "create-run-next") {
      syncCreateFormFromDom();
      runsState.create.step = Math.min(6, runsState.create.step + 1);
      if (runsState.create.step === 2 && !runsState.create.meeting_time) {
        runsState.create.meeting_time = defaultMeetingTime();
      }
      hooks.render();
      return true;
    }
    if (action === "create-run-prev") {
      syncCreateFormFromDom();
      runsState.create.step = Math.max(1, runsState.create.step - 1);
      hooks.render();
      return true;
    }
    if (action === "create-run-back") {
      if (runsState.create.step > 1) {
        syncCreateFormFromDom();
        runsState.create.step -= 1;
        hooks.render();
      } else {
        hooks.navigate("discover");
      }
      return true;
    }
    if (action === "create-distance") {
      const km = el?.dataset?.km;
      if (km === "custom") {
        runsState.create.distance_km = 12;
      } else {
        runsState.create.distance_km = Number(km);
      }
      hooks.render();
      return true;
    }
    if (action === "create-pace-preset") {
      const idx = Number(el?.dataset?.idx);
      const preset = PACE_PRESETS[idx];
      if (preset) {
        runsState.create.pace_min = preset.min;
        runsState.create.pace_max = preset.max;
      }
      hooks.render();
      return true;
    }
    if (action === "create-run-submit") {
      submitCreateRun();
      return true;
    }
    if (action === "join-run") {
      joinRun(el?.dataset?.runId);
      return true;
    }
    if (action === "leave-run") {
      leaveRun(el?.dataset?.runId);
      return true;
    }
    return false;
  }

  function onPageEnter(page, opts = {}) {
    if (page === "feed") {
      loadNearby(false).then(() => {
        if (hooks.getPage() === "feed") hooks.render();
      });
    }
    if (page === "discover") {
      if (runsState.discover.tab === "people") {
        loadPeopleMatches(false).then(() => {
          if (hooks.getPage() === "discover") hooks.render();
        });
      } else {
        loadDiscover(false).then(() => {
          if (hooks.getPage() === "discover") hooks.render();
        });
      }
    }
    if (page === "my-runs") {
      loadMyRuns(false).then(() => {
        if (hooks.getPage() === "my-runs") hooks.render();
      });
    }
    if (page === "create-run") {
      if (!runsState.create.meeting_time) runsState.create.meeting_time = defaultMeetingTime();
    }
    if (page === "run" && opts.runId) {
      loadRunDetail(opts.runId, true).then(() => {
        if (hooks.getPage() === "run") hooks.render();
      });
    }
  }

  function renderPage(page) {
    if (page === "discover") return renderDiscover();
    if (page === "my-runs") return renderMyRuns();
    if (page === "create-run") return renderCreateRun();
    if (page === "run") return renderRunDetail();
    return null;
  }

  window.PulseRuns = {
    attach(h) {
      hooks = h;
    },
    renderHomeRunsStrip,
    renderPage,
    handleAction,
    onPageEnter,
    openRun,
    getRunIdFromHash() {
      const raw = (location.hash || "").slice(1);
      if (raw.startsWith("run/")) return decodeURIComponent(raw.slice(4)).trim();
      return null;
    },
  };
})();
