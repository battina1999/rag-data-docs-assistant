# ETL Runbook — Nightly Batch

## Schedule & ownership
The nightly batch runs at **06:00 UTC** via Apache Airflow (DAG
`airline_operations_pipeline`). The Data Engineering team owns it; the on-call
engineer is listed in the `#data-oncall` channel topic.

## Pipeline stages
1. **generate / extract** — land raw source files into the `raw` schema.
2. **ingest** — full-refresh load with an ingestion-audit row per source.
3. **validate** — Great Expectations checks on the raw layer (monitor mode).
4. **dbt build** — staging → dimensions/facts → analytics marts, plus tests.
5. **reconcile** — source-to-target row-count reconciliation.

Each stage must succeed before the next starts; `reconcile` failing raises and
fails the DAG run so bad data never reaches BI.

## SLAs
- Marts refreshed and reconciled by **08:00 UTC**.
- Data freshness alert fires if `fact_flights` max load timestamp is older than
  **26 hours**.

## Retries & backfill
- Airflow retries each task **once** after a 2-minute delay.
- To backfill a date range, trigger the DAG with a `run_date` config; loads are
  idempotent (`CREATE OR REPLACE`), so re-runs are safe.

## Common failures
- **dbt relationships test fails** → an orphan key reached a fact; check the
  staging filter that drops unknown airports.
- **reconciliation FAIL** → unexplained row loss; inspect the ingestion-audit
  table and the staging de-duplication logic.
- **freshness alert** → confirm the upstream source file arrived; re-run
  `ingest` then `dbt build`.
