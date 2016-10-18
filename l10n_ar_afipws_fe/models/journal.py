# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api, fields, _
import logging
from openerp.exceptions import UserError
_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    _afip_ws_selection = (
        lambda self, *args, **kwargs: self._get_afip_ws_selection(
            *args, **kwargs))

    @api.model
    def _get_afip_ws_selection(self):
        return [
            ('wsfe', 'Mercado interno -sin detalle- RG2485 (WSFEv1)'),
            ('wsmtxca', 'Mercado interno -con detalle- RG2904 (WSMTXCA)'),
            ('wsfex', 'Exportación -con detalle- RG2758 (WSFEXv1)'),
            ('wsbfe', 'Bono Fiscal -con detalle- RG2557 (WSBFE)'),
        ]

    afip_ws = fields.Selection(
        _afip_ws_selection,
        'AFIP WS',
    )

    @api.model
    def create(self, vals):
        journal = super(AccountJournal, self).create(vals)
        if journal.point_of_sale_type == 'electronic' and journal.afip_ws:
            try:
                journal.sync_document_local_remote_number()
            except:
                _logger.info(
                    'Could not sincronize local and remote numbers')
        return journal

    @api.model
    def _get_point_of_sale_types(self):
        types = super(AccountJournal, self)._get_point_of_sale_types()
        types.append(['electronic', _('Electronic')])
        return types

    @api.one
    @api.constrains('point_of_sale_type', 'afip_ws')
    def check_afip_ws_and_type(self):
        if self.point_of_sale_type != 'electronic' and self.afip_ws:
            raise UserError(_(
                'You can only use an AFIP WS if type is "Electronic"'))

    @api.multi
    def get_journal_letter(self, counterpart_partner=False):
        """Function to be inherited by afip ws fe"""
        letters = super(AccountJournal, self).get_journal_letter()
        # filter only for sales journals

        if self.type != 'sale':
            return letters
        if self.afip_ws == 'wsfe':
            letters = letters.filtered(
                lambda r: r.name != 'E')
        elif self.afip_ws == 'wsfex':
            letters = letters.filtered(
                lambda r: r.name == 'E')
        return letters

    @api.multi
    def sync_document_local_remote_number(self):
        if self.type != 'sale':
            return True
        for journal_document_type in self.journal_document_type_ids:
            next_by_ws = int(
                journal_document_type.get_pyafipws_last_invoice(
                )['result']) + 1
            journal_document_type.sequence_id.number_next_actual = next_by_ws

    @api.multi
    def check_document_local_remote_number(self):
        msg = ''
        if self.type != 'sale':
            return True
        for journal_document_type in self.journal_document_type_ids:
            next_by_ws = int(
                journal_document_type.get_pyafipws_last_invoice(
                )['result']) + 1
            next_by_seq = journal_document_type.sequence_id.number_next_actual
            if next_by_ws != next_by_seq:
                msg += _(
                    '* Document Type %s, Local %i, Remote %i\n' % (
                        journal_document_type.document_type_id.name,
                        next_by_seq,
                        next_by_ws))
        if msg:
            msg = _('There are some doument desynchronized:\n') + msg
            raise UserError(msg)
        else:
            raise UserError(_('All documents are synchronized'))

    @api.multi
    def test_pyafipws_dummy(self):
        """
        AFIP Description: Método Dummy para verificación de funcionamiento de
        infraestructura (FEDummy)
        """
        self.ensure_one()
        afip_ws = self.afip_ws
        if not afip_ws:
            raise UserError(_('No AFIP WS selected'))
        ws = self.company_id.get_connection(afip_ws).connect()
        ws.Dummy()
        title = _("AFIP service %s\n") % afip_ws
        msg = (
            "AppServerStatus: %s DbServerStatus: %s AuthServerStatus: %s" % (
                ws.AppServerStatus,
                ws.DbServerStatus,
                ws.AuthServerStatus))
        raise UserError(title + msg)

    @api.multi
    def test_pyafipws_point_of_sales(self):
        self.ensure_one()
        afip_ws = self.afip_ws
        if not afip_ws:
            raise UserError(_('No AFIP WS selected'))
        ws = self.company_id.get_connection(afip_ws).connect()
        if afip_ws == 'wsfex':
            ret = ws.GetParamPtosVenta()
        else:
            ret = ws.ParamGetPtosVenta(sep=" ")
        msg = (_(" %s %s") % (
            '. '.join(ret), " - ".join([ws.Excepcion, ws.ErrMsg, ws.Obs])))
        title = _('Enabled Point Of Sales on AFIP\n')
        raise UserError(title + msg)

    @api.multi
    def get_pyafipws_cuit_document_classes(self):
        self.ensure_one()
        afip_ws = self.afip_ws
        if not afip_ws:
            raise UserError(_('No AFIP WS selected'))
        ws = self.company_id.get_connection(afip_ws).connect()
        if afip_ws == 'wsfex':
            ret = ws.GetParamTipoCbte(sep=",")
        else:
            ret = ws.ParamGetTiposCbte(sep=",")
        msg = (_(
            "Authorized Document Clases on AFIP\n%s\n. \nObservations: %s") % (
            '\n '.join(ret), ".\n".join([ws.Excepcion, ws.ErrMsg, ws.Obs])))
        raise UserError(msg)

    @api.multi
    def get_pyafipws_currencies(self):
        self.ensure_one()
        return self.env['res.currency'].get_pyafipws_currencies(
            afip_ws=self.afip_ws, company=self.company_id)

    @api.multi
    def action_get_connection(self):
        self.ensure_one()
        afip_ws = self.afip_ws
        if not afip_ws:
            raise UserError(_('No AFIP WS selected'))
        self.company_id.get_connection(afip_ws).connect()

    @api.multi
    def get_pyafipws_currency_rate(self, currency):
        raise UserError(currency.get_pyafipws_currency_rate(
            afip_ws=self.afip_ws,
            company=self.company_id,
        )[1])
