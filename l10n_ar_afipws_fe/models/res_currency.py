# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api, _
from openerp.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ResCurrency(models.Model):
    _inherit = "res.currency"

    @api.multi
    def action_get_pyafipws_currencies(self):
        return self.get_pyafipws_currencies()

    @api.model
    def get_pyafipws_currencies(self, afip_ws='wsfex', company=False):
        # if not company, then we search one that uses argentinian localization
        if not company:
            company = self.env['res.company'].search(
                [('localization', '=', 'argentina')],
                limit=1)
        if not company:
            raise UserError(_(
                'No company found using argentinian localization'))

        ws = company.get_connection(afip_ws).connect()

        if afip_ws == 'wsfex':
            ret = ws.GetParamMon(sep=" ")
        elif afip_ws == 'wsfe':
            ret = ws.ParamGetTiposMonedas(sep=" ")
        else:
            raise UserError(_('AFIP WS %s not implemented') % (
                afip_ws))
        msg = (_("Authorized Currencies on AFIP%s\n. \nObservations: %s") % (
            '\n '.join(ret), ".\n".join([ws.Excepcion, ws.ErrMsg, ws.Obs])))
        raise UserError(msg)

    @api.multi
    def action_get_pyafipws_currency_rate(self):
        raise UserError(self.get_pyafipws_currency_rate()[1])

    @api.multi
    def get_pyafipws_currency_rate(self, afip_ws='wsfex', company=False):
        self.ensure_one()
        # if not company, then we search one that uses argentinian localization
        if not company:
            company = self.env['res.company'].search(
                [('localization', '=', 'argentina')],
                limit=1)
        if not company:
            raise UserError(_(
                'No company found using argentinian localization'))

        if not self.afip_code:
            raise UserError(_('No AFIP code for currency %s') % self.name)

        ws = company.get_connection(afip_ws).connect()

        if afip_ws == "wsfex":
            rate = ws.GetParamCtz(self.afip_code)
        else:
            raise UserError(_('AFIP WS %s not implemented') % (
                afip_ws))
        msg = (_("Currency rate for %s: %s.\nObservations: %s") % (
            self.name, rate, ".\n".join([ws.Excepcion, ws.ErrMsg, ws.Obs])))

        return (float(rate), msg)
