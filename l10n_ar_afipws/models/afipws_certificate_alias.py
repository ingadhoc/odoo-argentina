# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models, api, _
from OpenSSL import crypto
import logging
_logger = logging.getLogger(__name__)


class afipws_certificate_alias(models.Model):
    _name = "afipws.certificate_alias"
    _description = "AFIP Distingish Name / Alias"
    _rec_name = "common_name"

    """
    Para poder acceder a un servicio, la aplicación a programar debe utilizar
    un certificado de seguridad, que se obtiene en la web de afip. Entre otras
    cosas, el certificado contiene un Distinguished Name (DN) que incluye una
    CUIT. Cada DN será identificado por un "alias" o "nombre simbólico",
    que actúa como una abreviación.
    EJ alias: AFIP WS Prod - ADHOC SA
    EJ DN: C=ar, ST=santa fe, L=rosario, O=adhoc s.a., OU=it,
           SERIALNUMBER=CUIT 30714295698, CN=afip web services - adhoc s.a.
    """

    common_name = fields.Char(
        'Common Name',
        size=64,
        default='AFIP WS',
        help='Just a name, you can leave it this way',
        states={'draft': [('readonly', False)]},
        readonly=True,
        required=True,
        )
    key = fields.Text(
        'Private Key',
        readonly=True,
        states={'draft': [('readonly', False)]},
        )
    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        states={'draft': [('readonly', False)]},
        readonly=True,
        )
    country_id = fields.Many2one(
        'res.country', 'Country',
        states={'draft': [('readonly', False)]},
        readonly=True,
        required=True,
        )
    state_id = fields.Many2one(
        'res.country.state', 'State',
        states={'draft': [('readonly', False)]},
        readonly=True,
        required=True,
        )
    city = fields.Char(
        'City',
        states={'draft': [('readonly', False)]},
        readonly=True,
        required=True,
        )
    department = fields.Char(
        'Department',
        default='IT',
        states={'draft': [('readonly', False)]},
        readonly=True,
        required=True,
        )
    cuit = fields.Char(
        _('CUIT'),
        compute='get_cuit',
        required=True,
        )
    company_cuit = fields.Char(
        'Company CUIT',
        size=16,
        states={'draft': [('readonly', False)]},
        readonly=True,
        )
    service_provider_cuit = fields.Char(
        'Service Provider CUIT',
        size=16,
        states={'draft': [('readonly', False)]},
        readonly=True,
        )
    certificate_ids = fields.One2many(
        'afipws.certificate',
        'alias_id',
        'Certificates',
        states={'cancel': [('readonly', True)]},
        )
    service_type = fields.Selection(
        [('in_house', 'In House'), ('outsourced', 'Outsourced')],
        'Service Type',
        default='in_house',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        )
    state = fields.Selection([
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('cancel', 'Cancelled'),
        ], 'State', select=True, readonly=True, default='draft',
        help='* The \'Draft\' state is used when a user is creating a new pair key. Warning: everybody can see the key.\
        \n* The \'Confirmed\' state is used when the key is completed with public or private key.\
        \n* The \'Canceled\' state is used when the key is not more used. You cant use this key again.')
    type = fields.Selection(
        [('production', 'Production'), ('homologation', 'Homologation')],
        'Type',
        required=True,
        default='production',
        readonly=True,
        states={'draft': [('readonly', False)]},
        )

    @api.onchange('company_id')
    def change_company_name(self):
        if self.company_id:
            self.common_name = 'AFIP WS %s - %s' % (
                self.type, self.company_id.name)

    @api.one
    @api.depends('company_cuit', 'service_provider_cuit', 'service_type')
    def get_cuit(self):
        if self.service_type == 'outsourced':
            self.cuit = self.service_provider_cuit
        else:
            self.cuit = self.company_cuit

    @api.onchange('company_id')
    def change_company_id(self):
        if self.company_id:
            self.country_id = self.company_id.country_id.id
            self.state_id = self.company_id.state_id.id
            self.city = self.company_id.city
            if self.company_id.partner_id.vat:
                self.company_cuit = self.company_id.partner_id.vat[2:]

    @api.multi
    def action_confirm(self):
        if not self.key:
            self.generate_key()
        self.write({'state': 'confirmed'})
        return True

    @api.one
    def generate_key(self, key_length=1024):
        """
        """
        # TODO reemplazar todo esto por las funciones nativas de pyafipws
        k = crypto.PKey()
        k.generate_key(crypto.TYPE_RSA, key_length)
        self.key = crypto.dump_privatekey(crypto.FILETYPE_PEM, k)

    @api.multi
    def action_to_draft(self):
        self.write({'state': 'draft'})
        return True

    @api.multi
    def action_cancel(self):
        self.write({'state': 'cancel'})
        self.certificate_ids.write({'state': 'cancel'})
        return True

    @api.multi
    def action_create_certificate_request(self):
        """
        TODO agregar descripcion y ver si usamos pyafipsw para generar esto
        """
        for record in self:
            req = crypto.X509Req()
            req.get_subject().C = self.country_id.code.encode(
                'ascii', 'ignore')
            req.get_subject().ST = self.state_id.name.encode(
                'ascii', 'ignore')
            req.get_subject().L = self.city.encode(
                'ascii', 'ignore')
            req.get_subject().O = self.company_id.name.encode(
                'ascii', 'ignore')
            req.get_subject().OU = self.department.encode(
                'ascii', 'ignore')
            req.get_subject().CN = self.common_name.encode(
                'ascii', 'ignore')
            req.get_subject().serialNumber = 'CUIT %s' % self.cuit.encode(
                'ascii', 'ignore')
            k = crypto.load_privatekey(crypto.FILETYPE_PEM, self.key)
            self.key = crypto.dump_privatekey(crypto.FILETYPE_PEM, k)
            req.set_pubkey(k)
            req.sign(k, 'sha1')
            csr = crypto.dump_certificate_request(crypto.FILETYPE_PEM, req)
            vals = {
                'csr': csr,
                'alias_id': record.id,
            }
            self.certificate_ids.create(vals)
        return True
