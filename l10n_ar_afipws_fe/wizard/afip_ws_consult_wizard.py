# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
from openerp.exceptions import Warning


class afip_ws_consult_wizard(models.TransientModel):
    _name = 'afip.ws.consult.wizard'
    _description = 'AFIP WS Consult Wizard'

    number = fields.Integer(
        'Number',
        required=True,
        )

    @api.multi
    def confirm(self):
        self.ensure_one()
        journal_afip_document_class_id = self._context.get('active_id', False)
        if not journal_afip_document_class_id:
            raise Warning(_(
                'No Journal Document Class as active_id on context'))
        journal_doc_class = self.env[
            'account.journal.afip_document_class'].browse(
            journal_afip_document_class_id)
        return journal_doc_class.get_pyafipws_consult_invoice(self.number)
