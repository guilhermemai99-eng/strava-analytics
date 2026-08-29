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
    "linear-gradient(155deg, #24301c 0%, #0e120c 70%)",
  ];

  const FEED_LOADING_LINES = [
    "Finding the miles…",
    "Checking who’s been avoiding recovery…",
    "Loading questionable pace decisions…",
  ];

  const state = {
    page: "feed",
    profile: null,
    activities: [],
    summary: null,
    loadedProfile: false,
    feed: {
      status: "idle",
      items: [],
      message: null,
      error: null,
      loadingLine: FEED_LOADING_LINES[0],
    },
    coach: {
      status: "idle",
      welcome: "",
      messages: [],
      sending: false,
      error: null,
    },
    explore: {
      status: "idle",
      me: null,
      sections: [],
      error: null,
      searchQ: "",
      searchStatus: "idle",
      searchResults: [],
      peek: null,
    },
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

  function renderCoachChat(options) {
    const opts = options || {};
    const compact = !!opts.compact;
    const coach = state.coach;
    const bubbles = [];

    if (coach.welcome) {
      bubbles.push(
        `<div class="coach-bubble is-system">${escapeHtml(coach.welcome)}</div>`
      );
    }

    coach.messages.forEach((msg) => {
      const roleClass = msg.role === "user" ? "is-user" : "is-assistant";
      bubbles.push(
        `<div class="coach-bubble ${roleClass}">${escapeHtml(msg.content)}</div>`
      );
    });

    if (coach.status === "loading" && !coach.messages.length) {
      bubbles.push(`<div class="coach-typing">Coach is reading your miles…</div>`);
    }
    if (coach.sending) {
      bubbles.push(`<div class="coach-typing">Typing something slightly rude but useful…</div>`);
    }
    if (coach.error) {
      bubbles.push(
        `<div class="coach-bubble is-system">${escapeHtml(coach.error)}</div>`
      );
    }

    const disabled = coach.sending ? "disabled" : "";
    return `
      <div class="coach-chat ${compact ? "is-compact" : ""}">
        <div class="coach-thread" data-coach-thread>${bubbles.join("")}</div>
        <form class="coach-composer" data-coach-form>
          <div class="coach-composer-row">
            <input
              type="text"
              name="message"
              maxlength="1200"
              placeholder="Ask about pace, recovery, long runs…"
              aria-label="Message the AI Coach"
              autocomplete="off"
              ${disabled}
            >
            <button type="submit" class="coach-send" ${disabled} aria-label="Send">↑</button>
          </div>
          <div class="coach-tools">
            <button type="button" data-action="clear-coach">Clear chat</button>
            <span style="color:var(--faint);font-size:11px;">Roasts included. Medical advice not.</span>
          </div>
        </form>
      </div>
    `;
  }

  function renderCoachWarmup() {
    // Kept as alias while sidebar still calls the chat renderer.
    return renderCoachChat({ compact: true });
  }

  async function loadCoachMessages(force = false) {
    if (state.coach.status === "ready" && !force) return;
    state.coach.status = "loading";
    paintCoachPanels();
    try {
      const res = await apiFetch("/api/coach/messages");
      if (!res.ok) throw new Error("Coach ghosted. Retry.");
      const data = await res.json();
      state.coach.welcome = data.welcome || "";
      state.coach.messages = Array.isArray(data.messages) ? data.messages : [];
      state.coach.status = "ready";
      state.coach.error = null;
    } catch (err) {
      state.coach.status = "error";
      state.coach.error = err.message || "That didn’t go the distance.";
    }
    paintCoachPanels();
  }

  async function sendCoachMessage(raw) {
    const message = (raw || "").trim();
    if (!message || state.coach.sending) return;
    state.coach.sending = true;
    state.coach.error = null;
    // Optimistic user bubble
    state.coach.messages.push({
      id: `tmp-${Date.now()}`,
      role: "user",
      content: message,
      created_at: new Date().toISOString(),
    });
    paintCoachPanels();

    try {
      const res = await apiFetch("/api/coach/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(
          typeof data.detail === "string" ? data.detail : "That didn’t go the distance."
        );
      }
      // Replace optimistic user message with server copies.
      state.coach.messages = state.coach.messages.filter(
        (m) => String(m.id).indexOf("tmp-") !== 0
      );
      if (data.user_message) state.coach.messages.push(data.user_message);
      if (data.assistant_message) state.coach.messages.push(data.assistant_message);
      else if (data.reply) {
        state.coach.messages.push({
          role: "assistant",
          content: data.reply,
          created_at: new Date().toISOString(),
        });
      }
      state.coach.status = "ready";
    } catch (err) {
      state.coach.error = err.message || "That didn’t go the distance.";
      // Keep optimistic user message so they can retry contextually.
    } finally {
      state.coach.sending = false;
      paintCoachPanels();
    }
  }

  async function clearCoachChat() {
    try {
      const res = await apiFetch("/api/coach/messages", { method: "DELETE" });
      const data = await res.json().catch(() => ({}));
      state.coach.messages = [];
      state.coach.welcome = data.welcome || state.coach.welcome;
      state.coach.error = null;
      showToast("Chat cleared. Ego reset optional.");
      paintCoachPanels();
    } catch (err) {
      showToast("Couldn’t clear chat.");
    }
  }

  function paintCoachPanels() {
    if (els.coachSidebarPanel) {
      els.coachSidebarPanel.innerHTML = renderCoachChat({ compact: true });
      wireCoachDom(els.coachSidebarPanel);
    }
    if (state.page === "coach") {
      // Re-render full page so mobile thread stays in sync.
      const html = renderCoachPage();
      els.viewRoot.innerHTML = html;
      bindViewInteractions();
      wireCoachDom(els.viewRoot);
    }
    scrollCoachThreads();
  }

  function scrollCoachThreads() {
    document.querySelectorAll("[data-coach-thread]").forEach((el) => {
      el.scrollTop = el.scrollHeight;
    });
  }

  function wireCoachDom(root) {
    if (!root) return;
    root.querySelectorAll("[data-coach-form]").forEach((form) => {
      if (form.dataset.wired === "1") return;
      form.dataset.wired = "1";
      form.addEventListener("submit", (event) => {
        event.preventDefault();
        const input = form.querySelector('input[name="message"]');
        const value = input ? input.value : "";
        if (input) input.value = "";
        sendCoachMessage(value);
      });
    });
  }

  /* ——— Feed helpers ——— */

  function decodePolyline(encoded) {
    if (!encoded) return [];
    let index = 0;
    const len = encoded.length;
    let lat = 0;
    let lng = 0;
    const coordinates = [];

    while (index < len) {
      let result = 0;
      let shift = 0;
      let b;
      do {
        b = encoded.charCodeAt(index++) - 63;
        result |= (b & 0x1f) << shift;
        shift += 5;
      } while (b >= 0x20);
      const dlat = result & 1 ? ~(result >> 1) : result >> 1;
      lat += dlat;

      result = 0;
      shift = 0;
      do {
        b = encoded.charCodeAt(index++) - 63;
        result |= (b & 0x1f) << shift;
        shift += 5;
      } while (b >= 0x20);
      const dlng = result & 1 ? ~(result >> 1) : result >> 1;
      lng += dlng;
      coordinates.push([lat / 1e5, lng / 1e5]);
    }
    return coordinates;
  }

  function polylineToSvg(encoded) {
    const points = decodePolyline(encoded);
    if (points.length < 2) return "";

    let minLat = Infinity;
    let maxLat = -Infinity;
    let minLng = Infinity;
    let maxLng = -Infinity;
    points.forEach(([la, ln]) => {
      minLat = Math.min(minLat, la);
      maxLat = Math.max(maxLat, la);
      minLng = Math.min(minLng, ln);
      maxLng = Math.max(maxLng, ln);
    });

    const pad = 0.08;
    const latSpan = Math.max(maxLat - minLat, 0.0001);
    const lngSpan = Math.max(maxLng - minLng, 0.0001);
    const width = 640;
    const height = 400;
    const path = points
      .map(([la, ln], i) => {
        const x = ((ln - minLng) / lngSpan) * (1 - pad * 2) * width + pad * width;
        const y =
          (1 - (la - minLat) / latSpan) * (1 - pad * 2) * height + pad * height;
        return `${i === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`;
      })
      .join(" ");

    return `
      <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
        <rect width="100%" height="100%" fill="#0c110e"/>
        <path d="${path}" fill="none" stroke="#b8f25a" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" opacity="0.92"/>
      </svg>
    `;
  }

  function relativeWhen(iso) {
    if (!iso) return "";
    const then = new Date(iso).getTime();
    if (Number.isNaN(then)) return "";
    const diff = Date.now() - then;
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return mins <= 1 ? "just now" : `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 48) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    if (days < 14) return `${days}d ago`;
    return formatDate(iso);
  }

  function authorAvatarHtml(author) {
    if (author?.avatar_url) {
      return `<div class="pulse-avatar"><img src="${escapeHtml(author.avatar_url)}" alt=""></div>`;
    }
    return `<div class="pulse-avatar">${escapeHtml(author?.initials || "P")}</div>`;
  }

  function renderFeedMedia(item) {
    const media = item.media || {};
    const activity = item.activity || {};
    if (media.primary_image_url) {
      return `
        <div class="feed-media">
          <img src="${escapeHtml(media.primary_image_url)}" alt="" loading="lazy" referrerpolicy="no-referrer">
        </div>
      `;
    }
    if (media.summary_polyline) {
      const svg = polylineToSvg(media.summary_polyline);
      if (svg) return `<div class="feed-media">${svg}</div>`;
    }
    const km =
      activity.distance_km != null
        ? Number(activity.distance_km).toFixed(
            Number(activity.distance_km) >= 10 ? 1 : 2
          )
        : "—";
    const bg = TILE_BACKGROUNDS[(Number(activity.id) || 0) % TILE_BACKGROUNDS.length];
    return `
      <div class="feed-media">
        <div class="feed-media-fallback" style="background:${bg}">
          <div class="tile-label">${escapeHtml((activity.type || "Run").toUpperCase())}</div>
          <div class="tile-distance">${escapeHtml(km)} KM</div>
        </div>
      </div>
    `;
  }

  function renderFeedPost(item) {
    const author = item.author || {};
    const activity = item.activity || {};
    const location = item.location?.display_name;
    const handle = author.username ? `@${author.username}` : "@runner";
    const when = relativeWhen(
      activity.start_date_local || activity.start_date || item.created_at
    );
    const distance =
      activity.distance_km != null
        ? `${Number(activity.distance_km).toFixed(
            Number(activity.distance_km) >= 10 ? 1 : 2
          )} KM`
        : "—";
    const pace = activity.pace_label ? `${activity.pace_label}/KM` : "—";
    const duration = activity.duration_label || "—";

    return `
      <article class="feed-post" data-feed-activity-id="${escapeHtml(activity.id)}">
        <div class="feed-post-head">
          ${authorAvatarHtml(author)}
          <div class="feed-post-meta">
            <strong>${escapeHtml(author.name || "Runner")}</strong>
            <span>${escapeHtml(handle)}${when ? ` · ${escapeHtml(when)}` : ""}</span>
          </div>
          <div class="feed-post-type">${escapeHtml(activity.type || "Run")}</div>
        </div>
        ${
          location
            ? `<div class="feed-location">📍 ${escapeHtml(location)}</div>`
            : `<div class="feed-location">📍 Somewhere out there</div>`
        }
        <div class="feed-title-block">
          <h3>${escapeHtml(activity.title || "Survived another one.")}</h3>
          ${
            activity.original_name
              ? `<div class="original-name">${escapeHtml(activity.original_name)}</div>`
              : ""
          }
        </div>
        ${renderFeedMedia(item)}
        <div class="feed-metrics">
          <div class="feed-metric"><span>Distance</span><strong>${escapeHtml(distance)}</strong></div>
          <div class="feed-metric"><span>Pace</span><strong>${escapeHtml(pace)}</strong></div>
          <div class="feed-metric"><span>Time</span><strong>${escapeHtml(duration)}</strong></div>
        </div>
      </article>
    `;
  }

  function renderFeed() {
    const feed = state.feed;
    let body = "";

    if (feed.status === "loading" || feed.status === "idle") {
      body = `
        <div class="feed-status">
          <h2>${escapeHtml(feed.loadingLine || "Finding the miles…")}</h2>
          <p>Pulling your runs into something worth scrolling.</p>
        </div>
        <div class="post-skeleton" aria-hidden="true">
          <article class="post-card">
            <div class="post-card-head">
              <div class="pulse-avatar">R</div>
              <div><strong>Loading</strong><div style="color:var(--faint);font-size:12px;">hold up</div></div>
            </div>
            <div class="post-card-body"></div>
          </article>
        </div>
      `;
    } else if (feed.status === "error") {
      body = `
        <div class="feed-status">
          <h2>That didn’t go the distance.</h2>
          <p>${escapeHtml(feed.error || "Try again.")}</p>
          <button type="button" class="btn btn-primary" data-action="retry-feed">Retry</button>
        </div>
      `;
    } else if (!feed.items.length) {
      body = `
        <div class="feed-empty">
          <h2 class="feed-empty-hero">No miles yet.</h2>
          <p class="feed-empty-copy">Your couch is currently undefeated. Sync Strava and change that.</p>
          <div class="cta-row">
            <button type="button" class="btn btn-primary" data-action="open-settings">Open Settings</button>
          </div>
        </div>
      `;
    } else {
      const banner = feed.message
        ? `<div class="feed-banner"><strong>${escapeHtml(
            feed.message.eyebrow || "Your runs. Front row."
          )}</strong><p>${escapeHtml(feed.message.body || "")}</p></div>`
        : "";
      body = `${banner}<div class="feed-list">${feed.items
        .map(renderFeedPost)
        .join("")}</div>`;
    }

    return `
      <section class="pulse-page" data-page="feed">
        <p class="page-kicker">Feed</p>
        <h1 class="page-title">Where runners show up.</h1>
        <p class="page-sub">Running connects people. Your miles are the content.</p>
        ${body}
      </section>
    `;
  }

  async function loadFeed(force = false) {
    if (state.feed.status === "ready" && !force) return;
    state.feed.status = "loading";
    state.feed.loadingLine =
      FEED_LOADING_LINES[Math.floor(Math.random() * FEED_LOADING_LINES.length)];
    if (state.page === "feed") render();

    try {
      const res = await apiFetch("/api/feed?limit=30");
      if (!res.ok) throw new Error("That didn’t go the distance.");
      const data = await res.json();
      state.feed.items = Array.isArray(data.items) ? data.items : [];
      state.feed.message = data.message || null;
      state.feed.status = "ready";
      state.feed.error = null;
    } catch (err) {
      state.feed.status = "error";
      state.feed.error = err.message || "Try again.";
    }

    if (state.page === "feed") render();
  }

  function renderRunnerCard(athlete) {
    const handle = athlete.handle || athlete.username;
    const handleText = handle ? `@${handle}` : "no handle yet";
    const location = athlete.location?.display_name || "Somewhere on Earth";
    const count = athlete.stats?.activity_count;
    const km = athlete.stats?.total_distance_km;
    let stats = "";
    if (count != null && count > 0) {
      stats = `${count} run${count === 1 ? "" : "s"}`;
      if (km != null) stats += ` · ${km} km`;
    } else {
      stats = "Fresh legs";
    }
    const avatarProfile = {
      avatar_url: athlete.avatar_url,
      initials: athlete.initials || "P",
    };
    return `
      <button type="button" class="runner-card" data-action="peek-athlete" data-athlete-id="${escapeHtml(athlete.athlete_id)}">
        ${renderAvatarHtml(avatarProfile)}
        <div>
          <p class="runner-card-name">${escapeHtml(athlete.name || "Runner")}</p>
          <p class="runner-card-meta">${escapeHtml(handleText)} · ${escapeHtml(location)}</p>
        </div>
        <div class="runner-card-stats">${escapeHtml(stats)}</div>
      </button>
    `;
  }

  function renderExploreSection(section) {
    const athletes = Array.isArray(section.athletes) ? section.athletes : [];
    const body =
      athletes.length === 0
        ? `<p class="explore-empty">${escapeHtml(section.empty_hint || "Nobody here yet.")}</p>`
        : `<div class="runner-list">${athletes.map(renderRunnerCard).join("")}</div>`;
    return `
      <section class="explore-section" data-explore-section="${escapeHtml(section.id || "")}">
        <div class="explore-section-head">
          <h2>${escapeHtml(section.title || "Runners")}</h2>
          <span>${athletes.length || "0"}</span>
        </div>
        ${body}
      </section>
    `;
  }

  function renderExploreBody() {
    const ex = state.explore;
    const q = (ex.searchQ || "").trim();

    if (q.length >= 2) {
      if (ex.searchStatus === "loading") {
        return `<p class="explore-empty">Scanning the streets for “${escapeHtml(q)}”…</p>`;
      }
      if (ex.searchStatus === "error") {
        return `
          <p class="explore-empty">${escapeHtml(ex.error || "Search tripped.")}</p>
          <button type="button" class="btn btn-ghost" data-action="retry-explore-search">Try again</button>
        `;
      }
      const results = ex.searchResults || [];
      if (results.length === 0) {
        return `<p class="explore-empty">No public runners match “${escapeHtml(q)}”. Try another name — or ask them to flip Show me in Explore.</p>`;
      }
      return `
        <p class="explore-results-label">${results.length} match${results.length === 1 ? "" : "es"}</p>
        <div class="runner-list">${results.map(renderRunnerCard).join("")}</div>
      `;
    }

    if (ex.status === "loading" || ex.status === "idle") {
      return `<p class="explore-empty">Finding who’s putting in the miles…</p>`;
    }
    if (ex.status === "error") {
      return `
        <p class="explore-empty">${escapeHtml(ex.error || "That didn’t go the distance.")}</p>
        <button type="button" class="btn btn-primary" data-action="retry-explore">Retry</button>
      `;
    }

    const me = ex.me || {};
    const privacy = me.is_profile_public
      ? `<div class="explore-privacy"><p>You’re visible in Explore. Own the miles.</p></div>`
      : `<div class="explore-privacy">
          <p>You’re invisible right now. Flip <strong>Show me in Explore</strong> in Settings if you want company.</p>
          <button type="button" class="btn btn-ghost" data-action="open-settings">Settings</button>
        </div>`;

    const sections = Array.isArray(ex.sections) ? ex.sections : [];
    if (sections.length === 0) {
      return `${privacy}<p class="explore-empty">Quiet streets. Public runners show up here.</p>`;
    }
    return `${privacy}${sections.map(renderExploreSection).join("")}`;
  }

  function renderExplore() {
    const q = state.explore.searchQ || "";
    const hint =
      q.trim().length >= 2
        ? `Searching public runners for “${q.trim()}”.`
        : "Type at least 2 characters. Only public profiles show up.";
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
          <input id="exploreSearch" type="search" placeholder="Who are you looking for?" autocomplete="off" value="${escapeHtml(q)}">
        </div>
        <p class="search-hint" id="exploreSearchHint">${escapeHtml(hint)}</p>
        ${renderExploreBody()}
      </section>
    `;
  }

  async function loadExplore(force = false) {
    if (!force && (state.explore.status === "ready" || state.explore.status === "loading")) {
      return;
    }
    state.explore.status = "loading";
    state.explore.error = null;
    if (state.page === "explore" && !(state.explore.searchQ || "").trim()) render();

    try {
      const res = await apiFetch("/api/explore");
      if (!res.ok) throw new Error("That didn’t go the distance.");
      const data = await res.json();
      state.explore.me = data.me || null;
      state.explore.sections = Array.isArray(data.sections) ? data.sections : [];
      state.explore.status = "ready";
      state.explore.error = null;
    } catch (err) {
      state.explore.status = "error";
      state.explore.error = err.message || "Try again.";
    }

    if (state.page === "explore" && !(state.explore.searchQ || "").trim()) render();
  }

  let exploreSearchTimer = null;

  async function runExploreSearch(query) {
    const q = (query || "").trim();
    state.explore.searchQ = q;
    if (q.length < 2) {
      state.explore.searchStatus = "idle";
      state.explore.searchResults = [];
      if (state.page === "explore") render();
      return;
    }

    state.explore.searchStatus = "loading";
    if (state.page === "explore") render();

    try {
      const res = await apiFetch(`/api/explore/search?q=${encodeURIComponent(q)}`);
      if (!res.ok) throw new Error("Search tripped.");
      const data = await res.json();
      // Ignore stale responses if the user kept typing.
      if ((state.explore.searchQ || "").trim() !== q) return;
      state.explore.searchResults = Array.isArray(data.results) ? data.results : [];
      state.explore.searchStatus = "ready";
      state.explore.error = null;
    } catch (err) {
      if ((state.explore.searchQ || "").trim() !== q) return;
      state.explore.searchStatus = "error";
      state.explore.error = err.message || "Try again.";
    }

    if (state.page === "explore") render();
  }

  function scheduleExploreSearch(query) {
    state.explore.searchQ = query;
    clearTimeout(exploreSearchTimer);
    exploreSearchTimer = setTimeout(() => runExploreSearch(query), 280);
  }

  async function peekAthlete(athleteId) {
    try {
      const res = await apiFetch(`/api/athletes/${encodeURIComponent(athleteId)}/profile`);
      if (!res.ok) {
        showToast("That runner isn’t public — or vanished.");
        return;
      }
      const athlete = await res.json();
      state.explore.peek = athlete;
      openAthletePeek(athlete);
    } catch (_err) {
      showToast("That didn’t go the distance.");
    }
  }

  function openAthletePeek(athlete) {
    const handle = athlete.handle || athlete.username;
    const location = athlete.location?.display_name || "Somewhere on Earth";
    const count = athlete.stats?.activity_count ?? 0;
    const km = athlete.stats?.total_distance_km;
    const avatarProfile = {
      avatar_url: athlete.avatar_url,
      initials: athlete.initials || "P",
    };
    els.activityModalTitle.textContent = athlete.name || "Runner";
    els.activityModalBody.innerHTML = `
      <div style="display:flex;gap:16px;align-items:center;margin-bottom:18px;">
        ${renderAvatarHtml(avatarProfile, "is-lg")}
        <div>
          <p class="profile-handle" style="margin:0">${escapeHtml(handle ? `@${handle}` : "no handle yet")}</p>
          <p class="form-hint" style="margin:6px 0 0">${escapeHtml(location)}</p>
        </div>
      </div>
      ${athlete.bio ? `<p class="profile-bio">${escapeHtml(athlete.bio)}</p>` : `<p class="form-hint">No bio. The miles speak louder anyway.</p>`}
      <div class="modal-metrics" style="margin-top:18px;">
        <div class="stat-pill"><span>Runs</span><strong>${escapeHtml(count)}</strong></div>
        <div class="stat-pill"><span>Distance</span><strong>${escapeHtml(km != null ? `${km} km` : "—")}</strong></div>
        <div class="stat-pill"><span>Last</span><strong>${escapeHtml(formatDate(athlete.last_activity_at))}</strong></div>
      </div>
      <p class="form-hint" style="margin-top:18px;">
        Follows land later. For now: look, don’t lurk.
      </p>
    `;
    els.activityModal.hidden = false;
    void els.activityModal.offsetWidth;
    els.activityModal.classList.add("is-open");
  }

  function renderCoachPage() {
    return `
      <section class="pulse-page coach-page" data-page="coach">
        <p class="page-kicker">AI Coach</p>
        <h1 class="page-title">${escapeHtml(els.coachTagline?.textContent || "Your legs don’t lie.")}</h1>
        <p class="page-sub">Advice with bite. Numbers with jokes. No clipboard energy.</p>
        ${renderCoachChat({ compact: false })}
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
    if (next === "feed") {
      loadFeed(false);
    }
    if (next === "explore") {
      loadExplore(false);
    }
    if (next === "coach") {
      loadCoachMessages(false);
    }
  }

  function render() {
    const active = document.activeElement;
    const wasExploreSearch = active && active.id === "exploreSearch";
    const selStart = wasExploreSearch ? active.selectionStart : null;
    const selEnd = wasExploreSearch ? active.selectionEnd : null;

    let html = "";
    if (state.page === "feed") html = renderFeed();
    else if (state.page === "explore") html = renderExplore();
    else if (state.page === "coach") html = renderCoachPage();
    else html = renderProfile();

    els.viewRoot.innerHTML = html;
    els.coachSidebarPanel.innerHTML = renderCoachChat({ compact: true });
    bindViewInteractions();
    wireCoachDom(els.viewRoot);
    wireCoachDom(els.coachSidebarPanel);
    scrollCoachThreads();

    if (wasExploreSearch) {
      const input = document.getElementById("exploreSearch");
      if (input) {
        input.focus();
        if (selStart != null && selEnd != null) {
          try {
            input.setSelectionRange(selStart, selEnd);
          } catch (_err) {
            /* ignore */
          }
        }
      }
    }
  }

  function bindViewInteractions() {
    els.viewRoot.querySelectorAll("[data-activity-id]").forEach((tile) => {
      tile.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        openActivity(tile.dataset.activityId);
      });
    });

    els.viewRoot.querySelectorAll("[data-action]").forEach((btn) => {
      btn.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        const action = btn.dataset.action;
        if (action === "edit-profile" || action === "open-settings") openSettings();
        if (action === "followers-tease") showToast("Nobody’s watching. Yet.");
        if (action === "following-tease") {
          showToast("Follow someone. Running alone is overrated.");
        }
        if (action === "retry-feed") loadFeed(true);
        if (action === "retry-explore") loadExplore(true);
        if (action === "retry-explore-search") runExploreSearch(state.explore.searchQ || "");
        if (action === "peek-athlete") peekAthlete(btn.dataset.athleteId);
        if (action === "clear-coach") clearCoachChat();
      });
    });

    els.viewRoot.querySelectorAll("[data-feed-activity-id]").forEach((post) => {
      post.addEventListener("click", (event) => {
        if (event.target.closest("a,button")) return;
        openActivity(post.dataset.feedActivityId);
      });
    });
  }

  function openSettings() {
    els.drawerBackdrop.hidden = false;
    els.settingsDrawer.hidden = false;
    // Force reflow so transitions apply after un-hiding.
    void els.settingsDrawer.offsetWidth;
    els.drawerBackdrop.classList.add("is-open");
    els.settingsDrawer.classList.add("is-open");
    els.settingsDrawer.setAttribute("aria-hidden", "false");
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
    let activity = state.activities.find(
      (a) => String(a.id) === String(activityId)
    );

    if (!activity) {
      const feedItem = state.feed.items.find(
        (item) => String(item.activity?.id) === String(activityId)
      );
      if (feedItem) {
        activity = {
          id: feedItem.activity.id,
          name: feedItem.activity.original_name,
          sport_type: feedItem.activity.sport_type,
          distance_m: feedItem.activity.distance_m,
          moving_time_s: feedItem.activity.moving_time_s,
          elevation_gain_m: feedItem.activity.elevation_gain_m,
          start_date_local: feedItem.activity.start_date_local,
          start_date: feedItem.activity.start_date,
        };
      }
    }

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
    void els.activityModal.offsetWidth;
    els.activityModal.classList.add("is-open");
  }

  function closeActivity() {
    els.activityModal.classList.remove("is-open");
    setTimeout(() => {
      els.activityModal.hidden = true;
    }, 250);
  }

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
    document.getElementById("settingsCity").value = profile.location?.city || "";
    document.getElementById("settingsCountry").value = profile.location?.country || "";
    document.getElementById("settingsPublicExplore").checked = !!profile.is_profile_public;
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
      state.activities = (Array.isArray(raw) ? raw : []).slice().sort((a, b) => {
        const da = new Date(a.start_date_local || a.start_date || 0).getTime();
        const db = new Date(b.start_date_local || b.start_date || 0).getTime();
        return db - da;
      });
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
        await loadFeed(true);
        if (state.page === "profile" || state.page === "feed") render();
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
      if (action === "retry-feed") loadFeed(true);
      if (action === "retry-explore") loadExplore(true);
      if (action === "retry-explore-search") runExploreSearch(state.explore.searchQ || "");
      if (action === "peek-athlete") peekAthlete(actionEl.dataset.athleteId);
      if (action === "clear-coach") clearCoachChat();
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
        city: document.getElementById("settingsCity").value,
        country: document.getElementById("settingsCountry").value,
        is_profile_public: document.getElementById("settingsPublicExplore").checked,
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
      // Refresh Explore so “Show me” / city changes land immediately.
      state.explore.status = "idle";
      if (state.page === "explore") loadExplore(true);
      if (state.page === "profile") render();
    });
  }

  function wireExploreSearch() {
    els.viewRoot.addEventListener("input", (event) => {
      if (event.target.id !== "exploreSearch") return;
      scheduleExploreSearch(event.target.value);
    });
    els.viewRoot.addEventListener("keydown", (event) => {
      if (event.target.id !== "exploreSearch") return;
      if (event.key === "Enter") {
        event.preventDefault();
        clearTimeout(exploreSearchTimer);
        runExploreSearch(event.target.value);
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
    loadCoachMessages(false);

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
      syncStrava(true).then(() =>
        Promise.all([loadProfileBundle(true), loadFeed(true)]).then(() => {
          if (state.page === "profile" || state.page === "feed") render();
        })
      );
    }
  }

  boot().catch((err) => {
    console.error(err);
  });
})();
