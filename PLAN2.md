Implementation Plan — Dual-Rail Billing (Work Done + Raw Edges) with Python + Lago
Scope: Build a production-grade billing platform that can price by raw usage (edges) and work done (workflows/outcomes), evolve to outcome/prize-for-results models, and remain margin-aware and auditable.
0) Executive Summary
   Why: Seat pricing breaks for agentic & workflow software. We need first-class billing for work done and raw edges, with outcome pricing readiness.
   How: Instrument everything with OpenTelemetry → derive Meters (edges + work) → apply Rating Policy (precedence, envelopes, spill) → push to Lago for invoicing.
   New deltas included: outcome oracles & settlement windows, margin intelligence, success fees, plan A/B experiments, partner revenue share, dispute workflows, fraud controls, and transparent consumer UX.
1) Goals & Non-Goals
   Goals
   Hybrid pricing (base + included + overage + success fees).
   Pricing maturity: inputs → workflows → outcomes → per-agent equivalents.
   Outcome verification via external systems + settlement windows.
   Margin intelligence per meter/customer/invoice line.
   Auditability: invoice → rated usage → meter readings → trace/span.
   Non-Goals (initially)
   Full CPQ, RevRec, or GL integrations beyond Lago/exports.
   On-platform payments (we can link to PSPs; defer owning card vaults).
2) Architecture Overview
   Producers
   Your apps/services/agents emit OTel spans for steps and OTel events for outcomes.
   Ingestion Layer (Python/FastAPI)
   /v1/otel accepts Collector exports; normalizes to raw_events.
   /lago/webhooks receives invoice/credit note events.
   Derivation Jobs (Python workers)
   Edges: tokens, API calls, compute ms, GB-hours → meter_readings.
   Work: workflow completion, outcome events (with attributes/SLA).
   Composite: doc.processed = constraints across edges.
   Rating Engine (Python)
   Applies plan precedence, envelopes, spill, included quotas, tiers.
   Computes success fees and joins COGS to output margin.
   Lago Adapter
   Pushes usage/add-ons to Lago.
   Pulls invoice status via webhook → persists invoice refs.
   Dashboards (internal API + UI)
   Usage & forecast, drill-downs, disputes, margin reports.
   Storage
   Postgres (state, readings, rated usage); optional S3 for long-term logs.
   Redis (idempotency & locks).
3) Domain Model & Data Schema (Postgres)
   3.1 Core Entities
   Customer ↔ Plan/Contract (mirrored in Lago).
   WorkflowDefinition (versioned), WorkflowRun, StepRun.
   Outcome (business result event).
   Meters:
   Edges: api.calls, llm.tokens, compute.ms, storage.gbh
   Work: workflow.completed, outcome.ticket_resolved, doc.processed
   MeterReadings: aggregated per time window with links to raw events.
   RatedUsage: pre-invoice pricing breakdown + COGS + margin.
   3.2 New Tables for Design Deltas
   -- Outcome verification & settlement
   create table outcome_verifications (
   id bigserial primary key,
   workflow_run_id uuid not null,
   outcome_key text not null,
   external_system text not null,      -- e.g. zendesk, salesforce, stripe
   external_ref text not null,
   status text not null,               -- pending, verified, reversed
   verified_at timestamptz,
   reversal_reason text,
   holdback_until timestamptz          -- settlement window end
   );

-- Disputes & adjustments ledger
create table adjustments (
id bigserial primary key,
customer_id uuid not null,
period_start date not null,
period_end date not null,
subject_type text not null,         -- run|meter|invoice
subject_id text not null,           -- id or composite key
kind text not null,                 -- freeze|credit|debit|override
amount numeric(20,6),
meter_key text,
reason text,
created_by text not null,
created_at timestamptz not null default now()
);

-- Partner revenue share & marketplace splits
create table revenue_shares (
id bigserial primary key,
workflow_run_id uuid,
partner_code text not null,
basis text not null,                -- percentage|flat
value numeric(9,6) not null,        -- pct or flat amount
calculated_amount numeric(20,6),    -- set during rating
currency text not null default 'EUR'
);

-- Plan experiments (A/B envelope sizes, unit prices)
create table plan_experiments (
id uuid primary key,
name text,
plan_id text not null,
variant text not null,              -- A|B|C...
policy_json jsonb not null,         -- precedence/envelopes/tiers overrides
active boolean not null default true
);

-- Fraud/abuse signals
create table anomaly_signals (
id bigserial primary key,
customer_id uuid not null,
ts timestamptz not null,
signal_key text not null,           -- e.g., tokens_spike_without_work
score numeric(10,4) not null,
details_json jsonb
);

-- COGS
create table cost_records (
id bigserial primary key,
workflow_run_id uuid,
ts timestamptz not null,
cost_amount numeric(20,6) not null,
cost_type text not null,            -- tokens|compute|storage|api
details_json jsonb
);
4) Instrumentation (OpenTelemetry)
   4.1 Required Attributes on Spans/Events
   billing.customer_id (internal UUID)
   billing.workflow_run_id (when applicable)
   billing.meter_candidates (e.g., ["api.calls","llm.tokens"])
   Edge attrs
   llm.tokens_input, llm.tokens_output (→ llm.tokens)
   compute.ms
   net.bytes_in, net.bytes_out (optional for egress/ingress)
   Work attrs
   workflow.definition, workflow.version, step.key
   actor.type ∈ {human,service,agent}
   Outcome events named outcome.<key> with attrs like sla.met=true, business.amount_eur=...
   Invariant: Every billable unit must be traceable to spans/events with stable IDs.
5) Metering & Derivation
   5.1 Ingestion (FastAPI)
   Accept OTel exports; validate minimal billing attributes.
   Persist to raw_events with idempotent keys: (trace_id, span_id, event_type, ts).
   5.2 Derivation Jobs
   Edges: Aggregate by window (hour/day) → meter_readings.
   Work:
   Detect terminal workflow states → workflow.completed=1.
   Emit outcome.<key>=1 on outcome events; create outcome_verifications with status='pending' if external verification required.
   Composite: if doc.processed requires edge limits (e.g., ≤50k tokens), only count when constraints met; otherwise degrade to edges billing.
   5.3 Idempotency & Backfills
   INSERT … ON CONFLICT … DO UPDATE for windowed readings.
   Late spans trigger re-derivation with versioned markers; readings carry src_event_ids.
6) Pricing & Rating Policy (with Deltas)
   6.1 Plan JSON (example)
   {
   "plan": "Pro v3",
   "currency": "EUR",
   "base_fee": 499,
   "included": { "workflow.completed": 1000, "llm.tokens": 5000000, "api.calls": 100000 },
   "overage": [
   {"meter":"workflow.completed","tiers":[{"upto":5000,"ppu":0.10},{"upto":null,"ppu":0.07}]},
   {"meter":"llm.tokens","ppu":0.00000025},
   {"meter":"api.calls","ppu":0.0002},
   {"meter":"storage.gbh","ppu":0.0006}
   ],
   "success_fees": [
   {"meter":"outcome.ticket_resolved","ppu":0.35,"conditions":{"sla.met":true},"settlement_days":7}
   ],
   "policy": {
   "precedence": "work_over_edges",
   "edges_included_per_work": { "workflow.completed": {"llm.tokens": 50000, "api.calls": 10} },
   "overage_spill": true
   },
   "caps": {"monthly_max": 25000},
   "discounts":[{"type":"commit","pct":10}],
   "experiments":[{"variant":"B","overrides":{"policy":{"edges_included_per_work":{"workflow.completed":{"llm.tokens":65000}}}}}]
   }
   6.2 Rating Algorithm (Python sketch)
   from decimal import Decimal
   from collections import defaultdict

def rate_period(customer_id, start, end, plan):
usage = load_meter_readings(customer_id, start, end)           # {meter_key: Decimal}
included = plan["included"]
policy = plan["policy"]

    # 1) Work envelopes
    envelopes = defaultdict(Decimal)
    per_work = policy.get("edges_included_per_work", {}).get("workflow.completed", {})
    work_units = Decimal(usage.get("workflow.completed", 0))
    for edge_key, cap in per_work.items():
        envelopes[edge_key] += Decimal(cap) * work_units

    lines = []

    # 2) Work overage
    work_used = work_units
    work_incl = Decimal(included.get("workflow.completed", 0))
    work_over = max(Decimal("0"), work_used - work_incl)
    if work_over > 0:
        lines += rate_tiers("workflow.completed", work_over, plan["overage"])

    # 3) Edge spill (beyond included + envelopes)
    for edge_key in ("llm.tokens", "api.calls", "storage.gbh"):
        total = Decimal(usage.get(edge_key, 0))
        edge_incl = Decimal(included.get(edge_key, 0))
        spill = max(Decimal("0"), total - edge_incl - envelopes[edge_key])
        if spill > 0:
            lines.append(line(edge_key, spill, unit_price(plan["overage"], edge_key)))

    # 4) Success fees with settlement
    for fee in plan.get("success_fees", []):
        meter = fee["meter"]
        cond = fee.get("conditions", {})
        settled_qty = settled_outcomes(customer_id, meter, start, end, cond, fee.get("settlement_days", 0))
        if settled_qty > 0:
            lines.append(line(meter, Decimal(settled_qty), Decimal(fee["ppu"]), kind="success_fee"))

    # 5) Caps, discounts, credits
    total = sum(l["amount"] for l in lines)
    total = apply_caps(total, plan.get("caps"))
    total = apply_discounts(total, plan.get("discounts"), customer_id, start, end)
    total = apply_credits(total, customer_id)

    # 6) COGS & margin
    cogs = compute_cogs(customer_id, start, end, lines)            # joins cost_records
    margin = total - cogs

    return {"lines": lines, "total": total, "cogs": cogs, "margin": margin}
Notes
Precedence: Also support edges_over_work for cost-sensitive customers.
Experiments: Pull overrides from plan_experiments → swap policy at runtime.
Revenue share: After total per run/meter, compute partner lines from revenue_shares.
7) Outcome Oracles & Settlement Windows
   7.1 Connectors (examples)
   Support: Zendesk/Intercom → verify ticket_resolved (who/when/SLA met).
   Sales: Salesforce/HubSpot → verify meeting_booked or opportunity_created.
   Payments: Stripe → verify payment_captured, handle refunds/chargebacks.
   7.2 Process
   Emit outcome event → create outcome_verifications (pending).
   Connector cron polls/pushes external system → flips status to verified or reversed.
   Only settled outcomes (past holdback_until) are billable; reversed outcomes issue credit notes via adjustments + Lago credit.
8) Lago Integration
   8.1 Catalog
   Billable metrics in Lago for each meter you price there (workflow.completed, llm.tokens, api.calls, etc.).
   Plans: base fee, included quantities, tiers.
   Add-ons: for success fees or complex composite charges (push as add-on lines when pricing is done on our side).
   8.2 Usage Push Patterns
   Pattern A (Recommended):
   We do derivation + envelope/spill logic in our rater.
   Push only billable quantities (edge spill, work overage, settled success fees) to Lago usage metrics.
   Use Lago to compute invoice totals per plan tiers.
   Pattern B:
   Push raw usage to Lago; let Lago do tiers.
   Use add-ons for success fees or any item Lago can’t infer.
   Pick one pattern per meter and stick with it to avoid drift.
   8.3 Webhooks
   Handle invoice.created, invoice.finalized, credit_note.created.
   Persist invoice URL/reference to rated_usage; update dashboards; trigger emails.
9) Customer UX & Transparency
   Real-time usage by meter; forecast end-of-period bill.
   Allowance trackers: included vs consumed vs spill.
   Why am I charged? Drill-down invoice → lines → meter readings → run → spans.
   Alerts: 80/90/100% thresholds, anomaly spikes, soft/hard spend caps.
   Disputes: One-click “dispute this line/run” → freezes runs, opens an adjustments case.
10) Fraud/Abuse Controls
    mTLS or signed headers from trusted producers.
    Heuristics: tokens spike without corresponding work/outcomes; repeated retries with different IDs; country/device anomalies.
    Automatic kill-switch per tenant; spend caps; throttle edges.
11) Testing Strategy
    Unit: derivation + rating policy (precedence/envelopes/spill).
    Property-based: random usage distributions to prove no double-charging.
    Backfill/Late events: deterministic re-derivation; ensure idempotency.
    Outcome settlement: simulate verify/reverse; ensure credits flow to Lago.
    Lago contract tests: usage push, plans, add-ons, webhooks.
    Margin tests: inject COGS curves and verify positive margins by tier.
12) Rollout Plan
    Phase 1 (MVP)
    OTel ingestion + Postgres schema + edge & work derivation.
    One plan with precedence/envelopes; success fee for 1 outcome with 7-day settlement.
    Lago setup: metrics, plan, usage push; webhook handler.
    Minimal dashboard: usage + forecast + invoice link.
    Phase 2
    Outcome connectors (Support + Payments).
    Disputes/adjustments ledger; credit notes.
    Anomaly detection + caps.
    Margin reports per meter/customer.
    Phase 3
    Plan experiments (A/B envelope sizes, unit price).
    Marketplace revenue share lines.
    Contract constructs (commits, pre-purchased credits).
    Broader outcome templates by vertical.
13) Repository Layout
    billing-platform/
    apps/
    ingest_api/            # FastAPI: /v1/otel, /lago/webhooks, admin
    deriver/               # workers for edges/work/composite meters
    rater/                 # rating engine (precedence/envelopes/spill)
    lago_adapter/          # push usage/add-ons, handle webhooks
    dashboard_api/         # usage, forecast, disputes
    lib/
    otel_schemas.py        # canonical attr keys, validators
    meters.py              # catalog and units
    rating_policies.py     # algorithms & experiments
    costs.py               # COGS joiners
    lago_client.py         # typed Lago API wrapper
    db.py                  # SQLAlchemy/SQLModel
    infra/
    collector/             # OTel Collector config
    migrations/            # Alembic DDL
    docker/ k8s/           # deployment
    tests/
    unit/ property/ integration/
14) Code Starters
    14.1 Envelopes & Spill
    from decimal import Decimal
    def envelope_for(plan_policy, meter_key, work_units):
    per_work = plan_policy.get("edges_included_per_work", {}).get("workflow.completed", {})
    cap = Decimal(per_work.get(meter_key, 0))
    return cap * Decimal(work_units)

def edge_spill(total, included, envelope):
return max(Decimal("0"), Decimal(total) - Decimal(included) - Decimal(envelope))
14.2 Success Fee (with settlement)
def settled_outcomes(customer_id, meter_key, start, end, cond, settlement_days):
rows = fetch_verified_outcomes(customer_id, meter_key, start, end, cond)
matured = 0
for r in rows:
if r.holdback_until and r.holdback_until <= now_utc():
matured += 1
return matured
14.3 Revenue Share
def apply_revenue_shares(lines, shares):
partner_lines = []
for share in shares:  # per run or meter basis
basis, value = share["basis"], Decimal(share["value"])
amount_basis = compute_basis_amount(lines, share)  # your rule
amt = amount_basis * value / Decimal("100") if basis == "percentage" else value
partner_lines.append({"code":"revenue_share", "partner":share["partner_code"], "amount":amt})
return partner_lines
14.4 Lago Usage Push (per meter, billed qty only)
import httpx, datetime as dt

async def push_metric(lago_api_key, lago_url, customer_code, meter_code, value, ts=None):
ts = (ts or dt.datetime.utcnow()).isoformat()
payload = {
"event": {
"transaction_id": f"{customer_code}:{meter_code}:{ts}",
"external_subscription_id": customer_code,  # or Lago sub ID
"code": meter_code,                         # Lago metric code
"timestamp": ts,
"properties": {"value": float(value)}
}
}
async with httpx.AsyncClient(headers={"Authorization": f"Bearer {lago_api_key}"}) as c:
r = await c.post(f"{lago_url}/api/v1/events", json=payload, timeout=30)
r.raise_for_status()
15) Compliance & Trust
    PII minimization in billing events; tokenized IDs only.
    Data retention with per-customer purge; cascade deletes to runs/events/readings.
    Idempotency everywhere (transaction IDs; DB uniques).
    Audit trail that links invoice ↔ rated usage ↔ readings ↔ spans.
16) Deliverables Checklist (MVP)
    Alembic migrations for all core/delta tables
    FastAPI ingest with OTel export receiver
    Edge + Work derivation workers (hourly windows)
    Rating engine with precedence/envelopes/spill
    Success fee (one outcome) with 7-day settlement
    Lago metric/plan setup + usage push + webhook handler
    Dashboard endpoints: usage, forecast, invoice link
    Tests: unit + property + Lago contract + settlement & reversal
    Runbook: backfills, disputes, credit notes, plan experiments
    Final Notes
    Start with Pattern A (we compute billable quantities; Lago invoices). It gives us full control over precedence/envelopes/outcome logic.
    Keep experiments easy to roll (env-flag plan overrides).
    Treat margin as a product feature — visible to us; optional to expose in customer dashboards as % saved vs edges.
    If you want, I can produce:
    The Alembic migration scripts,
    A FastAPI ingest scaffold, and
    A Lago catalog bootstrap script (create metrics, plan, and a sample subscription) ready to run.
