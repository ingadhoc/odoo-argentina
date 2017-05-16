# -*- coding: utf-8 -*-
from openupgradelib import openupgrade


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    """
    Copy afip responsability on invoices to moves
    For all other moves, copy responsability from partner
    """

    cr = env.cr
    openupgrade.logged_query(cr, """
        SELECT afip_responsability_type_id, move_id
        FROM account_invoice
        WHERE move_id is not Null and afip_responsability_type_id is not Null
    """,)
    recs = cr.fetchall()
    for rec in recs:
        afip_responsability_type_id, move_id = rec
        env['account.move'].browse(move_id).afip_responsability_type_id = (
            afip_responsability_type_id)

    invoice_moves = env['account.invoice'].search([
        ('move_id', '!=', False),
        ('afip_responsability_type_id', '!=', False),
    ])
    moves = env['account.move'].search([
        ('id', 'not in', invoice_moves.ids), ('partner_id', '!=', False)])
    moves.set_afip_responsability_type_id()
