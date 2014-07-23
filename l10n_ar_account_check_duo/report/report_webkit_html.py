import time
from report import report_sxw
from osv import osv


class report_webkit_thirdcheck_html(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(report_webkit_thirdcheck_html, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'cr':cr,
            'uid': uid,
        })
        
report_sxw.report_sxw('report.webkit.account.thirdcheck',
                       'account.third.check', 
                       'addons/l10n_ar_account_check_duo/report/report_webkit_thirdcheck_html.mako',
                       parser=report_webkit_thirdcheck_html)
                       

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
