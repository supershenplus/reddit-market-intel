# Lienclear — Feature List v2 (comment-validated + competitor-deep)

**Generated**: 2026-05-27
**Supersedes**: `lienclear-feature-list-v1.md` for prioritization; v1 still has the per-feature design narratives
**Method delta vs v1**: Pulled all 102 comments on the 6 Tier-1 posts + 60 highest-score comments mentioning Procore/Buildertrend/Levelset/Siteline/JobTread/Sage/Foundation across the construction vertical. Comments are the validation signal — v1 ranked on submission-only.

---

## TL;DR — what changes from v1

| | v1 | v2 |
|---|---|---|
| **Strategic posture** | Build pay-app tool to wedge between Excel and Procore | **Planyard is already in this lane and posting in our top threads.** Differentiation must be explicit, not assumed |
| **Headline feature** | F1 G702/G703 generator | **Notice-of-Intent-to-Lien generator** (highest-leverage moment in the corpus — "I sent a NOI… was paid by EOD" was the most upvoted concrete solution) |
| **F4 (AR chase)** | Featured Tier 1 | Reframe as part of F5 — community doesn't want dunning emails, they want lien leverage |
| **F7 (per-building SOV)** | Tier 1 | **Demoted to Tier 3** — N=1 with a single "try contacting Autodesk" reply. No corpus validation. |
| **Struggling Estimator post** | Counted as Tier 1 evidence | **Removed** — 4 me_too's are about estimating win rate, not pay apps. Off-topic, false positive. |
| **F8 sub/vendor CRM** | Tier 2 | **Demoted to Tier 3** — Procore + JobTread + Airtable already saturate this; no wedge |
| **New: F11 lien-rights deadline calendar** | — | Promoted from corpus — state-variance confirmed by multiple commenters |
| **New: F12 retention-release tracker** | Subsumed in F2 | Broken out — distinct sub-feature with strong DIY signal |

---

## Strategic finding #1 — Planyard is direct competition, already in our threads

The same Planyard co-founder posted near-identical pitches in **four** of the top construction threads in the corpus:

| Thread | Comment (verbatim excerpt) |
|---|---|
| "How the hell do you track AIA billing" (the headline F1 post) | "digitises the schedule of values, tracks retainage and change orders, and sits on top of your existing accounting (QBO, Xero, whatever). Most teams get running in a few hours" |
| "Owner Rep Project Control Templates" (F6 post) | "for pay apps, commitments, and change orders its purpose-built and way simpler to get running than those enterprise tools" |
| "Leaving BuilderTrend" (F9/F10 post) | "we built it specifically for that transition from resi to commercial. It handles POs, subbie pay apps, budget tracking and syncs everything back to QuickBooks" |
| "Best accounting software for contractors" | "budgets, POs, subbie pay apps, and it syncs the approved stuff back into QBO or Xero" |

**Implication**: Lienclear's stated Phase-2 scope (F1+F2+F3+F6+F9) is **Planyard's exact product**, and Planyard is already executing the founder-led Reddit GTM motion on our beachhead subs. Lienclear has to either:
- **(a) Outflank on positioning**: lean hard into the *lien/legal* side (Planyard is finance/PM-flavored, not lien-flavored) — go where their name is
- **(b) Find a thinner wedge**: e.g. owner-side (F6 owner-rep dashboard) where Planyard explicitly says "we focus strictly on the commercial/financial side" — and commitments/retention is their financial lens, not lien rights
- **(c) Pivot upmarket or downmarket** — Planyard targets the "GC who refused Procore" mid-market. There may be a smaller-sub / single-trade niche under it

Recommendation: **(a)** is the natural Lienclear move. The brand name and Phase-1 plan already point there. v1 underweighted Phase 1 — comment data corrects this.

---

## Strategic finding #2 — The lien threat is the actual workflow, not the pay app

In the $96k commercial-AR post (62 comments — far more than any other Tier-1 post), the community's near-unanimous concrete advice is **threaten or file a mechanics lien**, not "use better invoicing software". Direct quotes from the highest-upvoted comments:

- (↑104, top comment) "be ready to threaten shutting the job down… threaten lien"
- (↑13) "Contractors need to learn that they are not a bank. Make clear payment schedules, enforce contracts, **threaten lien**"
- (↑5) "A notice of intent to lien from your attorney can be a negotiation tool to force payment. **It's also required in many states**."
- (↑2) **"For weeks I got dragged along with 'check is in the mail.' The 3rd time I sent a notice with intent to file lien to customer (GC, I'm a sub) and the building owner. Was paid by EOD."**
- Multiple others: "Lien them.", "NOTICE TO OWNER, intent to lien", "Just threaten or file a mechanics lien. It will light a fire under their ass."

The Mechanics-Lien post itself (11 comments) reinforces the same point with the **cost asymmetry**: filing the lien is cheap, threatening it triggers payment, the actual lawsuit/foreclosure costs **$50-90k and takes 2 years**:

- (↑3) "A lawsuit in 2026 will typically cost $50-90k… we lost our money he owed us. We had to pay both his attorney and ours. The lesson? It cost us over $100k and wasted 2 years."
- (↑4) "In a lot of states you are not able to force a foreclosure on the property, you are just blocking them from being able to sell"

**Implication**: The highest-leverage Lienclear feature is **the Notice-of-Intent-to-Lien generator + state-aware statutory deadline tracker**. Foreclosure workflow (v1's F5) is the dead end. NOI is the live wire — it's where the actual money moves, it's cheap to produce, and it's already required-by-statute in many states for lien rights to attach.

---

## Re-ranked feature list (v2)

### Tier 0 — Bet the company

#### F11 (new). Notice-of-Intent-to-Lien generator + state statutory deadline calendar
**Promoted from corpus.** Highest validation density of any feature: the entire 62-comment $96k AR thread orbits this, plus 5+ comments in the Mechanics Lien thread.

Requirements surfaced by comments:
- Per-state NOI/preliminary-notice templates (TX, FL, CA, NY, IN explicitly mentioned)
- Deadline calendar — "Indiana give you a year to file a lawsuit after notice of intent is filed" (some states 1-yr enforce-or-expire)
- Notice goes to **both the GC and the building owner** ("I sent a notice with intent to file lien to customer (GC, I'm a sub) and the building owner")
- Sent via certified mail / cert-of-service generation
- Tie-in to retainage / pay-app status — auto-flag when a job crosses statutory tripwire
- **Free tier candidate** — fits Phase-1 ("Free waiver gen + SEO") thesis, and acts as a top-of-funnel for Phase-2

#### F1+F2+F3 (bundle). AIA G702/G703 generator + retainage ledger + CO traceability
**Still Tier 1 by pain intensity** — the headline thread is real — but now competing directly with Planyard. Comment validation included:
- (↑2) "Aia billing literally tracks itself, schedule of values for all the work items in your contract at the start, billing this period, previously billed, retainage, and change orders" — this is a *spec*, given by a peer
- (↑1) "Every contractor we work with has the same story with G702/G703 in Excel. Works fine for 1-2 jobs, then once you're running a few in parallel the rounding errors and retainage mistakes start compounding" — independent N=2 confirmation, from a competitor founder
- (↑1) "**A locked-down template helps a lot for a single project. Once you're juggling multiple active schedules of values with change orders hitting at different points in the billing cycle, that's where dedicated tools start earning their keep.**" — defines the wedge: multi-project, not single-project. Single-project users will stick with Excel.

Also surfaced: **Textura** (Oracle) is the named alternative for AIA — "Textura does a much better job of this than Procore in my opinion" (↑2). Add to competitor list.

### Tier 1 — Ship in MVP

#### F5 (revised). Mechanics lien filing assistant — narrow scope: **filing only, not foreclosure**
Drop foreclosure-claim estimator entirely. v1's "ballpark figure estimator" was actively dangerous per the top comment in the foreclosure thread: "You can't 'ballpark' a mechanic's lien, lol. You are certifying that the debt is true and accurate and can face legal consequences if it isn't."

Keep:
- Per-state filing wizard (claim of lien + proof of service + recording instructions)
- Tied to F11 (NOI) — natural escalation if NOI doesn't move money

Drop:
- Foreclosure workflow (community consensus: too expensive, lose-lose)
- Claim amount auto-suggester (legal liability risk per the corpus itself)

#### F6 (revised). Owner-rep project-controls dashboard — Planyard explicitly punts on schedule
A comment in the owner-rep thread provided the **complete feature spec**, which I'm transcribing because it's better than anything I'd write:

> "one tab for the contract value tracker with original GMP, approved COs, pending COs, and current contract sum, one for pay app log with each application's gross, retention, and net by period, one for commitments showing what's been bought out versus open scope, one for the milestone schedule pulled from the contractor's baseline with actual versus planned dates. The dashboard tab should give the owner a one-page snapshot, contract value, billed to date, percent complete by dollars and by schedule, projected final cost, and any variance flags. Most owner reps we work with track CO log separately with status columns for pending, in review, approved, rejected, and pricing under negotiation, because that's where owners get burned the most. Keep a separate risk register tab too, contingency drawdown is the single most useful thing you can show an owner monthly and almost nobody tracks it well."

**Planyard explicitly says they don't do schedule** ("It won't do schedule milestones (we focus strictly on the commercial/financial side)"). That's a real gap — owner reps want schedule + financial in one view. Possible differentiation wedge.

#### F12 (broken out from v1's F2). Retention-release tracker
Distinct from the G702 generator. Surfaced by:
- The owner-rep thread spec: "pay app log with each application's **gross, retention, and net** by period"
- The Leaving-BuilderTrend competitor-comment: "commercial adds subcontractor payment management, **retention tracking**, budget vs actuals reporting"
- Multiple "lien threatened on retention release" patterns in the AR thread

Why it's a feature, not a sub-feature of F1: retention is held for months past pay-app issuance, has its own statutory release rules (substantial completion + state-specific waiting period), and the lien window often hinges on retention disputes. Pairs naturally with F5/F11.

### Tier 2 — Adjacent / expansion

#### F9 (confirmed). QuickBooks Online + Desktop sync — table stakes
Multiple comments confirm QBO/Xero is the universal accounting layer. Planyard, Knowify, Foundation all sync — Lienclear cannot skip this.

#### F10 (confirmed). Self-serve, no-sales-call onboarding — counter-positioning
Procore pricing repeatedly cited: "plans start at $5-6k/yr", "BT pricing creep is wild", "Procore is massively overkill". The Leaving-BuilderTrend post user explicitly says "I don't want to sit through a million sales pitches". Anti-positioning wedge confirmed.

### Tier 3 — Park or drop

| Feature | Why parked |
|---|---|
| **F4 standalone AR chase / dunning** (v1) | Reframed into F11 — community wants lien leverage, not better email cadence |
| **F7 Per-building SOV / Autodesk Forma gap** (v1) | N=1 post, 1 comment, comment was "try contacting Autodesk?". No validation. |
| **F8 sub/vendor CRM** (v1) | "Procore. But Claude could build this for you" (↑3) — solved by incumbents + AI; no wedge |
| **Struggling Estimator post** (v1 evidence) | False positive — me_too's are about estimating win-rate, not pay apps |

---

## Competitor landscape (corrected from corpus)

| Competitor | Surface area | Comment evidence |
|---|---|---|
| **Procore** | Everything; $5-6k/yr floor; "hot mess", "stagnated since 2016", "massively overkill" | 30+ mentions across vertical |
| **Buildertrend** | Mid-market resi GC; "BT pricing creep is wild"; "half-baked CRM" | 10+ mentions |
| **Planyard** | **Direct competitor for F1+F2+F3+F6+F9.** Founder posting in our top threads. | 4 self-posts found |
| **JobTread** | Buildertrend alternative; founder also in threads; Claude AI integration touted | 4+ mentions, founder self-posts |
| **Levelset** (now Procore) | Lien filing — directly overlaps F5/F11. "I've been using it for a long time. I think LinkedIn bought it. Still works great." | 1 strong mention in r/Concrete "Client doesn't want to pay" (↑982 post) |
| **Textura** (Oracle) | AIA billing — directly overlaps F1 | "does a much better job than Procore" (↑2) |
| **Foundation Software** | Contractor accounting between QB and Sage | "preferred construction accounting software" |
| **Knowify** | QB add-on for construction job costing | 1 mention with positive framing |
| **Houzz Pro** | Small/residential Procore alternative | "couldn't afford Procore, came across Houzz Pro" |
| **Owners Insight** | Owner-rep specific — overlaps F6 | 2 mentions in owner-rep thread |
| **Sage 300** | Enterprise (8-fig+ revenue) — out of ICP | "gold standard above 8-figure" |
| **Smartsheet** | Spreadsheet-with-extras — corpus position is "Procore-overkill alternative but still just a spreadsheet" | 3 mentions |

**Critical Levelset note**: The r/Concrete "Client doesn't want to pay" post (↑982, top of `Phase 1` pain) has someone saying Levelset works great for them. **v1 missed that Levelset = Procore-owned now.** Procore has already absorbed the Phase-1 wedge. Lienclear's Phase 1 must outflank Levelset, not just Excel.

---

## Recommended sequencing (v2)

1. **F11 (NOI generator + statutory deadline tracker)** — Free, SEO-driven, builds list of contractors actively in payment disputes. Highest comment-validated pain. **Outflanks Levelset by being the "before you file a lien" tool, not the filing tool itself.**
2. **F5 (revised — filing only, no foreclosure)** — Natural escalation from F11. Paid tier.
3. **F1+F2+F3 bundle** — Paid tier. **Position vs Planyard explicitly** — Lienclear sells "billing tied to your lien rights"; Planyard sells "billing tied to your accounting". Different center of gravity.
4. **F12 (retention tracker)** — Bundles with F1 + F11. Retention is where lien windows close.
5. **F9 (QuickBooks sync)** — Required for F1 to ship; not optional.
6. **F10 (self-serve onboarding / public pricing)** — Company-level decision, not a build.
7. **F6 (owner-rep dashboard)** — Only after the sub-side is validated. Planyard punts on schedule, which is a real gap if Lienclear wants this market.

---

## Open methodological gaps (still unresolved)

- **Levelset deep-dive missing** — they're the literal incumbent for F5/F11 and Procore-owned. Need to read their feature set + pricing before betting on F11.
- **No pricing signal in corpus** — Procore "$5-6k/yr" is the only firm dollar anchor. No idea what Lienclear-comparable SMBs pay or would pay.
- **State-by-state lien-law complexity untouched** — F11 requires legal-grade per-state templates. Build vs. partner-with-attorney decision required before ship.
- **Comments only pulled for 6 Tier-1 posts** — there are 127 posts at relevance ≥ 0.20. Comments on the other 121 may surface additional patterns (esp. retainage-specific threads).
- **No founder/Reddit handle profiling** — Planyard founder's username is in the corpus; could be tracked for ongoing competitive intel.
