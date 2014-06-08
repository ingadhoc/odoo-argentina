# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv

class account_tax(osv.osv):
    _inherit = "account.tax"
    _columns = {
    # TODO ver que campos de aca sirven
        # 'imponible_ganancias_ids': fields.one2many('imponible.ganancias', 'account_tax_id', 'Imponible Ganancias', translate=True, help='o'),
        # 'regimen_ganancia': fields.one2many('account.regimenes.ganancia', 'account_tax_id', 'Regimen', translate=True, ),
        # 'retencion_minima_inscriptos': fields.integer('Retencion minima Inscriptos', translate=True),
        # 'retencion_minima_no_inscriptos': fields.integer('Retencion minima No Inscriptos'),
    }

class account_tax_withhold(osv.osv):
    _name = "account.partner.tax"
    _description = "Withhold Tax"
    _rec_name = 'account_tax_id'
    
    _columns = {
    'account_tax_id': fields.many2one('account.tax', 'Tax', required=True),
    # TODO este!!!
    # 'account_regimenes_ganancia': fields.many2one('account.regimenes.ganancia', 'Codigo de regimen', required=True),
    'date': fields.date('Date',),
    'agent_number': fields.char('Agent number',),
    'exception_ids': fields.one2many('account.partner.tax.exception', 'partner_tax_id', 'Exceptions'),
    'partner_id': fields.many2one('res.partner', 'Partner', required=True),
    'comment': fields.text('Comment',),
    }

class account_partner_tax_exception(osv.osv):
    _name = "account.partner.tax.exception"
    _description = "Withhold Tax Exception"

    _columns = {
        'name': fields.char('Voucher', required=True),
        'partner_tax_id': fields.many2one('account.partner.tax', 'Partner Tax', required=True),
        # TODO hacer un related a un attachments
        # 'voucher_number': fields.binary('Comprobante'),
        'date_from': fields.date('Date From', required=True),
        'date_to': fields.date('Date To', required=True),
        'comment': fields.text('Comment',),
    }


# TODO ver cual es la diferencia entre estos dos que vienen ahora
class account_tax_withhold_gain_line(osv.osv):
    """
    HDB-2012-06-19
    Tabla de regimenes de ganancias en los que un Responsable Inscripto puede estar incluido.
    Esta tabla determina porcentuales e importes minimos no sujetos a retencion.
    ALICUOTAS Y MONTOS NO SUJETOS A RETENCION"
    """
    _name = "account.tax.withhold.gain.line"
    _description = "Withold Gain Tax Line"
    _columns = {
        'account_tax_id': fields.many2one('account.tax', 'Tax', required=True),
        'code': fields.char('Code', size=5, required=False, help='Codigo de regimen de inscripcion en impuesto a las ganancias.'),
        'anex': fields.char('Anex', size=128, required=True),
        'concept': fields.char('Concept', required=True),
        'registered_percentage': fields.float('Registered %',),
        'none_registered_percentage': fields.float('None Registered %'),
        'none_withholding_amount': fields.float('None Withholding Amount',),
    }

# class account_tax_withhold_gain(osv.osv):
#     _name = "account.tax.withhold.table"
#     _description = "Withhold Gain Tax"
#     _columns = {
#         'importe_desde': fields.float('Importe desde'),
#         'importe_hasta': fields.float('Importe hasta'),
#         'retener_importe_fijo': fields.float('Importe fijo'),
#         'retener_porcentaje': fields.float('Porcentaje'),
#         'importe_excedente': fields.float('Excedente'),
#         'account_tax_id': fields.many2one('account.tax', 'Impuesto', size=128),
#     }

class account_journal(osv.osv):
    _inherit = "account.journal"
    _columns = {    
        'tax_id': fields.many2one('account.tax', 'Impuesto retenido'),
        # 'gain_line_id': fields.many2one('account.tax.withhold.gain.line', 'Gain Line'),
        'is_retention_journal': fields.boolean('Is Retention Journal?'),
    }        

class account_voucher(osv.osv):
    _inherit = "account.voucher"
    _columns = {
        'withhold_number': fields.char('Withold Number',),
    }

# TODO cambiar a receipt para calcular o sugerir retenciones
#     def calcular_fecha_desdehasta(self, cr, uid, fecha):
#         logger = netsvc.Logger()
#         today = datetime.date.today()
#         #~ fecha2=datetime(*(time.strptime(fecha, ' %Y-%m-%d')[0:6]))
#         #~ fecha2=datetime.date.strptime(fecha, ' %Y-%m-%d')
#         fecha_desde = datetime.date(today.year, today.month, 1)
#         #~ raise osv.except_osv(_('Error !'), _("today:  %s  -  date: %s  -  desde: %s \n %s   %s   %s")%(today,fecha2,fecha_desde,type(today),type(fecha2),type(fecha_desde)))
#         if today.month == 12:    # para mes = diciembre
#             fecha_hasta = datetime.date(today.year, 12, 31)
#         elif today.month < 12:    # para cualquier otro mes
#             fecha_hasta = datetime.date(today.year, today.month + 1, 1) - datetime.timedelta(days=1)
#         logger.notifyChannel('addons.', netsvc.LOG_WARNING, 'desde %s   hasta %s   ' % (fecha_desde, fecha_hasta))
#         return [fecha_desde, fecha_hasta]

#     def calcular_acumulado_pagos(self, cr, uid, company, partner, fecha, id_actual):
#         #logger = netsvc.Logger()
#         acumulado_pagos = 0
#         ids = self.search(cr, uid, [('company_id', '=', company), ('partner_id', '=', partner), ('state', '=', 'posted'), ('id', '!=', id_actual)])
#         #~ logger.notifyChannel('addons.', netsvc.LOG_WARNING, 'respins %s   partner %s' % (ids,partner))
#         for voucher in self.pool.get('account.voucher').browse(cr, uid, ids):
#             acumulado_pagos += voucher.amount
#         return (acumulado_pagos)

#     def calcular_acumulado_retenciones(self, cr, uid, tax_id, company, partner, fecha, id_actual):
#         #logger = netsvc.Logger()
#         acumulado_retenciones = 0
#         #~ logger.notifyChannel('addons.', netsvc.LOG_WARNING, 'Date: %s  -- date str: %s' % (fecha,datetime.strptime(fecha, ' %Y-%m-%d'))
#         voucher_ids = self.search(cr, uid, [('company_id', '=', company), ('partner_id', '=', partner), ('state', '=', 'posted'), ('id', '!=', id_actual)])
#         i = 0
#         ids = []
#         for voucher_id in voucher_ids:
#             ids.extend(self.pool.get('registro.retenciones').search(cr, uid, [('tax_id', '=', tax_id), ('voucher_id', '=', voucher_id)]))
#             i += 1
#             #~ logger.notifyChannel('addons.', netsvc.LOG_WARNING, 'i: %s   ids: %s   voucher_id: %s   lala:%s   tx_id: %s ' % (i,ids,voucher_id,lala,tax_id))
#         for retencion in self.pool.get('registro.retenciones').browse(cr, uid, ids):    # WARNIGGGGGG: debo filtrar antes por partner, company, etc....
#             acumulado_retenciones += retencion.monto
#         return (acumulado_retenciones)

#     def calcular_retencion(self, cr, uid, ids, context):
#         logger = netsvc.Logger()
#         idsint = int(ids[0])
#         cr.execute("DELETE FROM registro_retenciones WHERE voucher_id=%s ", (idsint,))
#         logger.notifyChannel('addons.', netsvc.LOG_WARNING, 'paso 1 %s   ' % (ids))
#         monto_total_retenido = 0
#         voucher = self.pool.get('account.voucher').browse(cr, uid, idsint)
#         if not voucher.date:
#             raise osv.except_osv(_('Error !'), _("Ingrese la fecha del comprobante"))
#         #fecha_desde= self.calcular_fecha_desdehasta(cr, uid, voucher.date)[0]
#         #fecha_hasta= self.calcular_fecha_desdehasta(cr, uid, voucher.date)[1]
#         impuestos_ids = self.pool.get('account.tax.withhold').search(cr, uid, [('res_company_id', '=', voucher.company_id.id)])
#         #~ verifico que company sea agente de retencion de al menos 1 impuesto.
#         if len(impuestos_ids) == 0:
#             raise osv.except_osv(_('Error !'), _("Su compania no es agente de retencion de ningun impuesto.\nConfigure esto en Administracion/Companies "))
#         #~ verifico que la company sea agente de retencion de al menos un impuesto
#         if len(impuestos_ids) != 0:
#             #~ recorro todos los impuestos que corresponde retener según la "company" con la que estoy trabajando. (Actualmente está implementado solo ganancias).
#             for impuesto in self.pool.get('account.tax.withhold').browse(cr, uid, impuestos_ids):
#                 respins_idlist = self.pool.get('inscripto.impuesto').search(cr, uid, [('partner_id', '=', voucher.partner_id.id), ('account_tax_id', '=', impuesto.account_tax_id.id)])
#                 #~ verifico que partner tenga asignado el regimen de ganancias, en caso de no aviso con un Error
#                 if len(respins_idlist) == 0:
#                     raise osv.except_osv(_('Error !'), _("Debe configurar el provedor ' %s' con el regimen asignado por el AFIP.") % (voucher.partner_id.name))
#                 #~ WARRNINGGG: =ganancia (peligro) en caso de que si tiene asignado el regimen...
#                 elif len(respins_idlist) > 0 and impuesto.account_tax_id.name == "ganancias":
#                     logger.notifyChannel('addons.', netsvc.LOG_WARNING, 'paso 2%s   ' % (respins_idlist))
#                     monto_valido = 0
#                     monto = 0
#                     #~ Recorro todos los regimenes que tiene asignado el partner
#                     for respins in self.pool.get('inscripto.impuesto').browse(cr, uid, respins_idlist):
#                         excepciones_ids = self.pool.get('excepcion').search(cr, uid, [('impuesto.id', '=', respins.id)])
#                         logger.notifyChannel('addons.', netsvc.LOG_WARNING, '  paso 3 (repite) %s   ' % (excepciones_ids))
#                         saltar = False
#                         for excepcion in self.pool.get('excepcion').browse(cr, uid, excepciones_ids):
#                             if excepcion.fecha_desde_exceptuado <= voucher.date <= excepcion.fecha_hasta_exceptuado:
#                                 saltar = True
#                             logger.notifyChannel('addons.', netsvc.LOG_WARNING, '  excepcion    ' % ())
#                         if saltar:
#                             continue
#                         retencion_minima = self.pool.get('account.tax').read(cr, uid, respins.account_tax_id.id, ['retencion_minima_inscriptos', 'retencion_minima_no_inscriptos'])
#                         tax_id = respins.account_tax_id.id
#                         acumulado_pagos = self.calcular_acumulado_pagos(cr, uid, voucher.company_id.id, voucher.partner_id.id, voucher.date, idsint)
#                         logger.notifyChannel('addons.', netsvc.LOG_WARNING, 'acum pagos %s   ' % (acumulado_pagos))
#                         acumulado_retenciones = self.calcular_acumulado_retenciones(cr, uid, tax_id, voucher.company_id.id, voucher.partner_id.id, voucher.date, idsint)
#                         logger.notifyChannel('addons.', netsvc.LOG_WARNING, 'acum reten %s   ' % (acumulado_retenciones))
#                         if respins.inscripto:
#                             """
#                             aqui comienza la discriminacion por producto
#                             """
#                             monto_imponible = voucher.amount + acumulado_pagos - respins.account_regimenes_ganancia.monto_no_sujeto_a_retencion
#                             retener_porcentaje = respins.account_regimenes_ganancia.retener_porcentaje_inscripto
#                             if monto_imponible > 0 and retener_porcentaje == -1:
#                                 tabla_id = self.pool.get('imponible.ganancias').search(cr, uid, [('account_tax_id', '=', tax_id)])
#                                 for tabla in self.pool.get('imponible.ganancias').browse(cr, uid, tabla_id):
#                                     #~ logger.notifyChannel('addons.', netsvc.LOG_WARNING, 'desde %s   hasta %s  impo %s' % (tabla.importe_desde,tabla.importe_hasta,monto_imponible))
#                                     if tabla.importe_desde < monto_imponible < tabla.importe_hasta:
#                                         monto = (tabla.retener_importe_fijo + (tabla.retener_porcentaje / 100 * (monto_imponible - tabla.importe_excedente))) - acumulado_retenciones
#                                         logger.notifyChannel(
#                                             'INSCRIPTO TABLA  monto NO impo: %s  -  porcentaje: %s   -  monto: %s' % (monto_imponible, retener_porcentaje, monto))
#                                         if monto < retencion_minima['retencion_minima_inscriptos']:
#                                             monto = 0
#                             elif monto_imponible > 0 and retener_porcentaje > 0:
#                                 monto = (retener_porcentaje / 100 * monto_imponible) - acumulado_retenciones
#                                 logger.notifyChannel('addons.', netsvc.LOG_WARNING, 'INSCRIPTO   monto NO impo: %s  -  porcentaje: %s   -  monto: %s' % (monto_imponible, retener_porcentaje, monto))
#                                 if monto < retencion_minima['retencion_minima_inscriptos']:
#                                     monto = 0
#                         elif not respins.inscripto:
#                             monto_imponible = voucher.amount + acumulado_pagos
#                             retener_porcentaje = respins.account_regimenes_ganancia.retener_porcentaje_no_inscripto
#                             monto = (retener_porcentaje / 100 * monto_imponible) - acumulado_retenciones
#                             logger.notifyChannel('addons.', netsvc.LOG_WARNING, 'NO INSCRIPTO   monto NO impo: %s  -  porcentaje: %s   -  monto: %s' % (monto_imponible, retener_porcentaje, monto))
#                             if monto < retencion_minima['retencion_minima_no_inscriptos']:
#                                 monto = 0
#                         if monto > monto_valido:
#                             monto_valido = monto
#                             regimen_id = respins.account_regimenes_ganancia.id
#                             monto_total_retenido = monto_valido
#                     if monto_valido != 0:
#                         self.pool.get('registro.retenciones').create(cr, uid, {'voucher_id': ids[0], 'tax_id': tax_id, 'monto': monto_valido, 'regimen_id': regimen_id})
#                 """
#                 elif len(respins_idlist) > 0 and respins.account_tax_id.name="otro impuesto" :
#                 nuevo código para el calculo de retencion de otro impuesto.
#                 monto_total_retenido += monto_otroimpuesto
#                 """

#         self.write(cr, uid, [ids[0]], {'monto_retencion': monto_total_retenido})
#         return True

#     def proforma_voucher(self, cr, uid, ids, context=None):
#         logger = netsvc.Logger()
#         self.action_move_line_create(cr, uid, ids, context=context)
#         self.calcular_retencion(cr, uid, ids, context=context)
#         loco = self.pool.get('ir.sequence').get(cr, uid, 'nro_retencion')
#         logger.notifyChannel('addons.', netsvc.LOG_WARNING, 'LOCOO %s  ' % (loco))
#         self.write(cr, uid, [ids[0]], {'nro_retencion': loco})

#         return True


#     #~ def create(self, cursor, user, vals, context=None):
#         #~ if vals.has_key('monto_retencion') and vals.has_key('retencion'):
#             #~ self.pool.get('registro.retenciones').create(cr, uid,{ 'voucher_id': vals['id'], 'tax_id' : 1, 'monto':vals['monto_retencion']})
#         #~ return super(account_voucher, self).create(cursor, user, vals,context=context)

# account_voucher()
