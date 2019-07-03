from odoo import models, fields


class StockBook(models.Model):
    _inherit = 'stock.book'

    document_type_id = fields.Many2one(
        'account.document.type',
        'Document Type',
    )
