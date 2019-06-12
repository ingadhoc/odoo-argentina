from openupgradelib import openupgrade
import logging

_logger = logging.getLogger(__name__)


@openupgrade.migrate()
def migrate(env, version):
    arba_tag = env.ref('l10n_ar_account.tag_tax_jurisdiccion_902')
    env['account.tax'].search([
        ('type_tax_use', 'in', ['customer', 'supplier']),
        ('withholding_type', '=', 'arba_ws')]).write({
            'tag_ids': [(4, arba_tag.id, 0)],
            'withholding_type': 'partner_tax',
        })
    if 'python_compute' in env['account.tax']._fields:
        env['account.tax'].search([
            ('type_tax_use', 'in', ['sale', 'purchase']),
            ('amount_type', '=', 'code'),
            ('python_compute', 'ilike', 'arba')]).write({
                'tag_ids': [(4, arba_tag.id, 0)],
                'amount_type': 'partner_tax',
            })
    # a todos los registros de alicuotas en partners les escribimos que son
    # de arba porque era el único impuesto que soportabamos
    env['res.partner.arba_alicuot'].search([]).write({'tag_id': arba_tag.id})
