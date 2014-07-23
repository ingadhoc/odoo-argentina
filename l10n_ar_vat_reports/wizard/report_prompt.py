import io
import os
import xmlrpclib
import base64
import time
from lxml import etree

from datetime import date, datetime
import pytz

from osv import osv, fields

from dateutil.relativedelta import relativedelta

from tools import config
from tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from tools.translate import _

from pentaho_reports.core import DEFAULT_OUTPUT_TYPE

model = 'account.invoice'
report_name = 'account_invoice_vat_report'
def get_date_length(date_format=DEFAULT_SERVER_DATE_FORMAT):
    return len((datetime.now()).strftime(date_format))

class account_invoice_vat_report(osv.osv_memory):

    _name = "account.invoice.vat.report"
    _description = "Account Invoice VAT Report"

    _columns = {
                'output_type' : fields.selection([('pdf', 'Portable Document (pdf)'),('xls', 'Excel Spreadsheet (xls)'),('csv', 'Comma Separated Values (csv)'),\
                                                  ('rtf', 'Rich Text (rtf)'), ('html', 'HyperText (html)'), ('txt', 'Plain Text (txt)')],\
                                                  'Report format', help='Choose the format for the output', required=True),
                'company_id': fields.many2one('res.company', string='Company', readonly=True),
                'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscal Year', help='Keep empty for all open fiscal year'),
                'filter': fields.selection([('filter_no', 'No Filters'), ('filter_date', 'Date'), ('filter_period', 'Periods')], "Filter by", required=True),
                'period_from': fields.many2one('account.period', 'Start Period'),
                'period_to': fields.many2one('account.period', 'End Period'),
                'journal_ids': fields.many2many('account.journal', string='Journals', required=True),
                'date_from': fields.date("Start Date"),
                'date_to': fields.date("End Date"),
                # TODO add group by month functinality, that would be printing different reports for each month, the issue is that we can only reutrn one print. And calling different reports doesn't works
                # 'group_by_month': fields.boolean("Group by Month"),
                'starting_page': fields.integer("Starting Page", required=True),                
                }

    def _get_output_type(self, cr, uid, context=None):
        
        if context is None:
            context = {}
        reports_obj = self.pool.get('ir.actions.report.xml')
        domain = [('report_name','=',report_name)]
        report_id = reports_obj.search(cr, uid, domain, limit=1)
        res = reports_obj.browse(cr, uid, report_id, context=context)[0].pentaho_report_output_type
        return res

    def _get_fiscalyear(self, cr, uid, context=None):
        if context is None:
            context = {}
        now = time.strftime('%Y-%m-%d')
        company_id = False
        ids = context.get('active_ids', [])
        if ids and context.get('active_model') == 'account.account':
            company_id = self.pool.get('account.account').browse(cr, uid, ids[0], context=context).company_id.id
        else:  # use current company id
            company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        domain = [('company_id', '=', company_id), ('date_start', '<', now), ('date_stop', '>', now)]
        fiscalyears = self.pool.get('account.fiscalyear').search(cr, uid, domain, limit=1)
        return fiscalyears and fiscalyears[0] or False

    def _get_all_journal(self, cr, uid, context=None):
        report_type = context.get('report_type', False)
        if report_type == 'sale':
            domain = ['sale', 'sale_refund']
        elif report_type == 'purchase':
            domain = ['purchase', 'purchase_refund']
        else:
            domain = ['sale', 'sale_refund', 'purchase', 'purchase_refund']
        return self.pool.get('account.journal').search(cr, uid ,[('type','in',domain)])

    def onchange_filter(self, cr, uid, ids, filter='filter_no', fiscalyear_id=False, context=None):
        res = {'value': {}}
        if filter == 'filter_no':
            res['value'] = {'period_from': False, 'period_to': False, 'date_from': False ,'date_to': False}
        if filter == 'filter_date':
            # res['value'] = {'period_from': False, 'period_to': False, 'date_from': time.strftime('%Y-01-01'), 'date_to': time.strftime('%Y-%m-%d')}
            res['value'] = {'period_from': False, 'period_to': False, 'date_from': datetime.strftime(date.today() + relativedelta(months=-1), '%Y-%m-01'), 'date_to': datetime.strftime(date.today() + relativedelta(day=1, days=-1), '%Y-%m-%d')}

        if filter == 'filter_period' and fiscalyear_id:
            start_period = end_period = False
            cr.execute('''
                SELECT * FROM (SELECT p.id
                               FROM account_period p
                               LEFT JOIN account_fiscalyear f ON (p.fiscalyear_id = f.id)
                               WHERE f.id = %s
                               AND p.special = false
                               ORDER BY p.date_start ASC, p.special ASC
                               LIMIT 1) AS period_start
                UNION ALL
                SELECT * FROM (SELECT p.id
                               FROM account_period p
                               LEFT JOIN account_fiscalyear f ON (p.fiscalyear_id = f.id)
                               WHERE f.id = %s
                               AND p.date_start < NOW()
                               AND p.special = false
                               ORDER BY p.date_stop DESC
                               LIMIT 1) AS period_stop''', (fiscalyear_id, fiscalyear_id))
            periods =  [i[0] for i in cr.fetchall()]
            if periods and len(periods) > 1:
                start_period = periods[0]
                end_period = periods[1]
            res['value'] = {'period_from': start_period, 'period_to': end_period, 'date_from': False, 'date_to': False}
        return res        

    _defaults = {
        'output_type': _get_output_type,
        'fiscalyear_id': _get_fiscalyear,
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'account.invoice',context=c),
        'journal_ids': _get_all_journal,
        'filter': 'filter_date',
        'starting_page': 1,        
    }

    # This function was copied from server report_sxw.py
    def formatLang(self, cr, uid, value, context=None):
        if not str(value):
            return ''

        pool_lang = self.pool.get('res.lang')
        lang = context.get('lang', 'en_US') or 'en_US'
        lang_ids = pool_lang.search(cr,uid,[('code','=',lang)])[0]
        lang_obj = pool_lang.browse(cr,uid,lang_ids)
        date_format = lang_obj.date_format
        parse_format = DEFAULT_SERVER_DATE_FORMAT

        if isinstance(value, basestring):
            # FIXME: the trimming is probably unreliable if format includes day/month names
            #        and those would need to be translated anyway. 
            date = datetime.strptime(value[:get_date_length(parse_format)], parse_format)
        elif isinstance(value, time.struct_time):
            date = datetime(*value[:6])
        else:
            date = datetime(*value.timetuple()[:6])
        return date.strftime(date_format)

    def check_report(self, cr, uid, ids, context=None):

        wizard = self.browse(cr, uid, ids[0], context=context)
        
        if context is None:
            context = {}
        data = {}

        obj_model = self.pool.get(model)
        filters = []

        #Range label (dates or periods)
        range_label = ''

        # Company
        if wizard.company_id:
            filters.append(('company_id','=', wizard.company_id.id))
        # Fiscal year
        if wizard.fiscalyear_id:
            filters.append(('period_id.fiscalyear_id','=', wizard.fiscalyear_id.id))
        
        # # Period From
        if wizard.period_from:
            filters.append(('period_id.id','>=', wizard.period_from.id))
            range_label = 'Periodo ' + wizard.period_from.name

        # # Period From
        if wizard.period_to:
            filters.append(('period_id.id','<=', wizard.period_to.id))
            range_label += ' hasta ' + wizard.period_to.name

        # Journals 
        if wizard.journal_ids:
            filters.append(('journal_id','in', [x.id for x in wizard.journal_ids]))

        # Date From
        if wizard.date_from:
            filters.append(('date_invoice','>=', wizard.date_from))
            range_label = 'Desde ' + self.formatLang(cr, uid, wizard.date_from, context)

        # Date To
        if wizard.date_to:
            filters.append(('date_invoice','<=', wizard.date_to))
            range_label += ' hasta ' + self.formatLang(cr, uid, wizard.date_to, context)

        model_ids = obj_model.search(cr, uid, filters, context=context)

        # Report Description
        report_type = context.get('report_type', False)
        if report_type == 'sale':
            report_description = 'Diario IVA Ventas'
        elif report_type == 'purchase':
            report_description = 'Diario IVA Compras'

        no_data_description = ''
        if not model_ids:
        # We remove this as we want to print it the same way but with a new message
        #     raise osv.except_osv(_('No Data!'),
        #                     _('There is no data for current filters.'))
            no_data_description = 'Sin Movimientos'
        
        company_vat = wizard.company_id.partner_id.printed_vat
        company_name = wizard.company_id.name

        data['ids'] = model_ids
        data['model'] = model
        data['variables'] = {'report_description':report_description,
                            'range_label':range_label,
                            'starting_page' :wizard.starting_page,
                            'no_data_description': no_data_description,
                            'company_name': company_name,
                            'company_vat': company_vat,
                            'report_type':report_type,}
        data['output_type'] = wizard.output_type

        return self._print_report(cr, uid, ids, data, context=context)


    def _print_report(self, cr, uid, ids, data, context=None):

        if context is None:
            context = {}

        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
    }



