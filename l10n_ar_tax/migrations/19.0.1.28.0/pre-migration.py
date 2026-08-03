import logging

logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Sacamos la opción 'agip' del campo webservice: CABA pasa a resolverse por 'padron',
    que lee el padrón subido en la base y, si no está, consulta el que Adhoc baja y procesa
    en la suya."""
    cr.execute("UPDATE account_fiscal_position_l10n_ar_tax SET webservice = 'padron' WHERE webservice = 'agip'")
    logger.info("Posiciones fiscales que pasaron de webservice 'agip' a 'padron': %s", cr.rowcount)
