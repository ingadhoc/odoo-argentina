# -*- coding: utf-8 -*-
from openerp import models, api, fields, _
from pyafipws.padron import PadronAFIP
from ast import literal_eval
from openerp.exceptions import Warning
import logging
_logger = logging.getLogger(__name__)


class res_partner_update_from_padron_line(models.TransientModel):
    _name = 'res.partner.update.from.padron.line'
    _order = 'min_id asc'

    wizard_id = fields.Many2one(
        'res.partner.update.from.padron.wizard',
        'Wizard'
        )
    min_id = fields.Integer(
        'MinID'
        )
    aggr_ids = fields.Char(
        'Ids',
        required=True
        )


class res_partner_update_from_padron_wizard(models.TransientModel):
    _name = 'res.partner.update.from.padron.wizard'

    @api.model
    def get_partners(self):
        return self.env['res.partner'].search(
            self._context.get('active_ids', []))

    # update_name = fields.Boolean(
    #     default=True,
    #     )
    # update_name = fields.Boolean(
    #     default=True,
    #     )
    # update_name = fields.Boolean(
    #     default=True,
    #     )
    # update_name = fields.Boolean(
    #     default=True,
    #     )
    # update_name = fields.Boolean(
    #     default=True,
    #     )

    state = fields.Selection([
        ('option', 'Option'),
        ('selection', 'Selection'),
        ('finished', 'Finished')],
        'State',
        readonly=True,
        required=True,
        default='selection',
        )
    current_line_id = fields.Many2one(
        'res.partner.update.from.padron.line',
        'Current Line'
        )
    line_ids = fields.one2many(
        'res.partner.update.from.padron.line',
        'wizard_id',
        'Lines'
        )
    partner_ids = fields.Many2many(
        'res.partner',
        string='Partners',
        default=get_partners,
        )
    partner_id = fields.Many2one(
        'res.partner',
        string='Actual Partner'
        )

    @api.multi
    def update_selection(self, cr, uid, ids, context=None):
        self.ensure_one()
        partner_ids = self.partner_ids
        if not partner_ids:
            self.write({'state': 'finished'})
            return {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }

        self._merge(
            partner_ids,
            self.partner_id,
            )

        if self.current_line_id:
            self.current_line_id.unlink()

        return self._next_screen()

    @api.multi
    def next_cb(self):
        """
        Don't compute any thing
        """
        self.ensure_one()
        if self.current_line_id:
            self.current_line_id.unlink()
        return self._next_screen()

    @api.multi
    def _next_screen(self):
        self.ensure_one()
        self.refresh()
        values = {}
        if self.line_ids:
            # in this case, we try to find the next record.
            current_line = self.line_ids[0]
            current_partner_ids = literal_eval(current_line.aggr_ids)
            values.update({
                'current_line_id': current_line.id,
                'partner_ids': [(6, 0, current_partner_ids)],
                # 'dst_partner_id': self._get_ordered_partner(cr, uid, current_partner_ids, context)[-1].id,
                'state': 'selection',
            })
        else:
            values.update({
                'current_line_id': False,
                'partner_ids': [],
                'state': 'finished',
            })

        self.write(values)
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
