# DESIGN — l10n_ar_tax

Internal architecture reference for developers maintaining or extending the module.

---

## Core principle: withholdings always in ARS (C)

AFIP requires withholding certificates in ARS. All internal computation follows this:

- `base_amount` is stored in ARS (C).
- `amount` (the withholding amount) is stored in ARS (C).
- `currency_id` on `l10n_ar.payment.withholding` = `company_currency_id` (ARS).
- `same_period_base` accumulates `balance` from move lines, which is already in ARS.
- `compute_all` always receives ARS.

The user sees amounts in the debt currency (B) only for UX purposes via `withholdings_amount` on `account.payment`.

---

## Rate conversion: `_get_withholding_rate()`

Returns a **direct multiplier** `base_B × rate = amount_C` (B → C).

```
Formula: (1 / accounting_rate) / counterpart_rate = (C/A) / (B1/A) = C/B1
```

| Scenario | accounting_rate | counterpart_rate | withholding_rate |
|----------|----------------|-----------------|-----------------|
| A=B=C=ARS | 1.0 | 1.0 | 1.0 |
| A=B=USD, C=ARS (1 USD=1200 ARS) | 0.000833 | 1.0 | 1200 |
| A=C=ARS, B=USD (1 USD=1500 ARS) | 1.0 | 0.000667 | 1500 |
| A=USD, B=EUR, C=ARS | 0.000833 | 0.909 | 1320 |

---

## Data model: `l10n_ar.payment.withholding`

| Field | Currency | Notes |
|-------|----------|-------|
| `currency_id` | C (ARS) | `related="payment_id.company_currency_id"` |
| `base_amount` | C (ARS) | Computed: sum of base in B, converted to C via `_get_withholding_rate()` |
| `amount` | C (ARS) | Result of `compute_all` — the actual withholding |

There is **no** `base_currency_id` field — `base_amount` is always ARS.

---

## Key methods

### `_compute_base_amount`

1. Collects debt amounts in currency B (`selected_debt_untaxed`, `withholdable_advanced_amount`, etc.).
2. Handles partial payments: compares `to_pay_amount` vs `selected_debt` to compute the proportional advance.
3. At the end, converts the B-denominated base to C via `_get_withholding_rate()`.

`@api.depends` includes `payment_id.accounting_rate` and `payment_id.counterpart_rate` so that changing rates in the wizard recalculates the base.

### `_tax_compute_all_helper`

Receives `self.base_amount` which is already in C (ARS). Calls `compute_all` with `currency=company_currency_id`. No internal currency conversion needed.

### `_prepare_move_withholding_lines`

Generates the journal entry lines for withholdings. Key branches:

| Condition | `currency_id` | `amount_currency` |
|-----------|--------------|-------------------|
| `use_company_currency` (A≠C, e.g. A=USD) | ARS (C) | = `balance` |
| `counterpart_is_foreign` (A=C=ARS, B≠C) | ARS (C) | = `balance` |
| else (A=B=C or similar) | A | `balance × accounting_rate` |

Uses `self.accounting_rate` (not the eliminated `exchange_rate`). The formula changed from `balance / exchange_rate` (where exchange_rate=1200) to `balance × accounting_rate` (where accounting_rate≈0.000833) — numerically identical.

### `_prepare_move_lines_per_type` (counterpart adjustment)

When `counterpart_is_foreign` (A=C=ARS, B=USD): withholding lines stay in ARS, but the AP counterpart line needs its `amount_currency` adjusted in USD:

```python
wth_amount_in_b = wth_balance / withholding_rate  # ARS → USD
counterpart_lines[0]["amount_currency"] -= wth_amount_in_b
```

This prevents the "Automatic Balancing Line" bug that occurred when withholding lines had `currency_id=USD` with small `amount_currency` values.

---

## Fields on `account.payment` (defined/modified by this module)

| Field | Currency | Notes |
|-------|----------|-------|
| `selected_debt_untaxed` | B (`destination_currency_id`) | Uses `amount_residual_currency` when B≠C |
| `withholdable_advanced_amount` | B (`destination_currency_id`) | |
| `withholdings_amount` | B (`destination_currency_id`) | Sum of withholding `amount` (C) converted C→B for UX |
| `withholding_warning` | — | **Eliminated** — replaced by full multi-currency support |

---

## Design decisions

### `base_amount` stays in C (ARS), not B

1. **AFIP requires ARS.** Certificates show ARS.
2. **`same_period_base` is already in ARS** — accumulated from move line `balance`. `C + C = C` without conversion.
3. **The user edits the base in ARS** — intuitive in the Argentine tax context.
4. **No migration script needed** — the `base_amount` column keeps its semantics.
5. **Simplifies `_tax_compute_all_helper`** — receives the base already in C.

### Rate source: payment rate, not spot or historical

The taxable base is converted B→C using the **payment's rate** (not the spot rate of the day nor the historical rate of each invoice). This is correct fiscally and avoids per-invoice rate lookups.

### Same-period accumulation works without changes

`_get_same_period_base_amount` and `_get_same_period_withholdings_amount` accumulate `balance` from move lines, which is already in ARS. No impact from the multi-currency refactor.

---

## Test coverage

Tests are in `tests/test_payment_withholding_multimoneda.py` and `tests/test_payment_withholding_checks_multimoneda.py`.

### Multi-currency withholding cases (`TestPaymentWithholdingMultimoneda`)

Each test validates: `base_amount` in ARS, `amount` (withholding) in ARS, `withholdings_amount` in B (UX), and correct journal entry lines.

| Test | Scenario | Currencies | Key verification |
|------|----------|-----------|-----------------|
| T.1 | Local payment | A=B=C=ARS | base=1000 ARS, wth=30 ARS |
| T.2 | Pure foreign currency | A=B=USD, C=ARS (1200) | base=1.200.000 ARS, wth=36.000 ARS, UX=30 USD |
| T.3 | Foreign currency purchase | A=C=ARS, B=USD (1500) | base=1.500.000 ARS, wth=45.000 ARS; withholding lines always in ARS |
| T.4 | Two invoices at different rates | A=C=ARS, B=USD (1500) | Uses payment rate for total (not per-invoice historical rate) |
| T.5 | Partial payment | A=C=ARS, B=USD (1500) | Proportional base calculation |
| T.6 | Arbitrage | A=USD, B=EUR, C=ARS | withholding_rate=1320, wth entry in USD (A) |
| T.7 | Ganancias with period accumulation | A=C=ARS, B=USD | `same_period_base` + new base both in C; threshold in ARS |
| T.8 | Reconcile: ARS journal, USD invoice | A=C=ARS, B1=USD, B2=ARS | Withholdings calculated correctly despite reconcile mode |
| T.9 | Reconcile: USD journal, ARS invoice | A=B1=USD, B2=ARS | Withholdings in ARS, entry lines in USD |

### Check + withholding cases (`TestPaymentChecksWithholding`)

| Test | Scenario |
|------|----------|
| TC6 | Single ARS check with IIBB withholding |
| TC7 | Two checks, foreign currency purchase with IIBB |
| TC8 | Two checks with IIBB and write-off |
| TC9 | Two USD checks with IIBB |
