# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _


class res_partner(osv.osv):
    _inherit = "res.partner"

    def _payment_earliest_date_search(self, cr, uid, obj, name, args, context=None):
        if not args:
            return []
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        having_where_clause = ' AND '.join(map(lambda x: '(MIN(l.date_maturity) %s %%s)' % (x[1]), args))
        having_values = [x[2] for x in args]
        query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)
        cr.execute('SELECT partner_id FROM account_move_line l '\
                    'WHERE account_id IN '\
                        '(SELECT id FROM account_account '\
                        'WHERE type=\'receivable\' AND active) '\
                    'AND l.company_id = %s '
                    'AND reconcile_id IS NULL '\
                    'AND '+query+' '\
                    'AND partner_id IS NOT NULL '\
                    'GROUP BY partner_id HAVING '+ having_where_clause,
                     [company_id] + having_values)
        res = cr.fetchall()
        if not res:
            return [('id','=','0')]
        return [('id','in', [x[0] for x in res])]
    
    def _payment_due_search(self, cr, uid, obj, name, args, context=None):
        if not args:
            return []
        query, query_args = self._get_followup_overdue_query(cr, uid, args, overdue_only=False, context=context)
        cr.execute(query, query_args)
        res = cr.fetchall()
        if not res:
            return [('id','=','0')]
        return [('id','in', [x[0] for x in res])]

    def _payment_overdue_search(self, cr, uid, obj, name, args, context=None):
        if not args:
            return []
        query, query_args = self._get_followup_overdue_query(cr, uid, args, overdue_only=True, context=context)
        cr.execute(query, query_args)
        res = cr.fetchall()
        if not res:
            return [('id','=','0')]
        return [('id','in', [x[0] for x in res])]

    def _get_amounts_and_date(self, cr, uid, ids, name, arg, context=None):
            
        res = {}
        company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
        company_obj=self.pool.get('res.company')
        current_date = fields.date.context_today(self, cr, uid, context=context)
        for partner in self.browse(cr, uid, ids, context=context):
            worst_due_date = False
            amount_due = amount_overdue = 0.0
            for aml in partner.unreconciled_aml_ids:
                company_ids = company_obj.search(cr, uid, [('id', 'child_of',aml.company_id.id)])
                company_ids.append(aml.company_id.id) 
                if (aml.company_id.id in company_ids):
                    date_maturity = aml.date_maturity or aml.date
                    if not worst_due_date or date_maturity < worst_due_date:
                        worst_due_date = date_maturity
                    amount_due += aml.result
                    if (date_maturity <= current_date):
                        amount_overdue += aml.result
            res[partner.id] = {'payment_amount_due': amount_due, 
                                'payment_amount_overdue': amount_overdue, 
                                'payment_earliest_due_date': worst_due_date}
        return res

    _columns = {
        'payment_amount_due':fields.function(_get_amounts_and_date, 
                                                 type='float', string="Amount Due",
                                                 store = False, multi="followup", 
                                                 fnct_search=_payment_due_search),
        'payment_amount_overdue':fields.function(_get_amounts_and_date,
                                                 type='float', string="Amount Overdue",
                                                 store = False, multi="followup", 
                                                 fnct_search = _payment_overdue_search),
        'payment_earliest_due_date':fields.function(_get_amounts_and_date,
                                                    type='date',
                                                    string = "Worst Due Date",
                                                    multi="followup",
                                                    fnct_search=_payment_earliest_date_search),



    }

    def get_followup_table_html(self, cr, uid, ids, context=None):
        """ Build the html tables to be included in emails send to partners,
            when reminding them their overdue invoices.
            :param ids: [id] of the partner for whom we are building the tables
            :rtype: string
        """
        import account_followup_print

        assert len(ids) == 1
        if context is None:
            context = {}
        partner = self.browse(cr, uid, ids[0], context=context)
        #copy the context to not change global context. Overwrite it because _() looks for the lang in local variable 'context'.
        #Set the language to use = the partner language
        context = dict(context, lang=partner.lang)
        followup_table = ''
        if partner.unreconciled_aml_ids:
            company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
            current_date = fields.date.context_today(self, cr, uid, context=context)
            rml_parse = account_followup_print.report_rappel(cr, uid, "followup_rml_parser")
            final_res = rml_parse._lines_get_with_partner(partner, company.id)

            for currency_dict in final_res:
                currency = currency_dict.get('line', [{'currency_id': company.currency_id}])[0]['currency_id']
                followup_table += '''
                <table border="2" width=100%%>
                <tr>
                    <td>''' + _("Invoice Date") + '''</td>
                    <td>''' + _("Document Number") + '''</td>
                    <td>''' + _("Reference") + '''</td>
                    <td>''' + _("Due Date") + '''</td>
                    <td>''' + _("Amount") + " (%s)" % (currency.symbol) + '''</td>
                    <td>''' + _("Lit.") + '''</td>
                </tr>
                ''' 
                total = 0
                for aml in currency_dict['line']:
                    block = aml['blocked'] and 'X' or ' '
                    total += aml['balance']
                    strbegin = "<TD>"
                    strend = "</TD>"
                    date = aml['date_maturity'] or aml['date']
                    if date <= current_date and aml['balance'] > 0:
                        strbegin = "<TD><B>"
                        strend = "</B></TD>"
                    followup_table +="<TR>" + strbegin + str(aml['date']) + strend + strbegin + aml['document_number'] + strend + strbegin + (aml['ref'] or '') + strend + strbegin + str(date) + strend + strbegin + str(aml['balance']) + strend + strbegin + block + strend + "</TR>"

                total = reduce(lambda x, y: x+y['balance'], currency_dict['line'], 0.00)

                total = rml_parse.formatLang(total, dp='Account', currency_obj=currency)
                followup_table += '''<tr> </tr>
                                </table>
                                <center>''' + _("Amount due") + ''' : %s </center>''' % (total)
        return followup_table

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
