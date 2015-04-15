# -*- coding: utf-8 -*-
from openerp import models


class account_voucher(models.Model):
    _inherit = 'account.voucher'

    # check_ids = fields.One2many(
    #     'account.check',
    #     compute='get_checks',
    #     string='Checks')
    # move_line_ids = fields.One2many(
    #     'account.move.line',
    #     compute='get_moves',
    #     string='Move Lines')
    # line_cr_ids = fields.One2many(
    #     'account.voucher.line',
    #     compute='get_moves',
    #     string='Credit Voucher Lines')
    # line_dr_ids = fields.One2many(
    #     'account.voucher.line',
    #     compute='get_moves',
    #     string='Debit Voucher Lines')
    # check_amount = fields.Float(
    #     compute='get_amounts',
    #     string='Check Amount')
    # bank_amount = fields.Float(
    #     compute='get_amounts',
    #     string='Bank Amount')
    # cash_amount = fields.Float(
    #     compute='get_amounts',
    #     string='Cash Amount')
    # total_amount = fields.Float(
    #     compute='get_amounts',
    #     string='Total Amount')
    # writeoff_amount = fields.Float(
    #     compute='get_amounts',
    #     string='Write OffAmount')
    # keepopen_amount = fields.Float(
    #     compute='get_amounts',
    #     string='Keep Open Amount')

    # @api.one
    # @api.depends(
    #     'voucher_ids',
    #     'voucher_ids.amount',
    # )
    # def get_amounts(self):
    #     '''TODO mejorar y ver si no hay un cheque duplicado
    #     (Se pueden usar los conjuntos con set)
    #     '''
    #     voucher_obj = self.pool['account.voucher']
    #     check_amounts = [
    #         v.amount for v in self.voucher_ids if v.journal_id.check_type]
    #     bank_amounts = [
    #         v.amount for v in self.voucher_ids if v.journal_id.type == 'bank' and not v.journal_id.check_type]
    #     cash_amounts = [
    #         v.amount for v in self.voucher_ids if v.journal_id.type == 'cash']
    #     total_amounts = [v.amount for v in self.voucher_ids]
    #     writeoff_amount = 0.0
    #     keepopen_amount = 0.0
    #     for voucher in self.voucher_ids:
    #         # Si usamos el campo funcion no se porque da error,
    #         # por eso lo calculamos con el metodo de account voucher
    #         # voucher.writeoff_amount
    #         dif_amount = voucher_obj._get_writeoff_amount(
    #             self.env.cr,
    #             self.env.uid,
    #             [voucher.id],
    #             False,
    #             False)[voucher.id]
    #         if voucher.payment_option == 'with_writeoff':
    #             writeoff_amount += dif_amount
    #         elif voucher.payment_option == 'without_writeoff':
    #             keepopen_amount += dif_amount

    #     self.check_amount = sum(check_amounts)
    #     self.bank_amount = sum(bank_amounts)
    #     self.cash_amount = sum(cash_amounts)
    #     self.total_amount = sum(total_amounts)
    #     self.writeoff_amount = writeoff_amount
    #     self.keepopen_amount = keepopen_amount

    # @api.one
    # @api.depends(
    #     'voucher_ids',
    #     'voucher_ids.received_third_check_ids',
    #     'voucher_ids.issued_check_ids',
    #     'voucher_ids.delivered_third_check_ids',
    # )
    # def get_checks(self):
    #     '''TODO mejorar y ver si no hay un cheque duplicado
    #     (Se pueden usar los conjuntos con set)
    #     '''
    #     self.check_ids = self.env['account.check']
    #     check_ids = []
    #     for voucher in self.voucher_ids:
    #         check_ids.extend(voucher.received_third_check_ids.ids)
    #         check_ids.extend(voucher.issued_check_ids.ids)
    #         check_ids.extend(voucher.delivered_third_check_ids.ids)
    #     print 'check_ids', check_ids
    #     self.check_ids = check_ids

    # @api.one
    # @api.depends(
    #     'voucher_ids',
    #     'voucher_ids.move_ids',
    #     'voucher_ids.line_cr_ids',
    #     'voucher_ids.line_dr_ids',
    # )
    # def get_moves(self):
    #     '''
    #     '''
    #     self.move_line_ids = self.env['account.move.line']
    #     self.line_dr_ids = self.env['account.voucher.line']
    #     self.line_cr_ids = self.env['account.voucher.line']
    #     move_line_ids = []
    #     line_dr_ids = []
    #     line_cr_ids = []
    #     for voucher in self.voucher_ids:
    #         move_line_ids.extend(voucher.move_ids.ids)

    #         line_dr_ids.extend(
    #             [x.id for x in voucher.line_dr_ids if x.amount != 0.0])

    #         line_cr_ids.extend(
    #             [x.id for x in voucher.line_cr_ids if x.amount != 0.0])

    #     self.move_line_ids = move_line_ids
    #     self.line_dr_ids = line_dr_ids
    #     self.line_cr_ids = line_cr_ids

    # @api.multi
    # def get_consolidated_moves(self):
    #     '''Devuelve un vector con vectores con browse de los moves
    #     y balances pagados
    #     '''
    #     ret = []
    #     move_dr_ids = []
    #     move_cr_ids = []
    #     for voucher in self.voucher_ids:
    #         move_dr_ids.extend(
    #             [x.move_line_id.id for x in voucher.line_dr_ids if x.amount != 0.0])
    #         move_cr_ids.extend(
    #             [x.move_line_id.id for x in voucher.line_cr_ids if x.amount != 0.0])
    #     move_ids = set(move_dr_ids) | set(move_cr_ids)
    #     for move_id in move_ids:
    #         domain = [
    #             ('move_line_id', '=', move_id),
    #             ('voucher_id', 'in', self.voucher_ids.ids)]
    #         cr_move_voucher_lines = self.env['account.voucher.line'].search(
    #             domain + [('type', '=', 'cr')])
    #         dr_move_voucher_lines = self.env['account.voucher.line'].search(
    #             domain + [('type', '=', 'dr')])
    #         cr_move_voucher_lines_amounts = [
    #             x.amount for x in cr_move_voucher_lines]
    #         dr_move_voucher_lines_amounts = [
    #             x.amount for x in dr_move_voucher_lines]
    #         paid = sum(cr_move_voucher_lines_amounts) - \
    #             sum(dr_move_voucher_lines_amounts)
    #         ret.append([self.env['account.move.line'].browse(move_id), paid])
    #     return ret

    # def receipt_send_rfq(self, cr, uid, ids, context=None):
    #     '''
    #     This function opens a window to compose an email, with the edi receipt template message loaded by default
    #     '''
    #     assert len(ids) == 1, 'This option should only be used for a single id at a time.'
    #     ir_model_data = self.pool.get('ir.model.data')
    #     try:
    #         template_id = ir_model_data.get_object_reference(cr, uid, 'report_extended_voucher_receipt', 'email_template_edi_receipt')[1]
    #     except ValueError:
    #         template_id = False
    #     try:
    #         compose_form_id = ir_model_data.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
    #     except ValueError:
    #         compose_form_id = False 
    #     ctx = dict()
    #     ctx.update({
    #         'default_model': 'account.voucher.receipt',
    #         'default_res_id': ids[0],
    #         'default_use_template': bool(template_id),
    #         'default_template_id': template_id,
    #         'default_composition_mode': 'comment',
    #         'mark_so_as_sent': True
    #     })
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'view_type': 'form',
    #         'view_mode': 'form',
    #         'res_model': 'mail.compose.message',
    #         'views': [(compose_form_id, 'form')],
    #         'view_id': compose_form_id,
    #         'target': 'new',
    #         'context': ctx,
    #     }
