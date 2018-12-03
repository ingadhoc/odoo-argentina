from openupgradelib import openupgrade
import logging

_logger = logging.getLogger(__name__)


@openupgrade.migrate()
def migrate(env, version):
    _logger.info('Set no monetaria tag to corresponding accounts')
    tag = env.ref('l10n_ar_account.no_monetaria_tag')
    xml_ids = [
        'account.data_account_type_non_current_assets',  # Activos no-Corriente
        'account.data_account_type_fixed_assets',  # Activos fijos
        'account.data_account_type_other_income',  # Otros Ingresos
        'account.data_account_type_revenue',  # Ingreso
        'account.data_account_type_expenses',  # Gastos
        'account.data_account_type_depreciation', # Depreciación
        'account.data_account_type_equity', # Capital
        'account.data_account_type_direct_costs',  # Coste de Ingreso
    ]
    account_types = []
    for xml_id in xml_ids:
        account_types.append(env.ref(xml_id).id)
    env['account.account'].search([
        ('user_type_id', 'in', account_types)]).write({
            'tag_ids': [(4, tag.id)],
    })

