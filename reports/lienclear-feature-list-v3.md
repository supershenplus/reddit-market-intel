# Lienclear — Feature List v3 (competitor-validated, wedge-narrowed)

**Generated**: 2026-05-27
**Supersedes**: `lienclear-feature-list-v2.md` for prioritization, positioning, and the competitive map. v1/v2 retained for narrative + per-feature design notes only.
**Method delta vs v2**: Three subagents ran in parallel — (1) verified the Planyard self-promotion claim (confirmed: `Top_Drummer_3801` solo founder, hand-prospect playbook), (2) deep-dove on real competitor product pages and pricing (Planyard, Siteline, Levelset, Adaptive, Built Technologies, Knowify, Foundation, JobTread), (3) expanded comment validation to ~120 Tier-2 corpus posts (mostly noise; weakly strengthens v2).

---

## TL;DR — what changes from v2

| | v2 | v3 |
|---|---|---|
| **Surviving wedge** | "Lien-flavored billing" + sub-side ICP | **Transparent per-action pricing for $1–10M specialty subs in trades Siteline skips (excavation, fence, low-voltage, solar, smaller masonry).** |
| **F11 (NOI generator)** | Headline paid Phase-1 feature | **Free SEO/funnel feature** — Built Technologies launched FREE lien waivers as a lender loss-leader, Levelset is bundled inside Procore. Pricing floor for lien tooling approaches $0. |
| **F1+F2+F3 (AIA bundle)** | Primary Phase-2 wedge | **Still primary paid wedge, but Siteline already does this for commercial subs $10M+.** Lienclear's defensible market is the verticals Siteline doesn't court. |
| **Planyard positioning** | Direct competitor | **Adjacent product, not competitor.** Confirmed zero lien features. Their Reddit hand-prospect is competitive intel about the *channel*, not the product surface. |
| **Levelset positioning** | "Procore-owned, must outflank" | **Bundled feature inside a $10B platform.** Can't outflank by feature — outflank by pricing transparency and vertical-specific templates. |
| **Built Technologies** | Not in v2 | **New pricing-floor threat.** Free lien waiver workflow as loss-leader for their lender product. Phase-1 monetization is dead. |
| **Foreclosure workflow + claim estimator (F5)** | Demoted to "filing only" | **Dropped entirely.** Legal liability + Agent 3 found a 3x-damages counter-signal (filing an invalid lien = fraud exposure). Stick to NOI + waiver generation. |
| **Risk surface** | Implicit | **Explicit risk section** — invalid-lien backlash is the moat *and* the liability. |

---

## Strategic posture (v3)

**One-line thesis**:
> Transparent, per-action + low-tier-subscription pricing for lien-rights workflows and AIA billing, aimed at $1–10M specialty trade subs in verticals Siteline doesn't court and who won't tolerate Levelset's opaque-subscription model.

**Why this is what's left**:
- Siteline already does lien-rights-integrated billing for commercial subs $10M+ (auto-NOI from overdue pay apps, conditional/unconditional/progress/final waivers auto-generated from pay-app data). The "lien-flavored billing" wedge from v2 is dead in their market.
- Levelset is a Procore product line with bundling leverage. Can't out-feature it.
- Built Technologies' free lien waiver workflow (loss-leader for their lender product) means anyone trying to monetize lien tooling alone competes with $0.
- Planyard hand-prospects mid-market GCs with finance-flavored billing; zero lien involvement.
- That leaves: **trades Siteline doesn't list** (their commercial vertical menu skips excavation, fence, low-voltage, solar — and goes light on smaller masonry/specialty) + **transparent pricing** (Siteline + Levelset are both opaque, requiring sales calls).

**Implicit ICP cuts**:
- $1–10M annual revenue (below Siteline floor, above hobbyist GCs)
- Specialty trades, not GCs (different workflow; GCs are Procore's market)
- US-based (lien law is jurisdictional)
- 1–10 person back-office (above this, they buy Siteline)
- Self-serve buyer (Procore/Siteline sales motion is the anti-positioning)

---

## Re-ranked feature list (v3)

### Free tier — funnel features (zero revenue, drive SEO + capture intent)

#### F11. Notice-of-Intent-to-Lien generator + state statutory deadline calendar
**Demoted from paid → free.** Built Technologies and Procore-Levelset have both moved this category toward $0. Keep it free; it's a top-of-funnel and an SEO play.

Scope:
- Per-state NOI templates (start with TX, FL, CA, NY — `LIENCLEAR_BEACHHEAD` per `config.py`)
- Deadline calendar tied to job-start date — auto-flag statutory tripwires
- Certified mail / cert-of-service instructions (don't try to print and mail; instruct)
- **Anti-feature**: do NOT auto-file. Filing has 3x-damages exposure if done wrong. Generate, instruct, hand off.

Anti-scope: foreclosure workflow, lien-amount estimator (legal liability — see Risk Section).

#### F-new. Lien waiver generator (conditional/unconditional progress/final)
**New in v3** — surfaced as table-stakes by Agent 2's Siteline + Levelset feature audit. Free tier. State-specific forms only; don't try to be a legal-doc-assembly product.

### Paid tier — primary revenue features

#### F1+F2+F3 bundle. AIA G702/G703 generator + retention/retainage tracker + change-order traceability
**Still the primary paid feature**, but positioning narrows:
- **Vertical-specialize**: ship templates and workflows tuned for excavation, fence, low-voltage, solar, smaller masonry. Use vertical-specific terminology in marketing.
- **Match Siteline's lien-integration depth where it matters**: NOI auto-fires from overdue pay app, waivers auto-generate from pay-app line items. This isn't a wedge against Siteline (they do it); it's table stakes for the *non-commercial* trades.
- **Decimal-safe math** is still the technical wedge against the Excel-G702 status quo (per the headline corpus thread).

#### F12. Retention/retainage tracker
Distinct sub-feature. Critical because retention is where lien windows close and where Levelset/Procore charge for filing. Owning the retention-release calendar = owning the moment subscriptions justify themselves.

#### F9. QuickBooks Online + Desktop sync
Table stakes, not differentiation. Every paid competitor has it (Planyard, Siteline, Adaptive, Knowify, Foundation). Lienclear without QB sync is DOA.

#### F10. Transparent public pricing + self-serve onboarding
**Promoted from "company decision" to "product feature".** Pricing-page-as-feature is the entire wedge. Per Agent 2: Siteline and Levelset both hide pricing behind sales calls; Planyard publishes a per-PM SaaS model. Lienclear's pricing page must be more transparent than Planyard's *and* more accessible than Siteline/Levelset's.

### Phase 3 — expansion (after Phase 1+2 validates)

#### F6. Owner-rep / GC-side dashboard
Real gap per Agent 2 (Siteline does sub→GC submission, not owner visibility; Planyard explicitly punts; Levelset has none). But this is a second product motion (different ICP, different sales cycle). Only after sub-side has paying customers.

### Dropped from v3

| Feature | Reason |
|---|---|
| **F4 standalone AR chase** | Absorbed into F11 — community wants lien leverage, not better dunning |
| **F5 mechanics lien filing** | Legal-liability risk per Agent 3 counter-signal. Generate notices, don't file. |
| **F5 foreclosure workflow + claim estimator** | Top corpus comment explicitly warns against ballpark claim amounts; $50-90k lawsuit cost; community consensus is "cut your losses" |
| **F7 per-building SOV (Forma gap)** | N=1, no comment validation, Agent 3 found zero corroboration in Tier-2 corpus |
| **F8 sub/vendor CRM** | Procore + JobTread + Airtable already saturate; "Claude could build this for you" was the top reply |
| **PLA/certified-payroll/prevailing-wage compliance** | Agent 3 surfaced LCPtracker as the incumbent (N=1). Park as adjacent watchlist; don't pursue without 2+ corroborating posts |

---

## Competitive landscape (v3, fully corrected)

| Competitor | ICP | Pricing | Lien | Billing | QB Sync | Verdict |
|---|---|---|---|---|---|---|
| **Siteline** | Commercial subs $10M+ | Opaque (custom quote) | ✓ (integrated) | ✓ AIA | ✓ | **Head-to-head competitor** — beat on transparent pricing + below-their-floor ICP |
| **Levelset** (Procore) | Subs + suppliers any size | $59/notice + ~$149/mo opaque | ✓ filing | ✗ | ✗ | **Outflank on pricing transparency**, not features |
| **Planyard** | Mid-market GCs (£2-30M EU) | $52-210/PM/mo + $43/staff | ✗ | ✓ | ✓ | **Adjacent product**, not competitor. Possible partnership target. |
| **Built Technologies** | Lenders + developers | Free for lien waivers (loss leader) | partial (waivers) | ✗ | ✗ | **Pricing-floor threat** — kills paid Phase-1 monetization |
| **Adaptive** | GCs | $599/mo flat | partial (waivers) | ✓ AP-heavy | ✓ | Different ICP (GC-leaning) |
| **Knowify** | Subs $1-5M | $99-400/mo | ✗ | ✓ AIA | ✓ (best-in-class) | **Direct paid Phase-2 competitor** in our ICP. Lacks lien layer. |
| **Foundation Software** | MEP, $1-10M | ~$200/mo | ✗ | ✓ AIA | ✓ | Direct Phase-2 competitor; trade-specific |
| **JobTread** | Resi GCs + remodelers | $349/mo flat | ✗ | ✓ | ✓ | Different ICP (resi GC) |
| **Textura** (Oracle) | Enterprise GCs | $25/pay-app | partial | ✓ AIA | varies | Out of ICP (enterprise) |
| **Procore** | GCs $10M+ | $5-6k/yr floor | (via Levelset) | (via Levelset) | varies | Out of ICP, but bundles Levelset |
| **LCPtracker** | Public-works PLA subs | (not researched) | ✗ | ✗ (certified payroll) | ✗ | Adjacent watchlist (N=1) |

**The two competitors that matter for v3**:
1. **Siteline** — defines the upper ICP bound (they sell to subs $10M+; Lienclear sells below)
2. **Knowify** — defines the lower-paid-tier price ceiling ($99-400/mo) and proves the QB-sync-first-class motion works

---

## Pricing thesis (validated by pricing agent)

**Substitution baselines** (what the $1-10M sub already pays):
- Construction-specialized outsourced bookkeeping: **$2,000-$4,000/mo** (the workflow Lienclear touches lives inside this)
- DIY mechanics-lien filing fee: **$5-$345** per state
- Levelset full-service lien filing: **$349 flat**; **$59/notice**; **~$149/mo subscription**
- Attorney flat-fee lien filing: **$500-$2,500**; hourly $150-$400/hr
- Construction IT spend per JBKnowledge/Avasant: **~1% of revenue** — a $5M sub spends ~$50k/yr total on tech, in $150-$1,000/mo slots
- Comparable SaaS in our ICP lane: Contractor Foreman $49/mo, Knowify $99-400/mo, Buildertrend $499-1099/mo

**Hard self-serve ceiling: $399/mo (~$4,800 ACV).** Above this, inside-sales-rep economics force a sales motion. Per SaaStr/Monetizely: under $5k ACV is PLG default; $5k-$25k is hybrid; $25k+ requires reps. F10's "no sales calls" promise sets the upper bound.

### Three ranked pricing options

**Option A (recommended for entry): "Lienclear Lite + per-NOI"**
- **$49/mo base** (NOI templates, deadline calendar, QBO sync) + **$29/NOI sent certified** + **$249 flat per lien filed**
- Beats Levelset $59/notice by ~50%, undercuts their $149/mo sub by 3x
- Lowest-friction "yes" — under finance-approval threshold for solo operators
- Per-action keeps the bursty-buyer (mid-dispute, won't negotiate, $29 to unlock $96k is a no-brainer)

**Option B: "Lienclear Pro" — bundled / predictable**
- **$149/mo** includes 5 NOIs + 1 lien filing/mo + AIA G702/G703 + retainage tracker; overage $19/NOI, $199/filing
- Matches Levelset's $149/mo headline, beats per-action overages
- Best fit for $3-10M subs with 3+ active jobs (predictable NOI volume)
- This is the bookkeeper-recommended line item

**Option C: "Lienclear Unlimited" — anti-sales-call ceiling**
- **$349/mo flat** — unlimited NOIs + unlimited filings + full F1/F2/F12 bundle
- Sits below Adaptive ($599), matches JobTread's $349, mirrors Knowify's top tier
- Stays under $400 PLG ceiling — F10 promise holds
- Upgrade path, not entry

### Three testable price hypotheses for the cold-DM survey
1. **H1 (per-action breakability)**: "Would you pay $29 per NOI sent if Levelset charges $59?" — tests whether 50% off is enough to switch, or if subs are price-insensitive mid-dispute
2. **H2 (subscription floor)**: "Would $99/mo all-in (5 NOIs + AIA + QBO sync) be a yes without asking your partner/bookkeeper?" — locates the self-approval ceiling between Option A's $49 and Option B's $149
3. **H3 (bundled-vs-unbundled preference)**: "Would you rather pay $49/mo + per-action OR $149/mo flat?" — direct preference test; determines marketing lead ("pay only when you need it" vs "predictable lien insurance")

**Key implications**:
- The Levelset $59/notice + $149/mo combo IS the explicit competitive anchor — Lienclear must beat both or differentiate via AIA+lien bundling (which Levelset doesn't do for the sub-side)
- $400/mo PLG ceiling is real and matches the F10 thesis — Option C at $349 is the highest defensible self-serve price
- Bookkeeping at $2-4k/mo dwarfs any Lienclear tier — positioning is *"make the bookkeeper's lien work 10x faster"*, not "replace the bookkeeper"
- A $1M sub has only ~$830/mo total software budget across all tools — Option A's $49 is the only realistic entry for the bottom of the ICP

---

## Risk section (new in v3)

**R1. Invalid-lien fraud exposure (3x damages)** — surfaced by Agent 3 from r/Contractor `1suadym`: a defendant-side commenter explicitly notes that if a sub files a sloppy or invalid lien, the property owner can pursue fraud-on-the-courts claims with treble damages. **This cuts both ways**: it's the reason F5 (filing assistant) is dropped from v3, AND it's the moat for F11 (state-correct NOI generation) — the value proposition is *exactly* "don't file sloppy paperwork". Lean into this in marketing.

**R2. Built Technologies' free-lien-waivers loss leader** — they can afford to give lien tooling away because their revenue is on the lender side. Any Lienclear pricing strategy that tries to charge for waiver generation walks into a $0 competitor. Mitigation: waivers stay free; charge for the workflow around them (AIA + retention + QB sync).

**R3. Procore/Levelset bundle expansion** — Procore can decide to bundle Levelset features into the base Procore subscription at any time. They've already moved from per-action pricing toward subscription bundling since the 2021 acquisition. If they make Levelset waivers free-for-Procore-users, Lienclear's funnel pressure shifts. Monitor.

**R4. Per-state lien law complexity** — F11 templates require legal-grade accuracy. Two options:
- (a) License/adapt from existing public state-bar resources (slow, narrow)
- (b) Partner with a construction-lawyer firm for template review (faster, expensive)
- (c) Ship for only 4 beachhead states (TX, FL, CA, NY) and grow from validated revenue
Recommend (c). Punts the build-vs-partner decision until there's paying-customer evidence.

**R5. Top_Drummer_3801's Planyard playbook** — confirmed solo founder running manual outreach in our exact target subs (Agent 1). Even though Planyard has no lien overlap, they own the founder-brand position in those threads. If Lienclear's GTM motion is also founder-led Reddit, expect to share airtime with them. Mitigation: post-on-the-lien-side-of-the-workflow, not the billing side, in the same threads.

---

## Recommended sequencing (v3)

1. **Lock pricing** — wait for pricing agent + run the 3-hypothesis cold-DM survey to 5–10 corpus contacts. Without this, the wedge is theoretical.
2. **Ship F11 (NOI generator) + lien waiver generator as free tier** — 4 beachhead states, SEO-optimized landing pages, capture email on use. This is the funnel.
3. **Build F1+F2+F3+F12+F9 paid tier** — vertical-templated for excavation/fence/low-voltage/solar. Match Siteline on lien-integrated billing; beat them on price + ICP fit.
4. **Public pricing page (F10)** — not a sales site; a pricing-comparison page that names Siteline, Levelset, Knowify openly with side-by-side feature/price grid. Be the transparent option.
5. **Cold-DM outreach to 5–10 corpus contacts** — G702 OP, $96k AR OP, Owner-Rep PM, Buildertrend leaver, foreclosure-question OP. Convert posts into interviews. This validates v3 before scaling.
6. **Owner-rep dashboard (F6)** — only after paid-tier has $5k/mo MRR. Different ICP, different motion.

---

## Open gaps / next moves (v3)

- **Pricing agent in flight** — three testable hypotheses will be sharpened
- **Top_Drummer_3801 history scrape in flight** — competitive intel on Planyard's GTM playbook
- **Cold-DM outreach not yet built** — scaffolding exists from Niche #1 work per memory; needs Lienclear-specific message templates
- **Prefilter v3 seed backfill** — add NOI / intent-to-lien / preliminary-notice / bond-claim / per-state-deadline language to the global `analysis/rag_classifier.py:SEEDS` dict, then re-scrape r/Contractor + r/ConstructionManagers + r/estimators with the v0.1 facets DB cleared for those subs. Expected lift: 3-5x more lienclear-relevance posts surfaced
- **Beachhead state lien-law research** — TX, FL, CA, NY NOI rules + deadlines + form requirements. Build-vs-partner decision still open
- **Watchlist additions**: LCPtracker (PLA compliance), Briq (construction finance ops), FundingShield (wire fraud / payment ops)
