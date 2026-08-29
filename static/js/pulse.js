/* Pulse app shell — social structure, real profile data, honest Coming Soon. */
(() => {
  "use strict";

  const PAGES = ["feed", "explore", "messages", "coach", "profile"];
  const Copy = window.PulseCopy || null;

  const TILE_BACKGROUNDS = [
    "linear-gradient(145deg, #1f3a28 0%, #0c1410 70%)",
    "linear-gradient(160deg, #2a3320 0%, #10150f 65%)",
    "linear-gradient(135deg, #16352f 0%, #0b1211 70%)",
    "linear-gradient(150deg, #3a2f18 0%, #12100c 70%)",
    "linear-gradient(145deg, #1a2c3a 0%, #0c1116 70%)",
    "linear-gradient(155deg, #24301c 0%, #0e120c 70%)",
  ];

  function copyPick(path, key) {
    if (!Copy) return "";
    return Copy.pick(path, key);
  }

  function copyFresh(path) {
    if (!Copy) return "";
    return Copy.pickFresh(path);
  }

  function copyEmpty(kind) {
    if (!Copy) {
      return { title: "Nothing here yet.", body: "" };
    }
    return Copy.emptyState(kind);
  }

  function errLine(fallback) {
    return copyFresh("errors") || fallback || "That didn’t go the distance.";
  }

  const state = {
    page: "feed",
    profile: null,
    activities: [],
    summary: null,
    loadedProfile: false,
    viewed: {
      handle: null,
      athleteId: null,
      status: "idle",
      data: null,
      error: null,
    },
    people: {
      kind: null,
      handle: null,
      athleteId: null,
      status: "idle",
      items: [],
      error: null,
      total: 0,
      offset: 0,
      hasMore: false,
      q: "",
    },
    feed: {
      status: "idle",
      items: [],
      message: null,
      error: null,
      loadingLine: copyPick("loading", "feed.loading") || "Crunching the numbers…",
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
      suggestions: [],
    },
    inbox: {
      status: "idle",
      items: [],
      unread_total: 0,
      error: null,
    },
    thread: {
      status: "idle",
      conversationId: null,
      peer: null,
      messages: [],
      can_send: false,
      is_mutual: false,
      error: null,
      sending: false,
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
    peopleModal: document.getElementById("peopleModal"),
    peopleModalBody: document.getElementById("peopleModalBody"),
    peopleModalTitle: document.getElementById("peopleModalTitle"),
    confirmModal: document.getElementById("confirmModal"),
    confirmModalTitle: document.getElementById("confirmModalTitle"),
    confirmModalBody: document.getElementById("confirmModalBody"),
    confirmModalActions: document.getElementById("confirmModalActions"),
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
    return "New athlete";
  }

  function publicHandleLabel(person) {
    const handle = person?.handle || null;
    if (handle) return `@${handle}`;
    return "New athlete";
  }

  function displayNameOf(person) {
    return person?.display_name || person?.name || "New athlete";
  }

  function athleteIdOf(person) {
    const raw = person?.athlete_id ?? person?.id ?? person;
    const n = Number(raw);
    return Number.isFinite(n) && n > 0 ? n : null;
  }

  function profileIncomplete(profile) {
    return !profile?.handle;
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
    return copyFresh("coachTaglines") || "Your legs don’t lie.";
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

  function polylineToSvg(encoded, gradientId = "routeGlow") {
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
      <svg class="feed-route-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
        <defs>
          <linearGradient id="${escapeHtml(gradientId)}" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#d6ff7a"/>
            <stop offset="100%" stop-color="#b8f25a"/>
          </linearGradient>
        </defs>
        <rect width="100%" height="100%" fill="#0b100d"/>
        <path d="${path}" fill="none" stroke="rgba(184,242,90,0.22)" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="${path}" fill="none" stroke="url(#${escapeHtml(gradientId)})" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>
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
    const polyline = media.summary_polyline || "";
    const gradientId = `routeGlow-${escapeHtml(activity.id || "x")}`;
    const mapSvg = polyline ? polylineToSvg(polyline, gradientId) : "";
    const km =
      activity.distance_km != null
        ? Number(activity.distance_km).toFixed(
            Number(activity.distance_km) >= 10 ? 1 : 2
          )
        : "—";
    const bg = TILE_BACKGROUNDS[(Number(activity.id) || 0) % TILE_BACKGROUNDS.length];
    const fallback = `
      <div class="feed-media-fallback" style="background:${bg}">
        <div class="tile-label">${escapeHtml((activity.type || "Run").toUpperCase())}</div>
        <div class="tile-distance">${escapeHtml(km)} KM</div>
      </div>
    `;
    const mapBlock = mapSvg
      ? `<div class="feed-media-map" data-feed-map>${mapSvg}</div>`
      : "";

    if (media.primary_image_url) {
      // Photo first; if CDN fails or is tiny, reveal map underneath.
      return `
        <div class="feed-media has-photo${mapSvg ? " has-map" : ""}">
          ${mapBlock || fallback}
          <img
            class="feed-media-photo"
            src="${escapeHtml(media.primary_image_url)}"
            alt=""
            loading="lazy"
            decoding="async"
            referrerpolicy="no-referrer"
            onerror="this.classList.add('is-broken'); this.parentElement.classList.add('photo-failed');"
          >
        </div>
      `;
    }
    if (mapSvg) {
      return `<div class="feed-media has-map">${mapBlock}</div>`;
    }
    return `<div class="feed-media">${fallback}</div>`;
  }

  function renderFeedPost(item) {
    const author = item.author || {};
    const activity = item.activity || {};
    const location = item.location?.display_name;
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
          <button type="button" class="feed-author-btn" data-action="open-user" data-athlete-id="${escapeHtml(author.athlete_id || "")}" data-handle="${escapeHtml(author.handle || "")}">
            ${authorAvatarHtml(author)}
            <div class="feed-post-meta">
              <strong>${escapeHtml(displayNameOf(author))}</strong>
              <span>${escapeHtml(publicHandleLabel(author))}${when ? ` · ${escapeHtml(when)}` : ""}</span>
            </div>
          </button>
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
        ${
          (() => {
            const line = Copy ? Copy.activityInsight(activity) : null;
            return line
              ? `<p class="feed-insight">${escapeHtml(line)}</p>`
              : "";
          })()
        }
      </article>
    `;
  }

  function renderFeed() {
    const feed = state.feed;
    let body = "";

    if (feed.status === "loading" || feed.status === "idle") {
      body = `
        <div class="feed-status">
          <h2>${escapeHtml(feed.loadingLine || "Crunching the numbers…")}</h2>
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
          <h2>${escapeHtml(errLine())}</h2>
          <p>${escapeHtml(feed.error || "Try again.")}</p>
          <button type="button" class="btn btn-primary" data-action="retry-feed">Retry</button>
        </div>
      `;
    } else if (!feed.items.length) {
      const empty = copyEmpty("feed");
      body = `
        <div class="feed-empty empty-state-block">
          <h2 class="feed-empty-hero">${escapeHtml(empty.title)}</h2>
          <p class="feed-empty-copy">${escapeHtml(empty.body)}</p>
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
    state.feed.loadingLine = copyFresh("loading") || "Crunching the numbers…";
    if (state.page === "feed") render();

    try {
      const res = await apiFetch("/api/feed?limit=30");
      if (!res.ok) throw new Error(errLine());
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
    const athleteId = athleteIdOf(athlete);
    const handle = athlete.handle || "";
    const handleText = publicHandleLabel(athlete);
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
    const idAttr = athleteId ? `data-athlete-id="${escapeHtml(athleteId)}"` : "";
    const followCtl = !athleteId
      ? ""
      : athlete.is_following
        ? `<button type="button" class="btn btn-ghost btn-follow is-following" data-action="confirm-unfollow" ${idAttr} data-handle="${escapeHtml(handle)}">Following</button>`
        : `<button type="button" class="btn btn-primary btn-follow" data-action="follow-user" ${idAttr} data-handle="${escapeHtml(handle)}">Follow</button>`;
    return `
      <div class="runner-card-wrap">
        <button type="button" class="runner-card" data-action="open-user" ${idAttr} data-handle="${escapeHtml(handle)}">
          ${renderAvatarHtml(avatarProfile)}
          <div>
            <p class="runner-card-name">${escapeHtml(displayNameOf(athlete))}</p>
            <p class="runner-card-meta">${escapeHtml(handleText)} · ${escapeHtml(location)}</p>
            <p class="runner-card-stats is-inline">${escapeHtml(stats)}</p>
          </div>
        </button>
        ${followCtl}
      </div>
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
    const incompleteHint =
      profileIncomplete(state.profile) || profileIncomplete(me)
        ? `<div class="explore-privacy explore-hint"><p>Complete your profile to help people find you.</p><button type="button" class="btn btn-ghost" data-action="edit-profile">Edit Profile</button></div>`
        : "";
    const privacy = me.is_profile_public
      ? `<div class="explore-privacy"><p>You’re visible in Explore. Own the miles.</p></div>`
      : `<div class="explore-privacy">
          <p>You’re invisible right now. Flip <strong>Show me in Explore</strong> in Settings if you want company.</p>
          <button type="button" class="btn btn-ghost" data-action="open-settings">Settings</button>
        </div>`;

    const suggestions = Array.isArray(ex.suggestions) ? ex.suggestions : [];
    const suggestedBlock =
      suggestions.length === 0
        ? ""
        : `
      <section class="explore-section" data-explore-section="suggested">
        <div class="explore-section-head">
          <h2>Suggested for you</h2>
          <span>${suggestions.length}</span>
        </div>
        <div class="runner-list">${suggestions.map(renderRunnerCard).join("")}</div>
      </section>`;

    const sections = Array.isArray(ex.sections) ? ex.sections : [];
    if (sections.length === 0 && suggestions.length === 0) {
      const empty = copyEmpty("explore");
      return `${incompleteHint}${privacy}<div class="empty-state-block" style="margin-top:28px"><h2>${escapeHtml(
        empty.title
      )}</h2><p>${escapeHtml(empty.body)}</p></div>`;
    }
    return `${incompleteHint}${privacy}${suggestedBlock}${sections.map(renderExploreSection).join("")}`;
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
      const [res, sugRes] = await Promise.all([
        apiFetch("/api/explore"),
        apiFetch("/api/profiles/suggestions?limit=6"),
      ]);
      if (!res.ok) throw new Error("That didn’t go the distance.");
      const data = await res.json();
      state.explore.me = data.me || null;
      state.explore.sections = Array.isArray(data.sections) ? data.sections : [];
      if (sugRes.ok) {
        const sug = await sugRes.json();
        state.explore.suggestions = Array.isArray(sug.people) ? sug.people : [];
      } else {
        state.explore.suggestions = [];
      }
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
    const location = athlete.location?.display_name || "Somewhere on Earth";
    const count = athlete.stats?.activity_count ?? 0;
    const km = athlete.stats?.total_distance_km;
    const avatarProfile = {
      avatar_url: athlete.avatar_url,
      initials: athlete.initials || "P",
    };
    const athleteId = athleteIdOf(athlete);
    const followCtl = athleteId
      ? athlete.is_following
        ? `<button type="button" class="btn btn-ghost btn-follow is-following" data-action="confirm-unfollow" data-athlete-id="${escapeHtml(athleteId)}" data-handle="${escapeHtml(athlete.handle || "")}">Following</button>`
        : `<button type="button" class="btn btn-primary btn-follow" data-action="follow-user" data-athlete-id="${escapeHtml(athleteId)}" data-handle="${escapeHtml(athlete.handle || "")}">Follow</button>`
      : "";
    els.activityModalTitle.textContent = displayNameOf(athlete);
    els.activityModalBody.innerHTML = `
      <div style="display:flex;gap:16px;align-items:center;margin-bottom:18px;">
        ${renderAvatarHtml(avatarProfile, "is-lg")}
        <div>
          <p class="profile-handle" style="margin:0">${escapeHtml(publicHandleLabel(athlete))}</p>
          <p class="form-hint" style="margin:6px 0 0">${escapeHtml(location)}</p>
        </div>
      </div>
      ${athlete.bio ? `<p class="profile-bio">${escapeHtml(athlete.bio)}</p>` : `<p class="form-hint">No bio. The miles speak louder anyway.</p>`}
      <div class="modal-metrics" style="margin-top:18px;">
        <div class="stat-pill"><span>Runs</span><strong>${escapeHtml(count)}</strong></div>
        <div class="stat-pill"><span>Distance</span><strong>${escapeHtml(km != null ? `${km} km` : "—")}</strong></div>
        <div class="stat-pill"><span>Last</span><strong>${escapeHtml(formatDate(athlete.last_activity_at))}</strong></div>
      </div>
      <div class="profile-actions" style="margin-top:18px;">
        ${followCtl}
        ${
          athleteId
            ? `<button type="button" class="btn btn-ghost" data-action="open-user" data-athlete-id="${escapeHtml(athleteId)}" data-handle="${escapeHtml(athlete.handle || "")}">Open profile</button>`
            : ""
        }
      </div>
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

    const followers = Number(p.follower_count || 0);
    const following = Number(p.following_count || 0);
    const grid =
      state.activities.length === 0
        ? (() => {
            const empty = copyEmpty("activities");
            return `<div class="tile-empty empty-state-block"><strong>${escapeHtml(
              empty.title
            )}</strong><br><span style="color:var(--faint)">${escapeHtml(
              empty.body
            )}</span></div>`;
          })()
        : state.activities.map(renderActivityTile).join("");

    const insightLine =
      Copy && Copy.profileInsight ? Copy.profileInsight(p, state.activities) : null;
    const insight = insightLine
      ? `<p class="profile-insight">${escapeHtml(insightLine)}</p>`
      : "";

    return `
      <section class="pulse-page" data-page="profile">
        <p class="page-kicker">Profile</p>
        <div class="profile-header">
          ${renderAvatarHtml(p, "is-lg")}
          <div class="profile-identity">
            <h1>${escapeHtml(p.display_name || "Runner")}</h1>
            <p class="profile-handle">${escapeHtml(handleLabel(p))}</p>
            ${p.bio ? `<p class="profile-bio">${escapeHtml(p.bio)}</p>` : ""}
            ${insight}
            <div class="profile-social profile-social-counts">
              <button type="button" class="profile-count" disabled><strong>${escapeHtml(
                Number(p.posts_count ?? p.stats?.total_activities ?? state.activities.length)
              )}</strong> posts</button>
              <button type="button" class="profile-count" data-action="open-followers" data-athlete-id="${escapeHtml(p.athlete_id || "")}" data-handle="${escapeHtml(p.handle || "")}"><strong>${escapeHtml(followers)}</strong> followers</button>
              <button type="button" class="profile-count" data-action="open-following" data-athlete-id="${escapeHtml(p.athlete_id || "")}" data-handle="${escapeHtml(p.handle || "")}"><strong>${escapeHtml(following)}</strong> following</button>
            </div>
            <div class="profile-actions">
              <button type="button" class="btn btn-primary" data-action="edit-profile">Edit Profile</button>
              <button type="button" class="btn btn-ghost" data-action="open-settings">Settings</button>
            </div>
            ${
              profileIncomplete(p)
                ? `<p class="form-hint" style="margin-top:10px">Complete your profile to help people find you.</p>`
                : ""
            }
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

  function renderViewedProfile() {
    const v = state.viewed;
    if (v.status === "loading" || v.status === "idle") {
      return `
        <section class="pulse-page">
          <p class="page-kicker">Profile</p>
          <h1 class="page-title">Finding that runner…</h1>
        </section>
      `;
    }
    if (v.status === "error" || !v.data) {
      return `
        <section class="pulse-page">
          <p class="page-kicker">Profile</p>
          <h1 class="page-title">Ghost mile.</h1>
          <p class="page-sub">${escapeHtml(v.error || "That profile isn’t public — or vanished.")}</p>
          <button type="button" class="btn btn-primary" data-nav="explore">Back to Explore</button>
        </section>
      `;
    }

    const p = v.data;
    if (p.is_self) {
      // Prefer own profile chrome with edit.
      return renderProfile();
    }

    const stats = p.stats || {};
    const distance =
      stats.total_distance_km != null ? Number(stats.total_distance_km).toFixed(1) : "—";
    const runs = stats.activity_count ?? (p.activities || []).length;
    const timeLabel =
      stats.total_moving_time_s != null
        ? formatDuration(stats.total_moving_time_s)
        : "—";
    const followers = Number(p.follower_count || 0);
    const following = Number(p.following_count || 0);
    const activities = Array.isArray(p.activities) ? p.activities : [];
    const grid =
      activities.length === 0
        ? `<div class="tile-empty">Zero miles. Plenty of potential.</div>`
        : activities
            .map((a, i) =>
              renderActivityTile(
                {
                  id: a.id,
                  name: a.name,
                  sport_type: a.sport_type,
                  distance_m: a.distance_m,
                  moving_time_s: a.moving_time_s,
                  start_date_local: a.start_date_local,
                  start_date: a.start_date,
                },
                i
              )
            )
            .join("");

    const athleteId = athleteIdOf(p);
    const idAttr = athleteId ? `data-athlete-id="${escapeHtml(athleteId)}"` : "";
    const followBtn = p.is_following
      ? `<button type="button" class="btn btn-ghost btn-follow is-following" data-action="confirm-unfollow" ${idAttr} data-handle="${escapeHtml(p.handle || "")}">${
          p.is_mutual ? "Friends" : "Following"
        }</button>`
      : `<button type="button" class="btn btn-primary btn-follow" data-action="follow-user" ${idAttr} data-handle="${escapeHtml(p.handle || "")}">Follow</button>`;

    const followedBy =
      p.is_followed_by && !p.is_following
        ? `<p class="form-hint" style="margin-top:8px">Follows you</p>`
        : p.is_mutual
          ? `<p class="form-hint" style="margin-top:8px">You follow each other</p>`
          : "";

    return `
      <section class="pulse-page" data-page="u">
        <p class="page-kicker">Profile</p>
        <div class="profile-header">
          ${renderAvatarHtml(p, "is-lg")}
          <div class="profile-identity">
            <h1>${escapeHtml(displayNameOf(p))}</h1>
            <p class="profile-handle">${escapeHtml(publicHandleLabel(p))}</p>
            ${p.bio ? `<p class="profile-bio">${escapeHtml(p.bio)}</p>` : ""}
            ${
              p.location?.display_name
                ? `<p class="profile-handle" style="margin-top:-6px">${escapeHtml(p.location.display_name)}</p>`
                : ""
            }
            <div class="profile-social profile-social-counts">
              <button type="button" class="profile-count" disabled><strong>${escapeHtml(
                Number(p.posts_count ?? p.stats?.activity_count ?? activities.length)
              )}</strong> posts</button>
              <button type="button" class="profile-count" data-action="open-followers" ${idAttr} data-handle="${escapeHtml(p.handle || "")}"><strong>${escapeHtml(followers)}</strong> followers</button>
              <button type="button" class="profile-count" data-action="open-following" ${idAttr} data-handle="${escapeHtml(p.handle || "")}"><strong>${escapeHtml(following)}</strong> following</button>
            </div>
            <div class="profile-actions">
              ${followBtn}
              ${
                p.is_mutual
                  ? `<button type="button" class="btn btn-primary btn-message" data-action="open-dm" ${idAttr} data-handle="${escapeHtml(p.handle || "")}">Message</button>`
                  : `<p class="form-hint dm-mutual-hint">Follow each other to start messaging.</p>`
              }
            </div>
            ${followedBy}
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

  /* ——— Direct messages (mutual-follow only) ——— */

  function dmRelativeTime(iso) {
    if (!iso) return "";
    const then = new Date(iso).getTime();
    if (Number.isNaN(then)) return "";
    const diff = Date.now() - then;
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "now";
    if (mins < 60) return `${mins}m`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h`;
    const days = Math.floor(hours / 24);
    if (days < 7) return `${days}d`;
    return formatDate(iso);
  }

  function dmClock(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "";
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  function updateDmBadges(count) {
    const n = Number(count) || 0;
    ["sidebarDmBadge", "bottomDmBadge"].forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;
      if (n > 0) {
        el.hidden = false;
        el.textContent = n > 99 ? "99+" : String(n);
      } else {
        el.hidden = true;
        el.textContent = "0";
      }
    });
  }

  function renderInboxRow(item) {
    const peer = item.peer || {};
    const last = item.last_message;
    const preview = last
      ? `${last.is_mine ? "You: " : ""}${last.content || ""}`
      : "Say hi — the miles can wait.";
    const unread = Number(item.unread_count || 0);
    const when = dmRelativeTime(item.last_message_at || item.updated_at);
    return `
      <button type="button" class="dm-inbox-row ${unread ? "is-unread" : ""}" data-action="open-thread" data-conversation-id="${escapeHtml(item.id)}">
        ${renderAvatarHtml(peer, "is-dm")}
        <div class="dm-inbox-meta">
          <div class="dm-inbox-top">
            <strong>${escapeHtml(displayNameOf(peer))}</strong>
            <span class="dm-inbox-time">${escapeHtml(when)}</span>
          </div>
          <div class="dm-inbox-preview ${unread ? "is-unread" : ""}">${escapeHtml(preview)}</div>
        </div>
        ${unread ? `<span class="dm-unread-dot" aria-label="${unread} unread"></span>` : ""}
      </button>
    `;
  }

  function renderMessagesInbox() {
    const inbox = state.inbox;
    let body = "";
    if (inbox.status === "loading" || inbox.status === "idle") {
      body = `<div class="dm-empty"><p>Loading messages…</p></div>`;
    } else if (inbox.status === "error") {
      body = `
        <div class="dm-empty">
          <p>${escapeHtml(inbox.error || errLine())}</p>
          <button type="button" class="btn btn-primary" data-action="retry-inbox">Retry</button>
        </div>`;
    } else if (!inbox.items.length) {
      body = `
        <div class="dm-empty">
          <h2>Your inbox is quiet.</h2>
          <p>Messages open when you follow each other. Find runners in Explore.</p>
          <button type="button" class="btn btn-primary" data-nav="explore">Explore</button>
        </div>`;
    } else {
      body = `<div class="dm-inbox-list">${inbox.items.map(renderInboxRow).join("")}</div>`;
    }

    return `
      <section class="pulse-page dm-page dm-inbox-page" data-page="messages">
        <header class="dm-topbar">
          <h1 class="dm-title">Messages</h1>
        </header>
        ${body}
      </section>
    `;
  }

  function renderDmBubbles(messages) {
    if (!messages.length) {
      return `<div class="dm-empty-thread"><p>No messages yet. Say something.</p></div>`;
    }
    let html = "";
    let prevSender = null;
    messages.forEach((msg, idx) => {
      const mine = !!msg.is_mine;
      const same = prevSender === msg.sender_id;
      const next = messages[idx + 1];
      const nextSame = next && next.sender_id === msg.sender_id;
      const classes = [
        "dm-bubble",
        mine ? "is-mine" : "is-theirs",
        same ? "is-grouped" : "",
        nextSame ? "is-stack" : "is-tail",
      ]
        .filter(Boolean)
        .join(" ");
      html += `
        <div class="dm-bubble-row ${mine ? "is-mine" : "is-theirs"} ${same ? "is-grouped" : ""}">
          <div class="${classes}">
            <p>${escapeHtml(msg.content)}</p>
            ${!nextSame ? `<time>${escapeHtml(dmClock(msg.created_at))}</time>` : ""}
          </div>
        </div>`;
      prevSender = msg.sender_id;
    });
    return html;
  }

  function renderDmThread() {
    const t = state.thread;
    const peer = t.peer || {};
    if (t.status === "loading" || t.status === "idle") {
      return `
        <section class="pulse-page dm-page dm-thread-page" data-page="dm">
          <header class="dm-thread-top">
            <button type="button" class="dm-back" data-action="back-inbox" aria-label="Back">←</button>
            <h1 class="dm-title">Messages</h1>
          </header>
          <div class="dm-empty"><p>Opening chat…</p></div>
        </section>`;
    }
    if (t.status === "error") {
      return `
        <section class="pulse-page dm-page dm-thread-page" data-page="dm">
          <header class="dm-thread-top">
            <button type="button" class="dm-back" data-action="back-inbox" aria-label="Back">←</button>
            <h1 class="dm-title">Messages</h1>
          </header>
          <div class="dm-empty">
            <p>${escapeHtml(t.error || errLine())}</p>
            <button type="button" class="btn btn-primary" data-action="back-inbox">Back to inbox</button>
          </div>
        </section>`;
    }

    const composer = t.can_send
      ? `
        <form class="dm-composer" id="dmComposer" autocomplete="off">
          <input type="text" id="dmInput" maxlength="2000" placeholder="Message…" enterkeyhint="send" />
          <button type="submit" class="dm-send" aria-label="Send" ${t.sending ? "disabled" : ""}>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12l15-7-6 14-2-5-7-2z"/></svg>
          </button>
        </form>`
      : `
        <div class="dm-readonly">
          You can message each other again when you both follow each other.
        </div>`;

    return `
      <section class="pulse-page dm-page dm-thread-page is-open" data-page="dm">
        <header class="dm-thread-top">
          <button type="button" class="dm-back" data-action="back-inbox" aria-label="Back">←</button>
          <button type="button" class="dm-peer" data-action="open-user" data-athlete-id="${escapeHtml(peer.athlete_id || "")}" data-handle="${escapeHtml(peer.handle || "")}">
            ${renderAvatarHtml(peer, "is-sm")}
            <div>
              <strong>${escapeHtml(displayNameOf(peer))}</strong>
              <span>${escapeHtml(publicHandleLabel(peer))}</span>
            </div>
          </button>
        </header>
        <div class="dm-thread-scroll" id="dmThreadScroll">
          ${renderDmBubbles(t.messages)}
        </div>
        ${composer}
      </section>
    `;
  }

  async function loadInbox(force = false) {
    if (state.inbox.status === "ready" && !force) return;
    state.inbox.status = "loading";
    if (state.page === "messages") render();
    try {
      const res = await apiFetch("/api/dms?limit=60");
      if (!res.ok) throw new Error(errLine());
      const data = await res.json();
      state.inbox.items = Array.isArray(data.items) ? data.items : [];
      state.inbox.unread_total = Number(data.unread_total || 0);
      state.inbox.status = "ready";
      state.inbox.error = null;
      updateDmBadges(state.inbox.unread_total);
    } catch (err) {
      state.inbox.status = "error";
      state.inbox.error = err.message || errLine();
    }
    if (state.page === "messages") render();
  }

  async function refreshUnreadBadge() {
    try {
      const res = await apiFetch("/api/dms/unread-count");
      if (!res.ok) return;
      const data = await res.json();
      state.inbox.unread_total = Number(data.unread_total || 0);
      updateDmBadges(state.inbox.unread_total);
    } catch (_err) {
      /* ignore */
    }
  }

  function navigateDm(conversationId, { replace = false } = {}) {
    state.page = "dm";
    state.thread.conversationId = conversationId;
    setNavActive("messages");
    document.body.classList.add("dm-thread-active");
    const hash = `#dm/${encodeURIComponent(conversationId)}`;
    if (replace) history.replaceState({ page: "dm", conversationId }, "", hash);
    else history.pushState({ page: "dm", conversationId }, "", hash);
    render();
    loadThread(conversationId, true);
  }

  function navigateInbox({ replace = false } = {}) {
    document.body.classList.remove("dm-thread-active");
    navigate("messages", { replace });
    loadInbox(true);
  }

  async function openDmWithPeer(athleteId) {
    if (!athleteId) {
      showToast("That runner went missing.");
      return;
    }
    try {
      const res = await apiFetch(`/api/dms/with/${encodeURIComponent(athleteId)}`, {
        method: "POST",
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        showToast(data.detail || "Follow each other to start messaging.");
        return;
      }
      navigateDm(data.id);
    } catch (err) {
      showToast(err.message || errLine());
    }
  }

  async function loadThread(conversationId, markRead = true) {
    state.thread.status = "loading";
    state.thread.conversationId = conversationId;
    state.thread.error = null;
    render();
    try {
      const res = await apiFetch(
        `/api/dms/${encodeURIComponent(conversationId)}/messages?limit=80`
      );
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || errLine());
      }
      const conv = data.conversation || {};
      state.thread.peer = conv.peer || null;
      state.thread.can_send = !!conv.can_send;
      state.thread.is_mutual = !!conv.is_mutual;
      state.thread.messages = Array.isArray(data.messages) ? data.messages : [];
      state.thread.status = "ready";
      if (markRead) {
        await apiFetch(`/api/dms/${encodeURIComponent(conversationId)}/read`, {
          method: "POST",
        }).catch(() => null);
        await refreshUnreadBadge();
      }
    } catch (err) {
      state.thread.status = "error";
      state.thread.error = err.message || errLine();
    }
    render();
    requestAnimationFrame(() => {
      const sc = document.getElementById("dmThreadScroll");
      if (sc) sc.scrollTop = sc.scrollHeight;
    });
  }

  async function sendDmMessage(raw) {
    const text = String(raw || "").trim();
    if (!text || !state.thread.conversationId || state.thread.sending) return;
    if (!state.thread.can_send) {
      showToast("You can message each other again when you both follow each other.");
      return;
    }
    state.thread.sending = true;
    render();
    try {
      const res = await apiFetch(
        `/api/dms/${encodeURIComponent(state.thread.conversationId)}/messages`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content: text }),
        }
      );
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        if (res.status === 403) {
          state.thread.can_send = false;
          state.thread.is_mutual = false;
        }
        throw new Error(data.detail || errLine());
      }
      state.thread.messages = [...state.thread.messages, data];
      state.thread.sending = false;
      // Keep inbox preview fresh next visit
      state.inbox.status = "idle";
      render();
      requestAnimationFrame(() => {
        const sc = document.getElementById("dmThreadScroll");
        if (sc) sc.scrollTop = sc.scrollHeight;
        const input = document.getElementById("dmInput");
        if (input) input.focus();
      });
    } catch (err) {
      state.thread.sending = false;
      render();
      showToast(err.message || errLine());
    }
  }

  function wireDmComposer() {
    const form = document.getElementById("dmComposer");
    if (!form || form.dataset.bound === "1") return;
    form.dataset.bound = "1";
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const input = document.getElementById("dmInput");
      const value = input ? input.value : "";
      if (input) input.value = "";
      sendDmMessage(value);
    });
  }

  /* ——— Routing ——— */

  function parseLocationHash() {
    const raw = (location.hash || "#feed").slice(1);
    if (raw.startsWith("u/")) {
      const handle = decodeURIComponent(raw.slice(2)).replace(/^@/, "").trim();
      return { page: "u", handle, athleteId: null, conversationId: null };
    }
    if (raw.startsWith("id/")) {
      const athleteId = athleteIdOf(decodeURIComponent(raw.slice(3)).trim());
      return { page: "u", handle: null, athleteId, conversationId: null };
    }
    if (raw.startsWith("dm/")) {
      const conversationId = decodeURIComponent(raw.slice(3)).trim();
      return {
        page: "dm",
        handle: null,
        athleteId: null,
        conversationId: conversationId || null,
      };
    }
    const page = PAGES.includes(raw) ? raw : "feed";
    return { page, handle: null, athleteId: null, conversationId: null };
  }

  function navigate(page, { replace = false } = {}) {
    const next = PAGES.includes(page) ? page : "feed";
    state.page = next;
    state.viewed.handle = null;
    state.viewed.athleteId = null;
    if (next !== "dm") {
      document.body.classList.remove("dm-thread-active");
      state.thread.conversationId = null;
    }
    setNavActive(next === "dm" ? "messages" : next);
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
    if (next === "messages") {
      loadInbox(true);
    }
    if (next === "coach") {
      loadCoachMessages(false);
    }
  }

  function openUserProfile(ref, { replace = false } = {}) {
    let athleteId = null;
    let handle = null;
    if (ref && typeof ref === "object") {
      athleteId = athleteIdOf(ref.athleteId ?? ref.athlete_id ?? ref.id);
      handle = String(ref.handle || "")
        .trim()
        .replace(/^@/, "");
    } else if (typeof ref === "string" || typeof ref === "number") {
      const asId = athleteIdOf(ref);
      const asHandle = String(ref || "")
        .trim()
        .replace(/^@/, "");
      // Numeric-only strings are athlete ids; handles are alphanumeric/underscore.
      if (/^\d+$/.test(asHandle) && asId) {
        athleteId = asId;
      } else {
        handle = asHandle;
      }
    }

    if (!athleteId && !handle) {
      showToast("That runner isn’t available yet.");
      return;
    }

    const meId = athleteIdOf(state.profile);
    if (
      (athleteId && meId && athleteId === meId) ||
      (handle && state.profile?.handle && state.profile.handle === handle)
    ) {
      navigate("profile", { replace });
      return;
    }

    state.page = "u";
    state.viewed.handle = handle || null;
    state.viewed.athleteId = athleteId;
    setNavActive("profile");

    let hash;
    if (handle) {
      hash = `#u/${encodeURIComponent(handle)}`;
    } else {
      hash = `#id/${encodeURIComponent(String(athleteId))}`;
    }
    const hist = { page: "u", handle: handle || null, athleteId };
    if (replace) {
      history.replaceState(hist, "", hash);
    } else if (location.hash !== hash) {
      history.pushState(hist, "", hash);
    }
    if (athleteId) {
      loadViewedProfileById(athleteId, true);
    } else {
      loadViewedProfile(handle, true);
    }
    render();
  }

  function openUserFromEl(el) {
    if (!el) return;
    openUserProfile({
      athleteId: el.dataset.athleteId,
      handle: el.dataset.handle,
    });
  }

  async function loadViewedProfileById(athleteId, force = false) {
    const id = athleteIdOf(athleteId);
    if (!id) return;
    if (
      !force &&
      state.viewed.athleteId === id &&
      state.viewed.status === "ready" &&
      state.viewed.data
    ) {
      return;
    }
    state.viewed.athleteId = id;
    state.viewed.status = "loading";
    state.viewed.error = null;
    if (state.page === "u") render();

    try {
      const res = await apiFetch(`/api/users/${encodeURIComponent(id)}`);
      if (res.status === 404) throw new Error("That profile isn’t public — or vanished.");
      if (!res.ok) throw new Error("That didn’t go the distance.");
      const data = await res.json();
      if (state.viewed.athleteId !== id) return;
      state.viewed.data = data;
      state.viewed.handle = data.handle || null;
      state.viewed.status = "ready";
      if (data.is_self && state.profile) {
        state.profile.follower_count = data.follower_count;
        state.profile.following_count = data.following_count;
        if (data.handle) state.profile.handle = data.handle;
      }
    } catch (err) {
      if (state.viewed.athleteId !== id) return;
      state.viewed.status = "error";
      state.viewed.error = err.message || "Try again.";
      state.viewed.data = null;
    }

    if (state.page === "u") render();
  }

  async function loadViewedProfile(handle, force = false) {
    const clean = String(handle || "").trim().replace(/^@/, "");
    if (!clean) return;
    if (
      !force &&
      state.viewed.handle === clean &&
      state.viewed.status === "ready" &&
      state.viewed.data
    ) {
      return;
    }
    state.viewed.handle = clean;
    state.viewed.status = "loading";
    state.viewed.error = null;
    if (state.page === "u") render();

    try {
      const res = await apiFetch(`/api/profiles/${encodeURIComponent(clean)}`);
      if (res.status === 404) throw new Error("That profile isn’t public — or vanished.");
      if (!res.ok) throw new Error("That didn’t go the distance.");
      const data = await res.json();
      if (state.viewed.handle !== clean) return;
      state.viewed.data = data;
      state.viewed.athleteId = athleteIdOf(data);
      state.viewed.status = "ready";
      if (data.is_self) {
        if (state.profile) {
          state.profile.follower_count = data.follower_count;
          state.profile.following_count = data.following_count;
          if (data.handle) state.profile.handle = data.handle;
        }
      }
    } catch (err) {
      if (state.viewed.handle !== clean) return;
      state.viewed.status = "error";
      state.viewed.error = err.message || "Try again.";
      state.viewed.data = null;
    }

    if (state.page === "u") render();
  }

  let followInFlight = new Set();
  let followGhostGuardUntil = 0;

  function followButtonsFor(athleteId) {
    const id = athleteIdOf(athleteId);
    if (!id) return [];
    return Array.from(document.querySelectorAll(".btn-follow[data-athlete-id]")).filter(
      (el) => athleteIdOf(el.dataset.athleteId) === id
    );
  }

  function applyFollowButtonDom(athleteId, { isFollowing, isMutual }) {
    const id = athleteIdOf(athleteId);
    followButtonsFor(id).forEach((btn) => {
      btn.disabled = false;
      btn.dataset.armed = "0";
      btn.classList.toggle("is-following", !!isFollowing);
      btn.classList.remove("is-unfollow");
      if (isFollowing) {
        btn.dataset.action = "confirm-unfollow";
        btn.textContent = isMutual ? "Friends" : "Following";
        btn.classList.add("btn-ghost");
        btn.classList.remove("btn-primary");
      } else {
        btn.dataset.action = "follow-user";
        btn.textContent = "Follow";
        btn.classList.add("btn-primary");
        btn.classList.remove("btn-ghost");
      }
    });
  }

  function applyFollowerCountDom(count) {
    document
      .querySelectorAll('[data-action="open-followers"] strong')
      .forEach((el) => {
        el.textContent = String(count);
      });
  }

  function syncExploreFollowFlag(athleteId, isFollowing) {
    const id = athleteIdOf(athleteId);
    if (!id) return;
    const mark = (list) =>
      (list || []).map((a) =>
        athleteIdOf(a) === id ? { ...a, is_following: isFollowing } : a
      );
    state.explore.suggestions = mark(state.explore.suggestions);
    state.explore.searchResults = mark(state.explore.searchResults);
    state.explore.sections = (state.explore.sections || []).map((section) => ({
      ...section,
      athletes: mark(section.athletes),
    }));
  }

  async function toggleFollow(ref, wantFollow) {
    const athleteId =
      typeof ref === "object" && ref !== null
        ? athleteIdOf(ref.athleteId ?? ref.athlete_id ?? ref.id)
        : athleteIdOf(ref);
    if (!athleteId) {
      showToast("That runner isn’t available yet.");
      return;
    }
    if (Date.now() < followGhostGuardUntil) return;
    if (followInFlight.has(athleteId)) return;
    followInFlight.add(athleteId);
    followGhostGuardUntil = Date.now() + 450;

    const prevViewed = state.viewed.data ? { ...state.viewed.data } : null;
    const prevPeople = state.people.items.map((p) => ({ ...p }));
    const viewingThis =
      state.viewed.athleteId === athleteId ||
      athleteIdOf(state.viewed.data) === athleteId;

    // Optimistic UI — update DOM in place (no full re-render mid-tap on mobile).
    if (viewingThis && state.viewed.data) {
      const delta = wantFollow ? 1 : -1;
      const nextCount = Math.max(
        0,
        Number(state.viewed.data.follower_count || 0) + delta
      );
      state.viewed.data = {
        ...state.viewed.data,
        is_following: wantFollow,
        is_mutual: wantFollow && !!state.viewed.data.is_followed_by,
        follower_count: nextCount,
        followers_count: nextCount,
      };
      applyFollowButtonDom(athleteId, {
        isFollowing: wantFollow,
        isMutual: state.viewed.data.is_mutual,
      });
      applyFollowerCountDom(nextCount);
    }

    state.people.items = state.people.items.map((p) => {
      if (athleteIdOf(p) !== athleteId) return p;
      return { ...p, is_following: wantFollow };
    });
    syncExploreFollowFlag(athleteId, wantFollow);
    if (els.peopleModal && !els.peopleModal.hidden) paintPeopleModal();
    if (state.page === "explore") {
      // Keep Explore follow buttons in sync without remounting mid-tap when possible.
      applyFollowButtonDom(athleteId, { isFollowing: wantFollow, isMutual: false });
    }

    try {
      const path = `/api/users/${encodeURIComponent(athleteId)}/follow`;
      const res = await apiFetch(path, { method: wantFollow ? "POST" : "DELETE" });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(
          typeof err.detail === "string" ? err.detail : "That didn’t go the distance."
        );
      }
      const data = await res.json();
      if (viewingThis) {
        state.viewed.data = { ...(state.viewed.data || {}), ...data };
        state.viewed.athleteId = athleteIdOf(data) || athleteId;
        state.viewed.handle = data.handle || state.viewed.handle;
        state.viewed.status = "ready";
        applyFollowButtonDom(athleteId, {
          isFollowing: !!data.is_following,
          isMutual: !!data.is_mutual,
        });
        applyFollowerCountDom(
          Number(data.follower_count ?? data.followers_count ?? 0)
        );
      }
      syncExploreFollowFlag(athleteId, !!data.is_following);
      applyFollowButtonDom(athleteId, {
        isFollowing: !!data.is_following,
        isMutual: !!data.is_mutual,
      });
      if (wantFollow && Math.random() < 0.55) {
        const line = copyFresh("follow");
        if (line) showToast(line);
      } else if (!wantFollow) {
        const line = copyFresh("success.unfollow");
        if (line) showToast(line);
      }
      // Refresh own following count quietly — do not remount mid-interaction.
      loadProfileBundle(true).catch(() => {});
      if (els.peopleModal && !els.peopleModal.hidden) {
        openPeopleList(state.people.kind, {
          athleteId: state.people.athleteId,
          handle: state.people.handle,
        }, true);
      }
    } catch (err) {
      if (prevViewed && viewingThis) {
        state.viewed.data = prevViewed;
        applyFollowButtonDom(athleteId, {
          isFollowing: !!prevViewed.is_following,
          isMutual: !!prevViewed.is_mutual,
        });
        applyFollowerCountDom(Number(prevViewed.follower_count || 0));
      }
      state.people.items = prevPeople;
      syncExploreFollowFlag(athleteId, !wantFollow);
      if (els.peopleModal && !els.peopleModal.hidden) paintPeopleModal();
      if (state.page === "explore") render();
      showToast(err.message || errLine());
    } finally {
      followInFlight.delete(athleteId);
    }
  }

  function renderPeopleRow(person) {
    const athleteId = athleteIdOf(person);
    const handle = person.handle || "";
    const idAttr = athleteId ? `data-athlete-id="${escapeHtml(athleteId)}"` : "";
    const followCtl = person.is_self
      ? `<span class="form-hint">You</span>`
      : !athleteId
        ? ""
        : person.is_following
          ? `<button type="button" class="btn btn-ghost btn-follow is-following" data-action="confirm-unfollow" ${idAttr} data-handle="${escapeHtml(handle)}">Following</button>`
          : `<button type="button" class="btn btn-primary btn-follow" data-action="follow-user" ${idAttr} data-handle="${escapeHtml(handle)}">Follow</button>`;
    return `
      <div class="people-row-wrap">
        <button type="button" class="people-row" data-action="open-user" ${idAttr} data-handle="${escapeHtml(handle)}">
          ${renderAvatarHtml(person)}
          <div>
            <p class="people-row-name">${escapeHtml(displayNameOf(person))}</p>
            <p class="people-row-meta">${escapeHtml(publicHandleLabel(person))}</p>
          </div>
        </button>
        ${followCtl}
      </div>
    `;
  }

  function paintPeopleModal() {
    const kind = state.people.kind;
    const q = state.people.q || "";
    const head = `
      <div class="people-search-wrap">
        <input id="peopleSearch" type="search" placeholder="Search runners" value="${escapeHtml(q)}" autocomplete="off">
      </div>
    `;
    if (state.people.status === "loading" && state.people.items.length === 0) {
      els.peopleModalBody.innerHTML = `${head}<p class="people-empty">${escapeHtml(
        copyFresh("loading") || "Loading…"
      )}</p>`;
      return;
    }
    if (state.people.items.length === 0) {
      const empty = copyEmpty(kind === "followers" ? "followers" : "following");
      els.peopleModalBody.innerHTML = `${head}<div class="empty-state-block" style="padding:12px 4px"><h2 style="font-size:22px">${escapeHtml(
        empty.title
      )}</h2><p>${escapeHtml(empty.body)}</p></div>`;
      return;
    }
    const more = state.people.hasMore
      ? `<button type="button" class="btn btn-ghost" style="width:100%;margin-top:8px" data-action="people-load-more">Load more</button>`
      : "";
    els.peopleModalBody.innerHTML =
      head + state.people.items.map(renderPeopleRow).join("") + more;
  }

  let peopleSearchTimer = null;

  async function openPeopleList(kind, ref, soft = false) {
    if (kind !== "followers" && kind !== "following") return;
    let athleteId = null;
    let handle = null;
    if (ref && typeof ref === "object") {
      athleteId = athleteIdOf(ref.athleteId ?? ref.athlete_id ?? ref.id);
      handle = String(ref.handle || "")
        .trim()
        .replace(/^@/, "");
    } else {
      handle = String(ref || state.profile?.handle || "")
        .trim()
        .replace(/^@/, "");
      athleteId = athleteIdOf(state.profile);
    }
    if (!athleteId && state.profile) athleteId = athleteIdOf(state.profile);
    if (!athleteId && !handle) return;

    const keepQ = soft ? state.people.q || "" : "";
    state.people.kind = kind;
    state.people.handle = handle || null;
    state.people.athleteId = athleteId;
    state.people.q = keepQ;
    state.people.offset = 0;
    state.people.items = soft ? state.people.items : [];
    state.people.status = "loading";
    els.peopleModalTitle.textContent = kind === "followers" ? "Followers" : "Following";
    els.peopleModal.hidden = false;
    void els.peopleModal.offsetWidth;
    els.peopleModal.classList.add("is-open");
    paintPeopleModal();
    await fetchPeoplePage({ reset: true });
  }

  async function fetchPeoplePage({ reset = false } = {}) {
    const kind = state.people.kind;
    const athleteId = state.people.athleteId;
    const handle = state.people.handle;
    if (!kind || (!athleteId && !handle)) return;
    const offset = reset ? 0 : state.people.offset;
    const q = state.people.q || "";
    state.people.status = "loading";
    try {
      const params = new URLSearchParams({
        limit: "30",
        offset: String(offset),
      });
      if (q.trim().length >= 2) params.set("q", q.trim());
      const base = athleteId
        ? `/api/users/${encodeURIComponent(athleteId)}/${kind}`
        : `/api/profiles/${encodeURIComponent(handle)}/${kind}`;
      const res = await apiFetch(`${base}?${params.toString()}`);
      if (!res.ok) throw new Error("Couldn’t load that list.");
      const data = await res.json();
      const batch = Array.isArray(data.people) ? data.people : [];
      state.people.items = reset ? batch : state.people.items.concat(batch);
      state.people.total = Number(data.total || state.people.items.length);
      state.people.hasMore = !!data.has_more;
      state.people.offset = data.next_offset != null ? data.next_offset : state.people.items.length;
      if (data.athlete_id) state.people.athleteId = athleteIdOf(data.athlete_id);
      if (data.handle) state.people.handle = data.handle;
      state.people.status = "ready";
      paintPeopleModal();
    } catch (err) {
      state.people.status = "error";
      els.peopleModalBody.innerHTML = `<p class="people-empty">${escapeHtml(err.message || "Try again.")}</p>`;
    }
  }

  function closePeopleModal() {
    els.peopleModal.classList.remove("is-open");
    setTimeout(() => {
      els.peopleModal.hidden = true;
    }, 250);
  }

  let confirmCloseTimer = null;

  function closeConfirmModal() {
    if (!els.confirmModal) return;
    els.confirmModal.classList.remove("is-open");
    if (confirmCloseTimer) {
      clearTimeout(confirmCloseTimer);
      confirmCloseTimer = null;
    }
    confirmCloseTimer = setTimeout(() => {
      confirmCloseTimer = null;
      // Only finalize hide if nothing re-opened the modal.
      if (!els.confirmModal.classList.contains("is-open")) {
        els.confirmModal.hidden = true;
        if (els.confirmModalActions) els.confirmModalActions.innerHTML = "";
      }
    }, 250);
  }

  function openConfirmModal({ title, body, actions, closeOnConfirm = true }) {
    if (!els.confirmModal) return Promise.resolve({ confirmed: false });
    return new Promise((resolve) => {
      let settled = false;
      const finish = (result) => {
        if (settled) return;
        settled = true;
        if (result.confirmed && !closeOnConfirm) {
          resolve(result);
          return;
        }
        closeConfirmModal();
        resolve(result);
      };

      // Cancel a pending hide from a previous step (e.g. delete step 1 → 2).
      if (confirmCloseTimer) {
        clearTimeout(confirmCloseTimer);
        confirmCloseTimer = null;
      }

      els.confirmModalTitle.textContent = title || "Confirm";
      els.confirmModalBody.textContent = body || "";
      els.confirmModalActions.innerHTML = "";

      (actions || []).forEach((action) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = action.danger
          ? "btn btn-danger"
          : action.primary
            ? "btn btn-primary"
            : "btn btn-ghost";
        btn.textContent = action.label;
        btn.dataset.confirmRole = action.role || "cancel";
        btn.addEventListener("click", (e) => {
          e.preventDefault();
          e.stopPropagation();
          if (action.role === "confirm") {
            finish({ confirmed: true, button: btn });
          } else {
            finish({ confirmed: false });
          }
        });
        els.confirmModalActions.appendChild(btn);
      });

      els.confirmModal.hidden = false;
      void els.confirmModal.offsetWidth;
      els.confirmModal.classList.add("is-open");

      const onBackdrop = (e) => {
        if (e.target === els.confirmModal && !settled) {
          els.confirmModal.removeEventListener("click", onBackdrop);
          finish({ confirmed: false });
        }
      };
      els.confirmModal.addEventListener("click", onBackdrop);
    });
  }

  async function confirmUnfollow(ref) {
    const athleteId =
      typeof ref === "object" && ref !== null
        ? athleteIdOf(ref.athleteId ?? ref.athlete_id ?? ref.id)
        : athleteIdOf(ref);
    if (!athleteId) return;
    if (Date.now() < followGhostGuardUntil) return;

    const handle =
      (typeof ref === "object" && ref && ref.handle) ||
      (state.viewed.athleteId === athleteId && state.viewed.data
        ? state.viewed.data.handle
        : "") ||
      "";
    const name =
      (state.viewed.athleteId === athleteId && state.viewed.data
        ? displayNameOf(state.viewed.data)
        : null) ||
      (handle ? `@${handle}` : "this runner");
    const handleLabelText = handle || "runner";

    const titleTpl =
      (Copy && Copy.COPY.unfollow.titles[0]) || "Unfollow {name}?";
    const bodyTpl = copyFresh("unfollow.bodies") ||
      "Are you sure you want to stop following @{handle}?";
    const title = Copy
      ? Copy.format(titleTpl, { name, handle: handleLabelText })
      : `Unfollow ${name}?`;
    const body = Copy
      ? Copy.format(bodyTpl, { name, handle: handleLabelText })
      : bodyTpl;

    const result = await openConfirmModal({
      title,
      body,
      actions: [
        {
          label: (Copy && Copy.COPY.unfollow.keep) || "Keep following",
          role: "cancel",
        },
        {
          label: (Copy && Copy.COPY.unfollow.confirm) || "Unfollow",
          role: "confirm",
          danger: true,
        },
      ],
    });
    if (!result.confirmed) return;
    await toggleFollow(athleteId, false);
  }

  async function runDeleteAccountFlow() {
    const step1 = Copy && Copy.COPY.deleteAccount.step1;
    const first = await openConfirmModal({
      title: (step1 && step1.title) || "Leaving already?",
      body:
        (step1 && step1.body) ||
        "Are you sure you want to delete your account?",
      actions: [
        { label: (step1 && step1.keep) || "Keep my account", role: "cancel" },
        {
          label: (step1 && step1.confirm) || "Delete account",
          role: "confirm",
          danger: true,
        },
      ],
    });
    if (!first.confirmed) return;

    const step2 = Copy && Copy.COPY.deleteAccount.step2;
    const second = await openConfirmModal({
      title: (step2 && step2.title) || "Last chance. Seriously.",
      body:
        (step2 && step2.body) ||
        "This is permanent. No undo button.",
      closeOnConfirm: false,
      actions: [
        {
          label: (step2 && step2.keep) || "Wait, I changed my mind",
          role: "cancel",
        },
        {
          label: (step2 && step2.confirm) || "Yes, delete everything",
          role: "confirm",
          danger: true,
        },
      ],
    });
    if (!second.confirmed) return;

    const confirmBtn = second.button;
    const cancelBtn = els.confirmModalActions.querySelector(
      '[data-confirm-role="cancel"]'
    );
    if (confirmBtn) {
      confirmBtn.disabled = true;
      confirmBtn.textContent = "Deleting…";
    }
    if (cancelBtn) cancelBtn.disabled = true;

    try {
      const res = await apiFetch("/api/me/account", { method: "DELETE" });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(
          typeof err.detail === "string" ? err.detail : errLine()
        );
      }
      const data = await res.json().catch(() => ({}));
      try {
        localStorage.clear();
        sessionStorage.clear();
      } catch (_e) {
        /* ignore */
      }
      closeConfirmModal();
      closeSettings();
      showToast(
        data.message ||
          (Copy && Copy.COPY.deleteAccount.done) ||
          "Your account has officially vanished into the void."
      );
      setTimeout(() => {
        window.location.href = "/";
      }, 900);
    } catch (err) {
      closeConfirmModal();
      showToast(err.message || errLine());
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
    else if (state.page === "messages") html = renderMessagesInbox();
    else if (state.page === "dm") html = renderDmThread();
    else if (state.page === "coach") html = renderCoachPage();
    else if (state.page === "u") html = renderViewedProfile();
    else html = renderProfile();

    els.viewRoot.innerHTML = html;
    els.coachSidebarPanel.innerHTML = renderCoachChat({ compact: true });
    bindViewInteractions();
    wireCoachDom(els.viewRoot);
    wireCoachDom(els.coachSidebarPanel);
    wireDmComposer();
    scrollCoachThreads();

    if (state.page === "dm") {
      requestAnimationFrame(() => {
        const sc = document.getElementById("dmThreadScroll");
        if (sc) sc.scrollTop = sc.scrollHeight;
        const input = document.getElementById("dmInput");
        if (input && state.thread.can_send) input.focus();
      });
    }

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
    // Activity tiles only — Follow/actions use document delegation (avoids double-fire on mobile).
    els.viewRoot.querySelectorAll("[data-activity-id]").forEach((tile) => {
      tile.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        openActivity(tile.dataset.activityId);
      });
    });

    els.viewRoot.querySelectorAll("[data-feed-activity-id]").forEach((post) => {
      post.addEventListener("click", (event) => {
        if (event.target.closest("a,button")) return;
        openActivity(post.dataset.feedActivityId);
      });
    });
  }

  function handleAction(action, el) {
    if (Date.now() < followGhostGuardUntil) {
      if (
        action === "follow-user" ||
        action === "unfollow-user" ||
        action === "confirm-unfollow"
      ) {
        return;
      }
    }
    if (action === "edit-profile" || action === "open-settings") openSettings();
    if (action === "retry-feed") loadFeed(true);
    if (action === "retry-explore") loadExplore(true);
    if (action === "retry-explore-search") runExploreSearch(state.explore.searchQ || "");
    if (action === "retry-inbox") loadInbox(true);
    if (action === "clear-coach") clearCoachChat();
    if (action === "open-user" || action === "peek-athlete") openUserFromEl(el);
    if (action === "open-dm") {
      openDmWithPeer(athleteIdOf(el?.dataset?.athleteId));
    }
    if (action === "open-thread") {
      const cid = el?.dataset?.conversationId;
      if (cid) navigateDm(cid);
    }
    if (action === "back-inbox") navigateInbox();
    if (action === "follow-user") {
      toggleFollow(
        { athleteId: el?.dataset?.athleteId, handle: el?.dataset?.handle },
        true
      );
    }
    if (action === "unfollow-user") {
      toggleFollow(
        { athleteId: el?.dataset?.athleteId, handle: el?.dataset?.handle },
        false
      );
    }
    if (action === "confirm-unfollow") {
      confirmUnfollow({
        athleteId: el?.dataset?.athleteId,
        handle: el?.dataset?.handle,
      });
    }
    if (action === "open-followers") {
      openPeopleList("followers", {
        athleteId: el?.dataset?.athleteId,
        handle: el?.dataset?.handle,
      });
    }
    if (action === "open-following") {
      openPeopleList("following", {
        athleteId: el?.dataset?.athleteId,
        handle: el?.dataset?.handle,
      });
    }
    if (action === "people-load-more") fetchPeoplePage({ reset: false });
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
    els.sidebarName.textContent = displayNameOf(profile);
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
        showToast(copyFresh("success.sync") || "Fresh data.");
        await loadProfileBundle(true);
        await loadFeed(true);
        if (state.page === "profile" || state.page === "feed") render();
      }
    } catch (err) {
      showToast(errLine());
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
      event.preventDefault();
      event.stopPropagation();
      handleAction(actionEl.dataset.action, actionEl);
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
    document.getElementById("closePeopleModal").addEventListener("click", closePeopleModal);
    els.peopleModal.addEventListener("click", (e) => {
      if (e.target === els.peopleModal) closePeopleModal();
      const actionEl = e.target.closest("[data-action]");
      if (actionEl) {
        e.preventDefault();
        const action = actionEl.dataset.action;
        if (action === "open-user") {
          closePeopleModal();
          openUserFromEl(actionEl);
          return;
        }
        handleAction(action, actionEl);
      }
    });
    const closeConfirmBtn = document.getElementById("closeConfirmModal");
    if (closeConfirmBtn) {
      closeConfirmBtn.addEventListener("click", closeConfirmModal);
    }
    const deleteBtn = document.getElementById("deleteAccountBtn");
    if (deleteBtn) {
      deleteBtn.addEventListener("click", () => {
        runDeleteAccountFlow();
      });
    }
    els.peopleModal.addEventListener("input", (e) => {
      if (e.target.id !== "peopleSearch") return;
      state.people.q = e.target.value;
      clearTimeout(peopleSearchTimer);
      peopleSearchTimer = setTimeout(() => {
        fetchPeoplePage({ reset: true });
      }, 280);
    });
    els.peopleModal.addEventListener("keydown", (e) => {
      if (e.target.id !== "peopleSearch") return;
      if (e.key === "Enter") {
        e.preventDefault();
        clearTimeout(peopleSearchTimer);
        fetchPeoplePage({ reset: true });
      }
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
      els.settingsMsg.textContent =
        copyFresh("success.profile") || "Saved. You’re still you — just clearer.";
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
      const loc = parseLocationHash();
      if (loc.page === "u") {
        openUserProfile(
          { athleteId: loc.athleteId, handle: loc.handle },
          { replace: true }
        );
      } else if (loc.page === "dm" && loc.conversationId) {
        navigateDm(loc.conversationId, { replace: true });
      } else {
        navigate(loc.page, { replace: true });
      }
    });

    wireSettingsForm();
    wireExploreSearch();

    await ensureAuth();
    await loadProfileBundle(true);
    loadCoachMessages(false);
    refreshUnreadBadge();

    const initial = parseLocationHash();
    if (initial.page === "u") {
      openUserProfile(
        { athleteId: initial.athleteId, handle: initial.handle },
        { replace: true }
      );
    } else if (initial.page === "dm" && initial.conversationId) {
      navigateDm(initial.conversationId, { replace: true });
    } else {
      navigate(initial.page, { replace: true });
    }

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
