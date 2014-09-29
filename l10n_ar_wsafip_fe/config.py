# -*- coding: utf-8 -*-
from openerp import fields, models, api, _
import logging
_logger = logging.getLogger(__name__)
_schema = logging.getLogger(__name__ + '.schema')


class l10n_ar_wsafip_fe_config(models.TransientModel):

    _name = 'l10n_ar_wsafip_fe.config'
    _inherit = 'res.config.installer'
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env['res.company']._company_default_get(
            'l10n_ar_wsafip_fe.config'),
        required=True)
    wsfe_certificate_id = fields.Many2one(
        'crypto.certificate', 'Certificate', required=True)
    wsfe_for_homologation = fields.Boolean(
        'Is for homologation')
    wsfe_point_of_sale_id = fields.Many2one(
        'afip.point_of_sale', 'Point of Sale', required=True)

    @api.one
    def execute(self):
        """
        """
        print 'execute multi!!!!'
        conn_obj = self.env['wsafip.connection']
        afipserver_obj = self.env['wsafip.server']
        sequence_obj = self.env['ir.sequence']
        journal_class_obj = self.env['account.journal.afip_document_class']

        # Tomamos la compania
        company = self.company_id
        conn_class = 'homologation' if self.wsfe_for_homologation else 'production'

        # Hay que crear la autorizacion para el servicio si no existe.
        connections = conn_obj.search(
            [('partner_id', '=', company.partner_id.id)])

        if not connections:
            # Hay que crear la secuencia de proceso en batch si no existe.
            sequences = sequence_obj.search(
                [('code', '=', 'wsafip_fe_sequence')])
            if sequences:
                sequence = sequences[0]
            else:
                sequence = sequence_obj.create({
                    'name': 'Web Service AFIP Sequence for Invoices',
                    'code': 'ws_afip_sequence'})

            # Crear el conector al AFIP
            loggings = afipserver_obj.search(
                [('code', '=', 'wsaa'), ('class', '=', conn_class)])
            servers = afipserver_obj.search(
                [('code', '=', 'wsfe'), ('class', '=', conn_class)])
            if not loggings:
                raise Warning(_('Not Loggin Server  found for WSAA!'))
            if not servers:
                raise Warning(_('Not Server found for WSFE!'))
            print 'loggings', loggings.id
            print 'servers', servers.id
            connection = conn_obj.create({
                'name': 'AFIP Sequence Authorization Invoice: %s' % company.name,
                'partner_id': company.partner_id.id,
                'logging_id': loggings.id,
                'server_id': servers.id,
                'certificate': self.wsfe_certificate_id.id,
                'batch_sequence_id': sequence.id,
            })
        else:
            connection = connections[0]

        # Asigno el conector al AFIP
        journal_afip_document_classes = journal_class_obj.search([
            ('journal_id.point_of_sale_id', '=',
             self.wsfe_point_of_sale_id.id),
            ('journal_id.type', 'in', ['sale', 'sale_refund'])])

        journal_afip_document_classes.write(
            {'afip_connection_id': connection.id})

        # Sincronizo el número de factura local con el remoto
        for journal_afip_document_class in journal_afip_document_classes:
            remote_number = journal_afip_document_class.afip_items_generated
            sequence = journal_afip_document_class.sequence_id
            if not type(remote_number) is bool:
                _logger.info(
                    "Journal '%s', Document Class '%s' syncronized." %
                    (journal_afip_document_class.journal_id.name,
                        journal_afip_document_class.afip_document_class_id.name))
                sequence.write({'number_next': remote_number + 1})
            else:
                _logger.info(
                    "Journal '%s', Document Class '%s' cant be used." %
                    (journal_afip_document_class.journal_id.name,
                        journal_afip_document_class.afip_document_class_id.name))

        # Actualizo el código de impuestos de la AFIP en los impuestos
        # locale.s
        print '[connection.server_id.id]', [connection.server_id.id]
        self.pool['wsafip.server'].wsfe_update_tax(
            self._cr, self._uid, [connection.server_id.id],
            connection.id, self._context)
        # connection.server_id.wsfe_update_tax(connection.id)

        return True

    # def execute(self, cr, uid, ids, context=None):
    #     """
    #     """
    #     print 'execute!!!!'
    #     conn_obj = self.pool.get('wsafip.connection')
    #     journal_obj = self.pool.get('account.journal')
    #     afipserver_obj = self.pool.get('wsafip.server')
    #     sequence_obj = self.pool.get('ir.sequence')

    #     for ws in self.browse(cr, uid, ids):
    # Tomamos la compania
    #         company = ws.company_id
    #         conn_class = 'homologation' if ws.wsfe_for_homologation else 'production'

    # Hay que crear la autorizacion para el servicio si no existe.
    #         conn_ids = conn_obj.search(
    #             cr, uid, [('partner_id', '=', company.partner_id.id)])

    #         if len(conn_ids) == 0:
    # Hay que crear la secuencia de proceso en batch si no existe.
    #             seq_ids = sequence_obj.search(
    #                 cr, uid, [('code', '=', 'wsafip_fe_sequence')])
    #             if seq_ids:
    #                 seq_id = seq_ids[0]
    #             else:
    #                 seq_id = sequence_obj.create(cr, uid, {
    #                                              'name': 'Web Service AFIP Sequence for Invoices', 'code': 'ws_afip_sequence'})

    # Crear el conector al AFIP
    #             conn_id = conn_obj.create(cr, uid, {
    #                 'name': 'AFIP Sequence Authorization Invoice: %s' % company.name,
    #                 'partner_id': company.partner_id.id,
    #                 'logging_id': afipserver_obj.search(cr, uid, [('code', '=', 'wsaa'), ('class', '=', conn_class)])[0],
    #                 'server_id': afipserver_obj.search(cr, uid, [('code', '=', 'wsfe'), ('class', '=', conn_class)])[0],
    #                 'certificate': ws.wsfe_certificate_id.id,
    #                 'batch_sequence_id': seq_id,
    #             })
    #         else:
    #             conn_id = conn_ids[0]

    # Asigno el conector al AFIP
    #         jou_ids = journal_obj.search(cr, uid, [('company_id', '=', company.id),
    #                                                ('point_of_sale', '=',
    #                                                 ws.wsfe_point_of_sale),
    #                                                ('type', '=', 'sale')])

    #         journal_obj.write(
    #             cr, uid, jou_ids, {'afip_connection_id': conn_id})

    # Sincronizo el número de factura local con el remoto
    #         for journal in journal_obj.browse(cr, uid, jou_ids):
    #             remote_number = journal.afip_items_generated
    #             seq_id = journal.sequence_id.id
    #             if not type(remote_number) is bool:
    #                 _logger.info("Journal '%s' syncronized." % journal.name)
    #                 sequence_obj.write(
    #                     cr, uid, seq_id, {'number_next': remote_number + 1})
    #             else:
    #                 _logger.info("Journal '%s' cant be used." % journal.name)

    # Actualizo el código de impuestos de la AFIP en los impuestos
    # locale.s
    #         conn = conn_obj.browse(cr, uid, conn_id)
    #         conn.server_id.wsfe_update_tax(conn_id)

    #     return True
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
