# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (C) 2012 OpenERP - Team de Localización Argentina.
# https://launchpad.net/~openerp-l10n-ar-localization
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import time
from lxml import etree
import decimal_precision as dp
import netsvc
import pooler
from osv import fields, osv, orm
from tools.translate import _
import logging



class account_invoice(osv.osv):
    _name = 'account.invoice'
    _inherit = 'account.invoice'
    _description = 'Account Invoice Debit Note'

    _columns = {
        'type': fields.selection([
            ('out_invoice', 'Customer Invoice'),
            ('in_invoice', 'Supplier Invoice'),
            ('out_refund', 'Customer Refund'),
            ('in_refund', 'Supplier Refund'),
            ('in_debit', 'Supplier Debit Note'),  # Added
            ('out_debit', 'Client Debit Note'),  # Added
            ], 'Type', readonly=True, select=True),  # Modified
    }

    # Modified
    def _get_analytic_lines(self, cr, uid, id,context=None):
        if context is None:
            context = {}
            
        inv = self.browse(cr, uid, id)
        cur_obj = self.pool.get('res.currency')

        company_currency = inv.company_id.currency_id.id
        if inv.type in ('out_invoice', 'in_refund'):
            sign = 1
        else:
            sign = -1

        iml = self.pool.get('account.invoice.line').move_line_get(cr, uid, inv.id,context=context)
        for il in iml:
            if il['account_analytic_id']:
                if inv.type in ('in_invoice', 'in_refund', 'in_debit'):  # Modified
                    ref = inv.reference
                else:
                    ref = self._convert_ref(cr, uid, inv.number)
                if not inv.journal_id.analytic_journal_id:
                    raise osv.except_osv(_('No Analytic Journal !'),_("You have to define an analytic journal on the '%s' journal!") % (inv.journal_id.name,))
                il['analytic_lines'] = [(0,0, {
                    'name': il['name'],
                    'date': inv['date_invoice'],
                    'account_id': il['account_analytic_id'],
                    'unit_amount': il['quantity'],
                    'amount': cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, il['price'], context={'date': inv.date_invoice}) * sign,
                    'product_id': il['product_id'],
                    'product_uom_id': il['uos_id'],
                    'general_account_id': il['account_id'],
                    'journal_id': inv.journal_id.analytic_journal_id.id,
                    'ref': ref,
                })]
        return iml

    # Modified
    def _get_journal(self, cr, uid, context=None):
        if context is None:
            context = {}
        type_inv = context.get('type', 'out_invoice')
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        company_id = context.get('company_id', user.company_id.id)
        type2journal = {'out_invoice': 'sale', 'out_debit': 'sale', 'in_invoice': 'purchase', 'in_debit': 'purchase', 'out_refund': 'sale_refund', 'in_refund': 'purchase_refund'}  # Modified
        refund_journal = {'out_invoice': False, 'out_debit': False, 'in_invoice': False, 'in_debit': False, 'out_refund': True, 'in_refund': True}  # Modified
        journal_obj = self.pool.get('account.journal')
        res = journal_obj.search(cr, uid, [('type', '=', type2journal.get(type_inv, 'sale')),
                                            ('company_id', '=', company_id)],
                                          #  ('refund_journal', '=', refund_journal.get(type_inv, False))],
                                                limit=1)
        return res and res[0] or False  # Modified

    # Modified
    def _get_journal_analytic(self, cr, uid, type_inv, context=None):
        type2journal = {'out_invoice': 'sale', 'out_debit': 'sale', 'in_invoice': 'purchase', 'in_debit': 'purchase', 'out_refund': 'sale', 'in_refund': 'purchase'}  # Modified
        tt = type2journal.get(type_inv, 'sale')
        result = self.pool.get('account.analytic.journal').search(cr, uid, [('type','=',tt)], context=context)
        if not result:
            raise osv.except_osv(_('No Analytic Journal !'),_("You must define an analytic journal of type '%s' !") % (tt,))
        return result and result[0] or False  # Modified

    # Modified
    def onchange_partner_id(self, cr, uid, ids, type, partner_id,\
            date_invoice=False, payment_term=False, partner_bank_id=False, company_id=False):
        invoice_addr_id = False
        contact_addr_id = False
        partner_payment_term = False
        acc_id = False
        bank_id = False
        fiscal_position = False

        opt = [('uid', str(uid))]
        if partner_id:

            opt.insert(0, ('id', partner_id))
            res = self.pool.get('res.partner').address_get(cr, uid, [partner_id], ['contact', 'invoice'])
            contact_addr_id = res['contact']
            invoice_addr_id = res['invoice']
            p = self.pool.get('res.partner').browse(cr, uid, partner_id)
            if company_id:
                if not p.property_account_receivable or not p.property_account_payable:
                    raise osv.except_osv(_('Error!'),
                                         _('You need define you account plan to your company'))

                if p.property_account_receivable.company_id.id != company_id and p.property_account_payable.company_id.id != company_id:
                    property_obj = self.pool.get('ir.property')
                    rec_pro_id = property_obj.search(cr,uid,[('name','=','property_account_receivable'),('res_id','=','res.partner,'+str(partner_id)+''),('company_id','=',company_id)])
                    pay_pro_id = property_obj.search(cr,uid,[('name','=','property_account_payable'),('res_id','=','res.partner,'+str(partner_id)+''),('company_id','=',company_id)])
                    if not rec_pro_id:
                        rec_pro_id = property_obj.search(cr,uid,[('name','=','property_account_receivable'),('company_id','=',company_id)])
                    if not pay_pro_id:
                        pay_pro_id = property_obj.search(cr,uid,[('name','=','property_account_payable'),('company_id','=',company_id)])
                    rec_line_data = property_obj.read(cr,uid,rec_pro_id,['name','value_reference','res_id'])
                    pay_line_data = property_obj.read(cr,uid,pay_pro_id,['name','value_reference','res_id'])
                    rec_res_id = rec_line_data and rec_line_data[0].get('value_reference',False) and int(rec_line_data[0]['value_reference'].split(',')[1]) or False
                    pay_res_id = pay_line_data and pay_line_data[0].get('value_reference',False) and int(pay_line_data[0]['value_reference'].split(',')[1]) or False
                    if not rec_res_id and not pay_res_id:
                        raise osv.except_osv(_('Configuration Error !'),
                            _('Can not find account chart for this company, Please Create account.'))
                    account_obj = self.pool.get('account.account')
                    rec_obj_acc = account_obj.browse(cr, uid, [rec_res_id])
                    pay_obj_acc = account_obj.browse(cr, uid, [pay_res_id])
                    p.property_account_receivable = rec_obj_acc[0]
                    p.property_account_payable = pay_obj_acc[0]

            if type in ('out_invoice', 'out_refund', 'out_debit'):  # Modified
                acc_id = p.property_account_receivable.id
            else:
                acc_id = p.property_account_payable.id
            fiscal_position = p.property_account_position and p.property_account_position.id or False
            partner_payment_term = p.property_payment_term and p.property_payment_term.id or False
            if p.bank_ids:
                bank_id = p.bank_ids[0].id

        result = {'value': {
            'address_contact_id': contact_addr_id,
            'address_invoice_id': invoice_addr_id,
            'account_id': acc_id,
            'payment_term': partner_payment_term,
            'fiscal_position': fiscal_position
            }
        }

        if type in ('in_invoice', 'in_refund', 'in_debit'):  # Modified
            result['value']['partner_bank_id'] = bank_id

        if payment_term != partner_payment_term:
            if partner_payment_term:
                to_update = self.onchange_payment_term_date_invoice(
                    cr, uid, ids, partner_payment_term, date_invoice)
                result['value'].update(to_update['value'])
            else:
                result['value']['date_due'] = False

        if partner_bank_id != bank_id:
            to_update = self.onchange_partner_bank(cr, uid, ids, bank_id)
            result['value'].update(to_update['value'])
        return result

    # Modified
    def onchange_company_id(self, cr, uid, ids, company_id, part_id, type, invoice_line, currency_id):
        val = {}
        dom = {}
        obj_journal = self.pool.get('account.journal')
        account_obj = self.pool.get('account.account')
        inv_line_obj = self.pool.get('account.invoice.line')
        if company_id and part_id and type:
            acc_id = False
            partner_obj = self.pool.get('res.partner').browse(cr,uid,part_id)
            if partner_obj.property_account_payable and partner_obj.property_account_receivable:
                if partner_obj.property_account_payable.company_id.id != company_id and partner_obj.property_account_receivable.company_id.id != company_id:
                    property_obj = self.pool.get('ir.property')
                    rec_pro_id = property_obj.search(cr, uid, [('name','=','property_account_receivable'),('res_id','=','res.partner,'+str(part_id)+''),('company_id','=',company_id)])
                    pay_pro_id = property_obj.search(cr, uid, [('name','=','property_account_payable'),('res_id','=','res.partner,'+str(part_id)+''),('company_id','=',company_id)])
                    if not rec_pro_id:
                        rec_pro_id = property_obj.search(cr, uid, [('name','=','property_account_receivable'),('company_id','=',company_id)])
                    if not pay_pro_id:
                        pay_pro_id = property_obj.search(cr, uid, [('name','=','property_account_payable'),('company_id','=',company_id)])
                    rec_line_data = property_obj.read(cr, uid, rec_pro_id, ['name','value_reference','res_id'])
                    pay_line_data = property_obj.read(cr, uid, pay_pro_id, ['name','value_reference','res_id'])
                    rec_res_id = rec_line_data and rec_line_data[0].get('value_reference',False) and int(rec_line_data[0]['value_reference'].split(',')[1]) or False
                    pay_res_id = pay_line_data and pay_line_data[0].get('value_reference',False) and int(pay_line_data[0]['value_reference'].split(',')[1]) or False
                    if not rec_res_id and not pay_res_id:
                        raise osv.except_osv(_('Configuration Error !'),
                            _('Can not find account chart for this company, Please Create account.'))
                    if type in ('out_invoice', 'out_refund'):
                        acc_id = rec_res_id
                    else:
                        acc_id = pay_res_id
                    val= {'account_id': acc_id}
            if ids:
                if company_id:
                    inv_obj = self.browse(cr,uid,ids)
                    for line in inv_obj[0].invoice_line:
                        if line.account_id:
                            if line.account_id.company_id.id != company_id:
                                result_id = account_obj.search(cr, uid, [('name','=',line.account_id.name),('company_id','=',company_id)])
                                if not result_id:
                                    raise osv.except_osv(_('Configuration Error !'),
                                        _('Can not find account chart for this company in invoice line account, Please Create account.'))
                               # inv_line_obj.write(cr, uid, [line.id], {'account_id': result_id[0]}) SIL
                                inv_line_obj.write(cr, uid, [line.id], {'account_id': result_id[-1]})
            else:
                if invoice_line:
                    for inv_line in invoice_line:
                        obj_l = account_obj.browse(cr, uid, inv_line[2]['account_id'])
                        if obj_l.company_id.id != company_id:
                            raise osv.except_osv(_('Configuration Error !'),
                                _('Invoice line account company does not match with invoice company.'))
                        else:
                            continue
        if company_id and type:
            if type in ('out_invoice', 'out_debit'):  # Modified
                journal_type = 'sale'
            elif type in ('out_refund'):
                journal_type = 'sale_refund'
            elif type in ('in_refund', 'in_debit'):  # Modified
                journal_type = 'purchase_refund'
            else:
                journal_type = 'purchase'
            journal_ids = obj_journal.search(cr, uid, [('company_id','=',company_id), ('type', '=', journal_type)])
            if journal_ids:
                val['journal_id'] = journal_ids[0]
            res_journal_default = self.pool.get('ir.values').get(cr, uid, 'default', 'type=%s' % (type), ['account.invoice'])
            for r in res_journal_default:
                if r[1] == 'journal_id' and r[2] in journal_ids:
                    val['journal_id'] = r[2]
            if not val.get('journal_id', False):
                raise osv.except_osv(_('Configuration Error !'), (_('Can\'t find any account journal of %s type for this company.\n\nYou can create one in the menu: \nConfiguration\Financial Accounting\Accounts\Journals.') % (journal_type)))
            dom = {'journal_id':  [('id', 'in', journal_ids)]}
        else:
            journal_ids = obj_journal.search(cr, uid, [])

        if currency_id and company_id:
            currency = self.pool.get('res.currency').browse(cr, uid, currency_id)
            if currency.company_id and currency.company_id.id != company_id:
                val['currency_id'] = False
            else:
                val['currency_id'] = currency.id
        if company_id:
            company = self.pool.get('res.company').browse(cr, uid, company_id)
            if company.currency_id.company_id and company.currency_id.company_id.id != company_id:
                val['currency_id'] = False
            else:
                val['currency_id'] = company.currency_id.id
        return {'value': val, 'domain': dom}

    # Modified
    def action_move_create(self, cr, uid, ids,context=None):
        """Creates invoice related analytics and financial move lines"""
        ait_obj = self.pool.get('account.invoice.tax')
        cur_obj = self.pool.get('res.currency')
        period_obj = self.pool.get('account.period')
        payment_term_obj = self.pool.get('account.payment.term')
        journal_obj = self.pool.get('account.journal')
        move_obj = self.pool.get('account.move')
        if context is None:
            context = {}
        for inv in self.browse(cr, uid, ids,context=context):
            if not inv.journal_id.sequence_id:
                raise osv.except_osv(_('Error !'), _('Please define sequence on invoice journal'))
            if not inv.invoice_line:
                raise osv.except_osv(_('No Invoice Lines !'), _('Please create some invoice lines.'))
            if inv.move_id:
                continue
            ctx = context.copy()
            ctx.update({'lang': inv.partner_id.lang})

            if not inv.date_invoice:
                self.write(cr, uid, [inv.id], {'date_invoice': fields.date.context_today(self,cr,uid,context=context)}, context=ctx)
            company_currency = inv.company_id.currency_id.id
            # create the analytical lines
            # one move line per invoice line
            iml = self._get_analytic_lines(cr, uid, inv.id,context=ctx)
            # check if taxes are all computed
            ctx = context.copy()
            ctx.update({'lang': inv.partner_id.lang})
            compute_taxes = ait_obj.compute(cr, uid, inv.id, context=ctx)
            self.check_tax_lines(cr, uid, inv, compute_taxes, ait_obj)

           # SIL  if inv.type in ('in_invoice', 'in_refund', 'in_debit') and abs(inv.check_total - inv.amount_total) >= (inv.currency_id.rounding/2.0):  # Modified
           #     raise osv.except_osv(_('Bad total !'), _('Please verify the price of the invoice !\nThe real total does not match the computed total.'))

            if inv.payment_term:
                total_fixed = total_percent = 0
                for line in inv.payment_term.line_ids:
                    if line.value == 'fixed':
                        total_fixed += line.value_amount
                    if line.value == 'procent':
                        total_percent += line.value_amount
                total_fixed = (total_fixed * 100) / (inv.amount_total or 1.0)
                if (total_fixed + total_percent) > 100:
                    raise osv.except_osv(_('Error !'), _("Cannot create the invoice !\nThe payment term defined gives a computed amount greater than the total invoiced amount."))

            # one move line per tax line
            iml += ait_obj.move_line_get(cr, uid, inv.id)

            entry_type = ''
            if inv.type in ('in_invoice', 'in_refund', 'in_debit'):  # Modified
                ref = inv.reference
                entry_type = 'journal_pur_voucher'
                if inv.type == 'in_refund':
                    entry_type = 'cont_voucher'
            else:
                ref = self._convert_ref(cr, uid, inv.number)
                entry_type = 'journal_sale_vou'
                if inv.type == 'out_refund':
                    entry_type = 'cont_voucher'

            diff_currency_p = inv.currency_id.id <> company_currency
            # create one move line for the total and possibly adjust the other lines amount
            total = 0
            total_currency = 0
            total, total_currency, iml = self.compute_invoice_totals(cr, uid, inv, company_currency, ref, iml)
            acc_id = inv.account_id.id

            name = inv['name'] or '/'
            totlines = False
            if inv.payment_term:
                totlines = payment_term_obj.compute(cr,uid, inv.payment_term.id, total, inv.date_invoice or False, context=ctx)
            if totlines:
                res_amount_currency = total_currency
                i = 0
                ctx.update({'date': inv.date_invoice})
                for t in totlines:
                    if inv.currency_id.id != company_currency:
                        amount_currency = cur_obj.compute(cr, uid, company_currency, inv.currency_id.id, t[1], context=ctx)
                    else:
                        amount_currency = False

                    # last line add the diff
                    res_amount_currency -= amount_currency or 0
                    i += 1
                    if i == len(totlines):
                        amount_currency += res_amount_currency

                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': t[1],
                        'account_id': acc_id,
                        'date_maturity': t[0],
                        'amount_currency': diff_currency_p \
                                and  amount_currency or False,
                        'currency_id': diff_currency_p \
                                and inv.currency_id.id or False,
                        'ref': ref,
                    })
            else:
                iml.append({
                    'type': 'dest',
                    'name': name,
                    'price': total,
                    'account_id': acc_id,
                    'date_maturity': inv.date_due or False,
                    'amount_currency': diff_currency_p \
                            and total_currency or False,
                    'currency_id': diff_currency_p \
                            and inv.currency_id.id or False,
                    'ref': ref
            })

            date = inv.date_invoice or time.strftime('%Y-%m-%d')
            part = inv.partner_id.id

            line = map(lambda x:(0,0,self.line_get_convert(cr, uid, x, part, date, context=ctx)),iml)

            line = self.group_lines(cr, uid, iml, line, inv)

            journal_id = inv.journal_id.id
            journal = self.pool.get('account.journal').browse(cr, uid, journal_id,context=ctx)
            if journal.centralisation:
                raise osv.except_osv(_('UserError'),
                        _('Cannot create invoice move on centralised journal'))

            line = self.finalize_invoice_move_lines(cr, uid, inv, line)

            move = {
                'ref': inv.reference and inv.reference or inv.name,
                'line_id': line,
                'journal_id': journal_id,
                'date': date,
                'type': entry_type,
                'narration':inv.comment
            }
            period_id = inv.period_id and inv.period_id.id or False
            if not period_id:
                period_ids = self.pool.get('account.period').search(cr, uid, [('date_start','<=',inv.date_invoice or time.strftime('%Y-%m-%d')),('date_stop','>=',inv.date_invoice or time.strftime('%Y-%m-%d')), ('company_id', '=', inv.company_id.id)])
                if period_ids:
                    period_id = period_ids[0]
            if period_id:
                move['period_id'] = period_id
                for i in line:
                    i[2]['period_id'] = period_id

            move_id = move_obj.create(cr, uid, move, context=ctx)
            new_move_name = move_obj.browse(cr, uid, move_id, context=ctx).name
            # make the invoice point to that move
            self.write(cr, uid, [inv.id], {'move_id': move_id,'period_id':period_id, 'move_name':new_move_name}, context=ctx)
            # Pass invoice in context in method post: used if you want to get the same
            # account move reference when creating the same invoice after a cancelled one:
            ctx.update({'invoice':inv})
            move_obj.post(cr, uid, [move_id], context=ctx)
        self._log_event(cr, uid, ids)
        return True

    # Modified
    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        if context is None:
            context = {}
        journal_obj = self.pool.get('account.journal')

        if context.get('active_model', '') in ['res.partner'] and context.get('active_ids', False) and context['active_ids']:
            partner = self.pool.get(context['active_model']).read(cr, uid, context['active_ids'], ['supplier','customer'])[0]
            if not view_type:
                view_id = self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'account.invoice.tree')])
                view_type = 'tree'
            if view_type == 'form':
                if partner['supplier'] and not partner['customer']:
                    view_id = self.pool.get('ir.ui.view').search(cr,uid,[('name', '=', 'account.invoice.supplier.form')])
                else:
                    view_id = self.pool.get('ir.ui.view').search(cr,uid,[('name', '=', 'account.invoice.form')])
        if view_id and isinstance(view_id, (list, tuple)):
            view_id = view_id[0]
        res = super(account_invoice,self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)

        type = context.get('journal_type', 'sale')
        for field in res['fields']:
            if field == 'journal_id':
                journal_select = journal_obj._name_search(cr, uid, '', [('type', '=', type)], context=context, limit=None, name_get_uid=1)
                res['fields'][field]['selection'] = journal_select

        if view_type == 'tree':
            doc = etree.XML(res['arch'])
            nodes = doc.xpath("//field[@name='partner_id']")
            partner_string = _('Customer')
            if context.get('type', 'out_invoice') in ('in_invoice', 'in_refund', 'in_debit'):  # Modified
                partner_string = _('Supplier')
            for node in nodes:
                node.set('string', partner_string)
            res['arch'] = etree.tostring(doc)
        return res

    # Modified
    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        try:
            res = super(account_invoice, self).create(cr, uid, vals, context)
            for inv_id, name in self.name_get(cr, uid, [res], context=context):
                ctx = context.copy()
                if vals.get('type', 'in_invoice') in ('out_invoice', 'out_refund', 'out_debit'):  # Modified
                    ctx = self.get_log_context(cr, uid, context=ctx)
                message = _("Invoice '%s' is waiting for validation.") % name
                self.log(cr, uid, inv_id, message, context=ctx)
            return res
        except Exception, e:
            if '"journal_id" viol' in e.args[0]:
                raise orm.except_orm(_('Configuration Error!'),
                     _('There is no Accounting Journal of type Sale/Purchase defined!'))
            else:
                raise orm.except_orm(_('Unknown Error'), str(e))

    # Modified
    def compute_invoice_totals(self, cr, uid, inv, company_currency, ref, invoice_move_lines):
        total = 0
        total_currency = 0
        cur_obj = self.pool.get('res.currency')
        for i in invoice_move_lines:
            if inv.currency_id.id != company_currency:
                i['currency_id'] = inv.currency_id.id
                i['amount_currency'] = i['price']
                i['price'] = cur_obj.compute(cr, uid, inv.currency_id.id,
                        company_currency, i['price'],
                        context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')})
            else:
                i['amount_currency'] = False
                i['currency_id'] = False
            i['ref'] = ref
            if inv.type in ('out_invoice','in_refund', 'out_debit'):  # Modified
                total += i['price']
                total_currency += i['amount_currency'] or i['price']
                i['price'] = - i['price']
            else:
                total -= i['price']
                total_currency -= i['amount_currency'] or i['price']
        return total, total_currency, invoice_move_lines

    # Modified
    def action_number(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        #TODO: not correct fix but required a frech values before reading it.
        self.write(cr, uid, ids, {})

        for obj_inv in self.browse(cr, uid, ids, context=context):
            id = obj_inv.id
            invtype = obj_inv.type
            number = obj_inv.number
            move_id = obj_inv.move_id and obj_inv.move_id.id or False
            reference = obj_inv.reference or ''

            self.write(cr, uid, ids, {'internal_number':number})

            if invtype in ('in_invoice', 'in_refund', 'in_debit'):  # Modified
                if not reference:
                    ref = self._convert_ref(cr, uid, number)
                else:
                    ref = reference
            else:
                ref = self._convert_ref(cr, uid, number)

            cr.execute('UPDATE account_move SET ref=%s ' \
                    'WHERE id=%s AND (ref is null OR ref = \'\')',
                    (ref, move_id))
            cr.execute('UPDATE account_move_line SET ref=%s ' \
                    'WHERE move_id=%s AND (ref is null OR ref = \'\')',
                    (ref, move_id))
            cr.execute('UPDATE account_analytic_line SET ref=%s ' \
                    'FROM account_move_line ' \
                    'WHERE account_move_line.move_id = %s ' \
                        'AND account_analytic_line.move_id = account_move_line.id',
                        (ref, move_id))

            for inv_id, name in self.name_get(cr, uid, [id]):
                ctx = context.copy()
                if obj_inv.type in ('out_invoice', 'out_refund', 'out_debit'):  # Modified
                    ctx = self.get_log_context(cr, uid, context=ctx)
                message = _('Invoice ') + " '" + name + "' "+ _("is validated.")
                self.log(cr, uid, inv_id, message, context=ctx)
        return True

    # Modified
    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        types = {
                'out_invoice': 'CI: ',
                'in_invoice': 'SI: ',
                'out_refund': 'OR: ',
                'in_refund': 'SR: ',
                'out_debit': 'CD',  # Added
                'in_debit': 'SD',  # Added
                }
        return [(r['id'], (r['number']) or types[r['type']] + (r['name'] or '')) for r in self.read(cr, uid, ids, ['type', 'number', 'name'], context, load='_classic_write')]


    def invoice_pay_customer(self, cr, uid, ids, context=None):
        if not ids: 
            return []
        inv = self.browse(cr, uid, ids[0], context=context)
        return {
            'name':_("Pay Invoice"),
            'view_mode': 'form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'account.voucher',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'domain': '[]',
            'context': {
                'default_partner_id': inv.partner_id.id,
                'default_amount': inv.residual,
                'default_name':inv.name,
                'close_after_process': True,
                'invoice_type':inv.type,
                'invoice_id':inv.id,
                'default_type': inv.type in ('out_invoice','out_refund','out_debit') and 'receipt' or 'payment', # Added
                'type': inv.type in ('out_invoice','out_refund','out_debit') and 'receipt' or 'payment' # Added
                }
        }
        
account_invoice()
