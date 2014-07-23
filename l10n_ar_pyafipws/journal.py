#!/usr/bin/python
# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the Affero GNU General Public License as published by
# the Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# Copyright 2013 by Mariano Reingart
# Based on code "factura_electronica" by Luis Falcon 
# Based on code "openerp-iva-argentina" by Gerardo Allende / Daniel Blanco
# Based on code "l10n_ar_wsafip" by OpenERP - Team de LocalizaciÃ³n Argentina

"Electronic Invoice for Argentina Federal Tax Administration (AFIP) webservices"

__author__ = "Mariano Reingart (reingart@gmail.com)"
__copyright__ = "Copyright (C) 2013 Mariano Reingart and others"
__license__ = "AGPL 3.0+"

from osv import fields, osv
try:
    from openerp.tools.translate import _
except:
    _ = str
    
DEBUG = True


class journal_pyafipws_electronic_invoice(osv.osv):
    _name = "account.journal"
    _inherit = "account.journal"
    _columns = {
        'pyafipws_electronic_invoice_service': fields.selection([
			    ('wsfe','Mercado interno -sin detalle- RG2485 (WSFEv1)'),
			    ('wsmtxca','Mercado interno -con detalle- RG2904 (WSMTXCA)'),
			    ('wsbfe','Bono Fiscal -con detalle- RG2557 (WSMTXCA)'),
			    ('wsfex','ExportaciÃ³n -con detalle- RG2758 (WSFEXv1)'),
            ], _('AFIP WS electronic invoice'), 
            help="Habilita la facturaciÃ³n electrÃ³nica por webservices AFIP"),
		'pyafipws_invoice_type' : fields.selection([
			    ( '1','01-Factura A'),
			    ( '2','02-Nota de DÃ©bito A'),
			    ( '3','03-Nota de CrÃ©dito A'),
			    ( '4','04-Recibos A'),
			    ( '5','05-Nota de Venta al Contado A'),
			    ( '6','06-Factura B'),
			    ( '7','07-Nota de DÃ©bito B'),
			    ( '8','08-Nota de CrÃ©dito B'),
			    ( '9','09-Recibos B'),
			    ('10','10-Notas de Venta al Contado B'),
			    ('11','11-Factura C'),
			    ('12','12-Nota de DÃ©bito C'),
			    ('13','13-Nota de CrÃ©dito C'),
			    ('15','Recibo C'),
			    ('19','19-Factura E'),
			    ('20','20-Nota de DÃ©bito E'),
			    ('21','21-Nota de CrÃ©dito E'),
			    ], 'Tipo Comprobante AFIP', 
            help="Tipo de Comprobante AFIP"),
		'pyafipws_point_of_sale' : fields.integer('Punto de Venta AFIP', 
            help="Prefijo de emisiÃ³n habilitado en AFIP"),
    }

    def test_pyafipws_dummy(self, cr, uid, ids, context=None):
        for journal in self.browse(cr, uid, ids):
            company = journal.company_id
            tipo_cbte = journal.pyafipws_invoice_type
            punto_vta = journal.pyafipws_point_of_sale
            service = journal.pyafipws_electronic_invoice_service
            # import AFIP webservice helper for electronic invoice
            if service == "wsfe":
                from pyafipws.wsfev1 import WSFEv1
                ws = WSFEv1()
            elif service == "wsfex":
                from pyafipws.wsfexv1 import WSFEXv1
                ws = WSFEXv1()
            elif service == "wsmtxca":
                from pyafipws.wsmtx import WSMTXCA
                ws = WSMTXCA()
            # create the proxy and get the configuration system parameters:
            cfg = self.pool.get('ir.config_parameter')
            cache = cfg.get_param(cr, uid, 'pyafipws.cache', context=context)
            proxy = cfg.get_param(cr, uid, 'pyafipws.proxy', context=context)
            wsdl = cfg.get_param(cr, uid, 'pyafipws.%s.url' % service, context=context)
            # connect to the webservice and call to the test method
            ws.Conectar(cache or "", wsdl or "", proxy or "")
            ws.Dummy()
            msg = "AFIP service %s " \
                  "AppServerStatus: %s DbServerStatus: %s AuthServerStatus: %s" 
            msg = msg % (
                    service,
                    ws.AppServerStatus, 
                    ws.DbServerStatus,
                    ws.AuthServerStatus)        
            self.log(cr, uid, ids[0], msg) 
            return {}

    def test_pyafipws_point_of_sales(self, cr, uid, ids, context=None):
        for journal in self.browse(cr, uid, ids):
            company = journal.company_id
            tipo_cbte = journal.pyafipws_invoice_type
            punto_vta = journal.pyafipws_point_of_sale
            service = journal.pyafipws_electronic_invoice_service
            # authenticate against AFIP:
            auth_data = company.pyafipws_authenticate(service=service)            
            # import AFIP webservice helper for electronic invoice
            from pyafipws.wsfev1 import WSFEv1
            wsfev1 = WSFEv1()
            # create the proxy and get the configuration system parameters:
            cfg = self.pool.get('ir.config_parameter')
            cache = cfg.get_param(cr, uid, 'pyafipws.cache', context=context)
            proxy = cfg.get_param(cr, uid, 'pyafipws.proxy', context=context)
            wsdl = cfg.get_param(cr, uid, 'pyafipws.%s.url' % service, context=context)
            # connect to the webservice and call to the test method
            wsfev1.Conectar(cache or "", wsdl or "", proxy or "")
            # set AFIP webservice credentials:
            wsfev1.Cuit = company.pyafipws_cuit
            wsfev1.Token = auth_data['token']
            wsfev1.Sign = auth_data['sign']
            # call the webservice method to get the enabled point of sales:
            ret = wsfev1.ParamGetPtosVenta(sep=" ")
            msg = "Pts.Vta. Habilitados en AFIP: " + '. '.join(ret)
            msg += " - ".join([wsfev1.Excepcion, wsfev1.ErrMsg, wsfev1.Obs])
            self.log(cr, uid, ids[0], msg) 
            return {}
    
    def get_pyafipws_last_invoice(self, cr, uid, ids, 
                                  fields_name=None, arg=None, context=None):
        ret = {}
        for journal in self.browse(cr, uid, ids):
            company = journal.company_id
            tipo_cbte = journal.pyafipws_invoice_type
            punto_vta = journal.pyafipws_point_of_sale
            service = journal.pyafipws_electronic_invoice_service
            # authenticate:
            auth_data = company.pyafipws_authenticate(service=service)            
            # import AFIP webservice helper for electronic invoice       
            if service == "wsfe":
                from pyafipws.wsfev1 import WSFEv1
                ws = WSFEv1()
            elif service == "wsfex":
                from pyafipws.wsfexv1 import WSFEXv1
                ws = WSFEXv1()
            elif service == "wsmtxca":
                from pyafipws.wsmtx import WSMTXCA
                ws = WSMTXCA()
            # create the proxy and get the configuration system parameters:
            cfg = self.pool.get('ir.config_parameter')
            cache = cfg.get_param(cr, uid, 'pyafipws.cache', context=context)
            proxy = cfg.get_param(cr, uid, 'pyafipws.proxy', context=context)
            wsdl = cfg.get_param(cr, uid, 'pyafipws.%s.url' % service, context=context)
            # connect to the webservice and call to the query method
            ws.Conectar(cache or "", wsdl or "", proxy or "")
            if auth_data['token']:
                # set AFIP webservice credentials:
                ws.Cuit = company.pyafipws_cuit
                ws.Token = auth_data['token']
                ws.Sign = auth_data['sign']
                # call the webservice method to get the last invoice at AFIP:
                if service == "wsfe" or service == "wsmtxca":
                    ult = ws.CompUltimoAutorizado(tipo_cbte, punto_vta)
                elif service == "wsfex":
                    ult = ws.GetLastCMP(tipo_cbte, punto_vta)
                msg = " - ".join([ws.Excepcion, ws.ErrMsg, ws.Obs])
                self.log(cr, uid, ids[0], u"Ult.Cbte: NÂ° %s %s" % (ult, msg))
                ret[journal.id] = str(ult)
            else:
                msg = auth_data['err_msg']
                raise osv.except_osv(_("ERROR"), msg)
        return ret

    #_columns.update({
    #    'pyafipws_last_invoice_number': fields.function(
    #        get_pyafipws_last_invoice, type='integer', string='Ult. Nro.', 
    #        help="Ãšltimo nÃºmero de factura registrada en AFIP", method=True),
    #})


journal_pyafipws_electronic_invoice()


if __name__ == "__main__":
    # basic tests:
    from osv import cursor

    
