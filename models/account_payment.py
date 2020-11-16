import time
from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import except_orm, ValidationError
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from odoo import http
from tempfile import TemporaryFile
from odoo.exceptions import UserError, ValidationError, RedirectWarning
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
import base64
import copy
import datetime
import io
import logging
from datetime import date
import xlrd
from xlrd import open_workbook
import csv
import sys


class account_payment(models.Model):
    _inherit = "account.payment"
    
    state = fields.Selection([('first_draft', 'Draft'), 
    ('draft', 'In Progress'), ('posted', 'Posted'), 
    ('sent', 'Sent'), 
    ('reconciled', 'Reconciled'),
    ('cancelled', 'Cancelled'),], 
    readonly=True, default='draft', copy=False, string="States")

    @api.one
    def set_draft_prop(self):
        self.write({'state':"draft"})
        return False

    balances = fields.Float('Balance')#, compute="_compute_difference")
    amount_to_pay = fields.Float('To pay')#, compute="_compute_difference")
    narration = fields.Text('Note')
    modes_payment = fields.Selection([
                                    ('POS', 'POS'),
                                    ('Cheque', 'Cheque'),
                                    ('Bank-Draft', 'Bank-Draft'),
                                    ('Transfer', 'Transfer')],
                                    'Mode of Payment',
                                    index=True,
                                    default='POS',
                                    required=False,
                                    readonly=False,
                                    copy=False,
                                    track_visibility='always')

    # @api.one
    @api.onchange('amount')
    def _compute_difference(self):
        self.amount_to_pay = self._compute_total_invoices_amount()
        if len(self.invoice_ids) == 0:
            return
        if self.invoice_ids[0].type in ['in_invoice', 'out_refund']: 
            self.balances = self.amount - self._compute_total_invoices_amount() # 400000 - 700000  = -300000
        else:
            self.balances = self._compute_total_invoices_amount() - self.amount   # 700000 - 300000 = 400000

    @api.multi
    def post(self):
        res = super(account_payment, self).post()
        domain_inv = [('invoice_id', 'in', [item.id for item in self.invoice_ids])]
        members_search = self.env['member.app'].search(domain_inv)
        outstanding = self.balances # self.amount - self.amount_to_pay
        if members_search: 
            members_search.state_payment_inv(self.amount, self.payment_date) 
            members_search.balance_total = members_search.balance_total + outstanding
        else:
            pass
        domain_sub = [('invoice_id', 'in', [item.id for item in self.invoice_ids])]
        sub_search = self.env['subscription.model'].search(domain_sub)
        if sub_search:
            # raise ValidationError(sub_search.member_id.balance_total + outstanding)
            sub_search.member_id.balance_total = sub_search.member_id.balance_total + outstanding
            sub_search.state_payment_inv(self.amount, self.payment_date, self.id, self.payment_difference)
        else:
            pass

        # domain_guest = [('invoice_id', 'in', [item.id for item in self.invoice_ids])]
        # if not self.communication.startswith('INV') or self.communication.startswith('SO'):
        domain_guest = [('invoice_id', 'in', [item.id for item in self.invoice_ids])]
        guest_search = self.env['register.guest'].search(domain_guest)
        if guest_search:
            guest_search.write({'state': 'wait',
                                'payment_idss': [(4, self.id)]
                                }) # state_payment_inv(self.amount, self.payment_date, guest_search, self.payment_difference)
        else:
            pass
        
        domain_suspend = [('invoice_id', 'in', [item.id for item in self.invoice_ids])]
        suspend_search = self.env['suspension.model'].search(domain_suspend)
        if suspend_search:
            suspend_search.member_id.balance_total = suspend_search.member_id.balance_total + outstanding
            suspend_search.state_payment_inv()
        else:
            pass 
        
        domain_spouse = [('invoice_id', 'in', [item.id for item in self.invoice_ids])]
        spouse_search = self.env['register.spouse.member'].search(domain_spouse)
        if spouse_search:
            spouse_search.button_make_confirm(outstanding)
        else:
            pass

        # domain_policy = [('invoice_id', 'in', [item.id for item in self.invoice_ids])]
        # policy_search = self.env['member.policy.line'].search(domain_policy)
        # if policy_search:
        #     policy_search.button_confirm_member()
        # else:
        #     pass
        return res

    def send_mail_accounts(self):
        email_from = self.env.user.email
        group_user_id2 = self.env.ref('ikoyi_module.account_payable_ikoyi').id
        group_user_id = self.env.ref('account.group_account_manager').id
        group_user_id3 = self.env.ref('ikoyi_module.account_boss_ikoyi').id

        bodyx = "Dear Sir, <br/>A Payment with Ref: {} have been sent to you for approval Kindly validate or refuse the payment to enable us proceed. <br/>\
        Regards".format(self.invoice_ids[0].number if self.invoice_ids else self.communication)
        self.mail_sending(
            email_from,
            group_user_id,
            group_user_id2,
            group_user_id3,
            bodyx)

    def mail_sending(
            self,
            email_from,
            group_user_id,
            group_user_id2,
            group_user_id3,
            bodyx):
        from_browse = self.env.user.name
        groups = self.env['res.groups']
        for order in self:
            group_users = groups.search([('id', '=', group_user_id)])
            group_users2 = groups.search([('id', '=', group_user_id2)])
            group_users3 = groups.search([('id', '=', group_user_id3)])
            group_emails = group_users.users
            group_emails2 = group_users2.users
            group_emails3 = group_users3.users

            append_mails = []
            append_mails_to = []
            append_mails_to3 = []
            for group_mail in group_emails:
                append_mails.append(group_mail.login)

            for group_mail2 in group_emails2:
                append_mails_to.append(group_mail2.login)

            for group_mail3 in group_emails3:
                append_mails_to3.append(group_mail3.login)

            all_mails = append_mails + append_mails_to + append_mails_to3
            print(all_mails)
            email_froms = str(from_browse) + " <" + str(email_from) + ">"
            mail_sender = (', '.join(str(item)for item in all_mails)) 
            subject = "Procurement Notification"
             
            mail_data = {
                'email_from': email_froms,
                'subject': subject,
                'email_to': mail_sender,
                'email_cc': mail_sender,  #  + (','.join(str(extra)),
                'reply_to': email_from,
                'body_html': bodyx
            }
            mail_id = order.env['mail.mail'].create(mail_data)
            order.env['mail.mail'].send(mail_id)

    # @api.multi
    # def print_membership_payment_receipt(self):
    #     report = self.env["ir.actions.report.xml"].search(
    #         [('report_name', '=', 'member_app.receipt_payment_template')], limit=1)
    #     if report:
    #         report.write({'report_type': 'qweb-pdf'})
    #     return self.env['report'].get_action(
    #         self.id, 'member_app.receipt_payment_template')
 


class AccountMigrationWizard(models.TransientModel):
    _name = 'account.migration.wizard'

    data_file = fields.Binary(string="Upload File (.xls)")
    filename = fields.Char("Filename")

    def date_formater(self, row):
        """
            Doc:
            args row is the column for the Provided format: 2020-09-07 00:00:00.000
        """
        if type(row) is not str:
            data = row.split(' ')[0].split('-')
            if data:
                yr = data[0]
                mm =data[1]
                dd = data[2]
                return '{}/{}/{}'.format(mm,dd,yr) # '%m/%d/%Y' 09/15/2020 oehealth dob format
            else:
                return fields.Date.today()
        else:
            return fields.Date.today()
         

    def create_account_analytic(self, name):
        account_analytic_tag = self.env['account.analytic.account']
        acc_analytic = account_analytic_tag.search([('name', '=', name)], limit=1)
        create_analytic_acc = account_analytic_tag.create({
            'name': name,
            'company_id': self.env.user.company_id.id
        })
        return acc_analytic.id if acc_analytic else create_analytic_acc.id 

    def create_move_lines(self, reference, narration, date, name, debit_amount, credit_amount, analytic_debit_account_id, analytic_credit_account_id, debit_account, credit_account, partner_id=False):
        journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        move_id = self.env['account.move'].create({
            'journal_id': journal.id, 
            'ref': reference, 
            'date': date, 
            'narration': narration
            })
        partner_browse = self.env['res.partner'].browse([partner_id])
        # create account.move.line for both debit and credit
        line_id_dr = self.env['account.move.line'].with_context(check_move_validity=False).with_context(check_move_validity=False).create({
                                        'move_id': move_id.id,
                                        'ref': narration,
                                        'name': name,
                                        'partner_id': partner_browse.id,
                                        'account_id': debit_account,
                                        'debit': debit_amount,
                                        'credit': credit_amount,
                                        'analytic_account_id': analytic_debit_account_id,
                        })

        line_id_cr = self.env['account.move.line'].with_context(check_move_validity=False).create({
                                        'move_id': move_id.id,
                                        'ref': narration,
                                        'name': name,
                                        'partner_id': partner_id,
                                        'account_id': partner_browse.property_account_receivable_id.id,# credit_account,
                                        'debit': credit_amount,
                                        'credit': debit_amount,
                                        'analytic_account_id': analytic_credit_account_id,
                        })
        return move_id.id

    @api.multi
    def import_data(self):
        if self.data_file:
            file_datas = base64.decodestring(self.data_file)
            workbook = xlrd.open_workbook(file_contents=file_datas)
            sheet = workbook.sheet_by_index(0)
            # sheet_quan_result = workbook.sheet_by_index(5)
            result = []
            data = [[sheet.cell_value(r, c) for c in range(sheet.ncols)] for r in range(sheet.nrows)]
            data.pop(0)
            file_data = data
        else:
            raise ValidationError('Please select file and type of file')
         
        member_obj = self.env['member.app']
        account_obj = self.env['account.account']
        account_analytic_tag = self.env['account.analytic.account']
        section_product_obj = self.env['section.product']
        member_account_migration = self.env['member.account.migration']

        for row in file_data:
            try: 
                def get_related_partner_id(partner_name):
                    partner_obj = self.env['res.partner']
                    partner = partner_obj.search([('name', '=', partner_name)], limit=1)
                    return partner.id if partner else partner_obj.create({'name': partner_name}).id
                transaction_date = self.date_formater(row[2])
                related_partner_id = get_related_partner_id(str(row[31])) if row[31] and str(row[31]) not in ["Null", 'null', ''] else False
                billed_amount = float(row[11]) if row[11] and type(row[11]) in [int, float] else 0
                source_code = str(row[29]).replace('/SLF', '')
                # raise ValidationError(billed_amount)

                analytic_acc_credit_name = str(row[8]) + " Credit"
                analytic_acc_debit_name = str(row[8]) +  " Debit"
                debitamount = float(row[12]) if row[12] and type(row[12]) in [int, float] else 0
                creditamount = float(row[13]) if row[13] and type(row[13]) in [int, float] else 0
                acc_analytic_credit_id = self.create_account_analytic(analytic_acc_credit_name)
                acc_analytic_debit_id = self.create_account_analytic(analytic_acc_debit_name)
                section_product = section_product_obj.search([('name', '=ilike', row[8])])
                
                def create_section_account(income=False, expense=False):
                    name = "Income" if income else "Expenses"
                    search_acm = account_obj.search([('code', '=ilike', str(row[3]))], limit=1)

                    account_id = search_acm.id if search_acm else account_obj.create({
                                                'code': str(int(row[3])), 
                                                'user_type_id':self.env['account.account.type'].search([('name','=', name)]).id, 
                                                'name': row[8] + ' '+name, 
                                                    }).id
                    return account_id

                credit_account = section_product.credit_account_id.id if section_product.credit_account_id else create_section_account(False, True)
                debit_account = section_product.debit_account_id.id if section_product.debit_account_id else create_section_account(True, False)
                if section_product:
                    section_product.write({'credit_account_id': create_section_account(False, True),
                    'debit_account_id': create_section_account(True, False),
                    })
                
                self.create_move_lines(row[0], row[1],transaction_date, row[17], debitamount, creditamount, acc_analytic_debit_id, acc_analytic_credit_id, debit_account, credit_account, related_partner_id) 
                migration_line = {
                    'reference_number': row[0],
                    'details': row[1],
                    'trans_date': transaction_date,
                    'account_id': row[3],
                    'gl_description': row[4],
                    'company_id': row[6],
                    'analytic_account_id': row[8],
                    'cost_center': row[9],
                    'amount': billed_amount,
                    'debit_amount': debitamount, # row[12],
                    'credit_amount': creditamount, # row[13],
                    'source': row[16],
                    'source_description': row[17],
                    'source_code': source_code,
                    'name': row[30],
                    'partner_id': related_partner_id,
                }
                migration_id = member_account_migration.create(migration_line)
                member_id = member_obj.search([('identification', '=', source_code)], limit=1)
                if member_id:
                    bills = billed_amount if billed_amount < 0 else 0
                    outstanding = member_id.balance_total + bills
                    member_id.write({
                        'balance_total': outstanding,
                        'partner_id': related_partner_id,
                        'account_migration_line': [(4, migration_id.id)]
                    })
                    member_id.balance_total = outstanding
                    member_id.button_filter_outstanding()
                    # raise ValidationError(member_id.balance_total)


                    # reference = row[0]
                    # narration = row[1]
                    # date=row[2]
                    # name = row[17] 
                    # debit_amount = row[12]
                    # credit_amount = row[13]
                    # analytic_debit_account_id = row[8]
                    # analytic_credit_account_id = 0
                    # debit_account = 0
                    # credit_account = 0 
                    # partner_id=row[31]

            except Exception as error:
                print('Caught error: ' + repr(error))
                raise ValidationError('There is a problem with the record at Row\n \
                        {}.\n Check the error around Column: {}' .format(row, error))
