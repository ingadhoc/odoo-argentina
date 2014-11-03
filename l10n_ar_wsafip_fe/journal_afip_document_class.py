# -*- coding: utf-8 -*-
from openerp import fields, models, api
import logging
import urllib2

_logger = logging.getLogger(__name__)
_schema = logging.getLogger(__name__ + '.schema')


class account_journal_afip_document_class(models.Model):
    _inherit = "account.journal.afip_document_class"

    @api.one
    def _get_afip_state(self):
        conn = self.afip_connection_id
        if not conn:
            afip_state = 'not_available'
        elif conn.server_id.code != 'wsfe':
            afip_state = 'connection_service_error'
        else:
            # Try to login just one time.
            try:
                conn.login()
                if conn.state not in ['connected', 'clockshifted']:
                    afip_state = 'connection_error'
                else:
                    authserver, appserver, dbserver = conn.server_id.wsfe_get_status(
                        conn.id)[conn.server_id.id]
                    if authserver == 'OK':
                        afip_state = 'connected'
                    else:
                        if appserver != 'OK':
                            afip_state = 'connected_but_appserver_error'
                        elif dbserver != 'OK':
                            afip_state = 'connected_but_dbserver_error'
                        else:
                            afip_state = 'connected_but_servers_error'
            except urllib2.URLError as e:
                if e[0][0] == 101:
                    afip_state = 'network_down'
                if e[0][0] == 104:
                    afip_state = 'connection_rejected'
                elif e[0][0] == -2:
                    afip_state = 'unknown_service'
                else:
                    import pdb
                    pdb.set_trace()
            except Exception as e:
                afip_state = 'something_wrong'
            _logger.debug("Connection return: %s" % afip_state)
        self.afip_state = afip_state

    @api.one
    def update_afip_data(self):
        self.get_afip_items_generated()
        self._get_afip_state()
        self.afip_connection_id.server_id.wsfe_update_tax(
            self.afip_connection_id.id)

    @api.one
    def get_afip_items_generated(self):
        glin = lambda conn, ps, jc: conn.server_id.wsfe_get_last_invoice_number(
            conn.id, ps, jc)[conn.server_id.id]
        afip_items_generated = False
        conn = self.afip_connection_id
        if conn and conn.server_id.code == 'wsfe':
            try:
                afip_items_generated = glin(
                    conn, self.journal_id.point_of_sale, self.afip_document_class_id.afip_code)
            except:
                afip_items_generated = False
        _logger.debug("AFIP number of invoices in %s is %s" %
                      (self.afip_document_class_id.name, afip_items_generated))
        self.afip_items_generated = afip_items_generated

    afip_connection_id = fields.Many2one(
        'wsafip.connection', 'Web Service connection',
        help="Which connection must be used to use AFIP services.")
    afip_state = fields.Selection(
        compute='_get_afip_state',
        string='Connection state',
        store=True,
        selection=[
            ('connected', 'Connected'),
            ('connection_service_error',
             'Connection Service Error'),
            ('connection_error',
             'Connection Error'),
            ('connected_but_appserver_error',
             'Application service has troubles'),
            ('connected_but_dbserver_error',
             'Database service is down'),
            ('not_available',
             'Not Available'),
            ('connected_but_authserver_error',
             'Authentication service is down'),
            ('connected_but_servers_error',
             'Services are down'),
            ('network_down', 'Network is down'),
            ('unknown_service',
             'Unknown service'),
            ('connection_rejection',
             'Connection reseted by host'),
            ('something_wrong',
             'Not identified error'),
        ],
        help="Connect to the AFIP and check service status.")
    afip_items_generated = fields.Integer(
        readonly=True,
        string='Number of Invoices Generated',
        help="Connect to the AFIP and check how many invoices was generated.")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
