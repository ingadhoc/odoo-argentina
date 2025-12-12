import logging

from odoo.upgrade import util

logger = logging.getLogger(__name__)


def migrate(cr, version):
    models = ["res.company", "account.account"]
    old_module = "l10n_ar_ux"
    new_module = "l10n_ar_reports_simple"
    old_fieldname = "l10n_ar_afip_activity_id"
    new_fieldname = "l10n_ar_arca_activity_id"
    for model in models:
        # Rename field l10n_ar_afip_activity_id to l10n_ar_arca_activity_id
        util.rename_field(cr, model, old_fieldname, new_fieldname)
        logger.info("Renombrando campo %s a %s en modelo %s", old_fieldname, new_fieldname, model)
        # Move field from l10n_ar_ux to l10n_ar_reports_simple
        util.move_field_to_module(cr, model, new_fieldname, old_module, new_module, skip_inherit=())
        logger.info("Moviendo campo %s a %s en modelo %s", new_fieldname, old_fieldname, model)
    logger.info("Migración de campos de l10n_ar_ux a l10n_ar_reports_simple finalizada.")
