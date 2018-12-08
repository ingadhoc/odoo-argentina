from openupgradelib import openupgrade
import logging

_logger = logging.getLogger(__name__)


@openupgrade.migrate()
def migrate(env, version):
    _logger.info('Set no monetaria tag to corresponding accounts')
    env['account.account'].set_no_monetaria_tag(
        env['res.company'].search([('localization', '=', 'argentina')]))
