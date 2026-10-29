# Measured baseline validation

Status: PASS

valid baseline only; deliberate anomalies and detection recall not evaluated

- SQLITE_INTEGRITY: 0/1 violations; PASS. Failed SQLite integrity check / one database integrity check.
- EXACT_CORE_COUNTS: 0/3 violations; PASS. Mismatched named entity counts / 3 required entity counts.
- FK_INTEGRITY: 0/5356 violations; PASS. Unresolved non-null references / evaluated non-null references.
- REQUIRED_TYPES_ENUMS: 0/82041 violations; PASS. Invalid field cells / evaluated field cells.
- IDENTIFIER_FORMATS: 0/4532 violations; PASS. Malformed identifiers / business-support rows.
- CALENDAR_AND_AS_OF: 0/4032 violations; PASS. Invalid calendar or future timestamps / non-null business timestamps.
- PK_UNIQUENESS: 0/4532 violations; PASS. Repeated identifiers / business-support rows.
- SAME_ORDER: 0/80 violations; PASS. Cross-order return lines / return lines.
- AUTHORIZATION_MEMBERSHIP: 0/56 violations; PASS. Invalid request/line allocations / authorization lines.
- SHIPPED_ALLOCATION_LIMIT: 0/56 violations; PASS. Over-shipped allocations / authorization lines.
- INSPECTED_RECEIPT_LIMIT: 0/53 violations; PASS. Over-inspected receipts / shipment lines.
- ELIGIBILITY_REPLAY: 0/80 violations; PASS. Incorrect policy/quantity outcomes / return lines.
- CUMULATIVE_RESERVATIONS: 0/602 violations; PASS. Over-reserved original lines / purchased order lines.
- QUANTITY_RECONCILIATION: 0/80 violations; PASS. Broken purchased/requested/authorized/received/inspected/refunded quantity ladders / return lines.
- LINE_FINANCIALS: 0/602 violations; PASS. Incorrect line discounts/tax/paid values / purchased lines.
- ORDER_DISCOUNT_ALLOCATION: 0/300 violations; PASS. Incorrect order discount allocations or missing lines / orders.
- REFUND_ENTITLEMENTS: 0/37 violations; PASS. Incorrect inspection-unit entitlements/fees / obligations.
- REFUND_BALANCES: 0/37 violations; PASS. Overpaid obligations / obligations.
- REFUND_POSTING_PREREQUISITES: 0/43 violations; PASS. Invalid successful/failed payout facts / refund attempts.
- DUPLICATE_SUCCESSFUL_PAYMENTS: 0/33 violations; PASS. Repeated successful logical payment keys / successful payouts.
- ORIGINAL_PAID_CEILING: 0/602 violations; PASS. Original lines refunded above paid / purchased lines.
- DISPOSITION_PREREQUISITES: 0/48 violations; PASS. Invalid route/evidence/quantity decisions / dispositions.
- PHYSICAL_MOVEMENTS: 0/45 violations; PASS. Invalid or repeated physical movements / movements.
- CROSS_ENTITY_DATES: 0/438 violations; PASS. Broken parent/child chronology / applicable parent-child timestamp checks.
- PENDING_REJECTED_EXCHANGE: 0/50 violations; PASS. Unauthorized descendants or exchange cash obligations / requests.
- AGGREGATE_REQUEST_PROGRESS: 0/50 violations; PASS. Request stages inconsistent with accepted child progress / requests.
- SETTLEMENT_PREREQUISITES: 0/29 violations; PASS. Settled lines with incomplete receipt/inspection/payment/movement / settled lines.
- EVENT_REPLAY: 0/2883 violations; PASS. Invalid/reordered event transitions / events.
- EVENT_PROJECTIONS: 0/1575 violations; PASS. Missing creation history or mismatched final projection / traceable records.
