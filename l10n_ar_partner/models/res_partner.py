from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


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
    formated_cuit = fields.Char(
        compute='_compute_formated_cuit',
    )
    # no podemos hacerlo asi porque cuando se pide desde algun lugar
    # quiere computar para todos los partners y da error para los que no
    # tienen por mas que no lo pedimos
    # cuit_required = fields.Char(
    #     compute='_compute_cuit_required',
    # )
    main_id_number = fields.Char(
        compute='_compute_main_id_number',
        inverse='_inverse_main_id_number',
        store=True,
        string='Main Identification Number',
    )
    main_id_category_id = fields.Many2one(
        string="Main Identification Category",
        comodel_name='res.partner.id_category',
        index=True,
        auto_join=True,
    )

    @api.multi
    def cuit_required(self):
        self.ensure_one()
        if not self.cuit:
            raise UserError(_('No CUIT configured for partner [%i] %s') % (
                self.id, self.name))
        return self.cuit

    @api.multi
    @api.depends(
        'cuit',
    )
    def _compute_formated_cuit(self):
        for rec in self:
            if not rec.cuit:
                continue
            cuit = rec.cuit
            rec.formated_cuit = "{0}-{1}-{2}".format(
                cuit[0:2], cuit[2:10], cuit[10:])

    @api.multi
    @api.depends(
        'id_numbers.category_id.afip_code',
        'id_numbers.name',
        'main_id_number',
        'main_id_category_id',
    )
    def _compute_cuit(self):
        for rec in self:
            # el cuit solo lo devolvemos si es el doc principal
            # para que no sea engañoso si no tienen activado multiples doc
            # y esta seleccionado otro que no es cuit
            # igualmente, si es un partner del extranjero intentamos devolver
            # cuit fisica o juridica del pais
            if rec.main_id_category_id.afip_code != 80:
                country = rec.country_id
                if country and country.code != 'AR':
                    if rec.is_company:
                        rec.cuit = country.cuit_juridica
                    else:
                        rec.cuit = country.cuit_fisica
                continue
            cuit = rec.id_numbers.search([
                ('partner_id', '=', rec.id),
                ('category_id.afip_code', '=', 80),
            ], limit=1)
            # agregamos esto para el caso donde el registro todavia no se creo
            # queremos el cuit para que aparezca el boton de refrescar de afip
            if not cuit:
                rec.cuit = rec.main_id_number
            else:
                rec.cuit = cuit.name

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
    def _inverse_main_id_number(self):
        to_unlink = self.env['res.partner.id_number']
        # we use sudo because user may have CRUD rights on partner
        # but no to partner id model because partner id module
        # only adds CRUD to "Manage contacts" group
        for partner in self:
            name = partner.main_id_number
            category_id = partner.main_id_category_id
            if category_id:
                partner_id_numbers = partner.id_numbers.filtered(
                    lambda d: d.category_id == category_id).sudo()
                if partner_id_numbers and name:
                    partner_id_numbers[0].name = name
                elif partner_id_numbers and not name:
                    to_unlink |= partner_id_numbers[0]
                # we only create new record if name has a value
                elif name:
                    partner_id_numbers.create({
                        'partner_id': partner.id,
                        'category_id': category_id.id,
                        'name': name
                    })
        to_unlink.unlink()

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """
        we search by id, if we found we return this results, else we do
        default search
        """
        if not args:
            args = []
        # solo para estos operadores para no romper cuando se usa, por ej,
        # no contiene algo del nombre
        if name and operator in ('ilike', 'like', '=', '=like', '=ilike'):
            recs = self.search(
                [('id_numbers.name', operator, name)] + args, limit=limit)
            if recs:
                return recs.name_get()
        return super(ResPartner, self).name_search(
            name, args=args, operator=operator, limit=limit)

    @api.multi
    def update_partner_data_from_afip(self):
        """
        Funcion que llama al wizard para actualizar data de partners desde afip
        sin abrir wizard.
        Podríamos mejorar  pasando un argumento para sobreescribir o no valores
        que esten o no definidos
        Podriamos mejorarlo moviento lógica del wizard a esta funcion y que el
        wizard use este método.
        """

        for rec in self:
            wiz = rec.env[
                'res.partner.update.from.padron.wizard'].with_context(
                active_ids=rec.ids, active_model=rec._name).create({})
            wiz.change_partner()
            wiz.update_selection()

    @api.model
    def try_write_commercial(self, data):
        """ User for website. capture the validation errors and return them.
        return (error, error_message) = (dict[fields], list(str()))
        """
        error = dict()
        error_message = []
        main_id_number = data.get('main_id_number', False)
        main_id_category_id = data.get('main_id_category_id', False)
        afip_responsability_type_id = data.get('afip_responsability_type_id',
                                               False)

        if main_id_number and main_id_category_id:
            commercial_partner = self.env['res.partner'].sudo().browse(
                int(data.get('commercial_partner_id', False)))
            try:
                values = {
                    'main_id_number': main_id_number,
                    'main_id_category_id': int(main_id_category_id),
                    'afip_responsability_type_id':
                        int(afip_responsability_type_id)
                        if afip_responsability_type_id else False,
                }
                commercial_fields = ['main_id_number', 'main_id_category_id',
                                     'afip_responsability_type_id']
                values = commercial_partner.remove_readonly_required_fields(
                    commercial_fields, values)
                with self.env.cr.savepoint():
                    commercial_partner.write(values)
            except Exception as exception_error:
                _logger.error(exception_error)
                error['main_id_number'] = 'error'
                error['main_id_category_id'] = 'error'
                error_message.append(_(exception_error))
        return error, error_message

    @api.multi
    def remove_readonly_required_fields(self, required_fields, values):
        """ In some cases we have information showed to the user in the form
        that is required but that is already set and readonly.
        We do not really update this fields and then here we are trying to
        write them: the problem is that this fields has a constraint if
        we are trying to re-write them (even when is the same value).

        This method remove this (field, values) for the values to write in
        order to do avoid the constraint and not re-writted again when they
        has been already writted.

        param: @required_fields: (list) fields of the fields that we want to
               check
        param: @values (dict) the values of the web form

        return: the same values to write and they do not include
        required/readonly fields.
        """
        self.ensure_one()
        for r_field in required_fields:
            value = values.get(r_field)
            if r_field.endswith('_id'):
                if self[r_field].id == value:
                    values.pop(r_field, False)
            else:
                if self[r_field] == value:
                    values.pop(r_field, False)
        return values
