# -*- coding: utf-8 -*-
from openerp import models, api, fields, _
from ast import literal_eval
from openerp.exceptions import Warning
import logging
_logger = logging.getLogger(__name__)


class res_partner_update_from_padron_field(models.TransientModel):
    _name = 'res.partner.update.from.padron.field'

    wizard_id = fields.Many2one(
        'res.partner.update.from.padron.wizard',
        'Wizard',
        # required=True,
    )
    field = fields.Char(
    )
    old_value = fields.Char(
    )
    new_value = fields.Char(
    )


class res_partner_update_from_padron_wizard(models.TransientModel):
    _name = 'res.partner.update.from.padron.wizard'

    @api.model
    def get_partners(self):
        domain = [
            ('document_number', '!=', False),
            ('document_type_id.afip_code', '=', 80),
        ]
        active_ids = self._context.get('active_ids', [])
        if active_ids:
            domain.append(('id', 'in', active_ids))
        return self.env['res.partner'].search(domain)

    @api.model
    def default_get(self, fields):
        res = super(res_partner_update_from_padron_wizard, self).default_get(
            fields)
        context = self._context
        if (
                context.get('active_model') == 'res.partner' and
                context.get('active_ids')
        ):
            res['state'] = 'selection'
            partners = self.get_partners()
            if not partners:
                raise Warning(_(
                    'No se encontró ningún partner con CUIT para actualizar'))
            res['partner_id'] = partners[0].id
        return res

    @api.model
    def _get_domain(self):
        fields_names = [
            'name',
            'estado_padron',
            'street',
            'city',
            'zip',
            'actividades_padron',
            'impuestos_padron',
            'imp_iva_padron',
            'state_id',
            'imp_ganancias_padron',
            'monotributo_padron',
            'actividad_monotributo_padron',
            'empleador_padron',
            'integrante_soc_padron',
            'last_update_padron',
            # 'constancia',
        ]
        return [
            ('model', '=', 'res.partner'),
            ('name', 'in', fields_names),
        ]

    @api.model
    def get_fields(self):
        return self.env['ir.model.fields'].search(self._get_domain())

    state = fields.Selection([
        ('option', 'Option'),
        ('selection', 'Selection'),
        ('finished', 'Finished')],
        'State',
        readonly=True,
        required=True,
        default='option',
    )
    field_ids = fields.One2many(
        'res.partner.update.from.padron.field',
        'wizard_id',
        string='Fields',
    )
    partner_ids = fields.Many2many(
        'res.partner',
        'partner_update_from_padron_rel',
        'update_id', 'partner_id',
        string='Partners',
        default=get_partners,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        readonly=True,
    )
    update_constancia = fields.Boolean(
        default=True,
    )
    title_case = fields.Boolean(
        string='Title Case',
        help='Converts retreived text fields to Title Case.',
        default=True,
    )
    field_to_update_ids = fields.Many2many(
        'ir.model.fields',
        'res_partner_update_fields',
        'update_id', 'field_id',
        string='Fields To Update',
        help='Only this fields are going to be retrived and updated',
        default=get_fields,
        domain=_get_domain,
        required=True,
    )

    @api.multi
    @api.onchange('partner_id')
    def change_partner(self):
        self.ensure_one()
        self.field_ids.unlink()
        partner = self.partner_id
        fields_names = self.field_to_update_ids.mapped('name')
        if partner:
            partner_vals = partner.get_data_from_padron_afip()
            lines = []
            # partner_vals.pop('constancia')
            for key, new_value in partner_vals.iteritems():
                old_value = getattr(partner, key)
                if new_value == '':
                    new_value = False
                if self.title_case and key in ('name', 'city', 'street'):
                    new_value = new_value and new_value.title()
                if key in ('impuestos_padron', 'actividades_padron'):
                    old_value = old_value.ids
                elif key == 'state_id':
                    old_value = old_value.id
                if key in fields_names and old_value != new_value:
                    line_vals = {
                        'wizard_id': self.id,
                        'field': key,
                        'old_value': old_value,
                        # 'new_value': new_value,
                        'new_value': new_value or False,
                    }
                    lines.append((0, False, line_vals))
            self.field_ids = lines

    # @mute_logger('openerp.osv.expression', 'openerp.models')
    @api.multi
    def _update(self):
        self.ensure_one()
        vals = {}
        for field in self.field_ids:
            if field.field in ('impuestos_padron', 'actividades_padron'):
                vals[field.field] = [(6, False, literal_eval(field.new_value))]
            else:
                vals[field.field] = field.new_value
        self.partner_id.write(vals)
        if self.update_constancia:
            self.partner_id.update_constancia_from_padron_afip()

    @api.multi
    def automatic_process_cb(self):
        self.start_process_cb()
        self.refresh()

        for partner in self.partner_ids:
            self._update()
            partner = self.partner_ids[0]
            self.partner_id = partner.id
            self.change_partner()

        self.write({'state': 'finished'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    @api.multi
    def update_selection(self):
        self.ensure_one()
        if not self.field_ids:
            self.write({'state': 'finished'})
            return {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }
        self._update()
        return self.next_cb()

    @api.multi
    def next_cb(self):
        """
        """
        self.ensure_one()
        if self.partner_id:
            self.write({'partner_ids': [(3, self.partner_id.id, False)]})
        return self._next_screen()

    @api.multi
    def _next_screen(self):
        self.ensure_one()
        self.refresh()
        values = {}
        if self.partner_ids:
            # in this case, we try to find the next record.
            partner = self.partner_ids[0]
            values.update({
                'partner_id': partner.id,
                'state': 'selection',
            })
        else:
            values.update({
                'state': 'finished',
            })

        self.write(values)
        # because field is not changed, view is distroyed and reopen, on change
        # is not called an we call it manually
        self.change_partner()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    @api.multi
    def start_process_cb(self):
        """
        Start the process.
        """
        self.ensure_one()
        return self._next_screen()
