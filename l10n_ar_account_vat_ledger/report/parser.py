# -*- coding: utf-8 -*-
from openerp.report.report_sxw import rml_parse
import logging
logger = logging.getLogger('report_aeroo')


class Parser(rml_parse):

    def __init__(self, cr, uid, name, context):
        super(self.__class__, self).__init__(cr, uid, name, context)
        # Se fuerza el usuario administador por un error de permisos que no
        # pude detectar para usuarios sin permiso contable, solo con "sale
        # user"
        uid = 1

        print 'context', context
        print 'name', name
        if not context:
            return False
        active_model = context.get('active_model', False)
        if not active_model or active_model != 'res.partner':
            return False
        partner_ids = context.get('active_ids', False)
        if not partner_ids:
            return False
        if not isinstance(partner_ids, list):
            partner_ids = [partner_ids]

        self.from_date = context.get('from_date', False)
        self.to_date = context.get('to_date', False)
        self.show_invoice_detail = context.get('show_invoice_detail', False)
        self.show_receipt_detail = context.get('show_receipt_detail', False)
        self.result_selection = context.get('result_selection', False)

        move_obj = self.pool.get('account.move')
        partner_obj = self.pool.get('res.partner')

        moves_dic = {}
        for partner in partner_obj.browse(cr, uid, partner_ids, context=context):
            move_ids = self.select_account_move_ids(
                partner.id, self.from_date, self.to_date)
            moves = move_obj.browse(cr, uid, move_ids, context=context)
            moves_dic[partner] = moves

        self.moves_dic = moves_dic
        self.localcontext.update({
            'moves_dic': moves_dic,
            'show_invoice_detail': self.show_invoice_detail,
            'show_receipt_detail': self.show_receipt_detail,

            'get_moves_from_partner': self.get_moves_from_partner,
            'contains_relevant_lines': self.contains_relevant_lines,
            'get_move_name': self.get_move_name,
            'get_move_debit': self.get_move_debit,
            'get_move_credit': self.get_move_credit,
            'get_move_debit_to_print': self.get_move_debit_to_print,
            'get_move_credit_to_print': self.get_move_credit_to_print,
            'get_move_accumulated_balance': self.get_move_accumulated_balance,

            'get_move_lines_to_show': self.get_move_lines_to_show,
            'get_move_line_name': self.get_move_line_name,
            'get_move_line_debit_to_print': self.get_move_line_debit_to_print,
            'get_move_line_credit_to_print': self.get_move_line_credit_to_print,

            'get_invoice_to_show': self.get_invoice_to_show,
            'get_invoice_line_name': self.get_invoice_line_name,

            'get_initial_credit': self.get_initial_credit,
            'get_initial_debit': self.get_initial_debit,
            'get_initial_balance': self.get_initial_balance,
            'get_initial_credit_to_print': self.get_initial_credit_to_print,
            'get_initial_debit_to_print': self.get_initial_debit_to_print,
            'get_initial_balance_to_print': self.get_initial_balance_to_print,
            'get_final_balance': self.get_final_balance,
            'get_invoice': self.get_invoice,
        })

    def get_moves_from_partner(self, dic, partner):
        return dic[partner]

    def contains_relevant_lines(self, move):
        '''
        This functions checks if the move contains move.lines that are asociated to an account
        that correspond with the field 'result_selection' of the wizard. If it does not, then
        the move should no be printed.
        '''
        res = False
        for line in move.line_id:
            if self.result_selection == 'customer':
                if line.account_id.type == 'receivable':
                    res = True
                    break
            elif self.result_selection == 'supplier':
                if line.account_id.type == 'payable':
                    res = True
                    break
            else:
                if line.account_id.type == 'receivable' or line.account_id.type == 'payable':
                    res = True
                    break
        if res:
            debit, credit = self.get_move_debit_and_credit(move)
            if debit or credit:
                return True
        return False

    def get_move_name(self, move):
        # name = ''
        # if move.journal_id:
        #     name += move.journal_id.name + ' '
        # name += move.name
        return move.document_number

    def get_move_debit_and_credit(self, move):
        debit = 0.0
        credit = 0.0
        for line in move.line_id:
            if self.result_selection == 'customer':
                if line.account_id.type == 'receivable':
                    debit += line.debit
                    credit += line.credit
            elif self.result_selection == 'supplier':
                if line.account_id.type == 'payable':
                    debit += line.debit
                    credit += line.credit
            else:
                if line.account_id.type == 'receivable' or line.account_id.type == 'payable':
                    debit += line.debit
                    credit += line.credit
        if debit and credit:
            if debit > credit:
                debit = debit - credit
                credit = 0.0
            else:
                credit = credit - debit
                debit = 0.0
        return debit, credit

    def get_move_debit(self, move):
        return self.get_move_debit_and_credit(move)[0]

    def get_move_credit(self, move):
        return self.get_move_debit_and_credit(move)[1]

    def get_move_debit_to_print(self, move):
        debit = self.get_move_debit_and_credit(move)[0]
        if debit == 0.0:
            return ''
            # return 0.0
        else:
            return debit

    def get_move_credit_to_print(self, move):
        credit = self.get_move_debit_and_credit(move)[1]
        if credit == 0.0:
            return ''
            # return 0.0
        else:
            return credit

    def get_move_accumulated_balance(self, move, partner):
        moves = self.moves_dic[partner]
        accumulated_balance = self.get_initial_balance(partner)
        for it_move in moves:
            accumulated_balance += self.get_move_debit(
                it_move) - self.get_move_credit(it_move)
            if it_move == move:
                break
        return accumulated_balance

    def get_move_lines_to_show(self, move):
        lines = []

        if not move.journal_id or move.journal_id.type not in ['cash', 'bank']:
            return lines

        for line in move.line_id:
            if self.result_selection == 'customer':
                if line.account_id.type == 'receivable':
                    lines += [line]
            elif self.result_selection == 'supplier':
                if line.account_id.type == 'payable':
                    lines += [line]
            else:
                if line.account_id.type == 'receivable' or line.account_id.type == 'payable':
                    lines += [line]
        return lines

    def get_move_line_name(self, line):
        return line.name

    def get_move_line_debit_to_print(self, line):
        if line.debit == 0.0:
            return 0.0
        else:
            return line.debit

    def get_move_line_credit_to_print(self, line):
        if line.credit == 0.0:
            return 0.0
        else:
            return line.credit

    def get_invoice(self, move):
        # invoice = False
        # for line in move.line_id:
        #     invoice = line.invoice
        #     if self.result_selection == 'customer':
        #         if line.account_id.type ==  'receivable':
        #             if line.invoice and line.invoice:
        #                 invoice = line.invoice
        #     elif self.result_selection == 'supplier':
        #         if line.account_id.type ==  'payable':
        #             if line.invoice and line.invoice:
        #                 invoice = line.invoice
        #     else:
        #         if line.account_id.type ==  'receivable' or line.account_id.type ==  'payable':
        #             if line.invoice and line.invoice:
        #                 invoice = line.invoice
        # return invoice

    # def get_one_process(self, registry_process_ids, partner_name,
    # state_name=False, context=None):
        ret = self.get_invoice_to_show(move)
        if not ret:
            return False
        else:
            return ret[0]

    def get_invoice_to_show(self, move):
        invoices = []
        for line in move.line_id:
            if self.result_selection == 'customer':
                if line.account_id.type == 'receivable':
                    if line.invoice and line.invoice not in invoices:
                        invoices += [line.invoice]
            elif self.result_selection == 'supplier':
                if line.account_id.type == 'payable':
                    if line.invoice and line.invoice not in invoices:
                        invoices += [line.invoice]
            else:
                if line.account_id.type == 'receivable' or line.account_id.type == 'payable':
                    if line.invoice and line.invoice not in invoices:
                        invoices += [line.invoice]
        return invoices

    def get_invoice_line_name(self, line):
        name = line.name + ' [' + str(line.quantity) + ' '
        if line.uos_id:
            name += line.uos_id.name + ' '
        name += ' x ' + str(line.price_unit * (1 - line.discount / 100)
                            ) + ']' + ' (' + str(line.discount) + '%' + ' dto)'

        return name

    def get_initial_credit(self, partner):
        if not self.from_date:
            return 0.0

        if self.result_selection == 'customer':
            account_type = ('receivable',)
        elif self.result_selection == 'supplier':
            account_type = ('payable',)
        else:
            account_type = ('payable', 'receivable')

        sql_stm = 'SELECT sum(l.credit) ' \
                  'FROM account_move_line l, account_move m, account_account a '\
                  'WHERE l.move_id = m.id ' \
            'AND l.account_id = a.id ' \
            'AND l.partner_id = %s' \
            'AND a.type IN %s ' \
            'AND m.date < \'%s\'' \
                  % (partner.id, account_type, self.from_date)
        self.cr.execute(sql_stm)
        res = self.cr.fetchall()
        if not res[0][0]:
            return 0.0
        else:
            return res[0][0]

    def get_initial_debit(self, partner):
        if not self.from_date:
            return 0.0

        if self.result_selection == 'customer':
            account_type = ('receivable',)
        elif self.result_selection == 'supplier':
            account_type = ('payable',)
        else:
            account_type = ('payable', 'receivable')

        sql_stm = 'SELECT sum(l.debit) ' \
                  'FROM account_move_line l, account_move m, account_account a '\
                  'WHERE l.move_id = m.id ' \
            'AND l.account_id = a.id ' \
            'AND l.partner_id = %s ' \
            'AND a.type IN %s ' \
            'AND m.date < \'%s\'' \
                  % (partner.id, account_type, self.from_date)
        self.cr.execute(sql_stm)
        res = self.cr.fetchall()
        if not res[0][0]:
            return 0.0
        else:
            return res[0][0]

    def get_initial_balance(self, partner):
        return self.get_initial_debit(partner) - self.get_initial_credit(partner)

    def get_initial_credit_to_print(self, partner):
        initial_credit = self.get_initial_credit(partner)
        if not initial_credit:
            return 0
        else:
            return initial_credit

    def get_initial_debit_to_print(self, partner):
        initial_debit = self.get_initial_debit(partner)
        if not initial_debit:
            return 0
        else:
            return initial_debit

    def get_initial_balance_to_print(self, partner):
        initial_balance = self.get_initial_balance(partner)
        if not initial_balance:
            return 0
        else:
            return initial_balance

    def select_account_move_ids(self, partner_id, from_date=False, to_date=False):
        sql_stm = 'SELECT DISTINCT m.id, m.date FROM account_move_line l, account_move m '\
                  'WHERE l.move_id = m.id AND l.partner_id = %s' % partner_id
        if from_date:
            sql_stm += ' AND m.date >= \'%s\'' % from_date
        if to_date:
            sql_stm += ' AND m.date <= \'%s\'' % to_date
        sql_stm += ' ORDER BY m.date'
        self.cr.execute(sql_stm)
        res = self.cr.fetchall()
        res = [r[0] for r in res]
        return res

    def get_final_balance(self, partner):
        moves = self.moves_dic[partner]
        final_balance = self.get_initial_balance(partner)
        for it_move in moves:
            final_balance += self.get_move_debit(it_move) - \
                self.get_move_credit(it_move)
        return final_balance
