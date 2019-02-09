from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    """ Al cambiar el nombre de un campo tenemos que forzar borrar la vista
    porque en este modulo se intenta actualizar antes la vista
    "view_res_partner_arba_alicuot_form"
    """
    view = env.ref(
        'l10n_ar_account_withholding.'
        'view_partner_withholding_amount_type_form', raise_if_not_found=False)
    if view:
        view.unlink()
