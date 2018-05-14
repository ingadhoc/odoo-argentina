from openupgradelib import openupgrade
import logging
# from odoo.exceptions import ValidationError
_logger = logging.getLogger(__name__)


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    migrate_automatic_withholding_config(env)
    migrate_retencion_ganancias_on_pay_group(env)


def migrate_retencion_ganancias_on_pay_group(env):
    """
    y tambien migramos el advance amount porque en la practica solo lo usaban
    los que tenian retenciones y no lo podemos hacer en l10n_ar_account porque
    no existen a ese momento los payment groups
    """
    cr = env.cr
    # migramos solo los que tengan moves para simplificar
    cr.execute("""
        SELECT move_id, retencion_ganancias, regimen_ganancias_id,
            advance_amount
        FROM account_voucher_copy
        WHERE move_id is not null
        """,)

    reads = cr.fetchall()
    for read in reads:
        (
            move_id,
            retencion_ganancias,
            regimen_ganancias_id,
            advance_amount) = read
        domain = [('move_id', '=', move_id), ('payment_id', '!=', False)]
        payment = env[('account.move.line')].search(domain).mapped(
            'payment_id')

        if len(payment) != 1:
            # raise ValidationError(
            # si no hay (por ej. no tiene move lines, no arrojamos error
            # ya que no es tan crítico y no queremos romper la actualizacion)
            _logger.error(
                'Se encontro mas de un payment o ninguno!!! \n'
                '* Payments: %s\n'
                '* Domain: %s' % (payment, domain))
            continue

        if not payment.payment_group_id:
            _logger.error(
                'No encontramos payment group para payment %s' % (payment))
            continue
        _logger.info('Seteando fecha de payment group %s' % payment)

        vals = {
            'retencion_ganancias': retencion_ganancias,
            'regimen_ganancias_id': regimen_ganancias_id,
            'unreconciled_amount': advance_amount,
        }

        payment.payment_group_id.write(vals)


def migrate_automatic_withholding_config(env):
    cr = env.cr
    openupgrade.logged_query(cr, """
    SELECT
        sequence_id,
        non_taxable_amount,
        non_taxable_minimum,
        base_amount_type,
        user_error_message,
        user_error_domain,
        advances_are_withholdable,
        accumulated_payments,
        type,
        id,
        new_tax_id
    FROM
        account_tax_withholding
    """,)
    updated_ids = []
    for tax_read in cr.fetchall():
        (
            sequence_id,
            non_taxable_amount,
            non_taxable_minimum,
            base_amount_type,
            user_error_message,
            user_error_domain,
            advances_are_withholdable,
            accumulated_payments,
            type,
            id,
            new_tax_id) = tax_read
        if not new_tax_id:
            continue
        _logger.info('Upgrading withholding tax %s' % new_tax_id)
        tax = env['account.tax'].browse(new_tax_id)
        tax.write({
            'withholding_non_taxable_amount': non_taxable_amount,
            'withholding_non_taxable_minimum': non_taxable_minimum,
            'withholding_amount_type': base_amount_type,
            'withholding_user_error_message': user_error_message,
            'withholding_user_error_domain': user_error_domain,
            'withholding_advances': advances_are_withholdable,
            'withholding_accumulated_payments': accumulated_payments,
            'withholding_type': type,
            # si bien la secuencia la creaba el withholding no auto, la
            # migramos solo si with automatico
            'withholding_sequence_id': sequence_id,
            # 'withholding_python_compute': python_compute,
        })

        # al final en realidad estamos usando la misma tabla, por lo cual solo
        # hay que arreglar los ids que referncian a los nuevos impuestos
        # todo este lio horrible seguro se podria mejorar, hacemos esto porque
        # una vez que se cambio uno id no queremos que en otra iteracion se
        # cambie equivocadamente
        if updated_ids:
            openupgrade.logged_query(cr, """
                SELECT id FROM account_tax_withholding_rule
                WHERE tax_withholding_id = %s and id NOT IN %s;
                """, (id, tuple(updated_ids)))
        else:
            openupgrade.logged_query(cr, """
                SELECT id FROM account_tax_withholding_rule
                WHERE tax_withholding_id = %s;
                """, (id,))

        tax_rule_read = cr.fetchall()
        tax_rule_ids = [x[0] for x in tax_rule_read]
        if tax_rule_ids:
            openupgrade.logged_query(cr, """
                UPDATE account_tax_withholding_rule
                SET tax_withholding_id = %s
                WHERE id in %s;
                """, (new_tax_id, tuple(tax_rule_ids)))

            updated_ids += tax_rule_ids
        # openupgrade.logged_query(cr, """
        #     UPDATE account_tax_withholding_rule
        #     SET tax_withholding_id = %s
        #     WHERE tax_withholding_id = %s;
        #     """, (new_tax_id, id))

        # migramos las rules
        # openupgrade.logged_query(cr, """
        # SELECT
        #     sequence,
        #     domain,
        #     tax_withholding_id,
        #     percentage,
        #     fix_amount
        # FROM
        #     account_tax_withholding_rule
        # WHERE
        #     tax_withholding_id = %s
        # """, (id,))
        # for tax_rule in cr.fetchall():
        #     (
        #         sequence,
        #         domain,
        #         tax_withholding_id,
        #         percentage,
        #         fix_amount) = tax_rule
        #     env['account.tax.withholding.rule'].create({
        #         'sequence': sequence,
        #         'domain': domain,
        #         'percentage': percentage,
        #         'fix_amount': fix_amount,
        #         'tax_withholding_id': new_tax_id,
        #     })
