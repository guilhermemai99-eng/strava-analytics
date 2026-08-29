/* Pulse microcopy — subtle personality, one source of truth.
   Categories are arrays of short English lines. Pick once per session key
   so UI does not flicker across re-renders. */
(() => {
  "use strict";

  const COPY = {
    landing: {
      headlines: [
        "Your training has stories.",
        "Run. Train. Overthink the data.",
        "Fitness, with slightly more personality.",
      ],
      secondary: [
        "The numbers know what you did last weekend.",
        "Some workouts deserve more than a spreadsheet.",
        "Because apparently, you needed more stats.",
        "Turn suffering into something worth sharing.",
        "Your miles, without the spreadsheet energy.",
        "Cardio was a choice. Sharing it is another.",
      ],
    },

    loading: [
      "Crunching the numbers…",
      "Consulting the running gods…",
      "Looking for your fastest questionable decision…",
      "Doing maths so you don’t have to.",
      "Almost there. Probably.",
      "Analysing questionable pacing decisions…",
      "Finding the important stuff.",
      "Making sense of your suffering…",
      "Checking who’s been avoiding recovery…",
    ],

    emptyStates: {
      activities: [
        {
          title: "Nothing here yet.",
          body: "Go outside and give us something to analyse.",
        },
        {
          title: "Zero miles on the board.",
          body: "Your couch is currently undefeated. Fix that.",
        },
        {
          title: "Quiet profile.",
          body: "Sync Strava when you’re ready to show receipts.",
        },
      ],
      followers: [
        {
          title: "It’s quiet here.",
          body: "Invite someone. Preferably someone who actually runs.",
        },
        {
          title: "No one’s watching. Yet.",
          body: "Share your handle when you’re ready for an audience.",
        },
      ],
      following: [
        {
          title: "Your feed is feeling lonely.",
          body: "Follow someone and start pretending you understand their training plan.",
        },
        {
          title: "Running solo. Socially, too.",
          body: "Explore is right there. No pressure. Some pressure.",
        },
      ],
      feed: [
        {
          title: "Too quiet.",
          body: "Follow some athletes and let the mileage start appearing.",
        },
        {
          title: "No miles yet.",
          body: "Sync Strava, or follow someone who’s already suffering productively.",
        },
      ],
      explore: [
        {
          title: "Quiet streets.",
          body: "Public runners show up here. Be patient — or be visible.",
        },
      ],
    },

    follow: [
      "New training to stalk.",
      "You’re officially invested now.",
      "Their easy runs are now your problem too.",
      "Consider yourself emotionally involved.",
      "Following noted. Judgement optional.",
    ],

    unfollow: {
      titles: ["Unfollow {name}?"],
      bodies: [
        "Are you sure you want to stop following @{handle}? Their runs will have to continue without your emotional support.",
        "You won’t see their questionable splits anymore.",
        "Their easy runs will have to continue without you.",
        "No hard feelings. Probably.",
      ],
      keep: "Keep following",
      confirm: "Unfollow",
    },

    deleteAccount: {
      step1: {
        title: "Leaving already?",
        body: "Are you sure you want to delete your account? All your stats, achievements and questionable running decisions will disappear with you.",
        keep: "Keep my account",
        confirm: "Delete account",
      },
      step2: {
        title: "Last chance. Seriously.",
        body: "This is permanent. Your activities, stats, achievements and profile will be gone. No undo button. No magical recovery. Even your legendary runs won’t survive.",
        keep: "Wait, I changed my mind",
        confirm: "Yes, delete everything",
      },
      done: "Your account has officially vanished into the void.",
    },

    achievements: {
      unlocked: [
        "Character development unlocked.",
        "Achievement unlocked. Try not to get used to it.",
      ],
      personalBest: [
        "New personal best. Your old self has been defeated.",
        "PB secured. Screenshots are forever.",
      ],
      streak: [
        "Consistency looks good on you.",
        "Consistency is becoming suspicious.",
      ],
      milestone: [
        "That’s a lot of kilometres for someone who could have stayed on the sofa.",
        "Apparently, staying home wasn’t an option.",
      ],
    },

    profileInsights: {
      highMileage: [
        "Apparently, staying home wasn’t an option.",
        "That’s a serious amount of pavement.",
      ],
      consistent: [
        "Consistency is becoming suspicious.",
        "Showing up again. We notice.",
      ],
      fresh: [
        "Still early. Character development pending.",
        "Nothing to see here. Yet.",
      ],
      afterPb: [
        "Your previous self would like a word.",
        "That one will age well in the archive.",
      ],
    },

    activityInsights: {
      long: ["Someone had time today.", "Distance with commitment."],
      hard: ["Definitely not an easy day.", "That one earned a quiet evening."],
      short: ["Short. Efficient. We respect it.", "In and out. Clean."],
      recovery: ["Rest-adjacent. We believe you.", "Easy on purpose. Allegedly."],
      uneven: [
        "The pacing had a personality of its own.",
        "Splits with opinions.",
      ],
    },

    success: {
      sync: [
        "Fresh data.",
        "Your suffering has been recorded.",
        "Stats updated. The numbers don’t lie.",
        "Another one for the archive.",
      ],
      generic: ["Done.", "Consider it handled.", "Sorted.", "Main character moment."],
      profile: [
        "Saved. You’re still you — just clearer.",
        "Profile updated. Looking intentional.",
      ],
      unfollow: [
        "Unfollowed. Space created.",
        "Done. Their splits will miss you.",
      ],
    },

    errors: [
      "Well, that didn’t go as planned.",
      "Something broke. We’re looking into it.",
      "That didn’t work. Try again?",
      "Technology is having a moment.",
      "That didn’t go the distance.",
    ],

    coachTaglines: [
      "Your legs don’t lie.",
      "Let’s make those miles count.",
      "Still alive after that long run?",
      "Advice with bite. Numbers with jokes.",
      "Cardio was a choice.",
    ],
  };

  const sessionPicks = Object.create(null);

  function list(categoryPath) {
    const parts = String(categoryPath || "").split(".");
    let cur = COPY;
    for (const part of parts) {
      if (cur == null || typeof cur !== "object") return [];
      cur = cur[part];
    }
    if (Array.isArray(cur)) return cur;
    return [];
  }

  function pick(categoryPath, sessionKey) {
    const items = list(categoryPath);
    if (!items.length) return "";
    const key = sessionKey || categoryPath;
    if (Object.prototype.hasOwnProperty.call(sessionPicks, key)) {
      return sessionPicks[key];
    }
    const chosen = items[Math.floor(Math.random() * items.length)];
    sessionPicks[key] = chosen;
    return chosen;
  }

  function pickFresh(categoryPath) {
    const items = list(categoryPath);
    if (!items.length) return "";
    return items[Math.floor(Math.random() * items.length)];
  }

  function format(template, vars) {
    return String(template || "").replace(/\{(\w+)\}/g, (_, name) => {
      const value = vars && vars[name];
      return value == null ? "" : String(value);
    });
  }

  function emptyState(kind, sessionKey) {
    const item = pick(`emptyStates.${kind}`, sessionKey || `empty.${kind}`);
    if (item && typeof item === "object") return item;
    return { title: "Nothing here yet.", body: "" };
  }

  function activityInsight(activity) {
    if (!activity || typeof activity !== "object") return null;
    const km =
      activity.distance_km != null
        ? Number(activity.distance_km)
        : activity.distance_m != null
          ? Number(activity.distance_m) / 1000
          : null;
    const moving = Number(activity.moving_time_s || 0);
    const type = String(activity.type || activity.sport_type || "").toLowerCase();
    const name = String(activity.original_name || activity.name || "").toLowerCase();

    if (km != null && Number.isFinite(km) && km >= 18) {
      return pickFresh("activityInsights.long");
    }
    if (
      type.includes("workout") ||
      name.includes("interval") ||
      name.includes("tempo") ||
      name.includes("repeat")
    ) {
      return pickFresh("activityInsights.hard");
    }
    if (
      (km != null && km > 0 && km < 5) ||
      (moving > 0 && moving < 25 * 60)
    ) {
      if (name.includes("recover") || name.includes("easy")) {
        return pickFresh("activityInsights.recovery");
      }
      return pickFresh("activityInsights.short");
    }
    if (name.includes("recover") || name.includes("easy")) {
      return pickFresh("activityInsights.recovery");
    }
    return null;
  }

  function profileInsight(profile, activities) {
    const stats = (profile && profile.stats) || {};
    const km =
      stats.total_running_km != null
        ? Number(stats.total_running_km)
        : stats.total_distance_km != null
          ? Number(stats.total_distance_km)
          : null;
    const runs =
      stats.running_activities ??
      stats.total_activities ??
      (Array.isArray(activities) ? activities.length : 0);

    if (km != null && km >= 200) {
      return pick("profileInsights.highMileage", "profile.insight");
    }
    if (runs >= 20) {
      return pick("profileInsights.consistent", "profile.insight");
    }
    if (!runs) {
      return pick("profileInsights.fresh", "profile.insight");
    }
    return null;
  }

  const root = typeof globalThis !== "undefined" ? globalThis : {};
  root.PulseCopy = {
    COPY,
    pick,
    pickFresh,
    format,
    emptyState,
    activityInsight,
    profileInsight,
    list,
  };
})();
