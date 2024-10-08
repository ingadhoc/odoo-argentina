# -*- coding: utf-8 -*-
from odoo import models, api


class PosSession(models.Model):

    _inherit = 'pos.session'

    def _validate_session(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        """
            Agrego este contexto para evitar el bloqueo en los modulos saas.
        """
        return super(PosSession, self.with_context(allow_no_partner=True))._validate_session(balancing_account=balancing_account, amount_to_balance=amount_to_balance, bank_payment_method_diffs=bank_payment_method_diffs)

    def _loader_params_res_company(self):
        params = super()._loader_params_res_company()
        if self.company_id.country_code == 'AR':
            params['search_params']['fields'] += ['l10n_ar_gross_income_number', 'l10n_ar_gross_income_type','l10n_ar_afip_responsibility_type_id',
                                                    'l10n_ar_company_requires_vat','l10n_ar_afip_start_date']
        return params

    def _loader_params_res_partner(self):
        params = super()._loader_params_res_partner()
        if self.company_id.country_code == 'AR':
            params['search_params']['fields'] += ['l10n_ar_afip_responsibility_type_id', 'l10n_latam_identification_type_id']
        return params

    def _pos_data_process(self, loaded_data):
        super()._pos_data_process(loaded_data)
        if self.company_id.country_code == 'AR':
            loaded_data['consumidor_final_anonimo_id'] = self.env.ref('l10n_ar.par_cfa').id

    @api.model
    def _pos_ui_models_to_load(self):
        models_to_load = super()._pos_ui_models_to_load()
        models_to_load += ['l10n_ar.afip.responsibility.type','l10n_latam.identification.type']
        return models_to_load

    def _get_pos_ui_l10n_ar_afip_responsibility_type(self, params):
        return self.env['l10n_ar.afip.responsibility.type'].search_read(**params['search_params'])

    def _loader_params_l10n_ar_afip_responsibility_type(self):
        return {
            'search_params': {
                'domain': [],
                'fields': ['name', 'code'],
            },
        }

    def _get_pos_ui_l10n_latam_identification_type(self, params):
        return self.env['l10n_latam.identification.type'].search_read(**params['search_params'])

    def _loader_params_l10n_latam_identification_type(self):
        return {
            'search_params': {
                'domain': [('l10n_ar_afip_code', '!=', False), ('active', '=', True)],
                'fields': ['name']
            },
        }
