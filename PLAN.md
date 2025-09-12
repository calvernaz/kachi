# Kachi Implementation Plan


Implementation Plan: Dual-Rail Usage Billing (Work Done + Raw Edges) with Python + Lago
0) Executive summary
   We will build a billing platform that charges customers for:
   Work done (e.g., completed workflows/outcomes), and
   Raw edges (e.g., API calls, tokens, compute ms, GB-hours),
   with guardrails to avoid double-charging (precedence + envelopes). Python powers ingestion, metering, rating policies, and the Lago integration. OpenTelemetry (OTel) is used for instrumentation and traceability.
1) Goals & non-goals
   Goals
   Hybrid pricing: base fee + included allowances + pay-as-you-go + outcome pricing.
   Accurate metering via OTel; auditable links from invoice line-items to traces.
   Margin awareness (COGS per unit of work).
   Lago used for product/plan catalog, usage events, invoicing, and AR.
   Non-goals (initially)
   Complex CPQ, advanced credits marketplace, or revenue recognition beyond Lago’s capabilities.
   Multi-ledger finance integrations (can come later).
2) High-level architecture
   Producers: Your services, workers, and UIs emit OTel spans/events.
   Ingestion: OTel Collector → HTTP/gRPC → Python “Ingest API”.
   Storage: Raw events (append-only) + derived MeterReadings.
   Derivers (Python jobs): transform raw spans into edge meters and work-done meters.
   Rater (Python): applies precedence/envelopes; computes RatedUsage.
   Lago adapter (Python): pushes metered usage to Lago; reconciles invoices via webhooks.
   Dashboards: Usage, forecast, drill-down, disputes.
   Data backbone: Postgres for online state; S3 (optional) for long-term logs; Redis for idempotency.
3) Core concepts & data model
   3.1 Entities
   Customer ↔ Contract/Plan (in Lago).
   WorkflowDefinition (versioned), WorkflowRun, StepRun.
   Outcome (business result).
   Meters:
   Edges (api.calls, llm.tokens, compute.ms, storage.gbh)
   Work (workflow.completed, outcome.ticket_resolved, doc.processed)
   MeterReadings: aggregated values per window (+ pointers to source events).
   RatedUsage: pre-invoice breakdown with COGS & margin.
   CostRecords: provider costs per run (tokens/compute/storage/3rd-party).
   AuditLog: all adjustments & disputes.
   3.2 Minimal Postgres schema (DDL sketch)
   create table customers (
   id uuid primary key,
   lago_customer_id text unique not null,
   name text not null,
   currency text not null default 'EUR',
   status text not null default 'active'
   );

create table workflow_definitions (
id uuid primary key,
key text not null,
version int not null,
schema_json jsonb not null,
active boolean not null default true,
unique(key, version)
);

create table workflow_runs (
id uuid primary key,
customer_id uuid not null references customers(id),
definition_id uuid not null references workflow_definitions(id),
started_at timestamptz not null,
ended_at timestamptz,
status text not null,
metadata_json jsonb
);

create table raw_events (
id bigserial primary key,
customer_id uuid not null references customers(id),
ts timestamptz not null,
event_type text not null,     -- span_started, span_ended, outcome, counter, etc.
trace_id text,
span_id text,
payload_json jsonb not null,
unique(trace_id, span_id, event_type, ts)  -- helps dedupe
);

create table meter_readings (
id bigserial primary key,
customer_id uuid not null references customers(id),
meter_key text not null,
window_start timestamptz not null,
window_end timestamptz not null,
value numeric(20,6) not null,
src_event_ids bigint[] not null default '{}',   -- links to raw_events.id
unique(customer_id, meter_key, window_start, window_end)
);

create table cost_records (
id bigserial primary key,
workflow_run_id uuid references workflow_runs(id),
ts timestamptz not null,
cost_amount numeric(20,6) not null,
cost_type text not null,     -- tokens, compute, storage, vendor_api
details_json jsonb
);

create table rated_usage (
id bigserial primary key,
customer_id uuid not null references customers(id),
period_start date not null,
period_end date not null,
items_json jsonb not null,   -- detailed lines
subtotal numeric(20,6) not null,
cogs numeric(20,6) not null,
margin numeric(20,6) not null,
unique(customer_id, period_start, period_end)
);

create table audit_log (
id bigserial primary key,
ts timestamptz not null default now(),
actor text not null,
action text not null,
subject text not null,
details_json jsonb
);
4) Instrumentation (OTel)
   4.1 Required attributes (all spans/events)
   billing.customer_id (your UUID)
   billing.workflow_run_id (when applicable)
   billing.meter_candidates (e.g., ["api.calls","llm.tokens"])
   Edge specifics
   llm.tokens_input, llm.tokens_output (sum to llm.tokens)
   compute.ms
   net.bytes_in, net.bytes_out
   Work specifics
   workflow.definition, workflow.version
   step.key, actor.type (human|service|agent)
   Outcome event name, e.g., outcome.ticket_resolved; attributes like sla.met.
   4.2 Examples
   Step span name: step.validate_invoice
   Outcome event: outcome.invoice_approved with { "sla.met": true }
5) Meter derivation pipeline
   5.1 Ingestion (Python FastAPI)
   Endpoint /v1/otel accepts OTel Collector exports.
   Validate & normalize to raw_events.
   Deduplicate by (trace_id, span_id, event_type, ts).
   5.2 Derivers (Python jobs; Celery/Arq/RQ/cron)
   Edges: aggregate tokens, API calls, compute ms, GB-hours into 1-hour (or 1-day) windows → meter_readings.
   Work: detect terminal workflow states or outcome events and emit:
   workflow.completed = 1 per run
   outcome.ticket_resolved = 1 when outcome event fires
   Composite (optional): Validate that doc.processed meets constraints (e.g., ≤ 50k tokens) before counting it.
   Idempotency: Derivers should be deterministic; updates run with INSERT … ON CONFLICT … DO UPDATE semantics.
6) Pricing policy: precedence & envelopes
   6.1 Policy model (JSON stored per plan)
   {
   "precedence": "work_over_edges",
   "edges_included_per_work": {
   "workflow.completed": {"llm.tokens": 50000, "api.calls": 10}
   },
   "exclusions": [
   {"when":"workflow.completed", "drop":["api.calls","llm.tokens"]}
   ],
   "overage_spill": true
   }
   6.2 Rating algorithm (Python outline)
   def rate_period(customer_id, start, end, plan):
   usage = load_meter_readings(customer_id, start, end)
   envelopes = allocate_work_envelopes(usage, plan.policy)

   lines = []
   # 1) Work: compute included vs. overage
   lines += rate_work(usage, plan)

   # 2) Edge spill: bill edges beyond included + envelopes
   lines += rate_edges(usage, plan, envelopes)

   # 3) Outcomes with conditions (e.g., SLA)
   lines += rate_outcomes(usage, plan)

   # 4) Caps, discounts, credits
   total = apply_caps_discounts_credits(lines, plan)

   # 5) Compute COGS and margin
   cogs = attach_cogs(lines, customer_id, start, end)
   return RatedUsage(lines=lines, total=total, cogs=cogs)
7) Lago integration
   7.1 Concepts to use in Lago
   Customers: synchronize your customers with lago_customer_id.
   Billable metrics: define meters (workflow.completed, llm.tokens, etc.).
   Plans/Subscriptions: model base fee, included quotas, and overage tiers in Lago where possible.
   Usage events: push metered quantities to Lago (per meter, per period).
   Invoices: generated in Lago; listen to webhooks for invoice.created/updated.
   Pattern: Keep derivation and policy logic in your service. Push final meter quantities (including envelope spill decisions) to Lago to be priced according to the plan’s configuration—or push fully rated line-items via “add-on”/fee API when needed for complex cases. Choose one path consistently per meter.
   7.2 Sync flows
   One-time/catalog: Create billable metrics & plans in Lago (scripted).
   Nightly/rolling:
   Our rater computes RatedUsage.
   Push usage events to Lago (per meter, per customer, for the billing window).
   Trigger invoice draft generation (if plan invoices monthly).
   Receive Lago webhooks → persist invoice_ref, status, totals.
   7.3 Example: pushing usage (Python)
   import httpx, datetime as dt

async def push_usage_to_lago(lago_api_key, lago_url, customer_code, meter_code, value, timestamp=None):
ts = (timestamp or dt.datetime.utcnow()).isoformat()
payload = {
"event": {
"transaction_id": f"{customer_code}:{meter_code}:{ts}",
"external_subscription_id": customer_code,
"code": meter_code,      # matches Lago billable metric code
"timestamp": ts,
"properties": {"value": value}
}
}
async with httpx.AsyncClient(headers={"Authorization": f"Bearer {lago_api_key}"}) as c:
r = await c.post(f"{lago_url}/api/v1/events", json=payload, timeout=30)
r.raise_for_status()
(Adjust to Lago’s current API versions and auth scheme in your environment.)
7.4 Webhooks (Python FastAPI)
/lago/webhooks verifies signature, stores invoice summaries, updates rated_usage with final amounts + invoice URL, and triggers customer notifications.
8) APIs (internal)
   8.1 Ingest API (FastAPI)
   POST /v1/otel — receives OTel export payload (Collector → this endpoint).
   POST /v1/events/outcome — convenience endpoint for outcome events (optional).
   GET /v1/usage/preview?customer_id&from&to — returns provisional RatedUsage (quote).
   POST /v1/adjustments — freeze runs, apply corrections, re-rate.
   8.2 Admin API
   POST /admin/meter-catalog — declare meters.
   POST /admin/plan — upsert pricing plan JSON (policy + included + tiers).
   POST /admin/lago/sync — create/update Lago billable metrics and plans.
9) Customer UX
   Usage dashboard: per meter, by day; included vs consumed; forecasted bill end-of-month.
   Drill-down: meter → reading → source runs → traces/spans.
   Alerts: thresholds (80/90/100%), anomaly detection, spend caps.
   Invoices: link to Lago invoice; line-items mapped back to meters & runs.
10) Security, trust & compliance
    Idempotency: event transaction_id; DB constraints on unique keys.
    Signed sources: mutual TLS or signed headers from trusted services.
    PII minimization: keep personal data out of billing attributes; tokenized IDs.
    GDPR: data retention policies; delete requests cascade from customer to runs/events.
    Auditability: every invoice line can be traced back to raw_events.
11) Testing strategy
    Unit: derivation and rating policy (precedence + envelopes + spill).
    Property-based: random usage distributions to ensure no double-charging.
    Replay: synthetic traffic via OTel generator; verify idempotency.
    Contract tests: Lago API + webhooks (sandbox mode).
    Backfill tests: late spans reprocessing; ensure deterministic readings.
12) Rollout plan (phased)
    Phase 1 (MVP: 2–3 weeks)
    OTel ingestion (FastAPI) + Collector config.
    DB schema + basic derivers for edges & workflow.completed.
    One pricing plan with precedence/envelopes.
    Lago: create customer, 2–3 billable metrics, push usage events, draft invoice.
    Minimal dashboard (usage & forecast).
    Phase 2
    Outcomes with conditions (e.g., SLA), more meters (storage.gbh, compute.ms).
    COGS pipeline + margin per line.
    Alerts & anomaly detection.
    Dispute/adjustment flow; backfill handling.
    Phase 3
    Contracts (commits, pre-purchased credits), custom per-tenant rules.
    Feature flags per plan; A/B of envelope sizes.
    Advanced reporting (cohorts, LTV/CAC vs margin).
13) Python components (repo layout)
    billing-platform/
    apps/
    ingest_api/            # FastAPI endpoints (OTel, webhooks, admin)
    deriver/               # batch/stream jobs to produce meter_readings
    rater/                 # rating engine + Lago adapter
    dashboard_api/         # usage & forecast; authn via your IdP
    lib/
    otel_schemas.py        # attribute conventions
    meters.py              # catalog constants & validation
    rating_policies.py     # precedence/envelope logic
    lago_client.py         # Lago API wrapper
    db.py                  # SQLModel/SQLAlchemy sessions
    infra/
    docker/
    k8s/
    migrations/            # Alembic
    tests/
14) Code snippets (starters)
    Rating policy envelope accounting
    from collections import defaultdict
    from decimal import Decimal

def allocate_work_envelopes(usage, policy):
envelopes = defaultdict(Decimal)  # e.g., envelopes['llm.tokens'] += ...
per_work = policy.get("edges_included_per_work", {}).get("workflow.completed", {})
work_count = Decimal(usage.get(("workflow.completed"), 0))

    for edge_key, cap in per_work.items():
        envelopes[edge_key] = Decimal(cap) * work_count
    return envelopes
Edge spill calculation
def bill_edge_spill(edge_total, included, envelope, unit_price):
# bill only what exceeds included + envelope
billable = max(Decimal("0"), Decimal(edge_total) - Decimal(included) - Decimal(envelope))
return billable * Decimal(unit_price)
15) Risks & mitigations
    Late/duplicated events → Strict idempotency keys; periodic reconciliation job.
    Double-charging complexity → Precedence + envelopes tested with property-based tests.
    Customer bill shock → Forecasting, alerts, soft caps, spend limits.
    Margin erosion → Track COGS; adjust envelope sizes and unit prices.
16) Next steps (actionable)
    Lock the meter catalog (names/units) and the MVP plan JSON (precedence + envelopes).
    Stand up FastAPI ingest + Postgres + OTel Collector.
    Implement edge & work derivers + basic rater.
    Script Lago setup (customers, metrics, plans), and push first usage.
    Build the usage preview API & a simple dashboard.
    Run a synthetic month; reconcile vs Lago invoice; iterate.
