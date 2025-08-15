# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, models
from odoo.exceptions import RedirectWarning


class ArgentinianReportCustomHandler(models.AbstractModel):
    _inherit = 'l10n_ar.tax.report.handler'

    def _check_invoices(self, invoices):
        l10n_ar_vat_afip_code = {
        '0': 0,
        '1': 0,
        '2': 0,
        '3': 0,
        '4': 10.5,
        '5': 21,
        '6': 27,
        '8': 5,
        '9': 2.5}

        res = []
        # header = ['Fecha', 'Factura ID', 'Contacto', 'Factura Nombre', 'Alícuota IVA', 'Base Imponible', 'Importe Reportado', 'Importe Calculado', 'Diferencia']
        # res.append(header)
        for inv in invoices:
            vat_taxes = inv._get_vat()
            for vat_tax in vat_taxes:
                calculated_amount = (vat_tax['BaseImp'] * l10n_ar_vat_afip_code[vat_tax['Id']] / 100)
                diff = abs(vat_tax['Importe'] - calculated_amount)
                if diff > 0.5:
                    res.append((inv.id, inv.name, (vat_tax['BaseImp'], l10n_ar_vat_afip_code[vat_tax['Id']], vat_tax['Importe']), diff, calculated_amount))
        return res

    def _vat_book_get_REGINFO_CV_ALICUOTAS(self, options, tax_type, invoices):
        # only vat taxes with codes 3, 4, 5, 6, 8, 9. this follows what is mentioned in http://contadoresenred.com/regimen-de-informacion-de-compras-y-ventas-rg-3685-como-cargar-la-informacion/. We start counting codes 1 (not taxed) and 2 (exempt) if there are no aliquots, we add one of this with 0, 0, 0 in details. we also use mapped in case there are duplicate afip codes (eg manual and auto)
        invoices_domain = []
        if error := self._check_invoices(invoices):
            invoices_domain = [('id', 'in', [inv[0] for inv in error])]
            raise RedirectWarning(
                _('Existen comprobantes con diferencias mayores a 0.5 centavos en el cálculo de IVA.'
                ' Para más información, haga click en el siguiente link: https://www.adhoc.inc/knowledge/article/9963'),
                {
                    'type': 'ir.actions.act_window',
                    'name': 'Invoices with differences',
                    'res_model': 'account.move',
                    'view_mode': 'list',
                    'views': [(False, 'list'), (False, 'form')],
                    'domain': invoices_domain,
                },
                _('Corregir comprobantes'),
            )
