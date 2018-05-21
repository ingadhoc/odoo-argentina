##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api
# from odoo.exceptions import UserError


class AccountTax(models.Model):
    _inherit = 'account.tax'

    jurisdiction_code = fields.Char(
        compute='_compute_jurisdiction_code',
    )

    @api.multi
    def _compute_jurisdiction_code(self):
        for rec in self:
            tag = rec.tag_ids.filtered('jurisdiction_code')
            rec.jurisdiction_code = tag and tag[0].jurisdiction_code


class AccountTaxGroup(models.Model):
    _inherit = 'account.tax.group'

    afip_code = fields.Integer(
        'AFIP Code',
    )
    type = fields.Selection([
        ('tax', 'TAX'),
        ('perception', 'Perception'),
        ('withholding', 'Withholding'),
        ('other', 'Other'),
        # ('view', 'View'),
    ],
        index=True,
    )
    tax = fields.Selection([
        ('vat', 'VAT'),
        ('profits', 'Profits'),
        ('gross_income', 'Gross Income'),
        ('other', 'Other')],
        index=True,
    )
    application = fields.Selection([
        ('national_taxes', 'National Taxes'),
        ('provincial_taxes', 'Provincial Taxes'),
        ('municipal_taxes', 'Municipal Taxes'),
        ('internal_taxes', 'Internal Taxes'),
        ('others', 'Others')],
        help='Other Taxes According AFIP',
        index=True,
    )
    application_code = fields.Char(
        'Application Code',
        compute='_compute_application_code',
    )

    @api.multi
    @api.depends('application')
    def _compute_application_code(self):
        for rec in self:
            if rec.application == 'national_taxes':
                application_code = '01'
            elif rec.application == 'provincial_taxes':
                application_code = '02'
            elif rec.application == 'municipal_taxes':
                application_code = '03'
            elif rec.application == 'internal_taxes':
                application_code = '04'
            else:
                application_code = '99'
            rec.application_code = application_code


class AccountFiscalPositionTemplate(models.Model):
    _inherit = 'account.fiscal.position.template'

    afip_code = fields.Char(
        'AFIP Code',
        help='For eg. This code will be used on electronic invoice and citi '
        'reports'
    )
    # TODO borrar si no lo usamos, por ahora lo resolivmos de manera nativa
    afip_responsability_type_ids = fields.Many2many(
        'afip.responsability.type',
        'afip_reponsbility_account_fiscal_pos_temp_rel',
        'position_id', 'afip_responsability_type_id',
        'AFIP Responsabilities',
        help='Add this fiscalposition if partner has one of this '
        'responsabilities'
    )
    # TODO this fields should be added on odoo core
    auto_apply = fields.Boolean(
        string='Detect Automatically',
        help="Apply automatically this fiscal position.")
    country_id = fields.Many2one(
        'res.country', string='Country',
        help="Apply only if delivery or invoicing country match.")
    country_group_id = fields.Many2one(
        'res.country.group', string='Country Group',
        help="Apply only if delivery or invocing country match the group.")
    state_ids = fields.Many2many(
        'res.country.state', string='Federal States')
    zip_from = fields.Integer(
        string='Zip Range From', default=0)
    zip_to = fields.Integer(
        string='Zip Range To', default=0)


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    afip_code = fields.Char(
        'AFIP Code',
        help='For eg. This code will be used on electronic invoice and citi '
        'reports',
    )
    # TODO tal vez podriamos usar funcionalidad nativa con "vat subjected"
    afip_responsability_type_ids = fields.Many2many(
        'afip.responsability.type',
        'afip_reponsbility_account_fiscal_pos_rel',
        'position_id', 'afip_responsability_type_id',
        'AFIP Responsabilities',
        help='Add this fiscalposition if partner has one of this '
        'responsabilities'
    )

    @api.model
    def _get_fpos_by_region_and_responsability(
            self, country_id=False, state_id=False,
            zipcode=False, afip_responsability_type_id=False):
        """
        We use similar code than _get_fpos_by_region but we use
        "afip_responsability_type_id" insted of vat_required
        """

        base_domain = [
            ('auto_apply', '=', True),
            ('afip_responsability_type_ids', '=', afip_responsability_type_id)
        ]

        if self.env.context.get('force_company'):
            base_domain.append(
                ('company_id', '=', self.env.context.get('force_company')))

        null_state_dom = state_domain = [('state_ids', '=', False)]
        null_zip_dom = zip_domain = [
            ('zip_from', '=', 0), ('zip_to', '=', 0)]
        null_country_dom = [
            ('country_id', '=', False), ('country_group_id', '=', False)]

        if zipcode and zipcode.isdigit():
            zipcode = int(zipcode)
            zip_domain = [
                ('zip_from', '<=', zipcode), ('zip_to', '>=', zipcode)]
        else:
            zipcode = 0

        if state_id:
            state_domain = [('state_ids', '=', state_id)]

        domain_country = base_domain + [('country_id', '=', country_id)]
        domain_group = base_domain + [
            ('country_group_id.country_ids', '=', country_id)]

        # Build domain to search records with exact matching criteria
        fpos = self.search(
            domain_country + state_domain + zip_domain, limit=1)

        # return records that fit the most the criteria, and fallback on less
        # specific fiscal positions if any can be found
        if not fpos and state_id:
            fpos = self.search(
                domain_country + null_state_dom + zip_domain, limit=1)
        if not fpos and zipcode:
            fpos = self.search(
                domain_country + state_domain + null_zip_dom, limit=1)
        if not fpos and state_id and zipcode:
            fpos = self.search(
                domain_country + null_state_dom + null_zip_dom, limit=1)

        # fallback: country group with no state/zip range
        if not fpos:
            fpos = self.search(
                domain_group + null_state_dom + null_zip_dom, limit=1)

        if not fpos:
            # Fallback on catchall (no country, no group)
            fpos = self.search(
                base_domain + null_country_dom, limit=1)
        return fpos or False

    @api.model
    def get_fiscal_position(self, partner_id, delivery_id=None):
        """
        We overwrite original functionality and replace vat_required logic
        for afip_responsability_type_ids
        """
        # we need to overwrite code (between #####) from original function
        #####
        if not partner_id:
            return False
        # This can be easily overriden to apply more complex fiscal rules
        PartnerObj = self.env['res.partner']
        partner = PartnerObj.browse(partner_id)

        # if no delivery use invoicing
        if delivery_id:
            delivery = PartnerObj.browse(delivery_id)
        else:
            delivery = partner

        # partner manually set fiscal position always win
        if (
                delivery.property_account_position_id or
                partner.property_account_position_id):
            return (
                delivery.property_account_position_id.id or
                partner.property_account_position_id.id)
        #####

        afip_responsability = (
            partner.commercial_partner_id.afip_responsability_type_id)

        # First search only matching responsability positions
        fpos = self._get_fpos_by_region_and_responsability(
            delivery.country_id.id, delivery.state_id.id, delivery.zip,
            afip_responsability.id)
        if not fpos and afip_responsability:
            fpos = self._get_fpos_by_region_and_responsability(
                delivery.country_id.id, delivery.state_id.id, delivery.zip,
                False)

        return fpos.id if fpos else False
