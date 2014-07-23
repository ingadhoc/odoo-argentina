# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (C) 2012 OpenERP - Team de Localización Argentina.
# https://launchpad.net/~openerp-l10n-ar-localization
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp.osv import fields, osv
from openerp.tools.translate import _
import re
import logging

_logger = logging.getLogger(__name__)

# Number Filter
re_number = re.compile(r'\d{8}')

class invoice(osv.osv):

    _inherit = "account.invoice"
    _columns = {
        'afip_export_id': fields.integer('ID', size=15),
        'afip_export_concept': fields.selection([('1','Exportacion Definitiva de Bienes'),
                                                 ('2','Servicios'),
                                                 ('4','Otros')],
                                                 'AFIP Export concept', 
                                                 select=True, 
                                                 required=True),
        'afip_export_lang_invoice': fields.selection([('1','Español'),
                                                      ('2','Ingles'),
                                                      ('3','Portugues')],
                                                      'AFIP Invoice Language', 
                                                      select=True, 
                                                      required=True),
        'afip_export_obs_com': fields.text('Trade Observations'),
        'afip_export_incoterm': fields.many2one('afip.incoterms', 'Incoterm'),
        'afip_export_exist_perm' : fields.selection([('S','Yes'), 
                                                     ('N','No')], 
                                                     'Has export permissions', 
                                                     select=True, 
                                                     required=True),
        'afip_export_permissions': fields.one2many('afip.export.permissions', 'invoice_id', 'Permisos'),
        'afip_export_rsp': fields.related('partner_id', 'responsability_id', string='Customer Responsability Relation'),
        'afip_export_rspn': fields.related('afip_export_rsp', 'code', type='char', store=True, string='AFIP Responsability CODE'),
        'afip_export_dst_pais': fields.many2one('res.country', 'Destination Country'),
    }

    _defaults = {
        'afip_export_exist_perm': 'N',
    }
    
    def onchange_partner_id(self, cr, uid, ids, type, partner_id, date_invoice=False, payment_term=False, partner_bank_id=False, company_id=False):
        result = {}
        result = super(invoice,self).onchange_partner_id(cr, uid, ids, type, partner_id, date_invoice, payment_term, partner_bank_id, company_id)
        if partner_id:
            partner = self.pool.get('res.partner').browse(cr, uid, partner_id)
            if partner:
                rsp_code = partner.responsability_id.code
                country_code = partner.country_id.id
                if rsp_code:
                    result['value']['afip_export_rspn'] = rsp_code
                if country_code:
                    result['value']['afip_export_dst_pais'] = country_code
        return result

    def get_fex_item(self, cr, uid, ids, *args):
        r = {}
        _ids = [ids] if isinstance(ids, int) else ids

        for inv in self.browse(cr, uid, _ids):
            r[inv.id] = []
            ##Pro_codigo --> NOT REQUIRED. CODIGO INTERNO DEL PRODUCTO/SERVICIO.
            for item in inv.invoice_line:
                #~ import pdb; pdb.set_trace()
                uom = item.uos_id.afip_code
                if uom in [0, 97, 99]:
                    r[inv.id].append({
                        'Pro_codigo': item.product_id.default_code if item.product_id.default_code else '',
                        'Pro_ds': item.name,
                        'Pro_qty': 0,
                        'Pro_umed': item.uos_id.afip_code,
                        'Pro_precio_uni': 0,
                        'Pro_bonificacion': 0,
                        'Pro_total_item': item.price_subtotal,
                    })
                else:
                    r[inv.id].append({
                        'Pro_codigo': item.product_id.default_code if item.product_id.default_code else '',
                        'Pro_ds': item.name,
                        'Pro_qty': item.quantity,
                        'Pro_umed': item.uos_id.afip_code, 
                        'Pro_precio_uni': item.price_unit,
                        'Pro_bonificacion': ((item.price_unit/100)*item.discount)*item.quantity,
                        'Pro_total_item': item.price_subtotal,
                    })

        return r[ids] if isinstance(ids, int) else r
        
    def get_fex_permiso(self, cr, uid, ids, *args):
        r = {}
        _ids = [ids] if isinstance(ids, int) else ids

        for inv in self.browse(cr, uid, _ids):
            r[inv.id] = []
            if inv.afip_export_exist_perm == "N":
                return
            for item in inv.afip_export_permissions:
                if not item.valid_permission:
                    continue
                r[inv.id].append({
                    'Id_permiso': item.permission_code,
                    'Dst_merc': item.dst_merc.afip_code,
                })

        return r[ids] if isinstance(ids, int) else r
        
    def get_fex_existepermiso(self, cr, uid, ids, *args):

        _ids = [ids] if isinstance(ids, int) else ids

        inv = self.browse(cr, uid, _ids)[0]
        if inv.afip_export_exist_perm == "N":
            tipo_expo = inv.afip_export_concept
            comprobante = inv.journal_id.journal_class_id.afip_code
            if int(tipo_expo) in [2, 4]:
                return ''
            elif int(comprobante) in [20, 21]:
                return ''
            else:
                return 'N'
        elif inv.afip_export_exist_perm == "S":
            return 'S'
        else:
            return ''
        
    def get_fex_cuit_pais(self, cr, uid, ids, *args):
        
        cuit = 0
        
        inv = self.browse(cr, uid, ids)

        if inv.partner_id.is_company == True:
            if inv.partner_id.country_id.cuit_juridica != False:
                cuit = inv.partner_id.country_id.cuit_juridica 
            else:
                cuit = inv.partner_id.document_number
        else:
            if inv.partner_id.country_id.cuit_fisica != False:
                cuit = inv.partner_id.country_id.cuit_fisica
            else:
                cuit = inv.partner_id.document_number
        
        return cuit
    
    def get_fex_related_invoices(self, cr, uid, ids, *args):
        """
        List related invoice information to fill CbtesAsoc
        """
        r = {}
        _ids = [ids] if isinstance(ids, int) else ids

        for inv in self.browse(cr, uid, _ids):
            r[inv.id] = []
            rel_inv_ids = self.search(cr, uid, [('number','=',inv.origin),
                                                ('state','not in',['draft','proforma','proforma2','cancel'])])
            for rel_inv in self.browse(cr, uid, rel_inv_ids):
                journal = rel_inv.journal_id
                r[inv.id].append({
                    'Cbte_tipo': journal.journal_class_id.afip_code,
                    'Cbte_punto_vta': journal.point_of_sale,
                    'Cbte_nro': rel_inv.invoice_number,
                    'Cbte_cuit': '', #COMPLETAR
                })

        return r[ids] if isinstance(ids, int) else r
    
    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}
        default.update({
            'afip_export_id': False,
            'afip_export_permissions': False,
            'state': 'draft',
            'afip_error_id': False,
            'afip_batch_number': False,
            'afip_cae_due': False,
            'afip_cae': False,
            'afip_result': False,
            'date_invoice': default.get('date_invoice', False),
            'date_due': default.get('date_due', False)
        })
        return super(invoice, self).copy(cr, uid, id, default, context)
    
    def onchange_permissions(self, cr, uid, ids, afip_export_exist_perm, context=None):
        
        if ids:
            if afip_export_exist_perm: 
                if afip_export_exist_perm == 'S':
                    return True
                else:
                    cr.execute('DELETE FROM afip_export_permissions WHERE invoice_id=%s',(ids))
                    return {'value': {'afip_export_permissions': False}}
            else:
                cr.execute('DELETE FROM afip_export_permissions WHERE invoice_id=%s',(ids))
                return {'value': {'afip_export_permissions': False}}
        else:
            return True
            
    def onchange_concept_export(self, cr, uid, ids, afip_export_concept, context=None):
        if afip_export_concept: 
            if afip_export_concept == "1":
                self.write(cr, uid, ids, {'afip_export_exist_perm': 'S'})
                return {'value': {'afip_export_exist_perm': 'S'}}
            else:
                self.write(cr, uid, ids, {'afip_export_exist_perm': 'N'})
                return {'value': {'afip_export_exist_perm': 'N'}}
        return True
            
    def button_check_permissions(self, cr, uid, ids, context=None):
        result = ""
        list_of_permissions = self.pool.get('account.invoice').browse(cr, uid, ids)[0].afip_export_permissions
        self.write(cr, uid, ids, {'afip_export_exist_perm': 'S'})
        if not list_of_permissions:
                raise osv.except_osv(_(u'Error!'),
                                     _(u'Debe cargar permiso(s) antes de poder chequearlo(s).'))
        for permission in list_of_permissions:
            if not permission.dst_merc:
                raise osv.except_osv(_(u'Error!'),
                                     _(u'Primero debe elegir el pais de destino.'))
            if not permission.permission_code or len(permission.permission_code) < 16:
                raise osv.except_osv(_(u'Error!'),
                                     _(u'El codigo del permiso debe estar completo.')) 
            inv = self.browse(cr, uid, ids)[0]
            conn = inv.journal_id.afip_connection_id
            if not conn:
                raise osv.except_osv(_(u'Connection Error'),
                                     _(u'No hay una conexión definida! Cree/seleccione una sesión válida o hable con su administrador del sistema.'))
                                     
            if conn and conn.server_id.code == 'wsfex':
                try:
                    result = conn.server_id.wsfex_check_permissions(conn.id, permission.permission_code, permission.dst_merc.afip_code, context)
                    if result.get(conn.server_id.id) != 'OK':
                        raise osv.except_osv(_(u'Error!'),
                                             _(u'El permiso "'+permission.permission_code+'" no es valido!'))
                    else:
                        permission.write({'valid_permission': True}) 
                except:
                    result = False
                    raise osv.except_osv(_(u'Error!'),
                                         _(u'No se pudo chequear el permiso.')) 
                                         
        if result == "":
            raise osv.except_osv(_(u'Error!'),
                                 _(u'Chequee que el diario elegido sea el correcto.'))
        if result.get(conn.server_id.id) == 'OK': 
            #~ 
            return True
        else:
            raise osv.except_osv(_(u'Error!'),
                                 _(u'Uno o más permisos son inválidos. Verifique.')) 

    def action_retrieve_cae(self, cr, uid, ids, context=None):
        """
        Contact to the AFIP to get a CAE number.
        """
        if context is None:
            context = {}
        #TODO: not correct fix but required a frech values before reading it.
        self.write(cr, uid, ids, {})

        conn_obj = self.pool.get('wsafip.connection')
        serv_obj = self.pool.get('wsafip.server')
        currency_obj = self.pool.get('res.currency')
        

        next_id = 0
        Servers = {}
        Requests = {}
        Inv2id = {}
        for inv in self.browse(cr, uid, ids, context=context):

            #CHEQUEO DE PERMISOS.
            concept = inv.afip_export_concept
            exist_perm = inv.afip_export_exist_perm
            permissions = inv.afip_export_permissions
            has_valid_perm = False
            
            if concept == "1":
                if not permissions:
                    raise osv.except_osv(_(u'Error!'),
                                         _(u'Si se declara que hay permisos, debe haber al menos uno ingresado (y validado) para continuar'))
                else:
                    for perm in permissions:
                        if perm.valid_permission:
                            has_valid_perm = True
                            break
                        else:
                            continue
                    if not has_valid_perm:
                        raise osv.except_osv(_(u'Error!'),
                                             _(u'Si se declara que hay permisos, debe haber al menos uno ingresado (y validado) para continuar'))

                    
                    
            
            journal = inv.journal_id
            conn = journal.afip_connection_id

            # Only process if set to connect to afip
            if not conn: continue
            
            # Ignore invoice if connection server is not type WSFEX.
            if conn.server_id.code != 'wsfex': continue

            Servers[conn.id] = conn.server_id.id

            # Take the last number of the "number".
            # Could not work if your number have not 8 digits.
            invoice_number = int(re_number.search(inv.number).group())
            
            last_id = serv_obj.wsfex_get_last_id(cr, uid, [conn.server_id.id], conn.id)            
            next_id = last_id + 1

            _f_date = lambda d: d and d.replace('-','')
            
            if journal.journal_class_id.afip_code not in [19, 20, 21]: 
                raise osv.except_osv(_(u'Error!'),
                                     _(u'El comprobante debe estar entre los permitidos por WSFEX'))
                                     
            # Build request dictionary
            if conn.id not in Requests: Requests[conn.id] = {}
            Requests[conn.id][inv.id]=dict( (k,v) for k,v in {
                'Id': next_id,
                'Fecha_cbte': _f_date(inv.date_invoice),
                'Cbte_Tipo': journal.journal_class_id.afip_code,
                'Punto_vta': journal.point_of_sale,
                'Cbte_nro': invoice_number,
                'Tipo_expo': inv.afip_export_concept,
                
                'Permiso_existente': self.get_fex_existepermiso(cr, uid, inv.id),
                'Permisos': { 'Permiso': self.get_fex_permiso(cr, uid, inv.id) },
                
                'Dst_cmp': inv.afip_export_dst_pais.afip_code,
                'Cliente': inv.partner_id.name,
                'Cuit_pais_cliente': self.get_fex_cuit_pais(cr, uid, inv.id),
                'Domicilio_cliente': inv.partner_id.street+", "+inv.partner_id.city,
                'Id_impositivo': None, # ID DE LOS IMPUESTOS DE CADA PAIS: por ejemplo en uruguay es RUT.
                
                'Moneda_Id': inv.currency_id.afip_code,
                'Moneda_ctz': currency_obj.compute(cr, uid, inv.currency_id.id, inv.company_id.currency_id.id, 1.),
                
                'Obs_comerciales': inv.afip_export_obs_com,
                'Imp_total': inv.amount_total,
                'Obs': inv.comment,
                
                'Cmps_asoc': {'Cmp_asoc': self.get_fex_related_invoices(cr, uid, inv.id) },
                
                'Forma_pago': inv.payment_term.name,
                'Incoterms': inv.afip_export_incoterm.afip_export_incoterm_code,
                'Incoterms_Ds': inv.afip_export_incoterm.afip_export_incoterm_desc if inv.afip_export_incoterm.afip_export_incoterm_code else "", # MODIFICAR A QUE SEA ESCRITO POR EL USUARIO. ESTA TEMPORALMENTE DEFINIDO COMO SU PROPIA DESCRIPCION
                'Idioma_cbte': inv.afip_export_lang_invoice,
                
                'Items': { 'Item': self.get_fex_item(cr, uid, inv.id) },
                
            }.iteritems() if v is not None)
            Inv2id[invoice_number] = inv.id

        for c_id, req in Requests.iteritems():
            conn = conn_obj.browse(cr, uid, c_id)
            res = serv_obj.wsfex_get_cae(cr, uid, [conn.server_id.id], c_id, req)
            for k, v in res.iteritems():
                if 'CAE' in v:
                    self.write(cr, uid, Inv2id[k], {
                        'afip_export_id': next_id,
                        'afip_cae': v['CAE'],
                        'afip_cae_due': v['CAEFchVto'],
                        'afip_soap_request': v['Request'],
                        'afip_soap_response': v['Response'],
                    })
                else:
                    msg = 'Factura %s:\n' % k + '\n'.join(
                        [ u'(%s) %s\n' % e for e in v['Errores']] +
                        [ u'(%s) %s\n' % e for e in v['Eventos']]
                    )
                    raise osv.except_osv(_(u'AFIP Validation Error'), msg)

        return super(invoice, self).action_retrieve_cae(cr, uid, ids, context)

invoice()




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
