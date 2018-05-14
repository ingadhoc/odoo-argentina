from odoo import tools, models, fields, api, _
# from ast import literal_eval


class AccountArVatLine(models.Model):
    """
    Modelo base para nuevos reportes argentinos de iva. La idea es que estas
    lineas tenga todos los datos necesarios y que frente a cambios en odoo, los
    mismos sean abosrvidos por este cubo y no se requieran cambios en los
    reportes que usan estas lineas.
    Se genera una linea para cada apunte contable afectado por iva
    Basicamente lo que hace es convertir los apuntes contables en columnas
    segun la informacion de impuestos y ademas agrega algunos otros
    campos
    """
    _name = "account.ar.vat.line"
    _description = "Línea de IVA para análisis en localización argentina"
    _auto = False

    document_type_id = fields.Many2one(
        'account.document.type',
        'Document Type',
        readonly=True
    )
    date = fields.Date(
        readonly=True
    )
    # TODO analizar si lo hacemos related simplemente pero con store, no lo
    # hicimos por posibles temas de performance
    comprobante = fields.Selection([
        ('out_invoice', 'Customer Invoice'),
        ('in_invoice', 'Vendor Bill'),
        ('out_refund', 'Customer Refund'),
        ('in_refund', 'Vendor Refund'),
    ],
        readonly=True,
    )
    # TODO idem, tal vez related con store? Performance?
    # type = fields.Selection([
    #     ('purchase', 'Purchase'),
    #     ('sale', 'Sale'),
    #     # ('cash', 'Cash'),
    #     # ('bank', 'Bank'),
    #     # ('general', 'Miscellaneous'),
    # ],
    #     # readonly=True
    #     # related='journal_id.type',
    #     readonly=True
    # )
    ref = fields.Char(
        'Partner Reference',
        readonly=True
    )
    name = fields.Char(
        'Label',
        readonly=True
    )
    base_21 = fields.Monetary(
        readonly=True,
        string='Grav. 21%',
        currency_field='company_currency_id',
    )
    iva_21 = fields.Monetary(
        readonly=True,
        string='IVA 21%',
        currency_field='company_currency_id',
    )
    base_27 = fields.Monetary(
        readonly=True,
        string='Grav. 27%',
        currency_field='company_currency_id',
    )
    iva_27 = fields.Monetary(
        readonly=True,
        string='IVA 27%',
        currency_field='company_currency_id',
    )
    base_10 = fields.Monetary(
        readonly=True,
        string='Grav. 10,5%',
        currency_field='company_currency_id',
    )
    iva_10 = fields.Monetary(
        readonly=True,
        string='IVA 10,5%',
        currency_field='company_currency_id',
    )
    base_25 = fields.Monetary(
        readonly=True,
        string='Grav. 2,5%',
        currency_field='company_currency_id',
    )
    iva_25 = fields.Monetary(
        readonly=True,
        string='IVA 2,5%',
        currency_field='company_currency_id',
    )
    base_5 = fields.Monetary(
        readonly=True,
        string='Grav. 5%',
        currency_field='company_currency_id',
    )
    iva_5 = fields.Monetary(
        readonly=True,
        string='IVA 5%',
        currency_field='company_currency_id',
    )
    per_iva = fields.Monetary(
        readonly=True,
        string='Perc. IVA',
        help='Percepción de IVA',
        currency_field='company_currency_id',
    )
    no_gravado_iva = fields.Monetary(
        readonly=True,
        string='No grav/ex',
        help='No gravado / Exento.\n'
        'Todo lo que tenga iva 0, exento, no gravado o no corresponde',
        currency_field='company_currency_id',
    )
    otros_impuestos = fields.Monetary(
        readonly=True,
        string='Otr. Imp',
        help='Otros Impuestos. Todos los impuestos otros impuestos que no sean'
        ' ni iva ni perc de iibb y que figuren en comprobantes afectados por '
        'IVA',
        currency_field='company_currency_id',
    )
    total = fields.Monetary(
        readonly=True,
        currency_field='company_currency_id',
    )
    # currency_id = fields.Many2one(
    #     'res.currency',
    #     'Currency',
    #     readonly=True
    # )
    # amount_currency = fields.Monetary(
    #     readonly=True,
    #     currency_field='currency_id',
    account_id = fields.Many2one(
        'account.account',
        'Account',
        readonly=True,
        auto_join=True,
    )
    # TODO idem, tal vez related con store? Performance?
    state = fields.Selection(
        [('draft', 'Unposted'), ('posted', 'Posted')],
        'Status',
        readonly=True
    )
    journal_id = fields.Many2one(
        'account.journal',
        'Journal',
        readonly=True,
        auto_join=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        'Partner',
        readonly=True,
        auto_join=True,
    )
    # TODO idem, tal vez related con store? Performance?
    afip_responsability_type_id = fields.Many2one(
        'afip.responsability.type',
        string='AFIP Responsability Type',
        readonly=True,
        auto_join=True,
    )
    company_id = fields.Many2one(
        'res.company',
        'Company',
        readonly=True,
        auto_join=True,
    )
    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        readonly=True,
    )
    move_id = fields.Many2one(
        'account.move',
        string='Entry',
        auto_join=True,
    )
    move_line_id = fields.Many2one(
        'account.move.line',
        string='Journal Item',
        auto_join=True,
    )
    afip_activity_id = fields.Many2one(
        'afip.activity',
        'AFIP Activity',
        help='AFIP activity, used for IVA f2002 report',
        auto_join=True,
        readonly=True,
    )
    vat_f2002_category_id = fields.Many2one(
        'afip.vat.f2002_category',
        auto_join=True,
        string='Categoría IVA f2002',
        readonly=True,
    )
    # payment_group_id = fields.Many2one(
    #     'account.payment.group',
    #     'Payment Group',
    #     compute='_compute_move_lines_data',
    # )
    # invoice_id = fields.Many2one(
    #     'account.invoice',
    #     'Invoice',
    #     compute='_compute_move_lines_data',
    # )
    # es una concatenacion de los name de los move lines
    # name = fields.Char(
    #     compute='_compute_move_lines_data',
    # )

    @api.multi
    def open_journal_item(self):
        self.ensure_one()
        return {
            'name': _('Journal Item'),
            'target': 'current',
            'res_id': self.id,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.move.line',
            'type': 'ir.actions.act_window',
        }

    # TODO usar en v10
    # @api.model_cr
    def init(self, cr):
        tools.drop_view_if_exists(cr, self._table)
        env = api.Environment(cr, 1, {})
        ref = env.ref

        # TODO tal vez querramos agregar chequeo de que no haya tax groups
        # tipo vat que no esten en los ref
        vat_tax_groups = env['account.tax.group'].search(
            [('tax', '=', 'vat')])
        tg_nc = ref('l10n_ar_account.tax_group_iva_no_corresponde', False)
        tg_ng = ref('l10n_ar_account.tax_group_iva_no_gravado', False)
        tg_ex = ref('l10n_ar_account.tax_group_iva_exento', False)
        tg_0 = ref('l10n_ar_account.tax_group_iva_0', False)
        tg_21 = ref('l10n_ar_account.tax_group_iva_21', False)
        tg_10 = ref('l10n_ar_account.tax_group_iva_10', False)
        tg_27 = ref('l10n_ar_account.tax_group_iva_27', False)
        tg_25 = ref('l10n_ar_account.tax_group_iva_25', False)
        tg_5 = ref('l10n_ar_account.tax_group_iva_5', False)
        tg_iva0 = False
        if tg_nc and tg_ng and tg_ex and tg_0:
            tg_iva0 = tg_nc + tg_ng + tg_ex + tg_0
        tg_per_iva = ref('l10n_ar_account.tax_group_percepcion_iva', False)
        # TODO ver si en prox versiones en vez de usar los tax group y ext id
        # usamos labels o algo mas odoo way

        # if external ids not loaded yet, we load a dummy id 0
        vals = {
            'tg21': tg_21 and tg_21.id or 0,
            'tg10': tg_10 and tg_10.id or 0,
            'tg27': tg_27 and tg_27.id or 0,
            'tg25': tg_25 and tg_25.id or 0,
            'tg5': tg_5 and tg_5.id or 0,
            'tg_per_iva': tg_per_iva and tg_per_iva.id or 0,
            # tuple [0, 0] so we dont have error on sql
            'tg_iva0': tuple(tg_iva0 and tg_iva0.ids or [0, 0]),
            'tg_vats': tuple(vat_tax_groups and vat_tax_groups.ids or [0, 0]),
        }
        query = """
SELECT
    aml.id,
    aml.id as move_line_id,
    aml.date,
    aml.move_id,
    aml.journal_id,
    aml.account_id,
    aml.company_id,
    aml.partner_id,
    aml.name,
    aml.ref,
    am.afip_responsability_type_id,
    am.state,
    am.document_type_id,
    aa.afip_activity_id,
    aa.vat_f2002_category_id,
    /*TODO si agregamos recibos entonces tenemos que mapear valores aca*/
    ai.type as comprobante,
    /*aj.type,*/
    sum(CASE WHEN bt.tax_group_id=%(tg21)s THEN aml.balance ELSE 0 END)
        as base_21,
    sum(CASE WHEN nt.tax_group_id=%(tg21)s THEN aml.balance ELSE 0 END)
        as iva_21,
    sum(CASE WHEN bt.tax_group_id=%(tg10)s THEN aml.balance ELSE 0 END)
        as base_10,
    sum(CASE WHEN nt.tax_group_id=%(tg10)s THEN aml.balance ELSE 0 END)
        as iva_10,
    sum(CASE WHEN bt.tax_group_id=%(tg27)s THEN aml.balance ELSE 0 END)
        as base_27,
    sum(CASE WHEN nt.tax_group_id=%(tg27)s THEN aml.balance ELSE 0 END)
        as iva_27,
    sum(CASE WHEN bt.tax_group_id=%(tg25)s THEN aml.balance ELSE 0 END)
        as base_25,
    sum(CASE WHEN nt.tax_group_id=%(tg25)s THEN aml.balance ELSE 0 END)
        as iva_25,
    sum(CASE WHEN bt.tax_group_id=%(tg5)s THEN aml.balance ELSE 0 END)
        as base_5,
    sum(CASE WHEN nt.tax_group_id=%(tg5)s THEN aml.balance ELSE 0 END)
        as iva_5,
    --TODO separar sufido y aplicado o filtrar por tipo de operacion o algo?
    sum(CASE WHEN nt.tax_group_id=%(tg_per_iva)s THEN aml.balance ELSE 0 END)
        as per_iva,
    sum(CASE WHEN nt.tax_group_id in %(tg_iva0)s THEN aml.balance ELSE 0 END)
        as no_gravado_iva,
    sum(CASE WHEN nt.tax_group_id not in %(tg_vats)s THEN aml.balance ELSE
        0 END) as otros_impuestos,
    sum(aml.balance) as total
FROM
    account_move_line aml
LEFT JOIN
    account_move as am
    ON aml.move_id = am.id
LEFT JOIN
    account_invoice as ai
    ON aml.invoice_id = ai.id
/*LEFT JOIN
    res_partner as rp
    ON aml.partner_id = rp.id*/
LEFT JOIN
    account_account AS aa
    ON aml.account_id = aa.id
LEFT JOIN
    account_journal AS aj
    ON aml.journal_id = aj.id
LEFT JOIN
    -- nt = net tax
    account_tax AS nt
    ON aml.tax_line_id = nt.id
LEFT JOIN
    account_move_line_account_tax_rel AS amltr
    ON aml.id = amltr.account_move_line_id
LEFT JOIN
    -- bt = base tax
    account_tax AS bt
    ON amltr.account_tax_id = bt.id
WHERE
    aa.internal_type not in ('payable', 'receivable') and
    -- TODO analiza ri registramos cosas de iva en otros diarios que no son
    -- compras y ventas
    aj.type in ('sale', 'purchase') and
    (nt.tax_group_id in %(tg_vats)s or bt.tax_group_id in %(tg_vats)s)
GROUP BY
    aml.id, am.state, am.document_type_id,
    /*aj.type,*/
    am.afip_responsability_type_id,
    aa.afip_activity_id, aa.vat_f2002_category_id,
    ai.type
    /*move_id, journal_id, aj.type*/
        """ % vals

        cr.execute("""CREATE or REPLACE VIEW %s as (%s
        )""" % (self._table, query))
