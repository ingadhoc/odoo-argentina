# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # TODO see if we want to make vat computed from main_id_number
    # for compatibiltiy with other modules. We try to make vat "main_id_number"
    # but we raise some issues
    # vat = fields.Char(
    # )
    # TODO podriamos agregar tambien que el cuit se guarde en el vat con lo de
    # AR... si es necesario y entonces llamamos a vat en vez de cuit
    # field used only some argentinian methods that requires a CUIT and not
    # any other
    cuit = fields.Char(
        compute='_compute_cuit',
    )
    # no podemos hacerlo asi porque cuando se pide desde algun lugar
    # quiere computar para todos los partners y da error para los que no
    # tienen por mas que no lo pedimos
    # cuit_required = fields.Char(
    #     compute='_compute_cuit_required',
    # )
    main_id_number = fields.Char(
        compute='_compute_main_id_number',
        inverse='_set_main_id_number',
        store=True,
        string='Main Identification Number',
    )
    main_id_category_id = fields.Many2one(
        string="Main Identification Category",
        comodel_name='res.partner.id_category',
    )

    @api.multi
    def cuit_required(self):
        self.ensure_one()
        if not self.cuit:
            raise UserError(_('No CUIT cofigured for partner %s') % (
                self.name))
        return self.cuit

    @api.one
    def _compute_cuit(self):
        cuit = self.id_numbers.search([
            ('partner_id', '=', self.id),
            ('category_id.afip_code', '=', '80'),
        ], limit=1)
        self.cuit = cuit.name

    @api.multi
    @api.depends(
        'main_id_category_id',
        'id_numbers.category_id',
        'id_numbers.name',
    )
    def _compute_main_id_number(self):
        for partner in self:
            id_numbers = partner.id_numbers.filtered(
                lambda x: x.category_id == partner.main_id_category_id)
            if id_numbers:
                partner.main_id_number = id_numbers[0].name

    @api.multi
    def _set_main_id_number(self):
        for partner in self:
            name = partner.main_id_number
            category_id = partner.main_id_category_id
            if category_id:
                partner_id_numbers = partner.id_numbers.filtered(
                    lambda d: d.category_id == category_id)
                if partner_id_numbers and name:
                    partner_id_numbers[0].name = name
                elif partner_id_numbers and not name:
                    partner_id_numbers[0].unlink()
                # we only create new record if name has a value
                elif name:
                    partner_id_numbers.create({
                        'partner_id': partner.id,
                        'category_id': category_id.id,
                        'name': name
                    })

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        """
        we search by id, if we found we return this results, else we do
        default search
        """
        if not args:
            args = []
        if name:
            recs = self.search(
                [('id_numbers', operator, name)] + args, limit=limit)
            if recs:
                return recs.name_get()
        return super(ResPartner, self).name_search(
            name, args=args, operator=operator, limit=limit)
