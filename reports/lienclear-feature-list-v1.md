# Lienclear — Potential Feature List (v1, derived from corpus pain signal)

**Generated**: 2026-05-27
**Source corpus**: `data/market_intel.db` (1,670 lienclear-scored posts; 16 with LLM-extracted facets; 6 at relevance ≥ 0.30)
**Method**: All posts with `lienclear_relevance ≥ 0.30`, plus competitor-switching threads (Buildertrend/Procore) in construction subs, plus mechanics-lien / pay-app / retainage keyword hits. Pain summaries pulled from `pain_facets.pain_summary` where present; raw bodies inspected for high-relevance hits.

---

## Tier 1 — Hard signal (≥ 0.40 relevance, explicit feature asks)

These are the load-bearing pain points. Each has a direct user quote, a named DIY/competitor workaround, and a recurring/blocking urgency marker.

### F1. AIA G702/G703 pay-app generator with rounding-safe math
**Source**: r/ConstructionManagers "How the hell do you guys track AIA billing and change orders without paying for Procore?" (relevance 0.50, ↑0 but high comment engagement — competitor mentions Procore + Buildertrend; DIY = Excel template; urgency = "cash flow", "nightmare", "right now"; frequency = "every month")

User says verbatim:
- "G702/G703 spreadsheets are an absolute nightmare"
- "spending half my week just fixing rounding errors"
- "If the math is off by even a few cents, the GC kicks the pay app back and our cash flow stops"
- "I refuse to pay thousands of dollars a month for Procore or Buildertrend"

**Feature implications**:
- Decimal-safe (penny-exact) G702/G703 generation — no float drift, GC won't kick the pay app back
- Multi-project workspace (the user is "juggling a few commercial projects")
- Export to PDF formatted exactly as G702/G703 (GC submission format)
- "Reconcile this month's billing" view that flags drift before submission
- Sub-$100/mo target — the user's stated price ceiling is "not thousands"

### F2. Retainage ledger that doesn't break
**Same post** — "adjusting retainage mistakes" is one of the three named pain drivers.

**Feature implications**:
- Per-line-item retainage tracking (5%/10% configurable per project)
- Cumulative withheld vs released visible at-a-glance
- Retainage release workflow tied to substantial-completion milestone
- Pay-when-paid linkage: when GC releases retainage to sub, sub auto-releases to sub-tier

### F3. Change-order traceability into the SOV
**Same post** — "trying to trace change orders through to the agreed quotes on these messy spreadsheets is making reconciliation impossible".

**Feature implications**:
- CO log linked to the original SOV line item (not floating in a separate doc)
- Approved-quote artifact stored alongside the CO (PDF/email upload)
- CO impact on schedule of values rebuilds the next pay app automatically
- Audit trail: who approved what, when, against which quote

### F4. Commercial AR / net-N invoice chase
**Source**: r/Contractor "Commercial client hasn't paid by due date" (relevance 0.40, ↑35 — high engagement; $96k outstanding on $253k job; urgency = "Today", "past due"; buyer_role = owner)

User says verbatim:
- "Today is day 46 and I haven't been paid. Current outstanding balance is $96k"
- "I need the money as my line of credit is tapped out"
- "I'm concerned if I send an email they will purposely withhold or delay the next payments"

**Feature implications**:
- Per-phase progress-billing template (this user is on phase 5 of 6)
- Automated dunning at net+1, net+7, net+14 with templated language that doesn't burn the relationship
- "Polite but firm" letter generator (the user is terrified of poking the bear before phase 6)
- Cash-flow forecast: "given outstanding A/R, when does your LOC max?"
- Conditional/unconditional waiver-on-progress-payment generation (gate retainage release on receipt)

### F5. Mechanics lien filing + foreclosure workflow
**Source**: r/Contractor "Anyone here actually filed to foreclose on a Mechanics Lien?" (relevance 0.40)

The post is the user *asking peers* how to do this. That's the gap: there is no off-the-shelf workflow.

**Feature implications**:
- State-aware lien filing wizard (deadlines vary by state — TX/FL/CA/NY first per `LIENCLEAR_BEACHHEAD` config)
- Preliminary notice / NTO (Notice to Owner) generation + deadline reminders
- Lien filing packet (claim of lien + proof of service)
- Foreclosure escalation path: when statutory deadline approaches, prompt to file
- "Ballpark figure" estimator — the user literally asked what to claim. Pull SOV + retainage + interest + statutory penalties

### F6. Owner-rep / PM project-controls dashboard
**Source**: r/ConstructionManagers "Owner Rep Project Control Templates" (relevance 0.40, ↑10)

User explicitly asks for: "a simple way to track contractor pay apps, commitments, change orders, and schedule milestones in one place"

**Feature implications**:
- Owner-side view (Lienclear is sub-first, but the owner-rep is the *other* side of the same pay app)
- Commitments register (POs, sub-contracts) with %-complete + balance-to-complete
- Schedule milestones with conditional pay-app gating
- Cross-trade rollup (one project, many subs feeding pay apps)
- This is a Phase-2.5 expansion — moves Lienclear from "sub's billing tool" to "two-sided pay-app marketplace"

### F7. Per-building / multi-cost-code SOV (Autodesk Forma gap)
**Source**: r/ConstructionManagers "AutoDesk Forma Main Contract set up?" (relevance 0.40)

User can't link a budget code multiple times to the Main Contract SOV — 6 buildings × 25 codes = 150 SOV lines that Autodesk ACC won't model.

**Feature implications**:
- N-to-M budget-code-to-SOV-line mapping (one budget code can appear on multiple SOV lines proportionally)
- Per-building / per-phase / per-trade SOV breakdown toggle on the same project
- Direct positioning: "the SOV breakdown your owner wants, that ACC/Forma can't do"

---

## Tier 2 — Adjacent (relevance 0.10-0.30 but corpus-validated competitor gaps)

These hit the construction vertical but only weakly touch the lien/AIA domain. They expand the wedge.

### F8. Sub/vendor relational CRM (Buildertrend's CRM is "half-baked")
**Source**: r/estimators "What do you use to keep a running list of Subs/Vendors?" (↑12, Buildertrend mention)

User says verbatim:
- "We use Buildertrend to track our subs, but the CRM/organization side of it feels incredibly limited and half-baked"
- "I tried moving everything over to a massive Google Sheet, but a flat spreadsheet just isn't cutting it"
- Wants: company info + **multiple** contacts per company + visual "contact cards"
- Reaching for Airtable / Notion / Monday as substitutes

**Feature implications**:
- Sub/vendor CRM with multi-contact-per-company (estimator + PM + owner per sub)
- Trade tags, service areas, past project history per sub
- Direct integration with pay-app workflow: pay app *is* the sub-relationship event
- This is a real wedge into the GC side (Lienclear's natural ICP is the sub, but selling to GCs unlocks the directory effect)

### F9. QuickBooks integration (table stakes for the SMB GC)
**Source**: r/Construction "Leaving BuilderTrend" (↑9)

User says: "we'd be using QuickBooks to send invoices, so it would need to integrate"

**Feature implications**:
- QuickBooks Online + Desktop sync (pay app → invoice; payment received → A/R close)
- Two-way sync on customers/jobs
- Already on Lienclear's Phase-3 roadmap per `config.py:256` (`sync with (?:QuickBooks|Procore|Sage)`) — corpus confirms the demand

### F10. Self-serve, no-sales-call onboarding
**Same Buildertrend post**: "I don't want to sit through a million sales pitches or be pressured into making a quick decision by sales people given the task has fallen on me, but pricing tends to require that"

**Feature implications**:
- Public pricing page (don't hide it behind a demo)
- Free tier or 14-day trial without credit card
- Self-serve setup wizard (3-5 user companies don't have an IT team)
- Direct counter-positioning vs Procore/Buildertrend's sales-led motion

---

## Cross-cutting themes (appear in 3+ posts)

| Theme | Posts hitting it | Feature implication |
|---|---|---|
| **Excel/spreadsheet as the current "system"** | 4+ (G702 nightmare, owner-rep template ask, sub-tracking Google Sheet, Buildertrend leaver) | Import-from-Excel onboarding; "paste your messy SOV here" must work |
| **"Refuse to pay thousands"** | 2 explicit + Buildertrend cost-skyrocket | Pricing wedge — Lienclear ICP can't and won't pay Procore/BT money |
| **Cash-flow urgency** | 3 (G702 post, $96k AR post, Struggling Estimator) | DSO/cash-flow forecast feature pulls double duty as a hook + retention tool |
| **Recurring monthly pain** | 2 explicit "every month" markers | Subscription justifies itself when the pain is monthly, not one-off |
| **Multi-project juggling** | 2 explicit ("juggling a few commercial projects", "6 buildings") | Workspace must default to multi-project, not single-project |

---

## Mapping to the existing Lienclear phase model

Per `config.py` (`_LC_PHASES`):

| Phase | Existing scope | Corpus-validated additions |
|---|---|---|
| **Phase 1 — Free waiver gen + SEO** | lien waivers, prelim notices, mechanics lien | F5 (foreclosure workflow, claim estimator), state-aware deadlines, "filed to foreclose" SEO landing page |
| **Phase 2 — Paid AIA pay-app + dashboard** | G702/G703, SOV, retainage, pay-when-paid | F1 (rounding-safe math) + F2 (retainage ledger) + F3 (CO traceability) — these are *the* paid wedge. F4 (AR chase) folds in. F7 (per-building SOV) is a Forma-killer differentiator |
| **Phase 3 — Notifications + DocuSign + GC portal** | DocuSign, GC portal, QuickBooks/Procore/Sage sync | F6 (owner-rep dashboard = the GC-side portal), F9 (QuickBooks confirmed table-stakes) |
| **Phase 4 (new?)** | — | F8 (sub/vendor CRM) is its own product surface — could be a Phase 4 expansion or a Trojan-horse free tier |

---

## Recommended sequencing (corpus-weighted)

1. **F1 + F2 + F3 as a unit** — they're literally the same post's three pain drivers. Ship as the Phase-2 MVP. This is the *only* pain point in the corpus with all four signals lit (competitor mention + DIY workaround + urgency + frequency).
2. **F5** — Phase 1 already plans this; the foreclosure-claim estimator is a free-tier SEO magnet.
3. **F4** — natural extension of F1 (pay app issued → AR chase if unpaid). High emotional charge ($96k post got 35 upvotes vs F1's 0 — broader resonance).
4. **F9 (QuickBooks)** — required for F1 to actually replace the spreadsheet (the invoice has to land somewhere).
5. **F7** — narrow Forma-killer wedge; ship after F1 is validated.
6. **F6, F8** — expansion bets once Phase 2 has paying customers.

---

## What's *missing* from this analysis

- **No direct WTP dollar signal** for the headline AIA pain (the $96k post anchors AR pain, not pay-app-tool pricing). The "thousands/mo for Procore" ceiling is the only price reference.
- **N=1 on most Tier 1 features** — single post per feature in the LLM-facet set. Corpus needs more backfill in r/ConstructionManagers, r/estimators, r/Contractor to confirm frequency.
- **No comment-level extraction** — the AIA-nightmare post has unknown comment volume; comments likely contain "+1 me too" validation we're not capturing yet.
- **Zero signal on lien waivers as a standalone product** — Phase 1 is built on the *hypothesis* that free waiver gen drives SEO traffic, but the corpus shows users searching for foreclosure/filing process, not waiver generation. May need to re-scope Phase 1.

---

## Source posts (URLs for follow-up validation)

1. https://www.reddit.com/r/ConstructionManagers/comments/1tg7o94/ — G702/G703 nightmare (F1/F2/F3)
2. https://www.reddit.com/r/Contractor/comments/1t2t7bn/ — $96k commercial AR (F4)
3. https://www.reddit.com/r/Contractor/comments/1t7jfwq/ — Mechanics lien foreclosure (F5)
4. https://www.reddit.com/r/ConstructionManagers/comments/1tfhnx0/ — Owner-rep project controls (F6)
5. https://www.reddit.com/r/ConstructionManagers/comments/1taes8q/ — Autodesk Forma SOV gap (F7)
6. https://www.reddit.com/r/estimators/comments/1thrn1c/ — Buildertrend CRM gap (F8)
7. https://www.reddit.com/r/Construction/comments/1tjkyx6/ — Leaving Buildertrend (F9/F10)
