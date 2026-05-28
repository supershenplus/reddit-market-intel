# Lienclear feature list — derived from RIM 2026-05-28

> **⚠ STATUS (added 2026-05-28 post-review): Phase 2 (F5/F6/F7 — paid AIA pay-app + change-order core) is PAUSED.**
> A 3-agent strategic review the same day surfaced: (a) LienWaiver.pro launched at $49 in Feb 2026 and Built Payments went free in Oct 2025, partially commoditizing the per-action pricing wedge; (b) the feature list has zero buyer-side (owner/controller) validation behind it — all 41 source facets are sub/operator-side, hitting the [[feedback-construction-buyer-operator-split]] kill risk head-on; (c) F5 engineering is 4-6mo solo (not a paper MVP), plus AIA G702 form licensing risk. **Do not build F5/F6/F7 without 3+ owner-side paid pilots from the Phase 1 (F1-F4) funnel.**
>
> **Read first:** `reports/lienclear-strategic-review-2026-05-28.md` — has the convergent 3-agent verdict, the kill criterion (60 days, no paid owner pilot → kill), and the surviving-wedge re-anchor (compliance moat + California SB 440 statutory automation, not transparent pricing).
>
> **What survives:** Phase 1 (F1-F4 — NOI generation, waiver gen, lien filing wizard, late-AR/SB-440 notice generator) is the real product surface for the next 60 days. The compliance moat (state-correct NOI, 3x-damages avoidance, SB 440 24%-interest clocks) is the only differentiation that wasn't undercut by 2026-Q1/Q2 competitor moves.

---

**Derivation:** 41 lien-relevant `is_pain_point=1` facets from r/Construction + r/ConstructionManagers + r/Contractor (post-W4-1 batch). Features are mapped to the existing 3-phase ProductBlueprint (Free waiver → Paid AIA → Notifications/GC portal). Every feature carries a concrete evidence URL + signal type so prioritization arguments don't drift into vibes.

**Thesis fit:** all 41 facets are sub/contractor-side. Zero are owner/developer-side. Confirms the existing cohort target ($1-10M specialty subs in trades Siteline skips). Per-action pricing remains the only viable price-side differentiator vs Procore.

**Dominant signal across the corpus:**
- "How the hell do you guys track AIA billing and change orders without paying for Procore?" — names Procore AND Buildertrend, lists exact missing features (AIA billing + change orders), urgency (cash flow nightmare), frequency (every month), DIY workaround (Excel template). [Single most load-bearing post for the thesis.](https://www.reddit.com/r/ConstructionManagers/comments/1tg7o94/how_the_hell_do_you_guys_track_aia_billing_and/)
- "What I see every time I've logged into Procore this month" — 399 upvotes — pure incumbent rage. Direct churn signal.
- "Leaving BuilderTrend" — direct churn signal from the other major incumbent.
- "Commercial client hasn't paid by due date" — 35 upvotes, urgency: today + past due — proves the late-AR pain is acute and frequent.

---

## Phase 1 — Free funnel (waiver/lien education + SEO)

| # | Feature | Evidence | Priority | Procore/Buildertrend gap |
|---|---|---|---|---|
| F1 | **State-correct NOI/preliminary notice generator** | Existing thesis (per memory) + multiple state-anchor signals across corpus | P0 (already scoped) | Levelset paywalls this; Procore doesn't do it |
| F2 | **Conditional/unconditional waiver generator (state-specific)** | Existing thesis | P0 (already scoped) | Levelset $99/mo for this; transparent per-action wins |
| F3 | **Mechanics lien filing walkthrough/wizard (free guide)** | [r/Contractor "Anyone here actually filed to foreclose on a Mechanics Lien?"](https://www.reddit.com/r/Contractor/comments/1t7jfwq/) — direct unanswered question | P1 (SEO + funnel) | Levelset hides behind paid plan |
| F4 | **Late-AR first-step decision wizard + demand-letter generator** | [r/Contractor "Commercial client hasn't paid by due date"](https://www.reddit.com/r/Contractor/comments/1t2t7bn/) (35 ↑, urgency: today/past due) | P1 (SEO + funnel) | Neither addresses pre-lien AR escalation |

**Phase 1 strategy:** every Phase-1 feature is SEO-bait AND a way to capture email for the paid Phase-2 funnel. Compliance accuracy (state-correct lien rules) is the moat — the [[lien-3x-damages-risk]] memory is a wedge: get this right, competitors get sued.

---

## Phase 2 — Paid AIA pay-app + change-order core ($49-$349 tiers)

| # | Feature | Evidence | Priority | Procore/Buildertrend gap |
|---|---|---|---|---|
| F5 | **G702/G703 pay-app generator with SOV validation + rounding** | [Goldmine post: "How the hell do you guys track AIA billing without paying for Procore"](https://www.reddit.com/r/ConstructionManagers/comments/1tg7o94/) — DIY: Excel template, freq: every month, urgency: cash flow nightmare | **P0 (headline)** | This IS the gap. Procore charges $375+/mo just for this. |
| F6 | **Change-order tracker bolted onto pay-app workflow** | Same goldmine post — explicitly names "change orders" alongside AIA billing | **P0 (headline, bundle w/ F5)** | Procore has it but priced out of $1-10M cohort |
| F7 | **Per-action pricing display ($X per pay app filed, not per seat)** | Anti-subscription posture: ["Alternatives to Revu"](https://www.reddit.com/r/ConstructionManagers/comments/1tjtr92/) (anti-subscription), ["Leaving BuilderTrend"](https://www.reddit.com/r/Construction/comments/1tjkyx6/), ["Procore rage"](https://www.reddit.com/r/ConstructionManagers/comments/1nrfv76/) (399 ↑) | **P0 (positioning, not feature)** | Both run per-seat enterprise pricing. Per-action transparency is the wedge. |
| F8 | **Retainage tracker** | Implied across construction-vertical facets; standard AIA pay-app companion | P0 (bundle w/ F5) | Procore has it; same affordability gap |
| F9 | **Mobile pay-app submission (sign + submit from phone)** | [r/Construction "Tradesperson wants simple job tracker"](https://www.reddit.com/r/Construction/comments/1t89mnf/) (WTP: would_pay, urgency: blocking) + general mobile-first signal | P1 | Procore mobile is bloated; opportunity for narrow-scope mobile |
| F10 | **SOV scaffolder — auto-distribute contract sum across CSI divisions** | [r/ConstructionManagers "Won million dollar job, noticed 6 grand mistake"](https://www.reddit.com/r/ConstructionManagers/comments/1twvg47/) — estimating-QA gap, $5K errors in manual SOV | P2 | Neither auto-validates SOV math |

**Phase 2 strategy:** F5 + F6 + F7 are the headline launch. Ship those three together. F8 (retainage) bundles because every pay-app needs it. F9/F10 are fast-follows.

---

## Phase 3 — Notifications, GC portal, intelligent contract review

| # | Feature | Evidence | Priority | Procore/Buildertrend gap |
|---|---|---|---|---|
| F11 | **E-signature on waivers (DocuSign or built-in)** | Existing thesis (Phase 3 per ProductBlueprint) | P1 | Procore has DocuSign integration; lienclear needs parity |
| F12 | **GC notification flow (waiver-sent / waiver-required / pay-app-due)** | Existing thesis + recurring "waiver coordination" signal across corpus | P1 | Procore has it; affordability gap continues |
| F13 | **Scope-gap auto-flag (templated library: anchor bolts, trench backfill, condensate lines, etc.)** | [r/ConstructionManagers "Most common scope gaps"](https://www.reddit.com/r/ConstructionManagers/comments/1ejfip7/) — direct enumeration of what to flag | **P1 (genuine new wedge)** | Neither does this. Real differentiator. |
| F14 | **RFI ledger with vague-response detection (flag "see detail 3/A102" style single-line responses)** | [r/ConstructionManagers "If I could realtalk an architect about RFIs"](https://www.reddit.com/r/ConstructionManagers/comments/1k4cqja/) — specific pattern named | P2 (small but unique) | Neither does this |
| F15 | **Daily-log voice dictation → formatted PDF export** | [r/ConstructionManagers "Question about a tool" (voice-dictated daily-log app)](https://www.reddit.com/r/ConstructionManagers/comments/1t5wr8c/) — explicit validation, frames Procore job-logs as manual | P2 | Procore daily logs are manual entry — voice-first is a real wedge |
| F16 | **Subcontractor compliance doc collection + expiry tracking (insurance, W9, license)** | [r/ConstructionManagers "UK contractors how do you collect and track sub compliance docs"](https://www.reddit.com/r/ConstructionManagers/comments/1t1qeqz/) + recurring scope-gap reconciliation needs | P2 | Procore has it; affordability gap |

---

## Explicitly out of scope (different products)

These appeared in the corpus but are NOT lienclear features — they're different SaaS theses. Surface to the operator so they aren't mistaken for missed opportunities:

- **Full estimating engine** — [r/ConstructionManagers "Struggling Estimator"](https://www.reddit.com/r/ConstructionManagers/comments/1sy6w1u/), [Australian labour-hours reference](https://www.reddit.com/r/ConstructionManagers/comments/1tjg42p/) → separate product (estimating tools are their own vertical)
- **Subcontractor marketplace** — [JCB/tipper marketplace](https://www.reddit.com/r/ConstructionManagers/comments/1t47vhh/), [Crew lodging marketplace](https://www.reddit.com/r/ConstructionManagers/comments/1t2uq54/) → marketplace plays, different go-to-market
- **Construction scheduling** — ["best construction scheduling software"](https://www.reddit.com/r/ConstructionManagers/comments/1szre76/) → Smartsheet/MS Project competitor space
- **Plans search/AI** — ["AI app for construction site plans"](https://www.reddit.com/r/Construction/comments/1tdfdeb/) → AI/vision-heavy, different stack
- **Lead-gen + CRM** — [Utah GC siding lead-gen ask](https://www.reddit.com/r/Contractor/comments/1sxrats/) → contractor CRM space, crowded
- **General accounting/job costing** — [QuickBooks-isn't-enough thread](https://www.reddit.com/r/ConstructionManagers/comments/1t9s8x1/) → BuilderTrend/Sage 300/Foundation territory

---

## Recommended build order (Q3/Q4 2026 if shipping)

1. **F5 + F6 + F7 bundled** (AIA pay-app + change-orders + per-action pricing) — the headline launch. Without these, lienclear is just another lien tool. With them, it's the "kill-Procore-for-small-subs" play.
2. **F1 + F2 + F3 + F4** (free Phase-1 funnel) — ship in parallel with F5/F6/F7 since they're SEO-bait and feed the paid funnel. Different team if you have one.
3. **F8** (retainage) — bundle with F5/F6 launch if possible; cheap to add once pay-app pipe exists.
4. **F11** (e-sig) — needed for waiver workflow at scale
5. **F13** (scope-gap flag) — Phase 3 differentiator; can ship as "intelligent contract review" wedge
6. **F9** (mobile), **F12** (GC notifications), **F10** (SOV scaffolder) — fast-follows
7. **F14** (RFI ledger), **F15** (voice daily-log), **F16** (sub compliance) — Phase 3 expansion features, ship as the product justifies more surface area

---

## What this list doesn't include (limitations of the synthesis)

- **No pricing-tier mapping** — features above don't say which tier ($49/$149/$349) they go into. That's a packaging decision separate from feature priority.
- **No build-effort estimates** — F5 (G702/G703 generator with SOV math) is real engineering; F4 (demand-letter generator) is a template. Treat priorities as importance, not as effort-adjusted ROI.
- **Voice from owners/buyers is absent.** All 41 facets are sub-side. Buyer-side validation (GCs paying for the SaaS) requires direct outreach, not corpus mining. Same construction-buyer/operator-split risk as [[feedback-construction-buyer-operator-split]].
- **Yield was low this batch** (8 new pain points from 200 posts). A second batch with `--prefilter sampled --category construction` would surface ~25-30 more lien-relevant facets — better signal-to-noise than `--prefilter off`. If this list is decision-supporting and you want to refine before scoping, the next batch costs ~1hr.

---

## Related memories

- [[project-lienclear-v3-thesis]] — positioning + pricing context
- [[feedback-planyard-competitor-intel]] — adjacent competitor analysis
- [[feedback-lien-3x-damages-risk]] — compliance moat for state-correct generators
- [[feedback-construction-buyer-operator-split]] — buyer/operator split risk to track during sales
- [[project-lienclear-trigger-event]] — first-big-AR-stiff is the conversion event; aligns with F4 (late-AR funnel)
