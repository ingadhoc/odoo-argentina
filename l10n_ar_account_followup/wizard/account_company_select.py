# -*- coding: utf-8 -*-
from openerp import models, fields, _


class select_company_wizard(models.TransientModel):
    _name = 'select.company.wizard'
    
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.user.company_id.id)
        

    
    def confirm_company(self, cr, uid, ids, context=None):
            if context is None:
                context = {}
            partner_obj=self.pool['res.partner']
            active_id = context.get('active_id', False)
            company_id=self.browse(cr, uid, ids, context=context).company_id.id
            partner_id = partner_obj.browse(cr, uid, active_id, context=context).id
            context = dict(context, company_id=company_id)
            if context['mode'] == 'payments':
                return partner_obj.do_button_print(cr, uid, [partner_id], company_id=company_id, context=None)
            elif context['mode'] == 'mail':
                return partner_obj.do_partner_mail(cr, uid, [partner_id], context=context)

    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
