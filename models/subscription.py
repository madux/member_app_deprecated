import time
from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import except_orm, ValidationError
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from odoo import http

TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale',
    'in_refund': 'purchase',
}
class Subscription_Member(models.Model):
    _name = "subscription.model"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _rec_name = "partner_id"
    _order = "id desc"

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            result.append(
                (record.id, u"%s - %s" % (record.member_id.partner_id.name, record.identification) 
                 ))
            record.name = result
        return result

    partner_id = fields.Many2one(
        'res.partner', 'Name', required=True, domain=[
            ('is_member', '=', True)])
    member_id = fields.Many2one(
        'member.app',
        'Member ID',
        domain=[
            ('state',
             '!=',
             'suspension')],
        readonly=False,
        compute="Domain_Member_Field")
    identification = fields.Char('Identification.', size=6, compute="Domain_Member_Field")
    email = fields.Char('Email', compute="Domain_Member_Field")
    account_id = fields.Many2one('account.account', 'Account', compute="Domain_Member_Field")
    date = fields.Datetime('Date', required=False,  store=True)
    # suspension_date = fields.Datetime('Suspension Date')
    users_followers = fields.Many2many('hr.employee', string='Add followers')
    subscription = fields.Many2many(
        'subscription.payment',
        string='Add Sections') 
        # , compute='get_all_packages', store=True)
    section_line = fields.Many2many('section.line', string='Add Sections')#compute="get_all_packages"
        
    package = fields.Many2many(
        'package.model',
        string='Packages')
        # store=True, compute='get_all_packages')  #  ,compute='get_all_packages')
    state = fields.Selection([('draft', 'Draft'),
                              ('suscription', 'Suscribed'),
                              ('manager_approve', 'F&A Manager'),
                              ('fined', 'Fined'),
                              ('partial', 'Partially Paid'),
                              ('done', 'Done'),
                              ], default='draft', string='Status')

    p_type = fields.Selection([('normal', 'Normal'),
                               ('ano', 'Anomaly'),
                               ('sub', 'Subscription'),

                               ], default='normal', string='Type')
    barcode = fields.Char(string='Barcode')
    depend_name = fields.Many2many(
        'register.spouse.member',
        string="Dependents")#, compute='get_all_packages', store=True)
    invoice_id = fields.Many2many('account.invoice', string='Invoice', store=True)
    total_paid = fields.Float('Total Paid', default =0)
    balance_total = fields.Float('Outstanding', default =0, store=True, compute="get_balance_total")
    date_of_last_sub = fields.Datetime('Last Subscription Date', store=True, compute="Domain_Member_Field")
    periods_month = fields.Selection([
        ('Jan-June 2011', 'Jan-June 2011'),
        ('July-Dec 2011', 'July-Dec 2011'),
        ('Jan-June 2012', 'Jan-June 2012'),
        ('July-Dec 2012', 'July-Dec 2012'),
        ('Jan-June 2013', 'Jan-June 2013'),
        ('July-Dec 2013', 'July-Dec 2013'),
        ('Jan-June 2014', 'Jan-June 2014'),
        ('July-Dec 2014', 'July-Dec 2014'),
        ('Jan-June 2015', 'Jan-June 2015'),
        ('July-Dec 2015', 'July-Dec 2015'),
        ('Jan-June 2016', 'Jan-June 2016'),
        ('July-Dec 2016', 'July-Dec 2016'),
        ('Jan-June 2017', 'Jan-June 2017'),
        ('July-Dec 2017', 'July-Dec 2017'),
        ('Jan-June 2018', 'Jan-June 2018'),
        ('July-Dec 2018', 'July-Dec 2018'),
        ('Jan-June 2019', 'Jan-June 2019'),
        ('July-Dec 2019', 'July-Dec 2019'),
        ('Jan-June 2020', 'Jan-June 2020'),
        ('July-Dec 2020', 'July-Dec 2020'),
        ('Jan-June 2021', 'Jan-June 2021'),
        ('July-Dec 2021', 'July-Dec 2021'),
    ], 'Period', index=True, required=True, readonly=False, copy=False,
                                           track_visibility='always')
    duration_period = fields.Selection([
        ('Months', 'Months'),
        ('Full Year', 'Full Year'),
    ], 'Duration to Pay', default="Months", index=True, required=False, readonly=False, copy=False, 
                                           track_visibility='always')

    number_period = fields.Integer('No. of Years/Months', default=6)
    date_end = fields.Datetime(
        string='End Date',
        default=fields.Datetime.now,
    )
    total = fields.Float(
        'Total Subscription Fee',
        required=True,
        compute="get_total")
    
    @api.one
    @api.depends('invoice_id')
    def get_balance_total(self):
        balance = 0.0
        for rec in self.invoice_id:
            balance += rec.residual
        self.balance_total = balance

    @api.onchange('partner_id')
    def onchange_partner_invoice(self):
        res = {}
        if self.partner_id:
            res['domain'] = {'invoice_id': [('partner_id', '=', self.partner_id.id)]}
        return res

    @api.depends('section_line', 'periods_month')
    def get_total(self):
        for rec in self:
            tot = 0.0
            for sub in rec.section_line:
                tot += sub.amount
            rec.total = tot

    @api.onchange('partner_id')
    def get_all_packages(self):
        """This will filter list of subscription that is not of type levy, entry fee, additional fee"""
        get_package = self.env['member.app'].search(
            [('partner_id', '=', self.partner_id.id)], limit=1)
        
        section_line = get_package.mapped('section_line').filtered(lambda x: x.sub_payment_id.paytype not in ['addition', 'entry_fee', 'main_house'])
        if section_line:
            self.section_line = section_line
        self.depend_name = get_package.depend_name
        # for r3 in get_package.depend_name:
        #     self.depend_name = [(4, r3.id)]
  
    @api.one
    @api.depends('partner_id')
    def Domain_Member_Field(self):
        for record in self:
            member = self.env['member.app'].search(
                [('partner_id', '=', record.partner_id.id)])
            for tec in member:
                record.account_id = tec.account_id.id
                record.identification = tec.identification
                record.email = tec.email
                record.member_id = tec.id
                record.date_of_last_sub = tec.date_of_last_sub
                record.duration_period = tec.duration_period
                record.number_period = tec.number_period
                # self.check_expiry()

    def _set_dates(self):
        number = 0
        if self.duration_period == "Months":
            number = self.number_period * 30
        if self.duration_period == "Full Year":
            number = self.number_period * 365
        required_date = datetime.strptime(self.date_of_last_sub, '%Y-%m-%d %H:%M:%S')
        self.date_end = required_date + timedelta(days=number)
        self.member_id.due_dates = required_date + timedelta(days=number)

    def check_expiry(self):
        self.state = "suscription"
        self._set_dates()

    @api.multi
    def see_breakdown_invoice(self): 
        search_view_ref = self.env.ref(
            'account.view_account_invoice_filter', False)
        form_view_ref = self.env.ref('account.invoice_form', False)
        tree_view_ref = self.env.ref('account.invoice_tree', False)

        return {
            'domain': [('id', 'in', [item.id for item in self.invoice_id])],
            'name': 'Subscription Invoices',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            #  'views': [(form_view_ref.id, 'form')],
            'views': [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')],
            'search_view_id': search_view_ref and search_view_ref.id,
        }

    # def check_expiry(self):
    #     if self.member_id:
            
    #         due_date = self.member_id.due_dates
    #         current_date = fields.Datetime.now()
    #         if due_date and current_date:
    #             if current_date < due_date:
    #                 raise ValidationError("The member's subscription has not expired")
    #             else:
    #                 popup_message = "Membership subscription has expired and is \n due for payment on the date: {} You can proceed to generate an Invoice".format(due_date)
    #                 self.state = "suscription"
    #                 self.send_mail_to_member_sub()
    #                 self._set_dates()
    #                 return self.popup_notification('Date Expired: {}'.format(current_date))


    # def check_expiryss(self):
    #     if self.member_id:
    #         member = self.env['member.app'].search([('id', '=', self.member_id.id)])
    #         start = datetime.strptime(member.date_of_last_sub, '%Y-%m-%d %H:%M:%S')
    #         today = fields.Datetime.now()
    #         end = datetime.strptime(today, '%Y-%m-%d %H:%M:%S')
    #         cal = end - start
    #         total = cal.days
    #         if member.duration_period == "Months":
    #             record = member.number_period * 30
    #             # period_notification = (member.number_period * 30) - (member.number_period/6 * 30)
    #             # if period_notification:
    #             #     message = "Your subscription will expire in a month time. Kindly visit the membership department for renewal"
    #             #     self.send_reminder_message(message)
    #             if record < total:
    #                 message = "your membership subscription has expired and is due for payment on the date: {}".format(fields.Datetime.now())
    #                 popup_message = "Membership subscription has expired. You can proceed to generate an Invoice"
    #                 # self.send_reminder_message(message)
    #                 self.state = "suscription"
    #                 self.send_mail_to_member_sub()
    #                 self._set_dates()
    #                 return self.popup_notification(popup_message)
    #             else:
    #                 raise ValidationError("The member's subscription has not expired")
    #         elif member.duration_period == "Full Year":
    #             total = cal.days  # / 365
    #             record = member.number_period * 365
    #             if record < total:
    #                 self.send_reminder_message()
    #                 self.state = "suscription"
    #                 self._set_dates()
    #                 return self.popup_notification(popup_message)
    #             else:
    #                 raise ValidationError("The member's subscription has not expired")
                
    def popup_notification(self,popup_message):
        view = self.env.ref('sh_message.sh_message_wizard')
        view_id = view and view.id or False
        context = dict(self._context or {})
        context['message'] = popup_message # 'Successful'
        return {'name':'Alert',
                    'type':'ir.actions.act_window',
                    'view_type':'form',
                    'res_model':'sh.message.wizard',
                    'views':[(view.id, 'form')],
                    'view_id':view.id,
                    'target':'new',
                    'context':context,
                } 
 
    def send_reminder_message(self, message):
        email_from = self.env.user.company_id.email
        group_user_id = self.env.ref('member_app.manager_member_ikoyi').id
        # extra = self.env.ref('ikoyi_module.inventory_officer_ikoyi').id
        extra = self.email
        bodyx = "Dear Sir/Madam, </br>We wish to notify that you -ID {} , that" + message + "</br> Kindly contact the Ikoyi Club 1968 for any further enquires. \
        </br>Thanks".format(self.identification)
        self.mail_sending(email_from, group_user_id, extra, bodyx)
 
    def button_send_mail(self):  #  draft
        self.send_mail_to_member()

    @api.multi
    def send_mail_to_member(self, force=False):  #  draft
        email_from = self.env.user.company_id.email
        group_user_id = self.env.ref('member_app.manager_member_ikoyi').id
        # extra = self.env.ref('ikoyi_module.inventory_officer_ikoyi').id
        extra = self.email
        bodyx = "Dear Sir/Madam, </br>We wish to notify that you -ID {} , that your membership subscription is \
        due for payment on the date: {} </br> Kindly contact the Ikoyi Club 1968 for any further enquires. \
        </br>Thanks" .format(self.identification, fields.Datetime.now())
        self.mail_sending(email_from, group_user_id, extra, bodyx)

    @api.multi
    def send_mail_to_member_sub(self, force=False):  #  draft
        email_from = self.env.user.company_id.email
        group_user_id = self.env.ref('member_app.manager_member_ikoyi').id
        # extra = self.env.ref('ikoyi_module.inventory_officer_ikoyi').id
        extra = self.email
        bodyx = "Dear Sir/Madam, </br>We wish to notify that you -ID {} , that your membership subscription \
        have been updated on the date: {}. </br> Kindly contact the Ikoyi Club 1968 for any further enquires. \
        </br>Thanks" .format(self.identification, fields.Datetime.now())
        self.mail_sending(email_from, group_user_id, extra, bodyx)

    @api.multi
    def send_mail_to_accountmanager(self, force=False):
        email_from = self.env.user.company_id.email
        group_user_id = self.env.ref('ikoyi_module.account_boss_ikoyi').id
        # extra = self.env.ref('ikoyi_module.inventory_officer_ikoyi').id

        extra = self.email
        bodyx = "Sir/Madam, </br>We wish to notify you that a member with ID: {} had Anomalities on renewal payments on the date: {}.</br>\
             Kindly <a href={}> </b>Click <a/> to Login to the ERP to view</br> \
             Thanks".format(self.identification, fields.Datetime.now(), self.get_url(self.id, self._name))
        self.mail_sending(email_from, group_user_id, extra, bodyx)

    @api.multi
    def send_mail_to_mem_officer(self, force=False):
        email_from = self.env.user.company_id.email
        group_user_id = self.env.ref('member_app.membership_officer_ikoyi').id
        extra_user = self.env.ref('member_app.manager_member_ikoyi').id

        groups = self.env['res.groups']
        group_users = groups.search([('id', '=', extra_user)], limit=1)
        group_emails = group_users.users or None
        extra = group_emails.login

        #  extra=self.email
        bodyx = "Sir/Madam, </br>We wish to notify you that a member with ID: {} had Anomalities on renewal payments on the date: {}.</br>\
             Kindly <a href={}> </b>Click <a/> to Login to the ERP to view</br> \
             Thanks".format(self.identification, fields.Datetime.now(), self.get_url(self.id, self._name))
        self.mail_sending(email_from, group_user_id, extra, bodyx)

    @api.multi
    def button_subscribe(self):  #  draft, fine
        self.write({'state': 'suscription'})
        self.send_mail_to_member_sub()
        self._set_dates()
        self.check_expiry()

    @api.multi  # suscription , mem_manager
    def button_anamoly(self):
        self.write({'state': 'manager_approve', 'p_type': 'ano'})
        return self.send_mail_to_accountmanager()

    @api.multi
    def send_Finmanager_Fine(self):  #  manager_approve , accountboss
        self.write({'state': 'fined'})
        self.send_mail_to_mem_officer()
        return self.payment_button_normal()

    @api.one
    def payment_button_normal2(self):  # suscription, 
        self.create_member_billing()

    @api.multi
    def print_receipt_sus(self):
        report = self.env["ir.actions.report.xml"].search(
            [('report_name', '=', 'member_app.subscription_receipt_template')], limit=1)
        if report:
            report.write({'report_type': 'qweb-pdf'})
        return self.env['report'].get_action(
            self.id, 'member_app.subscription_receipt_template')

    
# #  FUNCTIONS # # # #
    @api.multi
    def send_mail_suspend(self, force=False):
        email_from = self.env.user.company_id.email
        group_user_id = self.env.ref('member_app.manager_member_ikoyi').id
        # extra = self.env.ref('ikoyi_module.inventory_officer_ikoyi').id
        extra = self.email
        bodyx = "Dear Sir/Madam, </br>We wish to notify that the member with ID {} have been Suspended from Ikoyi Club on the date: {} </br>\
             Kindly contact the Ikoyi Club 1968 for any further enquires. </br><a href={}> </b>Click <a/> to review. Thanks"\
             .format(self.identification, fields.Datetime.now(), self.get_url(self.id, self._name))
        self.mail_sending(email_from, group_user_id, extra, bodyx)

    def get_url(self, id, model):
        base_url = http.request.env['ir.config_parameter'].sudo(
        ).get_param('web.base.url')
        base_url += '/web# id=%d&view_type=form&model=%s' % (id, model)

    def mail_sending(self, email_from, group_user_id, extra, bodyx):
        from_browse = self.env.user.name
        groups = self.env['res.groups']
        for order in self:
            group_users = groups.search([('id', '=', group_user_id)])
            group_emails = group_users.users
            followers = []
            email_to = []
            for group_mail in self.users_followers:
                followers.append(group_mail.work_email)

            for gec in group_emails:
                email_to.append(gec.login)

            email_froms = str(from_browse) + " <" + str(email_from) + ">"
            mail_appends = (', '.join(str(item)for item in followers))
            mail_to = (','.join(str(item2)for item2 in email_to))
            subject = "Membership Suscription Notification"

            extrax = (', '.join(str(extra)))
            followers.append(extrax)
            mail_data = {
                'email_from': email_froms,
                'subject': subject,
                'email_to': mail_to,
                'email_cc': mail_appends,  #  + (','.join(str(extra)),
                'reply_to': email_from,
                'body_html': bodyx
            }
            mail_id = order.env['mail.mail'].create(mail_data)
            order.env['mail.mail'].send(mail_id) 
            
    @api.multi
    def button_payments(self, name, amount, level):  #  Send memo back
        return {
            'name': name,
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'register.payment.member',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_payment_type': "outbound",
                'default_date': fields.Datetime.now(),
                'default_amount': amount,
                'default_partner_id': self.partner_id.id,
                'default_member_ref': self.member_id.id,
                'default_name': "Subscription Payments",
                'default_level': level,
                'default_to_pay': amount,
                'default_num': self.id,
                'default_p_type': self.p_type,
            },
        }
     
    def _get_subscribe(self):
        return self.env['subscription.payment'].browse(self._context.get('active_ids'))

    def state_payment_inv(self, amount, pay_date, pay_id, payment_difference):
        members_search = self.env['member.app'].search([('id', '=', self.member_id.id)])

        inv = [x.id for x in self.invoice_id]
        members_search.write({
            'section_line': [(6, 0, [sub.id for sub in self.section_line])],
            'invoice_id': [(4, inv)], 'date_of_last_sub': fields.Datetime.now(),
            'subscription_period': self.periods_month,
            'duration_period': self.duration_period,
            'number_period': self.number_period,
            'payment_ids': [(4, [pay_id])],
                                })
        self.state = 'done'
        self.total_paid += amount
        if self.state == "fined" and self.p_type == "ano":
            members_search.date_of_last_sub = fields.Datetime.now()
            return self.payment_button_normal()
        else:
            pass
           
    def create_outstanding_line(self, inv_id):
        invoice_line_obj = self.env["account.invoice.line"] 
        members_search = self.env['member.app'].search([('id', '=', self.member_id.id)])
        account_obj = self.env['account.invoice']
        accounts = account_obj.browse([inv_id]).journal_id.default_credit_account_id.id
        income_account = self.env['account.account'].search([('user_type_id.name', '=ilike', 'Income')], limit=1)
        
        balance = members_search.balance_total
        if balance != 0: 
            curr_invoice_subs = {
                                'name': "Added Outstanding", 
                                'price_unit': balance, 
                                'quantity': 1,
                                'account_id': accounts if accounts else income_account.id,
                                'invoice_id': inv_id,
                                }

            invoice_line_obj.create(curr_invoice_subs)
            members_search.balance_total -= balance

            
    def define_invoice_line(self,invoice):
        inv_id = invoice.id
        invoice_line_obj = self.env["account.invoice.line"]
        journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        prd_account_id = journal.default_credit_account_id.id
        self.create_outstanding_line(inv_id)

        section_lines = self.mapped('section_line') #.filtered(lambda self: self.sub_payment_id.paytype in ['others'])
        if section_lines:
            for record in section_lines:
                curr_invoice_line = {
                        # 'product_id': product_search.id if product_search else False,
                        'name': "Member Charge for "+ str(record.sub_payment_id.name) + ' -- ' +str(record.section_ids.name),
                        'price_unit': record.amount,
                        'quantity': 1.0,
                        'account_id': invoice.journal_id.default_credit_account_id.id if invoice.journal_id.default_credit_account_id else prd_account_id, #product_search.categ_id.property_account_income_categ_id.id,
                        'invoice_id': inv_id,
                            }
                invoice_line_obj.create(curr_invoice_line)
        else:
            raise ValidationError('Please ensure at the stage, \n \
                that section line with paytype as others is set\n \
                e.g Subscription Fee')

    def dependent_invoice_line(self, invoice):
        child_total = 0.0
        spouse_total = 0.0
        inv_id = invoice.id
        percentage_cut = 50/100
        invoice_line_obj = self.env["account.invoice.line"]
         
        if self.depend_name:
            child_lines = self.mapped('depend_name').filtered(lambda self: self.relationship == 'Child')
            spouse_lines = self.mapped('depend_name').filtered(lambda self: self.relationship != 'Child')
            if child_lines:
                for child in child_lines:
                    
                    section_lines = child.mapped('section_line')#.filtered(lambda self: self.sub_payment_id.paytype in ['special'])
                    for sub2 in section_lines:
                        total = 0.0
                        if sub2.is_child != True:
                            if sub2.sub_payment_id.paytype == "main_house" and child.mode in ["jun", "new"]:
                                discount = percentage_cut * sub2.amount 
                                total = (discount / 6) * self.number_period if self.duration_period == "Months" else (sub2.price_mainhouse * 2) * self.number_period 
                                child_total += total

                            else: # sub2.sub_payment_id.paytype == "main_house" and not child.mode in ["jun", "new"]:
                                total = (sub2.amount / 6) * self.number_period if self.duration_period == "Months" else (sub2.amount * 2) * self.number_period 
                                child_total += total
                        else:
                            total = 0
                            child_total += 0
                             
                        curr_invoice_child_subs = {
                            # 'product_id': product_child.id if product_child else False,
                            'name': "Child Charge for "+ str(sub2.sub_payment_id.name) + ' -- ' + str(sub2.section_ids.name), # if product_child else sub2.subscription.name)+ ": Period-"+(self.subscription_period),
                            'price_unit': total,
                            'quantity': 1.0,
                            'account_id': invoice.journal_id.default_credit_account_id.id,# product_child.categ_id.property_account_income_categ_id.id or record.account_id.id,
                            'invoice_id': inv_id,
                        }
                        invoice_line_obj.create(curr_invoice_child_subs)
                         
            if spouse_lines:
                for spouse in spouse_lines:
                    section_lines = spouse.mapped('section_line')#.filtered(lambda self: self.sub_payment_id.paytype in ['special'])
                    for sub2 in section_lines:
                        if sub2.special_subscription != True:
                            if sub2.sub_payment_id.paytype == "main_house" and spouse.mode in ["jun", "new"]:
                                discount = percentage_cut * sub2.amount 
                                spousetotal = (discount / 6) * self.number_period if self.duration_period == "Months" else (sub2.price_mainhouse * 2) * self.number_period 
                                spouse_total += spousetotal

                            else: # sub2.sub_payment_id.paytype == "main_house" and not child.mode in ["jun", "new"]:
                                spousetotal = (sub2.amount / 6) * self.number_period if self.duration_period == "Months" else (sub2.amount * 2) * self.number_period 
                                spouse_total += spousetotal
                        else:
                            spousetotal = sub2.amount
                            spouse_total += spousetotal 
                        curr_invoice_spouse_subs = {
                            # 'product_id': product_child.id if product_child else False,
                            'name': "Spouse Charge for "+ str(sub2.sub_payment_id.name) + ' -- ' + str(sub2.section_ids.name), # if product_child else sub2.subscription.name)+ ": Period-"+(self.subscription_period),
                            'price_unit': spousetotal,
                            'quantity': 1.0,
                            'account_id': invoice.journal_id.default_credit_account_id.id,# product_child.categ_id.property_account_income_categ_id.id or record.account_id.id,
                            'invoice_id': inv_id,
                        }
                        invoice_line_obj.create(curr_invoice_spouse_subs)
           
         
    def payment_button_normal(self): 
        """ Create Customer Invoice for members.
        """
        invoice_list = []
        products = self.env['product.product']
        invoice_obj = self.env["account.invoice"]
        members_search = self.env['member.app'].search([('id', '=', self.member_id.id)])
        
        for inv in self:
            invoice = invoice_obj.create({
                'partner_id': inv.partner_id.id,
                'account_id': inv.partner_id.property_account_receivable_id.id,
                'fiscal_position_id': inv.partner_id.property_account_position_id.id,
                'branch_id': self.env.user.branch_id.id, 
                'date_invoice': datetime.today(),
                'type': 'out_invoice', # vendor
                # 'type': 'out_invoice', # customer
                'company_id': self.env.user.company_id.id,
            })
            if self.state == 'suscription':
                self.define_invoice_line(invoice)
                self.dependent_invoice_line(invoice)
                invoice_list.append(invoice.id)
            
            elif self.p_type == "ano":
                percent = 12.5 / 100
                amount = percent * self.total_paid
                desc = 'Anomaly'
                self.create_invoice_line(invoice, amount, desc)  
                invoice_list.append(invoice.id)
            
            form_view_ref = self.env.ref('account.invoice_form', False)
            tree_view_ref = self.env.ref('account.invoice_tree', False)
            self.write({'invoice_id':[(4, invoice_list)]})

            return {
                    'domain': [('id', 'in', [item.id for item in self.invoice_id])],
                    'name': 'Invoices',
                    'view_mode': 'form',
                    'res_model': 'account.invoice',
                    'type': 'ir.actions.act_window',
                    'views': [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')],
                } 
     
    def create_invoice_line(self, invoice, amount, desc):
        invoice_line_obj = self.env["account.invoice.line"]
        inv_id = invoice.id
        curr_invoice_line = {
                # 'product_id': product_search.id if product_search else False,
                'name': "Charge for "+desc,
                'price_unit': amount,
                'quantity': 1.0,
                'account_id': invoice.journal_id.default_credit_account_id.id if invoice.journal_id.default_credit_account_id else prd_account_id, #product_search.categ_id.property_account_income_categ_id.id,
                'invoice_id': inv_id,
                    }
        invoice_line_obj.create(curr_invoice_line)

    @api.multi
    def generate_receipt(self):  # verify,
        search_view_ref = self.env.ref(
            'account.view_account_invoice_filter', False)
        form_view_ref = self.env.ref('account.invoice_form', False)
        tree_view_ref = self.env.ref('account.invoice_tree', False)
        return {
            'domain': [('id', 'in', [item.id for item in self.invoice_id])],
            'name': 'Invoices',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'views': [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')],
            'search_view_id': search_view_ref and search_view_ref.id,
        }

class subscription_LineMain(models.Model):
    _name = "subscription.line"

    member_id = fields.Many2one('member.app', 'Member ID')
    sub_order = fields.Many2one('subscription.model', 'Member ID')
    name = fields.Char('Activity', required=True)

    total_price = fields.Float(
        string='Total Price',
        digits=dp.get_precision('Product Price'),
        required=True)
    paid_amount = fields.Float(string='Paid Amount')
    balance = fields.Float(string='Balance')

    pdate = fields.Date(
        'Subscription Date',
        default=fields.Date.today(),
        required=True)
    periods_month = fields.Selection([
        ('Jan-June 2011', 'Jan-June 2011'),
        ('July-Dec 2011', 'July-Dec 2011'),
        ('Jan-June 2012', 'Jan-June 2012'),
        ('July-Dec 2012', 'July-Dec 2012'),
        ('Jan-June 2013', 'Jan-June 2013'),
        ('July-Dec 2013', 'July-Dec 2013'),
        ('Jan-June 2014', 'Jan-June 2014'),
        ('July-Dec 2014', 'July-Dec 2014'),
        ('Jan-June 2015', 'Jan-June 2015'),
        ('July-Dec 2015', 'July-Dec 2015'),
        ('Jan-June 2016', 'Jan-June 2016'),
        ('July-Dec 2016', 'July-Dec 2016'),
        ('Jan-June 2017', 'Jan-June 2017'),
        ('July-Dec 2017', 'July-Dec 2017'),
        ('Jan-June 2018', 'Jan-June 2018'),
        ('July-Dec 2018', 'July-Dec 2018'),
        ('Jan-June 2019', 'Jan-June 2019'),
        ('July-Dec 2019', 'July-Dec 2019'),
        ('Jan-June 2020', 'Jan-June 2020'),
        ('July-Dec 2020', 'July-Dec 2020'),
        ('Jan-June 2021', 'Jan-June 2021'),
        ('July-Dec 2021', 'July-Dec 2021'),
    ], 'Period', index=True, required=False, readonly=False, copy=False, 
                                           track_visibility='always')
