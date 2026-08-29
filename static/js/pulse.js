/* Pulse app shell — social structure, real profile data, honest Coming Soon. */
(() => {
  "use strict";

  const PAGES = ["feed", "explore", "coach", "profile"];
  const COACH_TAGLINES = [
    "Your legs don’t lie.",
    "Let’s make those miles count.",
    "Still alive after that long run?",
  ];

  const TILE_BACKGROUNDS = [
    "linear-gradient(145deg, #1f3a28 0%, #0c1410 70%)",
    "linear-gradient(160deg, #2a3320 0%, #10150f 65%)",
    "linear-gradient(135deg, #16352f 0%, #0b1211 70%)",
    "linear-gradient(150deg, #3a2f18 0%, #12100c 70%)",
    "linear-gradient(145deg, #1a2c3a 0%, #0c1116 70%)",
    "linear-gradient(155deg, #2d1f2e 0%, #120e14 70%)",
  ];

  const state = {
    page: "feed",
    profile: null,
    activities: [],
    summary: null,
    loadedProfile: false,
  };

  const els = {
    viewRoot: document.getElementById("viewRoot"),
    coachSidebarPanel: document.getElementById("coachSidebarPanel"),
    coachTagline: document.getElementById("coachTagline"),
    sidebarAvatar: document.getElementById("sidebarAvatar"),
    sidebarName: document.getElementById("sidebarName"),
    sidebarHandle: document.getElementById("sidebarHandle"),
    settingsDrawer: document.getElementById("settingsDrawer"),
    drawerBackdrop: document.getElementById("drawerBackdrop"),
    activityModal: document.getElementById("activityModal"),
    activityModalBody: document.getElementById("activityModalBody"),
    activityModalTitle: document.getElementById("activityModalTitle"),
    toast: document.getElementById("toast"),
    syncChip: document.getElementById("syncChip"),
    settingsMsg: document.getElementById("settingsMsg"),
  };

  /* ——— utils ——— */

  async function apiFetch(url, options) {
    const response = await fetch(url, options);
    if (response.status === 401) {
      window.location.href = "/";
      throw new Error("Sessão expirada.");
    }
    return response;
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function formatKm(meters) {
    if (meters == null || Number.isNaN(Number(meters))) return "—";
    return (Number(meters) / 1000).toFixed(Number(meters) >= 10000 ? 1 : 2);
  }

  function formatPace(distanceM, movingTimeS) {
    const d = Number(distanceM);
    const t = Number(movingTimeS);
    if (!d || !t || d <= 0) return "—";
    const paceSec = t / (d / 1000);
    if (!Number.isFinite(paceSec) || paceSec <= 0) return "—";
    const m = Math.floor(paceSec / 60);
    const s = Math.round(paceSec % 60);
    return `${m}:${String(s).padStart(2, "0")}`;
  }

  function formatDuration(seconds) {
    const t = Number(seconds);
    if (!t || t < 0) return "—";
    const h = Math.floor(t / 3600);
    const m = Math.floor((t % 3600) / 60);
    const s = Math.floor(t % 60);
    if (h > 0) return `${h}h ${String(m).padStart(2, "0")}m`;
    return `${m}:${String(s).padStart(2, "0")}`;
  }

  function formatDate(iso) {
    if (!iso) return "—";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "—";
    return d.toLocaleDateString("pt-PT", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  }

  function handleLabel(profile) {
    if (profile?.handle) return `@${profile.handle}`;
    if (profile?.strava?.username) return `@${profile.strava.username}`;
    return "@runner";
  }

  function showToast(message) {
    els.toast.textContent = message;
    els.toast.classList.add("is-show");
    clearTimeout(showToast._t);
    showToast._t = setTimeout(() => {
      els.toast.classList.remove("is-show");
    }, 2800);
  }

  function setNavActive(page) {
    document.querySelectorAll("[data-nav]").forEach((btn) => {
      btn.classList.toggle("is-active", btn.dataset.nav === page);
    });
  }

  function pickTagline() {
    return COACH_TAGLINES[Math.floor(Math.random() * COACH_TAGLINES.length)];
  }

  function tileBackground(activity, index) {
    const seed = Number(activity.id) || index;
    return TILE_BACKGROUNDS[seed % TILE_BACKGROUNDS.length];
  }

  /* ——— Coming Soon ——— */

  function renderComingSoon({
    eyebrow = "Coming soon",
    title,
    message,
    ctaLabel,
    ctaNav,
    ctaHref,
  }) {
    const cta = ctaLabel
      ? ctaHref
        ? `<a class="btn btn-primary" href="${escapeHtml(ctaHref)}">${escapeHtml(ctaLabel)}</a>`
        : `<button type="button" class="btn btn-primary" data-nav="${escapeHtml(ctaNav || "explore")}">${escapeHtml(ctaLabel)}</button>`
      : "";

    return `
      <div class="coming-soon">
        <div class="coming-soon-eyebrow"><i></i> ${escapeHtml(eyebrow)}</div>
        <h2>${escapeHtml(title)}</h2>
        <p>${escapeHtml(message)}</p>
        ${cta ? `<div class="cta-row">${cta}</div>` : ""}
      </div>
    `;
  }

  function renderCoachWarmup() {
    return `
      ${renderComingSoon({
        eyebrow: "Warming up",
        title: "Coach is still tying its shoelaces.",
        message:
          "We’re teaching it how to turn your questionable training decisions into something useful. Advice better than “just run faster” is on the way.",
      })}
      <div class="coach-bubble" style="margin-top:18px;">
        Training your future coach.<br>
        It already knows skipping recovery doesn’t make you faster.
      </div>
      <div class="coach-composer">
        <input type="text" disabled placeholder="Coach is warming up…" aria-label="Mensagem ao coach (indisponível)">
      </div>
    `;
  }

  /* ——— Pages ——— */

  function renderFeed() {
    return `
      <section class="pulse-page" data-page="feed">
        <p class="page-kicker">Feed</p>
        <h1 class="page-title">Where runners show up.</h1>
        <p class="page-sub">Running connects people. Your miles are the content.</p>

        <div class="feed-empty">
          <h2 class="feed-empty-hero">Your feed is quieter than your recovery run.</h2>
          <p class="feed-empty-copy">
            Nothing to stalk. Yet. Follow some runners and this place will start moving.
          </p>
          <div class="cta-row">
            <button type="button" class="btn btn-primary" data-nav="explore">Explore runners</button>
          </div>
        </div>

        <div class="post-skeleton" aria-hidden="true">
          <article class="post-card">
            <div class="post-card-head">
              <div class="pulse-avatar">R</div>
              <div>
                <strong>Future post</strong>
                <div style="color:var(--faint);font-size:12px;">@soon · layout ready</div>
              </div>
            </div>
            <div class="post-card-body"></div>
            <div class="post-card-stats">
              <span>Distance</span><span>Pace</span><span>Time</span>
            </div>
          </article>
        </div>
      </section>
    `;
  }

  function renderExplore() {
    return `
      <section class="pulse-page" data-page="explore">
        <p class="page-kicker">Explore</p>
        <h1 class="page-title">Finding your people.</h1>
        <p class="page-sub">Curiosity first. Matching later. No creepy vibes.</p>

        <div class="search-wrap">
          <span class="search-ico" aria-hidden="true">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>
            </svg>
          </span>
          <input id="exploreSearch" type="search" placeholder="Who are you looking for?" autocomplete="off">
        </div>
        <p class="search-hint" id="exploreSearchHint">We’re still finding the runners.</p>

        ${renderComingSoon({
          eyebrow: "Under construction",
          title: "We’re scouting the streets.",
          message:
            "Soon you’ll discover who’s putting in the miles around you. Not in a creepy way — in a “want to run Thursday?” way.",
          ctaLabel: "Back to feed",
          ctaNav: "feed",
        })}
      </section>
    `;
  }

  function renderCoachPage() {
    return `
      <section class="pulse-page coach-page" data-page="coach">
        <p class="page-kicker">AI Coach</p>
        <h1 class="page-title">${escapeHtml(els.coachTagline?.textContent || "Your legs don’t lie.")}</h1>
        <p class="page-sub">Personal coach energy. Still warming up — honestly.</p>
        ${renderCoachWarmup()}
      </section>
    `;
  }

  function renderAvatarHtml(profile, extraClass = "") {
    const url = profile?.avatar_url;
    const initials = escapeHtml(profile?.initials || "P");
    if (url) {
      return `<div class="pulse-avatar ${extraClass}"><img src="${escapeHtml(url)}" alt=""></div>`;
    }
    return `<div class="pulse-avatar ${extraClass}">${initials}</div>`;
  }

  function renderActivityTile(activity, index) {
    const km = formatKm(activity.distance_m);
    const pace = formatPace(activity.distance_m, activity.moving_time_s);
    const name = (activity.name || "Run").toUpperCase();
    const bg = tileBackground(activity, index);
    return `
      <button type="button" class="activity-tile" data-activity-id="${escapeHtml(activity.id)}" style="--tile-bg:${bg}">
        <span class="tile-label">${escapeHtml(name)}</span>
        <div>
          <div class="tile-distance">${escapeHtml(km)} KM</div>
          <div class="tile-meta">${escapeHtml(pace)} /KM · ${escapeHtml(formatDate(activity.start_date_local || activity.start_date))}</div>
        </div>
      </button>
    `;
  }

  function renderProfile() {
    const p = state.profile;
    if (!p) {
      return `
        <section class="pulse-page">
          <p class="page-kicker">Profile</p>
          <h1 class="page-title">Loading your miles…</h1>
        </section>
      `;
    }

    const stats = p.stats || state.summary || {};
    const distance =
      stats.total_running_km != null
        ? Number(stats.total_running_km).toFixed(1)
        : stats.total_distance_km != null
          ? Number(stats.total_distance_km).toFixed(1)
          : deriveDistanceKm(state.activities);
    const runs =
      stats.running_activities ??
      stats.total_activities ??
      state.activities.length;
    let timeLabel;
    if (stats.total_training_hours != null) {
      const hours = Number(stats.total_training_hours);
      timeLabel = hours >= 10 ? `${hours.toFixed(0)}h` : `${hours.toFixed(1)}h`;
    } else {
      timeLabel = formatDuration(deriveMovingTime(state.activities));
    }

    const grid =
      state.activities.length === 0
        ? `<div class="tile-empty">Zero runs. Plenty of potential.<br><span style="color:var(--faint)">Sync Strava in Settings when you’re ready.</span></div>`
        : state.activities.map(renderActivityTile).join("");

    return `
      <section class="pulse-page" data-page="profile">
        <p class="page-kicker">Profile</p>
        <div class="profile-header">
          ${renderAvatarHtml(p, "is-lg")}
          <div class="profile-identity">
            <h1>${escapeHtml(p.display_name || "Runner")}</h1>
            <p class="profile-handle">${escapeHtml(handleLabel(p))}</p>
            ${p.bio ? `<p class="profile-bio">${escapeHtml(p.bio)}</p>` : ""}
            <div class="profile-social">
              <button type="button" data-action="followers-tease"><strong>0</strong> followers</button>
              <button type="button" data-action="following-tease"><strong>0</strong> following</button>
            </div>
            <div class="profile-actions">
              <button type="button" class="btn btn-primary" data-action="edit-profile">Edit Profile</button>
              <button type="button" class="btn btn-ghost" data-action="open-settings">Settings</button>
            </div>
          </div>
        </div>

        <div class="profile-stats">
          <div class="stat-pill"><span>Distance</span><strong>${escapeHtml(distance)} km</strong></div>
          <div class="stat-pill"><span>Runs</span><strong>${escapeHtml(runs)}</strong></div>
          <div class="stat-pill"><span>Time</span><strong>${escapeHtml(timeLabel)}</strong></div>
        </div>

        <h2 class="profile-section-title">Activities</h2>
        <div class="activity-grid">${grid}</div>
      </section>
    `;
  }

  function deriveDistanceKm(activities) {
    const meters = activities.reduce((sum, a) => sum + (Number(a.distance_m) || 0), 0);
    return (meters / 1000).toFixed(1);
  }

  function deriveMovingTime(activities) {
    return activities.reduce((sum, a) => sum + (Number(a.moving_time_s) || 0), 0);
  }

  /* ——— Routing ——— */

  function navigate(page, { replace = false } = {}) {
    const next = PAGES.includes(page) ? page : "feed";
    state.page = next;
    setNavActive(next);
    const hash = `#${next}`;
    if (replace) {
      history.replaceState({ page: next }, "", hash);
    } else if (location.hash !== hash) {
      history.pushState({ page: next }, "", hash);
    }
    render();
  }

  function render() {
    let html = "";
    if (state.page === "feed") html = renderFeed();
    else if (state.page === "explore") html = renderExplore();
    else if (state.page === "coach") html = renderCoachPage();
    else html = renderProfile();

    els.viewRoot.innerHTML = html;
    els.coachSidebarPanel.innerHTML = renderCoachWarmup();
  }

  /* ——— Data ——— */

  function applyProfileChrome(profile) {
    els.sidebarName.textContent = profile.display_name || "Runner";
    els.sidebarHandle.textContent = handleLabel(profile);
    els.sidebarAvatar.innerHTML = "";
    if (profile.avatar_url) {
      const img = document.createElement("img");
      img.src = profile.avatar_url;
      img.alt = "";
      els.sidebarAvatar.appendChild(img);
    } else {
      els.sidebarAvatar.textContent = profile.initials || "P";
    }

    document.getElementById("settingsDisplayName").value =
      profile.display_name_custom || profile.display_name || "";
    document.getElementById("settingsHandle").value = profile.handle || "";
    document.getElementById("settingsBio").value = profile.bio || "";
  }

  async function loadProfileBundle(force = false) {
    if (state.loadedProfile && !force) return;

    const [profileRes, activitiesRes, summaryRes] = await Promise.all([
      apiFetch("/api/me/profile"),
      apiFetch("/activities?limit=50"),
      apiFetch("/analytics/summary").catch(() => null),
    ]);

    if (!profileRes.ok) throw new Error("That didn’t go the distance.");
    state.profile = await profileRes.json();

    if (activitiesRes.ok) {
      const raw = await activitiesRes.json();
      state.activities = Array.isArray(raw) ? raw : [];
    } else {
      state.activities = [];
    }

    if (summaryRes && summaryRes.ok) {
      state.summary = await summaryRes.json();
      if (state.profile && !state.profile.stats) {
        state.profile.stats = state.summary;
      }
    }

    state.loadedProfile = true;
    applyProfileChrome(state.profile);
  }

  async function ensureAuth() {
    const res = await fetch("/auth/me");
    if (!res.ok) {
      window.location.href = "/";
      throw new Error("unauth");
    }
    return res.json();
  }

  /* ——— Settings / modal ——— */

  function openSettings() {
    els.drawerBackdrop.hidden = false;
    requestAnimationFrame(() => {
      els.drawerBackdrop.classList.add("is-open");
      els.settingsDrawer.classList.add("is-open");
      els.settingsDrawer.setAttribute("aria-hidden", "false");
    });
  }

  function closeSettings() {
    els.drawerBackdrop.classList.remove("is-open");
    els.settingsDrawer.classList.remove("is-open");
    els.settingsDrawer.setAttribute("aria-hidden", "true");
    setTimeout(() => {
      els.drawerBackdrop.hidden = true;
    }, 250);
  }

  function openActivity(activityId) {
    const activity = state.activities.find(
      (a) => String(a.id) === String(activityId)
    );
    if (!activity) {
      showToast("That run went missing.");
      return;
    }

    els.activityModalTitle.textContent = activity.name || "Run";
    const bg = tileBackground(activity, 0);
    els.activityModalBody.innerHTML = `
      <div class="modal-hero" style="background:${bg}">
        <div>
          <div class="tile-label">${escapeHtml((activity.sport_type || "Run").toUpperCase())}</div>
          <div class="tile-distance" style="margin-top:8px">${escapeHtml(formatKm(activity.distance_m))} KM</div>
        </div>
      </div>
      <p class="form-hint">${escapeHtml(formatDate(activity.start_date_local || activity.start_date))}</p>
      <div class="modal-metrics">
        <div class="stat-pill"><span>Pace</span><strong>${escapeHtml(formatPace(activity.distance_m, activity.moving_time_s))}</strong></div>
        <div class="stat-pill"><span>Time</span><strong>${escapeHtml(formatDuration(activity.moving_time_s))}</strong></div>
        <div class="stat-pill"><span>Elev</span><strong>${escapeHtml(
          activity.elevation_gain_m != null
            ? `${Math.round(activity.elevation_gain_m)} m`
            : "—"
        )}</strong></div>
      </div>
      <p class="form-hint" style="margin-top:18px;">
        Maps, AI notes, and photos land later. For now: the miles you actually ran.
      </p>
    `;

    els.activityModal.hidden = false;
    requestAnimationFrame(() => els.activityModal.classList.add("is-open"));
  }

  function closeActivity() {
    els.activityModal.classList.remove("is-open");
    setTimeout(() => {
      els.activityModal.hidden = true;
    }, 250);
  }

  async function syncStrava(quiet = false) {
    if (!quiet) els.syncChip.classList.add("is-show");
    try {
      const res = await apiFetch("/strava/sync", { method: "POST" });
      const data = await res.json().catch(() => ({}));
      if (data.error) {
        showToast(data.error);
      } else if (!quiet) {
        showToast("Miles refreshed.");
        await loadProfileBundle(true);
        if (state.page === "profile") render();
      }
    } catch (err) {
      showToast("That didn’t go the distance.");
    } finally {
      els.syncChip.classList.remove("is-show");
    }
  }

  /* ——— Events ——— */

  function onClick(event) {
    const nav = event.target.closest("[data-nav]");
    if (nav && nav.dataset.nav) {
      event.preventDefault();
      navigate(nav.dataset.nav);
      return;
    }

    const actionEl = event.target.closest("[data-action]");
    if (actionEl) {
      const action = actionEl.dataset.action;
      if (action === "edit-profile" || action === "open-settings") openSettings();
      if (action === "followers-tease") {
        showToast("Nobody’s watching. Yet.");
      }
      if (action === "following-tease") {
        showToast("Follow someone. Running alone is overrated.");
      }
      return;
    }

    const tile = event.target.closest("[data-activity-id]");
    if (tile) {
      openActivity(tile.dataset.activityId);
    }
  }

  function wireSettingsForm() {
    document.getElementById("openSettingsSidebar").addEventListener("click", openSettings);
    document.getElementById("closeSettings").addEventListener("click", closeSettings);
    els.drawerBackdrop.addEventListener("click", closeSettings);
    document.getElementById("closeActivityModal").addEventListener("click", closeActivity);
    els.activityModal.addEventListener("click", (e) => {
      if (e.target === els.activityModal) closeActivity();
    });

    document.getElementById("syncNowBtn").addEventListener("click", () => syncStrava(false));

    const fileInput = document.getElementById("settingsAvatarFile");
    document.getElementById("settingsAvatarPick").addEventListener("click", () => fileInput.click());
    document.getElementById("settingsAvatarRemove").addEventListener("click", async () => {
      const res = await apiFetch("/api/me/avatar", { method: "DELETE" });
      if (!res.ok) {
        els.settingsMsg.textContent = "That didn’t go the distance.";
        els.settingsMsg.className = "form-msg is-error";
        return;
      }
      els.settingsMsg.textContent = "Photo cleared.";
      els.settingsMsg.className = "form-msg is-ok";
      await loadProfileBundle(true);
      render();
    });

    fileInput.addEventListener("change", async () => {
      const file = fileInput.files && fileInput.files[0];
      if (!file) return;
      const body = new FormData();
      body.append("file", file);
      const res = await apiFetch("/api/me/avatar", { method: "POST", body });
      fileInput.value = "";
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        els.settingsMsg.textContent = err.detail || "Upload failed.";
        els.settingsMsg.className = "form-msg is-error";
        return;
      }
      els.settingsMsg.textContent = "Looking sharp.";
      els.settingsMsg.className = "form-msg is-ok";
      await loadProfileBundle(true);
      render();
    });

    document.getElementById("profileForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      const payload = {
        display_name: document.getElementById("settingsDisplayName").value,
        handle: document.getElementById("settingsHandle").value,
        bio: document.getElementById("settingsBio").value,
      };
      const res = await apiFetch("/api/me/profile", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        els.settingsMsg.textContent =
          typeof err.detail === "string" ? err.detail : "That didn’t go the distance.";
        els.settingsMsg.className = "form-msg is-error";
        return;
      }
      state.profile = await res.json();
      state.loadedProfile = true;
      applyProfileChrome(state.profile);
      els.settingsMsg.textContent = "Saved. You’re still you — just clearer.";
      els.settingsMsg.className = "form-msg is-ok";
      if (state.page === "profile") render();
    });
  }

  function wireExploreSearch() {
    els.viewRoot.addEventListener("keydown", (event) => {
      if (event.target.id !== "exploreSearch") return;
      if (event.key === "Enter") {
        event.preventDefault();
        const q = event.target.value.trim();
        const hint = document.getElementById("exploreSearchHint");
        if (hint) {
          hint.textContent = q
            ? `“${q}” — we’re still finding the runners.`
            : "We’re still finding the runners.";
        }
        showToast("Search is warming up. Personality first, matching later.");
      }
    });
  }

  /* ——— Boot ——— */

  async function boot() {
    els.coachTagline.textContent = pickTagline();
    document.addEventListener("click", onClick);
    window.addEventListener("popstate", () => {
      const page = (location.hash || "#feed").slice(1);
      navigate(PAGES.includes(page) ? page : "feed", { replace: true });
    });

    wireSettingsForm();
    wireExploreSearch();

    await ensureAuth();
    await loadProfileBundle(true);

    const initial = (location.hash || "#feed").slice(1);
    navigate(PAGES.includes(initial) ? initial : "feed", { replace: true });

    const params = new URLSearchParams(location.search);
    if (params.get("boot") === "1") {
      params.delete("boot");
      const clean =
        location.pathname +
        (params.toString() ? `?${params}` : "") +
        (location.hash || "#feed");
      history.replaceState({ page: state.page }, "", clean);
      syncStrava(true).then(() => loadProfileBundle(true).then(() => {
        if (state.page === "profile") render();
      }));
    }
  }

  boot().catch((err) => {
    console.error(err);
  });
})();
