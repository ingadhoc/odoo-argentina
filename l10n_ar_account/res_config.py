# -*- coding: utf-8 -*-
from openerp import models, fields, api
# from openerp.exceptions import UserError
from openerp.addons.l10n_ar_account.models import account_journal


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    # _point_of_sale_types_selection = (
    #     lambda self, *args, **kwargs: self.env[
    #         'account.journal']._get_point_of_sale_types(*args, **kwargs))

    point_of_sale_type = fields.Selection(
        account_journal.AccountJournal._point_of_sale_types_selection,
        'Point Of Sale Type',
        default='manual',
    )
    point_of_sale_number = fields.Integer(
        'Point Of Sale Number',
        help='On Argentina Localization with use documents and sales journals '
        ' is mandatory'
    )
    afip_responsability_type_id = fields.Many2one(
        related='company_id.afip_responsability_type_id',
    )

    @api.multi
    def set_chart_of_accounts(self):
        """
        We send this value in context because to use them on journals creation
        """
        return super(AccountConfigSettings, self.with_context(
            sale_use_documents=self.sale_use_documents,
            purchase_use_documents=self.purchase_use_documents,
            point_of_sale_number=self.point_of_sale_number,
            point_of_sale_type=self.point_of_sale_type,
        )).set_chart_of_accounts()
