# Data Quality & Governance Rules

## Quality gates
- **Raw layer** is validated with Great Expectations: not-null on keys,
  uniqueness on natural keys, schema/length checks, accepted-value sets, and
  numeric range checks.
- **Modelled layers** are validated with dbt tests: `unique`, `not_null`,
  `relationships` (referential integrity from facts to dimensions), and
  `accepted_values` on categorical columns.
- **Reconciliation** proves every source row is accounted for across
  source → raw → staging.

## Known cleaning rules
- Duplicate events are de-duplicated by keeping the latest by load timestamp.
- The `-9999` sentinel in delay columns is converted to NULL.
- Flights referencing an unknown airport code are dropped in staging and counted
  as DQ-filtered in reconciliation.

## Freshness
- Core marts must be no older than **26 hours**; a freshness alert pages
  on-call otherwise.

## PII & access
- Customer PII (email, address) is restricted to the `secure` schema and is
  **never** copied into analytics marts.
- Analytics marts contain surrogate keys only; natural customer ids are not
  exposed to BI users.
- Access to raw and secure schemas is granted by role, reviewed quarterly.

## Ownership
- Every mart has a named owner in the catalog. Questions about a table should go
  to its owner; this assistant cites the documentation but is not authoritative
  for access requests.
