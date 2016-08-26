# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _

from banks_def import ar_banks_iterator


class l10n_ar_banks_wizard(osv.osv_memory):
    _name = 'l10nar.banks.wizard'

    def on_cancel(self, cr, uid, ids, context):
        return {}

    def on_process(self, cr, uid, ids, context):
        """
            Tomo los datos de los banco de BCRA.
        """
        Resultados = {}

        country_obj = self.pool.get('res.country')
        state_obj = self.pool.get('res.country.state')
        bank_obj = self.pool.get('res.bank')

        state_translate = {
            'Autonomous City of Buenos Aires':
            'Ciudad Autónoma de Buenos Aires',
            'Ushuaia': 'Tierra del Fuego'
        }

        argentina_id = country_obj.search(cr, uid,
                                          [('name', '=', 'Argentina')])[0]

        for bank in ar_banks_iterator():
            print bank
            vals = {
                'name': bank['name'],
                'street': u'%s %s' % (bank.get('street', ''),
                                      bank.get('number', '')),
                'street2': False,
                'zip': bank.get('zip', False),
                'city': bank.get('city', False),
                'state': (state_obj.search(cr, uid, [
                    ('name', '=', state_translate.get(bank['state'],
                                                      bank['state'])),
                    ('country_id', '=', argentina_id)
                ]) + [False])[0],
                'country': argentina_id,
                'email': bank.get('email', False),
                'phone': bank.get('phone', False),
                'fax': bank.get('fax', False),
                'active': True,
                'bic': False,
                'vat': bank.get('vat', False)
            }
            bank_ids = bank_obj.search(cr, uid, [
                ('country', '=', argentina_id),
                ('vat', '=', bank['vat']),
            ])
            if bank_ids:
                self.pool.get('res.bank').write(cr, uid, [bank_ids[0]],
                                                vals, context=context)
            else:
                self.pool.get('res.bank').create(cr, uid, vals, context=context)

        return {
            'view_type': 'form',
            'view_mode': 'form',
            'context': Resultados,
            'res_model': 'l10nar.banks.wizard.result',
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

l10n_ar_banks_wizard()


class l10n_ar_banks_wizard_result(osv.osv_memory):
    _name = 'l10nar.banks.wizard.result'

    def _get_bancos_actualizados(self, cr, uid, context=None):
        if context is None:
            context = {}
        valor = context.get('bancos_actualizados')
        return valor

    def _get_bancos_nuevos(self, cr, uid, context=None):
        if context is None:
            context = {}
        valor = context.get('bancos_nuevos')
        return valor

    def _get_bancos_desahabilitados(self, cr, uid, context=None):
        if context is None:
            context = {}
        valor = context.get('bancos_desahabilitados')
        return valor

    def _get_bancos_procesados(self, cr, uid, context=None):
        if context is None:
            context = {}
        valor = context.get('bancos_procesados')
        return valor

    _columns = {
        'bancos_actualizados': fields.char(_('Banks Upgraded'), size=3),
        'bancos_nuevos': fields.char(_('New Banks'), size=3),
        'bancos_desahabilitados': fields.char(_('Desactivated Banks'), size=3),
        'bancos_procesados': fields.char(_('Banks total processed'), size=3)
    }
    _defaults = {
        'bancos_actualizados': _get_bancos_actualizados,
        'bancos_nuevos': _get_bancos_nuevos,
        'bancos_desahabilitados': _get_bancos_desahabilitados,
        'bancos_procesados': _get_bancos_procesados
    }

    def on_close(self, cr, uid, ids, context):
        return {}

l10n_ar_banks_wizard_result()
