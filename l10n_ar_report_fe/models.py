# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.osv import osv
from openerp.exceptions import except_orm, ValidationError
#from StringIO import StringIO
#import urllib2, httplib, urlparse, gzip, requests, json
import openerp.addons.decimal_precision as dp
import logging
import datetime
from openerp.fields import Date as newdate
from datetime import datetime, timedelta, date
from dateutil import relativedelta
#Get the logger
_logger = logging.getLogger(__name__)

class AccountInvoiceLine(models.Model):
	_inherit = 'account.invoice.line'

	@api.multi
	def _compute_price_subtotal_vat(self):
		for line in self:
			line.price_subtotal_vat = line.price_subtotal * ( 1 + line.vat_tax_id.amount / 100 )

	price_subtotal_vat = fields.Float('price_subtotal_vat',compute=_compute_price_subtotal_vat)


class account_invoice(models.Model):
	_inherit = 'account.invoice'

	@api.multi
	def _compute_cae_barcode(self):
                #company.partner_id.document_number,
                #o.journal_id.journal_class_id.afip_code,
                #o.journal_id.point_of_sale,
                #int(o.afip_cae or 0),
                #int(o.afip_cae_due is not False and flatdate(o.afip_cae_due) or 0)
		for inv in self:
			inv.cae_barcode = str(inv.company_id.partner_id.main_id_number) + str(inv.journal_document_type_id.document_type_id.code) + \
				str(inv.journal_id.point_of_sale_number) + str(inv.afip_auth_code or 0) + str(inv.afip_auth_code_due or 0).replace('-','')

	cae_barcode = fields.Char('CAE Barcode',compute=_compute_cae_barcode)
