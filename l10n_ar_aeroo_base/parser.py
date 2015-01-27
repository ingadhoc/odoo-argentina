# -*- coding: utf-8 -*-
import conversor
from openerp.report.report_sxw import rml_parse


class Parser(rml_parse):

    def __init__(self, cr, uid, name, context):
        super(self.__class__, self).__init__(cr, uid, name, context)

        # We search for the report
        report_obj = self.pool['ir.actions.report.xml']
        report_id = report_obj.search(
            cr, uid, [('report_name', '=', name)], context=context)
        report = report_obj.browse(cr, uid, report_id, context=context)
        if isinstance(report, list):
            report = report[0]

        # We add all the key-value pairs of the report configuration
        # We add keys so that you can use it in a safe way in reports
        # (like keys.get('key name'))
        keys = {}
        for report_conf_line in report.line_ids:
            if report_conf_line.value_type == 'text':
                key_value = report_conf_line.value_text
            elif report_conf_line.value_type == 'boolean':
                key_value = report_conf_line.value_boolean
            self.localcontext.update(
                {report_conf_line.name: key_value})
            keys[report_conf_line.name] = key_value
        self.localcontext.update(
            {'keys': keys})

        # We add the report
        self.localcontext.update({'report': report})

        active_object = False
        company = False
        # We add the company of the active object
        if 'active_model' in context and 'active_id' in context:
            active_model_obj = self.pool.get(context['active_model'])
            active_object = active_model_obj.browse(
                cr, uid, context['active_id'], context=context)
            if hasattr(
                    active_object, 'company_id') and active_object.company_id:
                company = active_object.company_id

        if not company:
            company = self.pool[
                'res.users'].browse(cr, uid, uid, context).company_id

        self.localcontext.update({'company': company})

        # We add logo
        print_logo = False
        if report.print_logo == 'specified_logo':
            print_logo = report.logo
        elif report.print_logo == 'company_logo':
            if company.logo:
                print_logo = company.logo

        self.localcontext.update({'logo_report': print_logo})
        # We add background_image
        self.localcontext.update(
            {'use_background_image': report.use_background_image})
        if report.use_background_image:
            self.localcontext.update(
                {'background_image': report.background_image})
        else:
            self.localcontext.update({'background_image': False})

        self.localcontext.update({
            'number_to_string': self.number_to_string,
            'partner_address': self.partner_address,
            'net_price': self.net_price,
            'context': context,
        })

    def net_price(self, gross_price, discount):
        return gross_price * (1-(discount / 100))

    def number_to_string(self, val):
        return conversor.to_word(val)

    # Partner
    def partner_address(self, partner, context=None):
        ret = ''
        if partner.street:
            ret += partner.street
        if partner.street2:
            if partner.street:
                ret += ' - ' + partner.street2
            else:
                ret += partner.street2
        if ret != '':
            ret += '. '

        if partner.zip:
            ret += '(' + partner.zip + ')'
        if partner.city:
            if partner.zip:
                ret += ' ' + partner.city
            else:
                ret += partner.city
        if partner.state_id:
            if partner.city:
                ret += ' - ' + partner.state_id.name
            else:
                ret += partner.state_id.name
        if partner.zip or partner.city or partner.state_id:
            ret += '. '

        if partner.country_id:
            ret += partner.country_id.name + '.'

        return ret
