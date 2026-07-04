# Metric Definitions (single source of truth)

These definitions are canonical. Dashboards and ad-hoc queries must match them.

## Airline operations
- **On-Time %** = on-time flights ÷ completed (non-cancelled) flights. A flight
  is **on-time** when it is not cancelled and its arrival delay is **< 15
  minutes** (US DOT convention).
- **Delayed flight** = arrival delay **≥ 15 minutes**.
- **Completion Factor %** = completed flights ÷ total scheduled flights
  (i.e. 1 − cancellation rate).
- **Cancellation %** = cancelled flights ÷ total flights.
- **Delay causes** follow the BTS breakdown: Carrier, Weather, NAS (National Air
  System), Security, and Late Aircraft. Cause minutes only apply to flights that
  arrived ≥ 15 minutes late.
- **Cancellation reasons** map from codes: A = Carrier, B = Weather,
  C = National Air System, D = Security.

## E-commerce (ShopSphere)
- **GMV (Gross Merchandise Value)** = sum of `net_revenue` on non-returned order
  lines.
- **Active customer** = placed at least one order in the trailing **90 days**.
- **Conversion rate** = sessions with a `purchase` event ÷ total sessions.
- **Return rate** = returned order lines ÷ total order lines.

## Rounding & currency
Percentages are rounded to **one decimal place**. Revenue is stored in the
warehouse in the account's base currency (USD) with no rounding until display.
