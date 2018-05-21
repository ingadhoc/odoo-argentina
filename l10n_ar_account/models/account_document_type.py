from odoo import models, api, fields
# from odoo.exceptions import UserError


class AccountDocmentType(models.Model):
    _inherit = 'account.document.type'

    document_letter_id = fields.Many2one(
        'account.document.letter',
        'Document Letter',
        auto_join=True,
        index=True,
    )
    purchase_cuit_required = fields.Boolean(
        help='Verdadero si la declaración del CITI compras requiere informar '
        'CUIT'
    )
    purchase_alicuots = fields.Selection(
        [('not_zero', 'No Cero'), ('zero', 'Cero')],
        help='Cero o No cero según lo requiere la declaración del CITI compras'
    )

    @api.multi
    def get_document_sequence_vals(self, journal):
        vals = super(AccountDocmentType, self).get_document_sequence_vals(
            journal)
        if self.localization == 'argentina':
            vals.update({
                'padding': 8,
                'implementation': 'no_gap',
                'prefix': "%04i-" % (journal.point_of_sale_number),
            })
        return vals

    @api.multi
    def get_taxes_included(self):
        """
        In argentina we include taxes depending on document letter
        """
        self.ensure_one()
        if self.localization == 'argentina':
            if self.document_letter_id.taxes_included:
                # solo incluir el IVA, el resto se debe discriminar
                # return self.env['account.tax'].search([])
                return self.env['account.tax'].search(
                    [('tax_group_id.tax', '=', 'vat'),
                     ('tax_group_id.type', '=', 'tax')])
            # included_tax_groups = (
            #     self.document_letter_id.included_tax_group_ids)
            # if included_tax_groups:
            #     return self.env['account.tax'].search(
            #         [('tax_group_id', 'in', included_tax_groups.ids)])
        else:
            return super(AccountDocmentType, self).get_taxes_included()
