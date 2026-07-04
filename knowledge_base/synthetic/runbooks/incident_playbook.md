# Data Incident Playbook

## Severity levels
- **SEV1** — executive dashboards wrong or unavailable; data is being consumed
  externally. Page on-call immediately.
- **SEV2** — a mart is stale or a test is failing but no external impact yet.
- **SEV3** — cosmetic or isolated issue; handle in normal working hours.

## First 15 minutes
1. Acknowledge the alert in `#data-oncall`.
2. Check the Airflow run: which task failed and its logs.
3. Check the latest reconciliation and Great Expectations reports.
4. Post an initial status in the incident thread with severity + suspected area.

## Rollback / mitigation
- Marts are rebuilt from raw each run, so **re-running `dbt build`** on the last
  good raw snapshot restores correct marts.
- If a bad source file caused it, quarantine the file, restore the prior day's
  raw snapshot, and re-run downstream stages.
- Never hand-edit marts; always fix upstream and rebuild.

## Communication
- Update the incident thread at least every 30 minutes for SEV1/SEV2.
- On resolution, record root cause, impact window, and a follow-up action in the
  incident log.
