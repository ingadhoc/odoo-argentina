##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

try:
    from odoo.addons.account_followup.tests.test_followup_report import TestAccountFollowupReports
except ImportError:
    # account_followup module might not be available
    TestAccountFollowupReports = None


def _revert_method(cls, name):
    """Revertir el método original llamado 'name'"""
    if cls is None:
        return
    method = getattr(cls, name, None)
    if method and hasattr(method, "origin"):
        setattr(cls, name, method.origin)


def uninstall_hook(cr, registry):
    """Hook para revertir los monkey patches al desinstalar el módulo"""
    if TestAccountFollowupReports:
        _revert_method(TestAccountFollowupReports, "test_followup_lines_branches")
        _revert_method(TestAccountFollowupReports, "test_followup_report_with_no_due_date_on_invoice")
