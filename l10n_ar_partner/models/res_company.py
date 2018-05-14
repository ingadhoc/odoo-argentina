from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    main_id_category_id = fields.Many2one(
        related='partner_id.main_id_category_id',
    )
    main_id_number = fields.Char(
        related='partner_id.main_id_number',
    )
    cuit = fields.Char(
        related='partner_id.cuit'
    )

    @api.multi
    def cuit_required(self):
        return self.partner_id.cuit_required()

    @api.model
    def create(self, vals):
        """
        On create, we set id number to partner
        """
        company = super(ResCompany, self).create(vals)
        company.change_main_id_category()
        main_id_number = vals.get('main_id_number')
        if main_id_number:
            company.partner_id.main_id_number = main_id_number
        return company

    @api.onchange('main_id_category_id')
    def change_main_id_category(self):
        # we force change on partner to get updated number
        if self.partner_id:
            self.partner_id.main_id_category_id = self.main_id_category_id
            self.main_id_number = self.partner_id.main_id_number
