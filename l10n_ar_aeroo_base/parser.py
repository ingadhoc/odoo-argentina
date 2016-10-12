from openerp.report.report_sxw import rml_parse


class Parser(rml_parse):

    def __init__(self, cr, uid, name, context):
        super(self.__class__, self).__init__(cr, uid, name, context)
