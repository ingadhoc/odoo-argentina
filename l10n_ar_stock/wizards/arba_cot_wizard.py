##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api


class ArbaCotWizard(models.TransientModel):
    _name = 'arba.cot.wizard'
    _description = 'arba.cot.wizard'

    datetime_out = fields.Datetime(
        required=True,
        help='Fecha de salida. No debe ser inferior a ayer ni superior a '
        'dentro de 30 días.'
    )
    tipo_recorrido = fields.Selection(
        [('U', 'Urbano'), ('R', 'Rural'), ('M', 'Mixto')],
        required=True,
        default='M',
    )
    carrier_id = fields.Many2one(
        'delivery.carrier',
        string="Carrier",
        required=True,
    )
    # TODO implementar validaciones de patentes
    patente_vehiculo = fields.Char(
        help='Requerido si CUIT Transportista = CUIT Compañía\n'
        '3 letras y 3 numeros o 2 letras, 3 números y 2 letras'
    )
    patente_acomplado = fields.Char(
        help='3 letras y 3 numeros o 2 letras, 3 números y 2 letras'
    )
    prod_no_term_dev = fields.Selection(
        [('0', 'No'), ('1', 'Si')],
        string='Productos no terminados / devoluciones',
        default='0',
        required=True,
    )
    # TODO implementar asistente de importe
    importe = fields.Float(
    )

    @api.multi
    def confirm(self):
        self.ensure_one()
        if self._context.get('active_model') != 'stock.picking':
            return True
        pickings = self.env['stock.picking'].browse(
            self._context.get('active_ids'))
        pickings.do_pyafipws_presentar_remito(
            fields.Date.from_string(self.datetime_out), self.tipo_recorrido,
            self.carrier_id.partner_id, self.patente_vehiculo,
            self.patente_acomplado, self.prod_no_term_dev, self.importe)
