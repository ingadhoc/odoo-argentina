# Automatic Argentinian Withholdings on Payments (l10n_ar_tax)

Implements automatic calculation of Argentine withholdings (retenciones) and perceptions on payments. Withholdings are computed based on fiscal positions, tax configurations, jurisdictional rules, and partner-specific tax identification. Fully supports **multi-currency payments** — withholdings are always calculated and stored in ARS (company currency) regardless of the payment or debt currency.

## Features

- Automatic withholding calculation based on jurisdictions and tax tables.
- Support for perception taxes.
- Multi-currency withholdings: payments in USD, EUR, or any foreign currency produce correct ARS-denominated withholdings.
- Configurable tax ratios for specific jurisdictions (e.g. Córdoba).
- Fiscal position-based tax automation.
- Withholding certificate generation.
- Integration with ARCA web services.
- ARBA and Santa Fe (PARP) padron importers.
- Same-period base accumulation for taxes like Ganancias with minimum thresholds.
- Integration with `account_payment_pro` tri-currency model.

## Dependencies

| Module | Purpose |
|--------|---------|
| `l10n_ar` | Argentine localization (auto-install trigger) |
| `l10n_ar_ux` | Argentine UX extensions |
| `l10n_ar_withholding` | Base withholding framework |
| `account_payment_pro` | Tri-currency payment model (provides `destination_currency_id`, `accounting_rate`, `counterpart_rate`) |
| `l10n_latam_check` | Check support for payment receipts |

## Configuration

1. **Taxes:** Accounting → Configuration → Taxes — configure withholding and perception taxes.
2. **Fiscal positions:** Accounting → Configuration → Fiscal Positions — set up automatic tax assignment.
3. **Partner tax ID:** in Contacts, configure CUIT/CUIL/DNI.
4. **Tax ratios:** set ratios (1–100) on percentage-based taxes to control the taxable base percentage.
5. **Padron importers:** for Santa Fe (PARP) and ARBA, configure the corresponding fiscal position with the web service setting. See `doc/padron_santa_fe/` for specs and examples.

## Usage

- Withholdings are automatically calculated when creating payments based on the partner's fiscal position.
- Perception taxes are applied via fiscal positions.
- Withholding certificates can be generated from the payment form.
- Multi-currency: the user sees withholding amounts expressed in the debt currency (B) for UX, but stored amounts and bases are always in ARS.

## Bug Tracker

Bugs are tracked on [GitHub Issues](https://github.com/ingadhoc/odoo-argentina/issues).

## Credits

**Author:** ADHOC SA · [www.adhoc.com.ar](https://www.adhoc.com.ar)
**License:** AGPL-3.0 or later

---

See [DESIGN.md](DESIGN.md) for internal architecture and design decisions.
