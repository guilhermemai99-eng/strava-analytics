/* Pulse — Runs UI (Create, Discover, Join, People, Clubs) */
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
    discover: { status: "idle", items: [], error: null, tab: "people" },
    people: { status: "idle", items: [], error: null },
    myRuns: { status: "idle", items: [], error: null, tab: "upcoming" },
    detail: { status: "idle", run: null, error: null, runId: null },
    clubs: { status: "idle", items: [], error: null, subtab: "discover" },
    clubDetail: {
      status: "idle",
      club: null,
      error: null,
      clubId: null,
      tab: "upcoming",
      runs: [],
      runsStatus: "idle",
      inviteOpen: false,
      inviteHandle: "",
      invitePending: [],
      invitePendingStatus: "idle",
      inviteBusy: false,
    },
    createClub: {
      name: "",
      location_name: "",
      description: "",
      visibility: "public",
      coverFile: null,
      submitting: false,
    },
    adminClubs: { status: "idle", items: [] },
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
      club_id: null,
      submitting: false,
      peer: null,
    },
  };

  function emptyCreateState() {
    return {
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
      club_id: null,
      submitting: false,
      peer: null,
    };
  }

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
    const cancelled = run.status === "cancelled";
    const joinBtn = cancelled
      ? `<span class="run-card-going">Cancelled</span>`
      : run.is_going
        ? `<span class="run-card-going">Going</span>`
        : run.can_join
          ? `<button type="button" class="btn btn-primary btn-sm" data-action="open-run" data-run-id="${h(run.id)}">Join</button>`
          : `<span class="run-card-full">Full</span>`;
    return `
      <article class="run-card ${compact ? "is-compact" : ""} ${cancelled ? "is-cancelled" : ""}" data-action="open-run" data-run-id="${h(run.id)}">
        <div class="run-card-top">
          <h3>${h(run.title)}</h3>
          <span class="run-card-type">${cancelled ? "Cancelled" : h(runTypeLabel(run.run_type))}</span>
        </div>
        <p class="run-card-when">📅 ${h(formatRunWhen(run.meeting_time))}</p>
        <p class="run-card-loc">📍 ${h(run.location_name)}</p>
        ${run.club && run.club.name ? `<p class="run-card-club">Hosted by ${h(run.club.name)}</p>` : ""}
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
      ? `<button type="button" class="btn btn-ghost btn-sm btn-follow is-following" data-action="confirm-unfollow" data-athlete-id="${h(person.athlete_id)}" data-handle="${h(person.handle || "")}">Following</button>`
      : person.is_follow_requested
        ? `<button type="button" class="btn btn-ghost btn-sm btn-follow is-requested" data-action="cancel-follow-request" data-athlete-id="${h(person.athlete_id)}" data-handle="${h(person.handle || "")}">Requested</button>`
        : `<button type="button" class="btn btn-primary btn-sm btn-follow" data-action="follow-user" data-athlete-id="${h(person.athlete_id)}" data-handle="${h(person.handle || "")}">Follow</button>`;
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

  function roleLabel(role) {
    if (role === "owner") return "Owner";
    if (role === "admin") return "Admin";
    return "Member";
  }

  function clubMarkHtml(club, extraClass = "") {
    const letter = h((club.name || "C").slice(0, 1).toUpperCase());
    if (club.cover_url) {
      return `<div class="club-card-mark ${extraClass} has-cover" aria-hidden="true"><img src="${h(club.cover_url)}" alt=""></div>`;
    }
    return `<div class="club-card-mark ${extraClass}" aria-hidden="true">${letter}</div>`;
  }

  function renderClubCard(club) {
    const joinCta = club.is_member
      ? `<span class="run-card-going">${h(roleLabel(club.role))}</span>`
      : club.visibility === "private"
        ? `<span class="run-card-going">Private</span>`
        : `<button type="button" class="btn btn-primary btn-sm" data-action="join-club" data-club-id="${h(club.id)}">Join</button>`;
    return `
      <article class="club-card" data-action="open-club" data-club-id="${h(club.id)}">
        ${clubMarkHtml(club)}
        <div class="club-card-body">
          <div class="run-card-top">
            <h3>${h(club.name)}</h3>
            ${club.visibility === "private" ? `<span class="run-card-type">Private</span>` : ""}
          </div>
          ${club.location_name ? `<p class="run-card-loc">📍 ${h(club.location_name)}</p>` : ""}
          <p class="club-card-desc">${h(club.description || "A running club. Show up, find your people.")}</p>
          <div class="run-card-foot">
            <span class="run-card-count">👥 ${h(String(club.member_count || 0))} members</span>
            ${joinCta}
          </div>
        </div>
      </article>`;
  }

  function renderClubsDiscover() {
    const block = runsState.clubs;
    const sub = block.subtab || "discover";
    const subtabs = [
      { id: "discover", label: "Discover" },
      { id: "mine", label: "My Clubs" },
    ];
    let list = "";
    if (block.status === "loading" || block.status === "idle") {
      list = `<p class="runs-section-sub">Finding clubs…</p>`;
    } else if (block.status === "error") {
      list = `<p class="runs-section-sub">${h(block.error)} <button type="button" class="btn btn-ghost btn-sm" data-action="retry-clubs">Retry</button></p>`;
    } else if (!block.items.length) {
      list =
        sub === "mine"
          ? `<p class="runs-section-sub">You haven’t joined a club yet. Discover one or start your own.</p>`
          : `<p class="runs-section-sub">No public clubs yet. Be the first — name it, meet up, run together.</p>`;
    } else {
      list = `<div class="clubs-list">${block.items.map(renderClubCard).join("")}</div>`;
    }
    return `
      <div class="clubs-discover">
        <div class="clubs-discover-toolbar">
          <div class="discover-tabs is-sub" role="tablist">
            ${subtabs
              .map(
                (t) =>
                  `<button type="button" class="discover-tab ${sub === t.id ? "is-active" : ""}" data-action="clubs-subtab" data-tab="${h(t.id)}">${h(t.label)}</button>`
              )
              .join("")}
          </div>
          <button type="button" class="btn btn-primary btn-sm" data-nav="create-club">Create Club</button>
        </div>
        ${list}
      </div>`;
  }

  function clubJoinLeaveCta(club) {
    if (club.pending_invite_id && !club.is_member) {
      return `
        <button type="button" class="btn btn-primary" data-action="accept-club-invite" data-invite-id="${h(club.pending_invite_id)}">Accept invite</button>
        <button type="button" class="btn btn-ghost" data-action="decline-club-invite" data-invite-id="${h(club.pending_invite_id)}">Decline</button>`;
    }
    if (club.is_owner) {
      return `
        <span class="run-card-going">You're the owner</span>
        <button type="button" class="btn btn-ghost" data-action="delete-club" data-club-id="${h(club.id)}">Delete club</button>`;
    }
    if (club.is_member) {
      return `<button type="button" class="btn btn-ghost" data-action="leave-club" data-club-id="${h(club.id)}">Leave Club</button>`;
    }
    if (club.visibility === "private") {
      return `<span class="run-card-going">Invite only</span>`;
    }
    return `<button type="button" class="btn btn-primary" data-action="join-club" data-club-id="${h(club.id)}">Join Club</button>`;
  }

  function renderInvitePanel(club) {
    const d = runsState.clubDetail;
    if (!club.can_manage || !d.inviteOpen) return "";
    const pending = Array.isArray(d.invitePending) ? d.invitePending : [];
    const pendingList = pending.length
      ? `<ul class="club-invite-pending">${pending
          .map(
            (inv) => `
          <li>
            <span>${h(inv.invitee?.name || inv.invitee?.handle || "Runner")}${
              inv.invitee?.handle ? ` · @${h(inv.invitee.handle)}` : ""
            }</span>
            <button type="button" class="btn btn-ghost btn-sm" data-action="cancel-club-invite" data-invite-id="${h(inv.id)}" data-club-id="${h(club.id)}">Cancel</button>
          </li>`
          )
          .join("")}</ul>`
      : `<p class="runs-section-sub">No pending invites.</p>`;
    return `
      <div class="club-invite-panel">
        <h3>Invite runners</h3>
        <p class="runs-section-sub">Send a handle invite, or copy a link that works even for private clubs.</p>
        <div class="club-invite-row">
          <input type="text" id="clubInviteHandle" value="${h(d.inviteHandle || "")}" placeholder="@handle" maxlength="32" autocomplete="off">
          <button type="button" class="btn btn-primary btn-sm" data-action="send-club-invite" data-club-id="${h(club.id)}" ${d.inviteBusy ? "disabled" : ""}>Send</button>
        </div>
        <div class="club-invite-row">
          <button type="button" class="btn btn-ghost btn-sm" data-action="copy-club-invite-link" data-club-id="${h(club.id)}" ${d.inviteBusy ? "disabled" : ""}>Copy invite link</button>
          <button type="button" class="btn btn-ghost btn-sm" data-action="close-club-invite">Close</button>
        </div>
        ${pendingList}
      </div>`;
  }

  function renderClubMemberRow(m, club) {
    const isOwnerViewer = !!club.is_owner;
    const isSelfOwner = m.role === "owner";
    let actions = "";
    if (isOwnerViewer && !isSelfOwner) {
      const roleBtn =
        m.role === "admin"
          ? `<button type="button" class="btn btn-ghost btn-sm" data-action="demote-club-member" data-club-id="${h(club.id)}" data-athlete-id="${h(m.athlete_id)}">Remove admin</button>`
          : `<button type="button" class="btn btn-ghost btn-sm" data-action="promote-club-member" data-club-id="${h(club.id)}" data-athlete-id="${h(m.athlete_id)}">Make admin</button>`;
      actions = `
        <div class="club-member-actions">
          ${roleBtn}
          <button type="button" class="btn btn-ghost btn-sm" data-action="transfer-club" data-club-id="${h(club.id)}" data-athlete-id="${h(m.athlete_id)}" data-name="${h(m.name || "this runner")}">Transfer ownership</button>
        </div>`;
    }
    return `
      <div class="club-member-row">
        <button type="button" class="club-member-main" data-action="open-user" data-athlete-id="${h(m.athlete_id)}">
          <span class="pulse-avatar">${m.avatar_url ? `<img src="${h(m.avatar_url)}" alt="">` : h(m.initials || "P")}</span>
          <span class="club-member-meta">
            <strong>${h(m.name || "Runner")}</strong>
            <span>${h(roleLabel(m.role))}${m.handle ? ` · @${h(m.handle)}` : ""}</span>
          </span>
        </button>
        ${actions}
      </div>`;
  }

  function renderClubPage() {
    const d = runsState.clubDetail;
    if (d.status === "loading" || d.status === "idle") {
      return `<section class="pulse-page club-page"><p class="runs-section-sub">Loading club…</p></section>`;
    }
    if (d.status === "error" || !d.club) {
      return `
        <section class="pulse-page club-page">
          <p class="runs-section-sub">${h(d.error || "Club not found.")}</p>
          <button type="button" class="btn btn-primary" data-action="back-from-club">Back to Discover</button>
        </section>`;
    }
    const club = d.club;
    const tab = d.tab || "upcoming";
    const tabs = [
      { id: "upcoming", label: "Upcoming" },
      { id: "feed", label: "Feed" },
      { id: "members", label: "Members" },
    ];
    const members = Array.isArray(club.members) ? club.members : [];
    let body = "";
    if (tab === "members") {
      const inviteCta = club.can_manage
        ? `<button type="button" class="btn btn-primary btn-sm" data-action="open-club-invite">Invite</button>`
        : "";
      body = `
        <div class="club-members-toolbar">${inviteCta}</div>
        ${renderInvitePanel(club)}
        ${
          members.length
            ? `<div class="club-member-list">${members
                .map((m) => renderClubMemberRow(m, club))
                .join("")}</div>`
            : `<p class="runs-section-sub">No members yet.</p>`
        }`;
    } else if (d.runsStatus === "loading" || d.runsStatus === "idle") {
      body = `<p class="runs-section-sub">${tab === "feed" ? "Loading club feed…" : "Loading upcoming runs…"}</p>`;
    } else if (!d.runs.length) {
      body =
        tab === "feed"
          ? `<p class="runs-section-sub">No past club runs yet. Host one and this feed fills up.</p>`
          : `<p class="runs-section-sub">No upcoming club runs. ${club.can_manage ? "Host the next one." : "Check back soon."}</p>`;
    } else {
      body = `<div class="runs-list">${d.runs.map((r) => renderRunCard(r)).join("")}</div>`;
    }

    const hostCta = club.can_manage
      ? `<button type="button" class="btn btn-primary" data-action="create-club-run" data-club-id="${h(club.id)}">Create a club run</button>`
      : "";
    const inviteCta = club.can_manage
      ? `<button type="button" class="btn btn-ghost" data-action="open-club-invite">Invite</button>`
      : "";
    const coverCta = club.can_manage
      ? `<button type="button" class="btn btn-ghost btn-sm" data-action="pick-club-cover" data-club-id="${h(club.id)}">${club.cover_url ? "Change cover" : "Add cover"}</button>
         <input type="file" id="clubCoverInput" accept="image/jpeg,image/png,image/webp" hidden>`
      : "";

    return `
      <section class="pulse-page club-page" data-page="club">
        <header class="run-detail-head">
          <button type="button" class="ig-action-btn" data-action="back-from-club" aria-label="Back">←</button>
          <h1>${h(club.name)}</h1>
          <span></span>
        </header>
        <div class="club-hero">
          ${clubMarkHtml(club, "club-hero-mark")}
          <div>
            ${club.location_name ? `<p class="run-detail-loc">📍 ${h(club.location_name)}</p>` : ""}
            <p class="club-hero-count">${h(String(club.member_count || 0))} members${club.visibility === "private" ? " · Private" : ""}</p>
            ${club.description ? `<p class="club-hero-desc">${h(club.description)}</p>` : ""}
            ${coverCta}
          </div>
        </div>
        <div class="club-hero-actions">${clubJoinLeaveCta(club)}${inviteCta}${hostCta}</div>
        ${tab !== "members" ? renderInvitePanel(club) : ""}
        <div class="discover-tabs" role="tablist">
          ${tabs
            .map(
              (t) =>
                `<button type="button" class="discover-tab ${tab === t.id ? "is-active" : ""}" data-action="club-tab" data-tab="${h(t.id)}">${h(t.label)}</button>`
            )
            .join("")}
        </div>
        ${body}
      </section>`;
  }

  function renderCreateClub() {
    const c = runsState.createClub;
    return `
      <section class="pulse-page runs-page create-club-page" data-page="create-club">
        <header class="runs-page-head">
          <button type="button" class="ig-action-btn" data-action="back-from-create-club" aria-label="Back">←</button>
          <h1>Create a Club</h1>
          <span></span>
        </header>
        <p class="runs-tagline">A home for people who show up. Name it, pick a city, start running together.</p>
        <label class="run-form-label">Club name
          <input type="text" id="createClubName" value="${h(c.name)}" placeholder="Porto Sunrise Runners" maxlength="120" autocomplete="off">
        </label>
        <label class="run-form-label">Location
          <input type="text" id="createClubLocation" value="${h(c.location_name)}" placeholder="Porto" autocomplete="off">
        </label>
        <label class="run-form-label">Description (optional)
          <textarea id="createClubDesc" rows="3" placeholder="Easy mornings by the river. All paces welcome.">${h(c.description)}</textarea>
        </label>
        <label class="run-form-label">Cover image (optional)
          <input type="file" id="createClubCover" accept="image/jpeg,image/png,image/webp">
        </label>
        <p class="run-form-label">Visibility</p>
        <div class="run-visibility-list">
          <label><input type="radio" name="clubVis" value="public" ${c.visibility === "public" ? "checked" : ""}> 🌍 Public — anyone can find and join</label>
          <label><input type="radio" name="clubVis" value="private" ${c.visibility === "private" ? "checked" : ""}> 🔒 Private — members only</label>
        </div>
        <div class="create-run-nav">
          <button type="button" class="btn btn-primary" data-action="create-club-submit" ${c.submitting ? "disabled" : ""}>
            ${c.submitting ? "Creating…" : "Create Club"}
          </button>
        </div>
      </section>`;
  }

  function renderDiscover() {
    const tab = runsState.discover.tab || "people";
    const tabs = [
      { id: "people", label: "People" },
      { id: "runs", label: "Runs" },
      { id: "clubs", label: "Clubs" },
    ];
    let body = "";
    if (tab === "people") {
      body = hooks.renderPeopleExplore
        ? hooks.renderPeopleExplore()
        : renderPeopleMatches();
    } else if (tab === "clubs") {
      body = renderClubsDiscover();
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
          <p class="runs-tagline">Who can I run with?</p>
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
    const cancelled = run.status === "cancelled";
    let joinCta = "";
    if (cancelled) {
      joinCta = `<span class="run-card-going">This run was cancelled</span>`;
    } else if (run.is_host) {
      joinCta = `<button type="button" class="btn btn-ghost run-detail-cta" data-action="cancel-run" data-run-id="${h(run.id)}">Cancel run</button>`;
    } else if (run.is_going) {
      joinCta = `<button type="button" class="btn btn-ghost run-detail-cta" data-action="leave-run" data-run-id="${h(run.id)}">Leave Run</button>`;
    } else if (run.visibility === "invite_only") {
      joinCta = `<span class="run-card-going">Invite only — ask the host</span>`;
    } else {
      joinCta = `<button type="button" class="btn btn-primary run-detail-cta" data-action="join-run" data-run-id="${h(run.id)}" ${run.can_join ? "" : "disabled"}>Join Run</button>`;
    }
    const inviteNote =
      !cancelled && run.visibility === "invite_only" && run.is_host
        ? `<p class="runs-section-sub">Invite only — people you invite show up here automatically.</p>`
        : "";
    const goingNote = cancelled
      ? ""
      : run.is_going
        ? `<p class="run-going-note">✓ You're going${run.is_host ? " · You're the host" : ""}</p>`
        : "";

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
            <span>${cancelled ? "Cancelled" : h(runTypeLabel(run.run_type))}</span>
            ${!cancelled && run.visibility === "invite_only" ? `<span>Invite only</span>` : ""}
          </div>
        </div>
        <div class="run-compat-block ${compatClass(compat.level)}">
          <strong>${h(compat.emoji || "")} ${h(compat.label || "Compatibility")}</strong>
          <p>${h(compat.message || "")}</p>
        </div>
        <section class="run-detail-block">
          <h2>${h(run.participant_count || 0)} going</h2>
          ${inviteNote}
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
          ${
            run.club && run.club.id
              ? `<button type="button" class="run-host-row" data-action="open-club" data-club-id="${h(run.club.id)}">
                   <span class="pulse-avatar club-mini-mark">${h((run.club.name || "C").slice(0, 1).toUpperCase())}</span>
                   <strong>${h(run.club.name)}</strong>
                 </button>`
              : ""
          }
          <button type="button" class="run-host-row" data-action="open-user" data-athlete-id="${h(host.athlete_id || "")}">
            <span class="pulse-avatar">${host.avatar_url ? `<img src="${h(host.avatar_url)}" alt="">` : h(host.initials || "P")}</span>
            <strong>${h(host.name || "Runner")}</strong>
          </button>
        </section>
        ${run.description ? `<section class="run-detail-block"><h2>About</h2><p>${h(run.description)}</p></section>` : ""}
        <div class="run-detail-actions">${joinCta}${goingNote}</div>
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
        ${
          runsState.adminClubs.items.length
            ? `<label class="run-form-label">Host as
                <select id="createRunClub">
                  <option value="">Just me</option>
                  ${runsState.adminClubs.items
                    .map(
                      (club) =>
                        `<option value="${h(club.id)}" ${Number(c.club_id) === Number(club.id) ? "selected" : ""}>${h(club.name)}</option>`
                    )
                    .join("")}
                </select>
              </label>`
            : ""
        }
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
           <div><strong>Running with ${h(c.peer.name)}</strong><span>We'll invite them when you create — invite-only by default.</span></div>
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

  async function loadClubs(force = false) {
    const sub = runsState.clubs.subtab || "discover";
    if (!force && runsState.clubs.status === "ready") return;
    runsState.clubs.status = "loading";
    try {
      const res = await hooks.apiFetch(`/api/clubs?tab=${encodeURIComponent(sub)}&limit=40`);
      if (!res.ok) throw new Error("Could not load clubs.");
      const data = await res.json();
      runsState.clubs.items = Array.isArray(data.items) ? data.items : [];
      runsState.clubs.status = "ready";
      runsState.clubs.error = null;
    } catch (err) {
      runsState.clubs.status = "error";
      runsState.clubs.error = err.message || "Try again.";
    }
  }

  async function loadAdminClubs(force = false) {
    if (!force && runsState.adminClubs.status === "ready") return;
    try {
      const res = await hooks.apiFetch("/api/clubs?tab=admin&limit=40");
      if (!res.ok) throw new Error("Could not load clubs.");
      const data = await res.json();
      runsState.adminClubs.items = Array.isArray(data.items) ? data.items : [];
      runsState.adminClubs.status = "ready";
    } catch (_err) {
      runsState.adminClubs.items = [];
      runsState.adminClubs.status = "error";
    }
  }

  async function loadClubDetail(clubId, force = false) {
    if (!force && runsState.clubDetail.clubId === clubId && runsState.clubDetail.status === "ready") {
      return;
    }
    if (String(runsState.clubDetail.clubId || "") !== String(clubId)) {
      runsState.clubDetail.tab = "upcoming";
      runsState.clubDetail.runsStatus = "idle";
      runsState.clubDetail.runs = [];
    }
    runsState.clubDetail.clubId = clubId;
    runsState.clubDetail.status = "loading";
    try {
      const res = await hooks.apiFetch(`/api/clubs/${encodeURIComponent(clubId)}`);
      if (!res.ok) throw new Error("Club not found.");
      runsState.clubDetail.club = await res.json();
      runsState.clubDetail.status = "ready";
      runsState.clubDetail.error = null;
    } catch (err) {
      runsState.clubDetail.status = "error";
      runsState.clubDetail.error = err.message || "Try again.";
      runsState.clubDetail.club = null;
    }
  }

  async function loadClubRuns(force = false) {
    const clubId = runsState.clubDetail.clubId;
    const tab = runsState.clubDetail.tab === "feed" ? "past" : "upcoming";
    if (!clubId) return;
    if (!force && runsState.clubDetail.runsStatus === "ready") return;
    runsState.clubDetail.runsStatus = "loading";
    try {
      const res = await hooks.apiFetch(
        `/api/clubs/${encodeURIComponent(clubId)}/runs?tab=${encodeURIComponent(tab)}&limit=40`
      );
      if (!res.ok) throw new Error("Could not load club runs.");
      const data = await res.json();
      runsState.clubDetail.runs = Array.isArray(data.items) ? data.items : [];
      runsState.clubDetail.runsStatus = "ready";
    } catch (_err) {
      runsState.clubDetail.runs = [];
      runsState.clubDetail.runsStatus = "ready";
    }
  }

  function syncCreateClubFromDom() {
    const c = runsState.createClub;
    const name = document.getElementById("createClubName");
    if (name) c.name = name.value.trim();
    const loc = document.getElementById("createClubLocation");
    if (loc) c.location_name = loc.value.trim();
    const desc = document.getElementById("createClubDesc");
    if (desc) c.description = desc.value.trim();
    const vis = document.querySelector('input[name="clubVis"]:checked');
    if (vis) c.visibility = vis.value;
    const cover = document.getElementById("createClubCover");
    if (cover && cover.files && cover.files[0]) c.coverFile = cover.files[0];
  }

  async function submitCreateClub() {
    syncCreateClubFromDom();
    const c = runsState.createClub;
    if (!c.name || c.name.length < 3) {
      hooks.showToast("Give the club a name (at least 3 characters).");
      return;
    }
    c.submitting = true;
    hooks.render();
    try {
      const res = await hooks.apiFetch("/api/clubs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: c.name,
          description: c.description || null,
          location_name: c.location_name || null,
          visibility: c.visibility || "public",
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Could not create club.");
      if (c.coverFile) {
        const fd = new FormData();
        fd.append("file", c.coverFile);
        const coverRes = await hooks.apiFetch(`/api/clubs/${data.id}/cover`, {
          method: "POST",
          body: fd,
        });
        if (coverRes.ok) {
          const covered = await coverRes.json().catch(() => null);
          if (covered) Object.assign(data, covered);
        }
      }
      hooks.showToast("Club created. Invite your people.");
      runsState.createClub = {
        name: "",
        location_name: "",
        description: "",
        visibility: "public",
        coverFile: null,
        submitting: false,
      };
      runsState.clubs.status = "idle";
      runsState.adminClubs.status = "idle";
      runsState.clubDetail.inviteOpen = true;
      openClub(data.id);
    } catch (err) {
      c.submitting = false;
      hooks.showToast(err.message || "Try again.");
      hooks.render();
    }
  }

  function openClub(clubId) {
    hooks.navigate("club", { clubId: String(clubId) });
  }

  async function joinClub(clubId) {
    const res = await hooks.apiFetch(`/api/clubs/${clubId}/join`, { method: "POST" });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      hooks.showToast(data.detail || "Could not join.");
      return;
    }
    runsState.clubDetail.club = data;
    runsState.clubDetail.status = "ready";
    runsState.clubDetail.clubId = String(data.id || clubId);
    runsState.clubs.status = "idle";
    hooks.showToast("You're in. See you at the next run.");
    if (hooks.getPage() !== "club") {
      openClub(data.id || clubId);
    } else {
      hooks.render();
    }
  }

  async function leaveClub(clubId) {
    const res = await hooks.apiFetch(`/api/clubs/${clubId}/leave`, { method: "POST" });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      hooks.showToast(data.detail || "Could not leave.");
      return;
    }
    runsState.clubDetail.club = data;
    runsState.clubs.status = "idle";
    hooks.showToast("You left this club.");
    hooks.render();
  }

  async function deleteClub(clubId) {
    if (hooks.openConfirmModal) {
      const result = await hooks.openConfirmModal({
        title: "Delete this club?",
        body: "Members lose the club home. Past club runs stay, but the club is gone for good.",
        actions: [
          { label: "Keep club", role: "cancel" },
          { label: "Delete club", role: "confirm", danger: true },
        ],
      });
      if (!result?.confirmed) return;
    } else if (!window.confirm("Delete this club?")) {
      return;
    }
    const res = await hooks.apiFetch(`/api/clubs/${clubId}`, { method: "DELETE" });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      hooks.showToast(data.detail || "Could not delete.");
      return;
    }
    runsState.clubDetail = {
      status: "idle",
      club: null,
      error: null,
      clubId: null,
      tab: "upcoming",
      runs: [],
      runsStatus: "idle",
    };
    runsState.clubs.status = "idle";
    hooks.showToast("Club deleted.");
    hooks.navigate("discover");
  }

  async function setClubMemberRole(clubId, athleteId, role) {
    const res = await hooks.apiFetch(
      `/api/clubs/${clubId}/members/${athleteId}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role }),
      }
    );
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      hooks.showToast(data.detail || "Could not update role.");
      return;
    }
    await loadClubDetail(clubId, true);
    hooks.showToast(role === "admin" ? "They're an admin now." : "Admin removed.");
    hooks.render();
  }

  async function transferClub(clubId, athleteId, name) {
    const label = name || "this runner";
    if (hooks.openConfirmModal) {
      const result = await hooks.openConfirmModal({
        title: `Make ${label} the owner?`,
        body: "You'll become an admin. Only they can transfer again or delete the club.",
        actions: [
          { label: "Keep ownership", role: "cancel" },
          { label: "Transfer", role: "confirm", primary: true },
        ],
      });
      if (!result?.confirmed) return;
    } else if (!window.confirm(`Make ${label} the owner?`)) {
      return;
    }
    const res = await hooks.apiFetch(`/api/clubs/${clubId}/transfer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ athlete_id: Number(athleteId) }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      hooks.showToast(data.detail || "Could not transfer.");
      return;
    }
    runsState.clubDetail.club = data;
    runsState.clubDetail.status = "ready";
    runsState.clubs.status = "idle";
    hooks.showToast(`${label} owns this club now.`);
    hooks.render();
  }

  async function loadClubInvites(force = false) {
    const clubId = runsState.clubDetail.clubId || runsState.clubDetail.club?.id;
    if (!clubId) return;
    if (runsState.clubDetail.invitePendingStatus === "ready" && !force) return;
    runsState.clubDetail.invitePendingStatus = "loading";
    try {
      const res = await hooks.apiFetch(`/api/clubs/${clubId}/invites`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Could not load invites.");
      runsState.clubDetail.invitePending = Array.isArray(data.items) ? data.items : [];
      runsState.clubDetail.invitePendingStatus = "ready";
    } catch (_err) {
      runsState.clubDetail.invitePending = [];
      runsState.clubDetail.invitePendingStatus = "error";
    }
  }

  async function openInvitePanel() {
    runsState.clubDetail.inviteOpen = true;
    runsState.clubDetail.tab = "members";
    hooks.render();
    await loadClubInvites(true);
    hooks.render();
  }

  async function sendClubInvite(clubId) {
    const input = document.getElementById("clubInviteHandle");
    const handle = (input ? input.value : runsState.clubDetail.inviteHandle || "").trim();
    runsState.clubDetail.inviteHandle = handle;
    if (!handle) {
      hooks.showToast("Enter a handle to invite.");
      return;
    }
    runsState.clubDetail.inviteBusy = true;
    hooks.render();
    try {
      const res = await hooks.apiFetch(`/api/clubs/${clubId}/invites`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ handle }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Could not send invite.");
      hooks.showToast("Invite sent.");
      runsState.clubDetail.inviteHandle = "";
      await loadClubInvites(true);
    } catch (err) {
      hooks.showToast(err.message || "Could not send invite.");
    } finally {
      runsState.clubDetail.inviteBusy = false;
      hooks.render();
    }
  }

  async function copyClubInviteLink(clubId) {
    runsState.clubDetail.inviteBusy = true;
    hooks.render();
    try {
      const res = await hooks.apiFetch(`/api/clubs/${clubId}/invite-link`, {
        method: "POST",
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Could not create link.");
      const url = `${location.origin}${data.path || ""}`;
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(url);
      }
      hooks.showToast("Invite link copied.");
    } catch (err) {
      hooks.showToast(err.message || "Could not create link.");
    } finally {
      runsState.clubDetail.inviteBusy = false;
      hooks.render();
    }
  }

  async function cancelClubInvite(clubId, inviteId) {
    const res = await hooks.apiFetch(
      `/api/clubs/${clubId}/invites/${inviteId}/cancel`,
      { method: "POST" }
    );
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      hooks.showToast(data.detail || "Could not cancel.");
      return;
    }
    await loadClubInvites(true);
    hooks.render();
  }

  async function acceptClubInvite(inviteId) {
    const res = await hooks.apiFetch(`/api/club-invites/${inviteId}/accept`, {
      method: "POST",
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      hooks.showToast(data.detail || "Could not accept.");
      return;
    }
    hooks.showToast("You're in. See you at the next run.");
    runsState.clubs.status = "idle";
    openClub(data.id);
  }

  async function declineClubInvite(inviteId) {
    const res = await hooks.apiFetch(`/api/club-invites/${inviteId}/decline`, {
      method: "POST",
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      hooks.showToast(data.detail || "Could not decline.");
      return;
    }
    hooks.showToast("Invite declined.");
    if (runsState.clubDetail.club) {
      runsState.clubDetail.club.pending_invite_id = null;
    }
    hooks.render();
  }

  async function uploadClubCover(clubId, file) {
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    const res = await hooks.apiFetch(`/api/clubs/${clubId}/cover`, {
      method: "POST",
      body: fd,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      hooks.showToast(data.detail || "Could not upload cover.");
      return;
    }
    runsState.clubDetail.club = data;
    runsState.clubs.status = "idle";
    hooks.showToast("Cover updated.");
    hooks.render();
  }

  async function redeemClubInviteToken(token) {
    if (!token) return null;
    const res = await hooks.apiFetch("/api/club-invites/redeem", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      hooks.showToast(data.detail || "Invite link is invalid.");
      return null;
    }
    hooks.showToast("You're in. See you at the next run.");
    runsState.clubs.status = "idle";
    return data;
  }

  function startClubRun(clubId) {
    const club = runsState.clubDetail.club;
    const c = runsState.create;
    Object.assign(c, emptyCreateState());
    c.club_id = Number(clubId) || null;
    if (club && club.location_name) c.location_name = club.location_name;
    if (club && club.name) c.title = `${club.name} run`;
    if (!c.meeting_time) c.meeting_time = defaultMeetingTime();
    hooks.navigate("create-run");
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
    const clubSel = document.getElementById("createRunClub");
    if (clubSel) c.club_id = clubSel.value ? Number(clubSel.value) : null;
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
      const inviteIds =
        c.peer && c.peer.athlete_id ? [Number(c.peer.athlete_id)] : [];
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
          club_id: c.club_id || null,
          invite_athlete_ids: inviteIds.length ? inviteIds : null,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Could not create run.");
      const peerName = c.peer?.name;
      hooks.showToast(
        peerName
          ? `Run created. ${peerName} is invited.`
          : "Run created. See you out there."
      );
      runsState.create = emptyCreateState();
      runsState.nearby.status = "idle";
      runsState.discover.status = "idle";
      runsState.clubDetail.runsStatus = "idle";
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

  async function cancelRun(runId) {
    if (hooks.openConfirmModal) {
      const result = await hooks.openConfirmModal({
        title: "Cancel this run?",
        body: "Everyone going will be notified. You can’t undo this.",
        actions: [
          { label: "Keep run", role: "cancel" },
          { label: "Cancel run", role: "confirm", primary: true },
        ],
      });
      if (!result?.confirmed) return;
    } else if (!window.confirm("Cancel this run? Everyone going will be notified.")) {
      return;
    }
    const res = await hooks.apiFetch(`/api/runs/${runId}`, { method: "DELETE" });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      hooks.showToast(data.detail || "Could not cancel.");
      return;
    }
    runsState.detail.run = data;
    runsState.detail.status = "ready";
    runsState.nearby.status = "idle";
    runsState.discover.status = "idle";
    runsState.myRuns.status = "idle";
    hooks.showToast("Run cancelled.");
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
      c.visibility = "invite_only";
      if (c.peer?.name) {
        c.description = `Run together with ${c.peer.name}. Suggested: ${
          (data.match && data.match.suggested_pace) || "easy pace"
        }.`;
      }
      hooks.navigate("create-run");
      hooks.showToast(
        data.match?.label
          ? `${data.match.emoji || ""} ${data.match.score}% · ${data.match.label}`
          : "Adjust the run — they'll get an invite."
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
    if (action === "open-club") {
      openClub(el?.dataset?.clubId);
      return true;
    }
    if (action === "back-from-run") {
      hooks.navigate("discover");
      return true;
    }
    if (action === "back-from-club") {
      runsState.discover.tab = "clubs";
      hooks.navigate("discover");
      return true;
    }
    if (action === "back-from-create-club") {
      runsState.discover.tab = "clubs";
      hooks.navigate("discover");
      return true;
    }
    if (action === "discover-tab") {
      runsState.discover.tab = el?.dataset?.tab || "runs";
      if (runsState.discover.tab === "people") {
        if (hooks.loadExplore) hooks.loadExplore(false);
        else loadPeopleMatches(false).then(() => hooks.render());
      } else if (runsState.discover.tab === "clubs") {
        loadClubs(false).then(() => hooks.render());
      } else if (runsState.discover.tab === "runs") {
        loadDiscover(false).then(() => hooks.render());
      } else {
        hooks.render();
      }
      return true;
    }
    if (action === "clubs-subtab") {
      runsState.clubs.subtab = el?.dataset?.tab || "discover";
      runsState.clubs.status = "idle";
      loadClubs(true).then(() => hooks.render());
      return true;
    }
    if (action === "retry-clubs") {
      loadClubs(true).then(() => hooks.render());
      return true;
    }
    if (action === "club-tab") {
      runsState.clubDetail.tab = el?.dataset?.tab || "upcoming";
      if (runsState.clubDetail.tab === "members") {
        hooks.render();
      } else {
        runsState.clubDetail.runsStatus = "idle";
        loadClubRuns(true).then(() => hooks.render());
      }
      return true;
    }
    if (action === "create-club-submit") {
      submitCreateClub();
      return true;
    }
    if (action === "create-club-run") {
      startClubRun(el?.dataset?.clubId);
      return true;
    }
    if (action === "join-club") {
      joinClub(el?.dataset?.clubId);
      return true;
    }
    if (action === "leave-club") {
      leaveClub(el?.dataset?.clubId);
      return true;
    }
    if (action === "open-club-invite") {
      openInvitePanel();
      return true;
    }
    if (action === "close-club-invite") {
      runsState.clubDetail.inviteOpen = false;
      hooks.render();
      return true;
    }
    if (action === "send-club-invite") {
      sendClubInvite(el?.dataset?.clubId);
      return true;
    }
    if (action === "copy-club-invite-link") {
      copyClubInviteLink(el?.dataset?.clubId);
      return true;
    }
    if (action === "cancel-club-invite") {
      cancelClubInvite(el?.dataset?.clubId, el?.dataset?.inviteId);
      return true;
    }
    if (action === "accept-club-invite") {
      acceptClubInvite(el?.dataset?.inviteId);
      return true;
    }
    if (action === "decline-club-invite") {
      declineClubInvite(el?.dataset?.inviteId);
      return true;
    }
    if (action === "pick-club-cover") {
      const input = document.getElementById("clubCoverInput");
      if (input) {
        input.onchange = () => {
          const file = input.files && input.files[0];
          uploadClubCover(el?.dataset?.clubId, file);
          input.value = "";
        };
        input.click();
      }
      return true;
    }
    if (action === "delete-club") {
      deleteClub(el?.dataset?.clubId);
      return true;
    }
    if (action === "promote-club-member") {
      setClubMemberRole(el?.dataset?.clubId, el?.dataset?.athleteId, "admin");
      return true;
    }
    if (action === "demote-club-member") {
      setClubMemberRole(el?.dataset?.clubId, el?.dataset?.athleteId, "member");
      return true;
    }
    if (action === "transfer-club") {
      transferClub(
        el?.dataset?.clubId,
        el?.dataset?.athleteId,
        el?.dataset?.name
      );
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
    if (action === "cancel-run") {
      cancelRun(el?.dataset?.runId);
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
        if (hooks.loadExplore) hooks.loadExplore(false);
        else {
          loadPeopleMatches(false).then(() => {
            if (hooks.getPage() === "discover") hooks.render();
          });
        }
      } else if (runsState.discover.tab === "clubs") {
        loadClubs(false).then(() => {
          if (hooks.getPage() === "discover") hooks.render();
        });
      } else if (runsState.discover.tab !== "routes") {
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
      loadAdminClubs(false).then(() => {
        if (hooks.getPage() === "create-run") hooks.render();
      });
    }
    if (page === "run" && opts.runId) {
      loadRunDetail(opts.runId, true).then(() => {
        if (hooks.getPage() === "run") hooks.render();
      });
    }
    if (page === "club" && opts.clubId) {
      loadClubDetail(opts.clubId, true).then(() => {
        if (hooks.getPage() === "club") hooks.render();
        const tab = runsState.clubDetail.tab;
        if (tab !== "members") {
          loadClubRuns(true).then(() => {
            if (hooks.getPage() === "club") hooks.render();
          });
        }
        if (runsState.clubDetail.inviteOpen) {
          loadClubInvites(true).then(() => {
            if (hooks.getPage() === "club") hooks.render();
          });
        }
      });
    }
  }

  function renderPage(page) {
    if (page === "discover") return renderDiscover();
    if (page === "my-runs") return renderMyRuns();
    if (page === "create-run") return renderCreateRun();
    if (page === "run") return renderRunDetail();
    if (page === "club") return renderClubPage();
    if (page === "create-club") return renderCreateClub();
    return null;
  }

  window.PulseRuns = {
    attach(h) {
      hooks = h;
    },
    renderHomeRunsStrip,
    renderPage,
    renderPeopleCard,
    handleAction,
    onPageEnter,
    openRun,
    openClub,
    redeemClubInviteToken,
    acceptClubInvite,
    declineClubInvite,
    setDiscoverTab(tab) {
      runsState.discover.tab = tab || "people";
    },
    getRunIdFromHash() {
      const raw = (location.hash || "").slice(1);
      if (raw.startsWith("run/")) return decodeURIComponent(raw.slice(4)).trim();
      return null;
    },
    getClubIdFromHash() {
      const raw = (location.hash || "").slice(1);
      if (raw.startsWith("club/")) return decodeURIComponent(raw.slice(5)).trim();
      return null;
    },
  };
})();
