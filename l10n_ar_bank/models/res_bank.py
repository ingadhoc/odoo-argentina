from odoo import fields, models, api


class Bank(models.Model):
    _inherit = "res.bank"

    # See http://www.bcra.gob.ar/SistemasFinancierosYdePagos/Sistema_financiero_nomina_de_entidades.asp
    l10n_ar_bcra_code = fields.Char(
        "BCRA Code",
        help="Five-digit number assigned by the BCRA to identify banking institutions ", size=5)

    @api.model
    def update_bcra_code(self):
        for bank in self.search([]):
            if not bank.l10n_ar_bcra_code:
                code = bank.get_external_id()[bank.id]
                if code and code.startswith('l10n_ar_bank'):
                    bank.l10n_ar_bcra_code=code.split('.')[1]
                    
                    