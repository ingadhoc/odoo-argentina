from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    is_backward_withholding_payment = fields.Boolean()

    # TODO: Este metodo modifica el pago para que utilize el impuesto definido en el regime_tax_id
    # y cree el asiento al estilo 18
    # Por ahora lo dejo pero si da problemas recalculamos ya que es un NTH
    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
        self.filtered("is_backward_withholding_payment").is_backward_withholding_payment = False
        return super()._prepare_move_line_default_vals(write_off_line_vals, force_balance=force_balance)
