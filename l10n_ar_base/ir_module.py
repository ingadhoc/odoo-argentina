# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api
import logging

_logger = logging.getLogger(__name__)


class IrModuleModule(models.Model):
    _inherit = 'ir.module.module'

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        """ We change this module search because odoo in module account
        loads l10n_ar chart on post_install "_auto_install_l10n"
        """
        new_args = []
        for arg in args:
            if arg[0] == 'name' and arg[1] == '=' and arg[2] == 'l10n_ar':
                # we overrwite because arg can be a tuple or a list
                # tuple does not support item assignment
                # arg = (arg[0], arg[1], 'l10n_ar_chart')
                arg = list(arg)
                arg[2] = 'l10n_ar_chart'
            elif arg[0] == 'name' and arg[1] == 'in' and 'l10n_ar' in arg[2]:
                arg = list(arg)
                arg[2] = [
                    'l10n_ar_chart' if x == 'l10n_ar' else x for x in arg[2]]
            new_args.append(arg)
        return super(IrModuleModule, self).search(
            new_args, offset, limit, order, count=count)
