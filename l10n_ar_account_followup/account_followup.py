# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _


class res_partner(osv.osv):
    _inherit = "res.partner"

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
