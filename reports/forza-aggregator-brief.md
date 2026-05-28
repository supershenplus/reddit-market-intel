# Forza Content Aggregator — Build Brief

*2026-05-27 — 8 days post-FH6 launch*

## TL;DR

There's a 4-6 week window to ship a **scrape-driven, ad-supported, SEO-optimized aggregator** for Forza creator content (tunes + liveries + EventLab) before the only credible incumbent locks the niche in. You're already building the tunes half. The economics work as a free-with-ads play (target $50–$100/mo per niche scales with reach, not per-user pricing). Three concrete wedges against the incumbent. Discrete deadline catalyst on June 30.

---

## The opportunity

A single website that indexes Forza shared content — **tunes, liveries, EventLab blueprints, photography** — from across r/forza, r/ForzaHorizon6, r/ForzaMotorsport, Imgur, and Discord. Filterable by car, class (S2/S1/A/B/C/D), surface (road/dirt/cross-country), creator GT tag, and freshness. Search-engine friendly so the long tail of "GT shared liveries Toyota Supra" / "FH6 best A 800 RWD tune" queries lands on your pages, not buried in 6-month-old Reddit threads.

Monetization: display ads (Google AdSense, Carbon, or a mid-tier network). Volume-driven — a few thousand monthly actives in the Forza community is enough.

---

## Why now (timing)

**Two discrete tailwinds stacking:**

1. **FH6 launched 2026-05-19.** The post-launch attention window is the highest-traffic period a Forza game ever gets. New players are forming search habits *right now* for "how do I tune class A AWD" / "best liveries for the Supra." Whoever's on page 1 of Google at week 4 keeps that real estate for a year.
2. **Official Forza Forums shut down 2026-06-30** after 20 years of league recruitment and creator galleries. Microsoft is explicitly pushing displaced traffic to Discord and the subreddits. Demand-side vacuum is *dated* — not a vague trend, an actual cliff in ~5 weeks. Creators who used to dump tunes/liveries on the forum need a new home.

Combined: the audience is bigger than normal AND the established gathering place is disappearing. Tools that ship in the next 4-6 weeks land into expanded, redirected attention. Tools that ship 3 months later land into ForzaHub's already-established habit loop.

---

## Competitive landscape

### The credible incumbent: [ForzaHub.io](https://forzahub.io)

Launched **2026-05-26** (one week post-FH6, exact same trigger window). Covers tunes, liveries, EventLab, photography. Accepts submissions from Reddit, Imgur, Discord, in-game galleries. They're going for the same thing.

**Their structural weaknesses — your three wedges:**

| Wedge | ForzaHub | Us |
|---|---|---|
| **Coverage** | Submission-based — creators must upload | Scraper-driven — indexes r/forza posts authors never bother to cross-post. Catches the long tail. |
| **Sustainability** | Ad-free (no monetization) | Ad-supported — revenue funds better UX, more content sources, faster scraping cadence |
| **SEO** | JS-heavy SPA — Google struggles to index | Server-rendered (Next.js SSG or Astro) — clean Google surface for high-intent queries |

They're 8 days old and growing fast. The window closes when they add scraping (probably within 1-2 months). If we ship in 4-6 weeks, we get there first on the scraper + SEO axes and lock in habit before they pivot.

### Other players (not real competition)

- **PJTierney.net** — single-creator livery portfolio, not aggregator
- **GTPlanet liveries thread** — forum thread, not searchable gallery
- **FELIXDICIT FH5 Hub** — dead since 2021
- **forza.tools / fh6tune.com / Apex Tune Hub / F.A.T.T.Y** — tuning *calculators*, orthogonal niche (input-driven, not content-aggregation)

### Niches we are NOT entering

- **Car-pass / backstage ROI calculator** — investigated; FH6 ships a fixed 30-car Car Pass with weekly auto-delivery, no "which to pick" decision exists. Static guides + YouTube own this query. Dead premise.
- **League / event directory** — separate product (SimGrid, SimLeaguePro, Grid Finder cover sim-serious; casual car-meet niche is genuinely open but a different audience and architecture). Possible v2, not v1.

---

## What we'd build

### MVP scope (v1, ship in 4-6 weeks)

**Two content surfaces at launch — tunes + liveries.** Same scraper, same schema, two browse paths. Photography and EventLab as v1.1 once we know which surface gets traction.

Core features:
- **Indexed search** by car (year + make + model), class (S2/S1/A/B/C/D/E), surface (road / dirt / cross-country / drag), creator GT tag, freshness
- **Server-rendered detail pages** — one per shared item, with the share code, screenshots, creator info, source post link, and 3-5 related items. These are the Google entry points.
- **Daily scrape** of r/forza, r/ForzaHorizon6, r/ForzaMotorsport new+top posts. Regex extraction of `Share code: NNN NNN NNN` patterns from titles, bodies, and comments. Imgur preview pulls.
- **Creator profiles** — auto-generated from GT tags. Lets a creator's portfolio aggregate without them needing an account.
- **Submission form** (secondary path) for creators who want to be sure they're indexed and don't post to Reddit.

What's NOT in v1:
- User accounts / favorites / comments (defer until traffic justifies)
- In-game share-code one-click copy (defer — needs Forza API or browser extension)
- Mobile app (web-first; mobile-web is fine for v1)
- Discord bot integration (v1.1 if a Forza Discord community wants it)

### Suggested division of work

Acknowledging you're already building tunes:

- **You (tunes side):** keep doing what you're doing — tune extraction, tune data model, tune-specific filters (PI rating, drivetrain, surface). You probably have most of this.
- **Me (liveries + plumbing):** livery extraction (regex + Imgur preview pull), shared infrastructure (Next.js app, scraper cron, search indexing — Meilisearch or Postgres FTS), SEO + analytics, ad integration. Reddit scraper code I've already built in another project I can adapt.
- **Together:** schema design (so tunes + liveries share the creator/car/class entities), domain pick, hosting setup, content moderation approach.

If you'd rather stay tunes-only and have liveries be a separate sibling site, that's also fine — but a single domain with two content tabs likely wins on SEO authority and ad-RPM at the volume we're targeting.

### Stack proposal (open to your preferences)

- **Frontend:** Next.js (SSG/ISR for content pages, SSR for search). Server-rendered = Google can index everything.
- **Backend:** Postgres on Supabase (or Neon free tier) — content schema is simple, no need for elaborate infra.
- **Scraper:** Python + PRAW (Reddit API) on a GitHub Actions cron (free tier, daily/hourly cadence). I already have the scraping pipeline working in another project; ~80% reusable.
- **Search:** Meilisearch (self-hosted on a $5 VPS) or Postgres FTS if we want zero ops. Meilisearch is faster for filter-heavy queries.
- **Hosting:** Vercel (frontend) + Supabase (DB) + Fly.io or a $5 Hetzner box (search + scraper cron). All free or near-free at MVP scale.
- **Domain + ads:** ~$15 for domain, Google AdSense or Carbon Ads. Initial revenue covers hosting; growth = pure margin.

Total cost to ship: **<$50 for the first 6 months.** Break-even at maybe ~3,000 monthly visits depending on ad CPM.

---

## Risks (honest list)

1. **ForzaHub adds scraping in week 4** and our wedge collapses. Mitigation: ship a v0.5 in 2 weeks (scrape + bare-bones browse, no SEO polish yet) to plant the flag and start indexing in Google before the v1 polish lands.
2. **Reddit changes API pricing or terms** (they've done it before). Mitigation: don't rely solely on PRAW; have a Pushshift-style fallback or direct HTML scrape ready. Also: most of the content is in post bodies anyway, not requiring auth.
3. **Ad CPMs in gaming verticals are mediocre** ($1-3 RPM typical, vs $10+ for finance/SaaS). At 10K monthly pageviews that's $10-30/mo. Need to think in terms of 100K+ pageviews to hit the $50-100/mo target. Achievable but takes 3-6 months of compounding SEO.
4. **Content moderation** — someone posts a NSFW livery or copyrighted brand work. We need a flag/takedown flow before launch.
5. **FM team shutdown** (Turn 10 was reportedly shut down) slows FM-side content velocity. Doesn't affect FH side; just means we lean Horizon-heavy in v1.

---

## What I need from you to move forward

1. **Are you in?** Or would you rather keep tunes as your own thing and have us build liveries as a sibling site?
2. **What's the current state of your tune work?** (codebase, data model, hosting if any — so I can mesh into it instead of duplicating)
3. **Time commitment** — what's a realistic shipping cadence on your end? I'm thinking 4-6 weeks to a public MVP if we move with intent.
4. **Brand / domain preferences** — any thoughts? (e.g., `forzashare.gg`, `tunehub.io`, something cleaner). Worth picking early so we don't squat on multiple namespaces.

If we're aligned on shape, the next concrete step is a 30-minute call to sync on schema + scope, then we both block out the first 2-week sprint.

---

*If you want the underlying analysis — competitive deep-dives on each candidate, the behavioral-signal methodology, the data I scraped to validate this — happy to share separately.*
