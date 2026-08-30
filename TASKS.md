# Pulse — project status

Last updated: 2026-08-30

Pulse is a social running app: find people, find a pace, run together.
Strava remains the activity data source. The product centre is real runs and people.

## Done

### Auth, profile, Strava
- Strava OAuth, sessions, encrypted tokens
- Pulse profile (name, handle, avatar, bio, city, public/private)
- Activity import with photos and polylines

### Social graph
- Follow / unfollow
- Followers / following lists
- Public vs private **profiles** (`is_profile_public`)
- **Follow requests** for private accounts (request / accept / decline / cancel)
- Accepted followers can see a private profile; everyone else sees a locked page

### Direct messages
- Mutual-follow required to start a chat
- Inbox, thread, unread badges
- Share a feed post into DMs

### Notifications
- Follow, mutual follow, new message, likes, comments
- Follow request + accepted request
- **Run join** — host notified when someone joins
- **Club join** — owners/admins notified
- **Club run** — members notified when a club-hosted run is posted
- Activity page + nav badge
- Caption edit uses in-app sheet (no `window.prompt`)

### Feed
- Home feed: **your runs + people you follow**
- Photo-first overlay (distance / time / pace); map fallback when there is no photo
- Likes, comments, hide (+ undo), privacy (public / followers / private), author delete
- Share a post into DMs (mutual follow required)

### Explore / Discover people
- Discover defaults to **People** — search, pace matches, nearby / recent / new
- No activity masonry, no runs or clubs as primary Explore content
- `#explore` and More → Find people open Discover → People
- Exact-handle search can find private accounts so you can request to follow

### Runs
- Create / discover / join / leave / My Runs
- Pace compatibility (Great / Possible / Challenging) — never blocks join

### People matching
- Match score + **Run together** prefill

### Run Clubs
- Create, join, leave, discover, members, club runs
- Host a run as a club (owner/admin)
- Cover image upload (blob) on club hero/cards
- Direct invites by handle + shareable invite links
- Accept/decline in Notifications and on the club page

## Next

| # | Phase | Status |
|---|--------|--------|
| 1 | Production pass (privacy, mobile, dead UI) | Ongoing (#34) |
| 2 | Broader polish | Later |

## Do not ship

- Dead buttons
- Explore as a dump of runs
- Exact GPS on people cards
- Follow-anyone DMs
