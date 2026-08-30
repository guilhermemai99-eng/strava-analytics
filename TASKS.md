# Pulse — project status

Last updated: 2026-08-30

Pulse is a social running app: find people, find a pace, run together.
Strava remains the activity data source. The product centre is real runs and people.

## Done

### Auth, profile, Strava
- Strava OAuth, sessions, encrypted tokens
- Pulse profile (name, handle, avatar, bio, city, public/private)
- Activity import with photos and polylines

### Social graph (partial)
- Follow / unfollow
- Followers / following lists
- Public vs private **profiles** (`is_profile_public`) — private profiles hide content from non-owners
- **Not done:** follow *requests* for private accounts (follow is currently blocked/hidden, not requested)

### Direct messages
- Mutual-follow required to start a chat
- Inbox, thread, unread badges
- **Not done:** sending a feed post as a message card

### Notifications
- Follow, mutual follow, new message
- Activity page + nav badge
- **Not done:** likes, comments, run join, club events

### Feed (partial)
- Own activities as Instagram-style posts
- Photo + map media, Pulse titles
- Like / comment / share / ⋯ menu are **visual only** (no backend)
- Feed scope is **self only** — does not yet include people you follow
- No post privacy, hide, comments, or likes

### Explore (partial)
- People search + suggested public runners
- Masonry still mixes activity tiles with people
- **Product rule (next):** Explore is people-only — no runs, clubs, or posts as primary content

### Runs (Phase 1)
- Create / discover / join / leave / My Runs
- Pace compatibility (Great / Possible / Challenging) — never blocks join
- Visibility: everyone / followers / invite only

### People matching (Phase 2)
- Discover → People, match score, **Run together** prefill

### Run Clubs (Phase 3) — current branch `cursor/run-clubs-b3a3`
- Models + APIs: create, join, leave, discover, members, club runs
- Public listable/joinable; private 404 for non-members; owner cannot leave
- UI: Discover → Clubs, `#club/{id}` (Upcoming / Feed / Members), Create Club
- Host a run as a club (owner/admin)
- Run cards: “Hosted by {club}”

## In progress / next (product roadmap)

Priority: finish Clubs, then social feed, then remaining gaps.

| # | Phase | Status |
|---|--------|--------|
| 0 | Finish Run Clubs (UI + tests + PR) | This PR |
| 1 | Audit / stabilize | After Clubs lands |
| 2 | Feed: photo-first overlay, likes, comments, share, hide, privacy, working menu | Next |
| 3 | Follow requests for private accounts; profile social/running/lab split | After feed |
| 4 | Explore people-only + simple filters | After feed |
| 5 | Chat: share posts into DMs | With feed share |
| 6 | Runs polish (already shipped core) | Later |
| 7 | Clubs polish (cover image, invites) | Later |
| 8 | Notifications for likes/comments/runs + UX polish | After social posts |
| 9 | Production pass (privacy, mobile, dead UI) | Ongoing |

## Do not ship

- Dead buttons (feed like/comment/share/menu)
- Explore as a dump of runs
- Exact GPS on people cards
- Follow-anyone DMs
