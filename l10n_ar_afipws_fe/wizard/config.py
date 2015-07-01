# -*- coding: utf-8 -*-
from openerp import fields, models, api, _
import logging
_logger = logging.getLogger(__name__)
_schema = logging.getLogger(__name__ + '.schema')


class l10n_ar_afipws_fe_config(models.TransientModel):

    _name = 'l10n_ar_afipws_fe.config'
    _inherit = 'res.config.installer'

    company_id = fields.Many2one(
        'res.company',
        'Company',
        default=lambda self: self.env['res.company']._company_default_get(
            'l10n_ar_afipws_fe.config'),
        required=True
        )
    wsfe_certificate_id = fields.Many2one(
        'afipws.certificate',
        'Certificate',
        required=True
        )
    wsfe_for_homologation = fields.Boolean(
        'Is for homologation'
        )
    wsfe_point_of_sale_id = fields.Many2one(
        'afip.point_of_sale',
        'Point of Sale',
        required=True
        )

    @api.multi
    def execute(self):
        """
        """
        self.ensure_one()
        conn_obj = self.env['afipws.connection']
        afipserver_obj = self.env['afipws.server']
        sequence_obj = self.env['ir.sequence']
        journal_class_obj = self.env['account.journal.afip_document_class']

        # Tomamos la compania
        company = self.company_id
        conn_class = 'homologation' if self.wsfe_for_homologation else 'production'

        # Hay que crear la autorizacion para el servicio si no existe.
        connection = conn_obj.search(
            [('partner_id', '=', company.partner_id.id)], limit=1)

        if not connection:
            # Hay que crear la secuencia de proceso en batch si no existe.
            sequences = sequence_obj.search(
                [('code', '=', 'afipws_fe_sequence')])
            if sequences:
                sequence = sequences[0]
            else:
                sequence = sequence_obj.create({
                    'name': 'Web Service AFIP Sequence for Invoices',
                    'code': 'ws_afip_sequence'})

            # Crear el conector al AFIP
            loggings = afipserver_obj.search(
                [('code', '=', 'wsaa'), ('type', '=', conn_class)])
            servers = afipserver_obj.search(
                [('code', '=', 'wsfe'), ('type', '=', conn_class)])
            if not loggings:
                raise Warning(_('Not Loggin Server  found for WSAA!'))
            if not servers:
                raise Warning(_('Not Server found for WSFE!'))
            connection = conn_obj.create({
                'name': 'AFIP Sequence Authorization Invoice: %s' % company.name,
                'partner_id': company.partner_id.id,
                'logging_id': loggings.id,
                'server_id': servers.id,
                'certificate_id': self.wsfe_certificate_id.id,
                'batch_sequence_id': sequence.id,
            })

        # Asigno el conector al AFIP
        journal_afip_document_classes = journal_class_obj.search([
            ('journal_id.point_of_sale_id', '=',
             self.wsfe_point_of_sale_id.id),
            ('journal_id.type', 'in', ['sale', 'sale_refund'])])

        journal_afip_document_classes.write(
            {'afip_connection_id': connection.id})

        # Sincronizo el número de factura local con el remoto
        for journal_afip_document_class in journal_afip_document_classes:
            # update afip data
            journal_afip_document_class.update_afip_data()
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
        self.pool['afipws.server'].wsfe_update_tax(
            self._cr, self._uid, [connection.server_id.id],
            connection.id, self._context)
        # connection.server_id.wsfe_update_tax(connection.id)

        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
