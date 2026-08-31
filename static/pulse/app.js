const ICONS = {
    feed: "/static/pulse/icons/feed.svg",
    runs: "/static/pulse/icons/runs.svg",
    discover: "/static/pulse/icons/discover.svg",
    profile: "/static/pulse/icons/profile.svg",
    heart: "/static/pulse/icons/heart.svg",
    comment: "/static/pulse/icons/comment.svg",
    share: "/static/pulse/icons/share.svg",
    plus: "/static/pulse/icons/plus.svg",
    bell: "/static/pulse/icons/bell.svg"
};

const PHOTOS = {
    urban: "/static/pulse/photos/run-urban.jpg",
    group: "/static/pulse/photos/run-group.jpg",
    map: "/static/pulse/photos/run-map.jpg",
    shoes: "/static/pulse/photos/run-shoes.jpg",
    water: "/static/pulse/photos/run-waterfront.jpg",
    ines: "/static/pulse/photos/avatar-ines.jpg",
    pedro: "/static/pulse/photos/avatar-pedro.jpg",
    marta: "/static/pulse/photos/avatar-marta.jpg"
};

const SOCIAL_FEED = [
    {
        id: "ines-12",
        name: "Inês Costa",
        avatar: PHOTOS.ines,
        when: "2H AGO · PORTO",
        media: PHOTOS.urban,
        kind: "photo",
        km: "12.4 KM",
        pace: "5:02 /KM",
        time: "01:02:21",
        city: "PORTO",
        likes: 128,
        comments: ["Que ritmo. Até sábado?", "Foz estava cheia hoje."]
    },
    {
        id: "pedro-8",
        name: "Pedro Alves",
        avatar: PHOTOS.pedro,
        when: "THIS MORNING · MATOSINHOS",
        media: PHOTOS.map,
        kind: "map",
        km: "8.6 KM",
        pace: "4:48 /KM",
        time: "00:41:12",
        city: "MATOSINHOS",
        likes: 86,
        comments: ["Vamos juntos na terça."]
    },
    {
        id: "marta-10",
        name: "Marta Reis",
        avatar: PHOTOS.marta,
        when: "YESTERDAY · FOZ",
        media: PHOTOS.group,
        kind: "photo",
        km: "10.0 KM",
        pace: "5:30 /KM",
        time: "00:55:04",
        city: "FOZ DO DOURO",
        likes: 64,
        comments: ["Crew energy."]
    }
];

const RUNNERS = [
    { id: "pedro", name: "Pedro Alves", meta: "5:00–5:20 /KM  ·  3 KM AWAY", avatar: PHOTOS.pedro },
    { id: "sofia", name: "Sofia Nunes", meta: "5:20–5:40 /KM  ·  1 KM AWAY", avatar: PHOTOS.marta },
    { id: "tiago", name: "Tiago Melo", meta: "4:40–5:00 /KM  ·  5 KM AWAY", avatar: PHOTOS.pedro },
    { id: "ana", name: "Ana Rocha", meta: "SIMILAR PACE  ·  4 MUTUAL", avatar: PHOTOS.ines, likeYou: true }
];

const CLUBS = [
    { id: "north", name: "NORTH RUN CLUB", meta: "1.2K MEMBERS  ·  NEXT RUN SATURDAY" },
    { id: "foz", name: "FOZ SUNRISE", meta: "340 MEMBERS  ·  NEXT RUN SUNDAY" }
];

const DEFAULT_RUNS = [
    {
        id: "sat",
        title: "SATURDAY MORNING RUN",
        detail: "10 KM  ·  EASY",
        when: "09:00  ·  Foz do Douro, Porto",
        pace: "5:30–6:00 /KM",
        extra: "+12 RUNNERS"
    },
    {
        id: "tue",
        title: "TUESDAY TRACK",
        detail: "8 KM  ·  STEADY",
        when: "19:30  ·  Estádio do Mar",
        pace: "4:50–5:10 /KM",
        extra: "+8 RUNNERS"
    }
];

function store(key, fallback) {
    try {
        const raw = localStorage.getItem(key);
        return raw ? JSON.parse(raw) : fallback;
    } catch (error) {
        return fallback;
    }
}

function save(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
}

const state = {
    likes: store("pulse-likes", {}),
    follows: store("pulse-follows", {}),
    joins: store("pulse-joins", {}),
    createdRuns: store("pulse-created-runs", []),
    comments: store("pulse-comments", {}),
    screen: "feed",
    athlete: null,
    activities: []
};

function icon(name) {
    return `<span class="icon"><img src="${ICONS[name]}" width="22" height="22" alt=""></span>`;
}

function toast(message) {
    const el = document.getElementById("toast");
    el.textContent = message;
    el.style.display = "block";
    clearTimeout(toast._t);
    toast._t = setTimeout(() => {
        el.style.display = "none";
    }, 1800);
}

function paceFromSpeed(ms) {
    if (!ms) {
        return "—";
    }
    const sec = 1000 / ms;
    const m = Math.floor(sec / 60);
    const s = Math.round(sec % 60).toString().padStart(2, "0");
    return `${m}:${s} /KM`;
}

function formatDuration(seconds) {
    if (!seconds) {
        return "—";
    }
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h) {
        return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
    }
    return `00:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function kmFrom(activity) {
    if (!activity.distance_m) {
        return "—";
    }
    return `${(activity.distance_m / 1000).toFixed(1)} KM`;
}

function setScreen(name) {
    state.screen = name;
    document.querySelectorAll(".screen").forEach((node) => {
        node.classList.toggle("active", node.dataset.screen === name);
    });
    document.querySelectorAll("[data-nav]").forEach((node) => {
        node.classList.toggle("active", node.dataset.nav === name);
    });
    if (location.hash.replace("#", "") !== name) {
        history.replaceState(null, "", `#${name}`);
    }
}

function likeCount(post) {
    const extra = state.likes[post.id] ? 1 : 0;
    const baseLiked = false;
    return post.likes + extra;
}

function renderFeed() {
    const root = document.getElementById("feed-list");
    const mine = state.activities.slice(0, 2).map((activity, index) => ({
        id: `me-${activity.strava_id || activity.id}`,
        name: "Tu",
        avatar: PHOTOS.ines,
        when: (activity.start_date_local || "RECENT").slice(0, 10) + " · A TUA CORRIDA",
        media: index % 2 ? PHOTOS.map : PHOTOS.water,
        kind: index % 2 ? "map" : "photo",
        km: kmFrom(activity),
        pace: paceFromSpeed(activity.average_speed_m_s),
        time: formatDuration(activity.moving_time_s),
        city: activity.name || "RUN",
        likes: activity.kudos_count || 0,
        comments: []
    }));
    const posts = [...SOCIAL_FEED, ...mine];
    root.innerHTML = posts.map((post) => {
        const liked = Boolean(state.likes[post.id]);
        const comments = [...(post.comments || []), ...(state.comments[post.id] || [])];
        return `
            <article class="post">
                <div class="identity">
                    <img class="avatar" src="${post.avatar}" alt="${post.name}">
                    <div>
                        <p class="name">${post.name}</p>
                        <p class="meta">${post.when}</p>
                    </div>
                </div>
                <img class="post-media ${post.kind}" src="${post.media}" alt="">
                <div class="post-body">
                    <p class="stat">${post.km}</p>
                    <div class="stat-row"><span>${post.pace}</span><span>${post.time}</span></div>
                    <p class="meta">${post.city}</p>
                    <div class="actions">
                        <button class="action ${liked ? "liked" : ""}" data-like="${post.id}">
                            <img src="${ICONS.heart}" width="20" height="20" alt="">
                            ${likeCount(post)}
                        </button>
                        <button class="action" data-comment="${post.id}">
                            <img src="${ICONS.comment}" width="20" height="20" alt="">
                            ${comments.length}
                        </button>
                        <button class="action" data-share="${post.id}">
                            <img src="${ICONS.share}" width="20" height="20" alt="">
                            SHARE
                        </button>
                    </div>
                </div>
            </article>
        `;
    }).join("");
}

function renderRuns() {
    const recent = document.getElementById("recent-runs");
    const photos = [PHOTOS.map, PHOTOS.water, PHOTOS.urban, PHOTOS.shoes];
    const items = state.activities.slice(0, 6);
    if (!items.length) {
        recent.innerHTML = `
            <article class="recent-card">
                <img src="${PHOTOS.map}" alt="">
                <div class="copy"><p class="km">8.2 KM</p><p class="meta">YESTERDAY · PORTO</p></div>
            </article>
            <article class="recent-card">
                <img src="${PHOTOS.water}" alt="">
                <div class="copy"><p class="km">14.1 KM</p><p class="meta">SUN · GAIA</p></div>
            </article>
        `;
    } else {
        recent.innerHTML = items.map((activity, index) => `
            <article class="recent-card">
                <img src="${photos[index % photos.length]}" alt="">
                <div class="copy">
                    <p class="km">${kmFrom(activity)}</p>
                    <p class="meta">${(activity.start_date_local || "").slice(0, 10)} · ${activity.name || "RUN"}</p>
                </div>
            </article>
        `).join("");
    }

    const upcoming = [...state.createdRuns, ...DEFAULT_RUNS];
    document.getElementById("upcoming-runs").innerHTML = upcoming.map((run) => {
        const joined = Boolean(state.joins[run.id]);
        return `
            <article class="run-card">
                <h2>${run.title}</h2>
                <p class="meta">${run.detail}</p>
                <p class="body-copy">${run.when}</p>
                <p class="stat-row" style="margin:8px 0 0">${run.pace}</p>
                <div class="people">
                    <div class="faces">
                        <img class="avatar sm" src="${PHOTOS.ines}" alt="">
                        <img class="avatar sm" src="${PHOTOS.pedro}" alt="">
                        <img class="avatar sm" src="${PHOTOS.marta}" alt="">
                    </div>
                    <span class="meta">${run.extra || "+1 RUNNER"}</span>
                </div>
                <button class="btn primary full ${joined ? "joined" : ""}" data-join="${run.id}">
                    ${joined ? "JOINED" : "JOIN RUN →"}
                </button>
            </article>
        `;
    }).join("");
}

function renderDiscover() {
    document.getElementById("runners-near").innerHTML = RUNNERS.filter((r) => !r.likeYou).map((runner) => `
        <article class="runner-card">
            <img class="avatar" src="${runner.avatar}" alt="">
            <div class="info">
                <p class="name">${runner.name}</p>
                <p class="meta">${runner.meta}</p>
            </div>
            <button class="btn ${state.follows[runner.id] ? "inverse" : ""}" data-follow="${runner.id}">
                ${state.follows[runner.id] ? "FOLLOWING" : "CONNECT"}
            </button>
        </article>
    `).join("");

    document.getElementById("runners-like").innerHTML = RUNNERS.filter((r) => r.likeYou).map((runner) => `
        <article class="runner-card">
            <img class="avatar" src="${runner.avatar}" alt="">
            <div class="info">
                <p class="name">${runner.name}</p>
                <p class="meta">${runner.meta}</p>
            </div>
            <button class="btn ${state.follows[runner.id] ? "inverse" : ""}" data-follow="${runner.id}">
                ${state.follows[runner.id] ? "FOLLOWING" : "CONNECT"}
            </button>
        </article>
    `).join("");

    document.getElementById("clubs").innerHTML = CLUBS.map((club) => `
        <article class="club-card">
            <div class="club-mark"></div>
            <h2>${club.name}</h2>
            <p class="meta">${club.meta}</p>
        </article>
    `).join("");
}

function renderProfile() {
    const runs = state.activities.filter((a) => {
        const sport = (a.sport_type || "").toLowerCase();
        return !sport || sport.includes("run");
    });
    const totalKm = runs.reduce((sum, a) => sum + (a.distance_m || 0), 0) / 1000;
    const avgSpeed = runs.length
        ? runs.reduce((sum, a) => sum + (a.average_speed_m_s || 0), 0) / runs.length
        : 0;

    document.getElementById("profile-distance").textContent = totalKm
        ? `${Math.round(totalKm).toLocaleString("pt-PT")} KM`
        : "1,284 KM";
    document.getElementById("profile-runs").textContent = runs.length || "92";
    document.getElementById("profile-pace").textContent = avgSpeed
        ? paceFromSpeed(avgSpeed).replace(" /KM", "")
        : "4:38";

    const gridPhotos = [PHOTOS.urban, PHOTOS.map, PHOTOS.group, PHOTOS.shoes, PHOTOS.water, PHOTOS.map];
    document.getElementById("activity-grid").innerHTML = gridPhotos.map((src) =>
        `<img src="${src}" alt="">`
    ).join("");
}

function renderAll() {
    renderFeed();
    renderRuns();
    renderDiscover();
    renderProfile();
}

function openSheet(id) {
    document.getElementById(id).classList.add("open");
}

function closeSheets() {
    document.querySelectorAll(".sheet").forEach((node) => node.classList.remove("open"));
}

document.addEventListener("click", (event) => {
    const nav = event.target.closest("[data-nav]");
    if (nav) {
        event.preventDefault();
        setScreen(nav.dataset.nav);
    }

    const like = event.target.closest("[data-like]");
    if (like) {
        const id = like.dataset.like;
        state.likes[id] = !state.likes[id];
        save("pulse-likes", state.likes);
        renderFeed();
    }

    const follow = event.target.closest("[data-follow]");
    if (follow) {
        const id = follow.dataset.follow;
        state.follows[id] = !state.follows[id];
        save("pulse-follows", state.follows);
        renderDiscover();
        toast(state.follows[id] ? "Ligado." : "Ligação removida.");
    }

    const join = event.target.closest("[data-join]");
    if (join) {
        const id = join.dataset.join;
        state.joins[id] = !state.joins[id];
        save("pulse-joins", state.joins);
        renderRuns();
        toast(state.joins[id] ? "Vais nesta corrida." : "Saiste da corrida.");
    }

    const share = event.target.closest("[data-share]");
    if (share) {
        const text = "PULSE — RUN TOGETHER. GET BETTER.";
        if (navigator.share) {
            navigator.share({ title: "PULSE", text });
        } else {
            navigator.clipboard.writeText(text);
            toast("Link copiado.");
        }
    }

    const comment = event.target.closest("[data-comment]");
    if (comment) {
        document.getElementById("comment-post").value = comment.dataset.comment;
        openSheet("comment-sheet");
    }

    if (event.target.closest("[data-open='create']")) {
        openSheet("create-sheet");
    }
    if (event.target.closest("[data-open='notify']")) {
        openSheet("notify-sheet");
    }
    if (event.target.closest("[data-close]")) {
        closeSheets();
    }
});

document.getElementById("create-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const data = new FormData(event.target);
    state.createdRuns.unshift({
        id: `new-${Date.now()}`,
        title: String(data.get("title") || "NEW RUN").toUpperCase(),
        detail: `${data.get("distance") || "10"} KM  ·  ${data.get("effort") || "EASY"}`,
        when: `${data.get("time") || "09:00"}  ·  ${data.get("place") || "Porto"}`,
        pace: data.get("pace") || "5:30–6:00 /KM",
        extra: "+1 RUNNER"
    });
    save("pulse-created-runs", state.createdRuns);
    event.target.reset();
    closeSheets();
    setScreen("runs");
    renderRuns();
    toast("Corrida criada.");
});

document.getElementById("comment-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const id = document.getElementById("comment-post").value;
    const text = String(new FormData(event.target).get("text") || "").trim();
    if (text) {
        state.comments[id] = state.comments[id] || [];
        state.comments[id].push(text);
        save("pulse-comments", state.comments);
        renderFeed();
    }
    event.target.reset();
    closeSheets();
});

window.addEventListener("hashchange", () => {
    const name = location.hash.replace("#", "") || "feed";
    if (["feed", "runs", "discover", "profile"].includes(name)) {
        setScreen(name);
    }
});

async function boot() {
    const hash = location.hash.replace("#", "") || "feed";
    if (["feed", "runs", "discover", "profile"].includes(hash)) {
        setScreen(hash);
    }

    try {
        const me = await fetch("/auth/me").then((r) => r.json());
        state.athlete = me;
        if (me.authenticated) {
            const activities = await fetch("/activities").then((r) => r.json());
            if (Array.isArray(activities)) {
                state.activities = activities
                    .slice()
                    .sort((a, b) => String(b.start_date || "").localeCompare(String(a.start_date || "")));
            }
        }
    } catch (error) {
        state.activities = [];
    }

    renderAll();
}

boot();
