# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _


class res_partner(osv.osv):
    _inherit = "res.partner"

    def _get_followup_overdue_query(self, cr, uid, args, overdue_only=False, context=None):
        '''
        This function is used to build the query and arguments to use when making a search on functional fields
            * payment_amount_due
            * payment_amount_overdue
        Basically, the query is exactly the same except that for overdue there is an extra clause in the WHERE.

        :param args: arguments given to the search in the usual domain notation (list of tuples)
        :param overdue_only: option to add the extra argument to filter on overdue accounting entries or not
        :returns: a tuple with
            * the query to execute as first element
            * the arguments for the execution of this query
        :rtype: (string, [])
        '''
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        company_obj = self.pool.get('res.company')
        company_ids = company_obj.search(cr, uid, [('id', 'child_of',company_id)])
        company_ids.append(company_id)

        having_where_clause = ' AND '.join(map(lambda x: '(SUM(bal2) %s %%s)' % (x[1]), args))
        having_values = [x[2] for x in args]
        print 'having_values', having_values
        query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)
        overdue_only_str = overdue_only and 'AND date_maturity <= NOW()' or ''
        return ('''SELECT pid AS partner_id, SUM(bal2) FROM
                    (SELECT CASE WHEN bal IS NOT NULL THEN bal
                    ELSE 0.0 END AS bal2, p.id as pid FROM
                    (SELECT (debit-credit) AS bal, partner_id
                    FROM account_move_line l
                    WHERE account_id IN
                            (SELECT id FROM account_account
                            WHERE type=\'receivable\' AND active)
                    ''' + overdue_only_str + '''
                    AND reconcile_id IS NULL
                    AND company_id in %s
                    AND ''' + query + ''') AS l
                    RIGHT JOIN res_partner p
                    ON p.id = partner_id ) AS pl
                    GROUP BY pid HAVING ''' + having_where_clause, [tuple(company_ids)] + having_values)

    def _payment_earliest_date_search(self, cr, uid, obj, name, args, context=None):
        if not args:
            return []
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        company_obj = self.pool.get('res.company')
        company_ids = company_obj.search(cr, uid, [('id', 'child_of',company_id)])
        company_ids.append(company_id)
        having_where_clause = ' AND '.join(map(lambda x: '(MIN(l.date_maturity) %s %%s)' % (x[1]), args))
        having_values = [x[2] for x in args]
        query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)
        cr.execute('SELECT partner_id FROM account_move_line l '\
                    'WHERE account_id IN '\
                        '(SELECT id FROM account_account '\
                        'WHERE type=\'receivable\' AND active) '\
                    'AND l.company_id in %s '
                    'AND reconcile_id IS NULL '\
                    'AND '+query+' '\
                    'AND partner_id IS NOT NULL '\
                    'GROUP BY partner_id HAVING '+ having_where_clause,
                     [tuple(company_ids)] + having_values)
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
                company_ids = company_obj.search(cr, uid, [('id', 'child_of',company.id)])
                company_ids.append(company.id)
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
            company_id = context.get('company_id', False)
            if not company_id:
                company = self.pool.get('res.company').browse(cr, uid, uid, context=context).company_id
            else:
                company = self.pool.get('res.company').browse(cr, uid, company_id, context=context)
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

    def do_button_print(self, cr, uid, ids, company_id=False, context=None):
        assert(len(ids) == 1)
        if not company_id:
            company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        #search if the partner has accounting entries to print. If not, it may not be present in the
        #psql view the report is based on, so we need to stop the user here.
        if not self.pool.get('account.move.line').search(cr, uid, [
                                                                   ('partner_id', '=', ids[0]),
                                                                   ('account_id.type', '=', 'receivable'),
                                                                   ('reconcile_id', '=', False),
                                                                   ('state', '!=', 'draft'),
                                                                   ('company_id', '=', company_id),
                                                                  ], context=context):
            raise osv.except_osv(_('Error!'),_("The partner does not have any accounting entries to print in the overdue report for the current company."))
        self.message_post(cr, uid, [ids[0]], body=_('Printed overdue payments report'), context=context)
        #build the id of this partner in the psql view. Could be replaced by a search with [('company_id', '=', company_id),('partner_id', '=', ids[0])]
        wizard_partner_ids = [ids[0] * 10000 + company_id]
        followup_ids = self.pool.get('account_followup.followup').search(cr, uid, [('company_id', '=', company_id)], context=context)
        if not followup_ids:
            raise osv.except_osv(_('Error!'),_("There is no followup plan defined for the current company."))
        data = {
            'date': fields.date.today(),
            'followup_id': followup_ids[0],
        }
        #call the print overdue report on this partner
        return self.do_partner_print(cr, uid, wizard_partner_ids, data, context=context)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
