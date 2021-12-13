from odoo import fields, models, api


class L10nLatamCheckbook(models.Model):
    _inherit = 'l10n_latam.checkbook'

    check_printing_type = fields.Selection([
        ('no_print', 'No Print'),
        ('print_with_number', 'Print with number'),
        ('print_without_number', 'Print without number'),
        ],
        default='no_print',
        help="* No Print: number will be assigned while creating payment, no print button\n"
        "* Print with number: number will be assigned when creating the payment and will be printed on the check\n"
        "* Print without number: number will be assigned when printing the check (to verify it's corresponds with next"
        " check) and number won't be printed on the check"
    )
