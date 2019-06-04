 # -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api
from odoo.exceptions import UserError,ValidationError
from odoo.tools.safe_eval import safe_eval

from odoo.addons.report_xlsx.report.report_xlsx import ReportXlsxAbstract

import pdb
import logging
_logger = logging.getLogger(__name__)

class AccountInvoiceTax(models.Model):
    _inherit = 'account.invoice.tax'

    #line_types = fields.Char('CAE Barcode',compute=_compute_cae_barcode)

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def _compute_vat_ledger_ref(self):
        for inv in self:
            if inv.type in ['in_invoice','in_refund']:
                for line in inv.invoice_line_ids:
                    if line.account_id:
                        inv.vat_ledger_ref = line.account_id.name


    @api.multi
    def _compute_cae_barcode(self):
        #company.partner_id.document_number,
        #o.journal_id.journal_class_id.afip_code,
        #o.journal_id.point_of_sale,
        #int(o.afip_cae or 0),
        #int(o.afip_cae_due is not False and flatdate(o.afip_cae_due) or 0)
        for inv in self:
            inv.cae_barcode = str(inv.company_id.partner_id.document_number) + str(inv.journal_id.journal_class_id.afip_code) + \
                            str(inv.journal_id.point_of_sale) + str(inv.afip_cae or 0) + str(inv.afip_cae_due or 0).replace('-','')

    cae_barcode = fields.Char('CAE Barcode',compute=_compute_cae_barcode)
    vat_ledger_ref = fields.Char('VAT Ledger Ref',compute=_compute_vat_ledger_ref)

class XHeader(object):
    def __init__(self, name, hint="", column=0, hidden=False):
        self.name = name
        self.hint = hint
        self.column = column
        self.hidden = hidden

        if (hint==""):
            self.hint = name

class VatLedgerXlsx(models.AbstractModel):
    _name = 'report.account.vat.ledger.xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, ledgers):
        for obj in ledgers:
            if obj.type == 'sale':
                report_name = obj.name
                # One sheet by partner
                sheet = workbook.add_worksheet(report_name[:31])
                bold = workbook.add_format({'bold': True})
                sheet.write(0, 0, obj.name, bold)#;import pdb; pdb.set_trace()
                headersdef = []
                headersdef.append( XHeader( 'Fecha','Fecha' ) )
                headersdef.append( XHeader( 'Tipo','Tipo' ) )
                headersdef.append( XHeader( 'Cpbte','Comprobante' ) )
                headersdef.append( XHeader( 'Cliente','Cliente' ) )
                headersdef.append( XHeader( 'Anul' ) )
                headersdef.append( XHeader( 'IVA' ) )
                headersdef.append( XHeader( 'CUIT' ) )

                headersdef.append( XHeader( 'PTIPO','Producto Tipo' ) )
                headersdef.append( XHeader( 'Gravado' ) )
                headersdef.append( XHeader( 'IVA 10.5%' ) )
                headersdef.append( XHeader( 'IVA 21%' ) )
                headersdef.append( XHeader( 'I.V.A.' ) )
                headersdef.append( XHeader( 'Total' ) )
                headers = {}

                           #'Nro': { "column": 0, "hint": "", "hidden": False },
                            #'PTIPO': { "column": 0, "hint": "Producto", "hidden": False },
                            #'Gravado': { "column": 0, "hint": "", "hidden": False },
                            #'IVA 10.5%': { "column": 0, "hint": "", "hidden": False },
                            #'IVA 21%': { "column": 0, "hint": "", "hidden": False },
                            #'I.V.A.': { "column": 0, "hint": "", "hidden": False },
                            #'S/S I.V.A.': { "column": 0, "hint": "", "hidden": False },
                            #'I.Interno': { "column": 0, "hint": "", "hidden": False },
                            #'S/S I.Int.': { "column": 0, "hint": "", "hidden": False },
                            #'Percepcion': { "column": 0, "hint": "", "hidden": False },
                            #'Total': { "column": 0, "hint": "", "hidden": False }
                            #}
                index = 0
                for header in headersdef:
                    if (header.hidden==False):
                        sheet.write(3,index,header.hint,bold)
                        header.column = index
                        headers[header.name] = header
                        index = index + 1
                row_index = 4+2

                for inv in obj.invoice_ids:

                    taxes_product_types = {}#;import pdb; pdb.set_trace()
                    for line in inv.invoice_line_ids:
                        txids = line.invoice_line_tax_ids;_logger.info(txids)
                        pid_type = line.product_id.type
                        taxid = txids
                        if ( type(txids)=="list" ):
                            taxid = txids[0]
                        if (taxid):
                            if (taxid.description in taxes_product_types):
                                #prevtype = taxes_product_types[taxid.description]
                                #if (prevtype!=pid_type):
                                #    taxes_product_types[taxid.description] = "MIXTO"
                                if (pid_type not in taxes_product_types[taxid.description]):
                                    taxes_product_types[taxid.description][pid_type] = [];
                                taxes_product_types[taxid.description][pid_type].append(line);
                            else:
                                taxes_product_types[taxid.description] = {}
                                taxes_product_types[taxid.description][pid_type] = [];
                                taxes_product_types[taxid.description][pid_type].append(line);
                    _logger.info(taxes_product_types)
                    #import pdb; pdb.set_trace()
                    for taxdes in taxes_product_types:
                        taxes_lines = taxes_product_types[taxdes]
                        for p_type in taxes_lines:
                            lines_type = taxes_lines[p_type]
                            for line in lines_type:
                                sheet.write(row_index,headers["Fecha"].column, inv.date_invoice)
                                sheet.write(row_index,headers["Tipo"].column, inv.journal_document_type_id.document_type_id.doc_code_prefix)
                                sheet.write(row_index,headers["Cpbte"].column, inv.document_number)
                                sheet.write(row_index,headers["Cliente"].column, inv.partner_id.name)
                                sheet.write(row_index,headers["CUIT"].column, inv.partner_id.main_id_number)
                                sheet.write(row_index,headers["IVA"].column, inv.partner_id.afip_responsability_type_id.name)
                                txids = line.invoice_line_tax_ids;
                                tax_id = txids
                                if ( type(txids)=="list" ):
                                    tax_id = txids[0]

                                sheet.write(row_index,headers["PTIPO"].column, p_type)
                                #exento
                                #sheet.write(row_index,headers["Exento"].column,inv.vat_exempt_base_amount)
                                #gravado
                                #sheet.write(row_index,7,inv.vat_base_amount)
                                sheet.write(row_index, headers["Gravado"].column, round(line.price_subtotal,2))
                                tax_subtotal = round(line.price_subtotal_vat - line.price_subtotal,2)
                                #iva 10.5
                                if (tax_id.amount==10.5):
                                    sheet.write(row_index, headers["IVA 10.5%"].column, tax_subtotal)
                                else:
                                    sheet.write(row_index, headers["IVA 10.5%"].column, 0.0)
                                #iva 21
                                if (tax_id.amount==21.0):
                                    sheet.write(row_index, headers["IVA 21%"].column, tax_subtotal )
                                else:
                                    sheet.write(row_index, headers["IVA 21%"].column, 0.0 )

                                #sheet.write(row_index,10,inv.vat_amount)
                                sheet.write(row_index, headers["I.V.A."].column, tax_subtotal)

                                #sheet.write(row_index,12,0)
                                #sheet.write(row_index,13,0)
                                #sheet.write(row_index,14,0)
                                #sheet.write(row_index,15,0)

                                sheet.write(row_index, headers["Total"].column, round(line.price_subtotal_vat,2))
                                row_index = row_index + 1
            else:
                report_name = obj.name
                # One sheet by partner
                sheet = workbook.add_worksheet(report_name[:31])
                bold = workbook.add_format({'bold': True})
                sheet.write(0, 0, obj.name, bold)
                headersdef = []
                headersdef.append( XHeader( 'Fecha','Fecha' ) )
                headersdef.append( XHeader( 'Tipo','Tipo' ) )
                headersdef.append( XHeader( 'Cpbte','Comprobante' ) )
                headersdef.append( XHeader( 'Proveedor','Proveedor' ) )
                #headersdef.append( XHeader( 'Anul' ) )
                headersdef.append( XHeader( 'IVA' ) )
                headersdef.append( XHeader( 'CUIT' ) )

                headersdef.append( XHeader( 'PTIPO','Producto Tipo' ) )
                headersdef.append( XHeader( 'Cat','Categoria' ) )
                headersdef.append( XHeader( 'Gravado' ) )
                headersdef.append( XHeader( 'No Gravado' ) )
                headersdef.append( XHeader( 'IVA 10.5%' ) )
                headersdef.append( XHeader( 'IVA 21%' ) )
                headersdef.append( XHeader( 'I.V.A.' ) )
                headersdef.append( XHeader( 'IIBB' ) )
                headersdef.append( XHeader( 'P.Gcias.' ) )
                headersdef.append( XHeader( 'Total' ) )
                headers = {}
                #headers = ['Fecha','Cpbte','Nro','Proveedor','C.U.I.T.','IVA',
                #            'Tipo','Gravado','No Gravado',
                #            'IVA 10.5%','IVA 21%','I.V.A.',
                #            'S/S I.V.A.','I.Interno',
                #            'S/S I.Int.','P.IVA',
                #            'P.IIBB','P.Gcias.','Total']

                index = 0
                for header in headersdef:
                    if (header.hidden==False):
                        sheet.write(3,index,header.hint,bold)
                        header.column = index
                        headers[header.name] = header
                        index = index + 1
                row_index = 4+2

                for inv in obj.invoice_ids:
                    taxes_product_types = {}
                    for line in inv.invoice_line_ids:
                        txids = line.invoice_line_tax_ids;_logger.info(txids)
                        pid_type = line.product_id.type
                        taxid = txids
                        if ( type(txids)=="list" ):
                            taxid = txids[0]
                        if (taxid):
                            if (taxid.description in taxes_product_types):
                                prevtype = taxes_product_types[taxid.description]
                                if (prevtype!=pid_type):
                                    taxes_product_types[taxid.description] = "MIXTO"
                            else:
                                taxes_product_types[taxid.description] = pid_type
                        taxes_product_types[taxid.description] = pid_type
                    _logger.info(taxes_product_types)

                    for tax in inv.tax_line_ids:
                        sheet.write(row_index,0,inv.date_invoice)
                        sheet.write(row_index,1,inv.vat_ledger_ref)
                        sheet.write(row_index,2,inv.display_name)
                        sheet.write(row_index,3,inv.partner_id.name)
                        sheet.write(row_index,4,inv.partner_id.main_id_number)
                        sheet.write(row_index,5,inv.partner_id.afip_responsability_type_id.name)

                        if (tax.tax_id.description in taxes_product_types):
                            sheet.write(row_index,6,taxes_product_types[tax.tax_id.description])
                        else:
                            sheet.write(row_index,6,"-")
                        #gravado
                        #sheet.write(row_index,7,inv.vat_base_amount)
                        sheet.write(row_index,7,tax.base)
                        sheet.write(row_index,8,inv.vat_exempt_base_amount)
                        #iva 10.5
                        if (tax.tax_id.amount==10.5):
                            sheet.write(row_index,9, 10.5)
                        else:
                            sheet.write(row_index,9, 0.0)
                        #iva 21
                        if (tax.tax_id.amount==21.0):
                            sheet.write(row_index,10, 21.0 )
                        else:
                            sheet.write(row_index,10, 0.0 )

                        #sheet.write(row_index,10,inv.vat_amount)
                        sheet.write(row_index,11,tax.amount)

                        sheet.write(row_index,12,0)
                        sheet.write(row_index,13,0)
                        sheet.write(row_index,14,0)
                        sheet.write(row_index,15,0)

                        sheet.write(row_index,16,(tax.base+tax.amount))
                        row_index = row_index + 1



#VatLedgerXlsx('report.account.vat.ledger.xlsx','account.vat.ledger')
