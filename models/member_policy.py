import time
from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import except_orm, ValidationError
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from odoo import http


class MemberShipPolicy(models.Model):
    _name = "member.policy"
    _rec_name = "periods_month"
    _order = "id desc"

    """
    Once the user selects the period, 
    select the operation type, either activation or deactivation,
    Set the start and end date, click the preview changes button, if operation type is "Deactivation", 
    Note:  the filtered list will be the records whose last subscritpion date falls between start and end date
    Click on the confirm changes button: if the operation type is deactivation, it will check all members that is not
    owning set deactivates them. {setting active fied to False}

    If operation type is Activation: click on the Activation changes button and the system automatically generate
    a bill for the records in the member line.
    """
     
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
    state = fields.Selection([
        ('Draft', 'Draft'),
        ('Deactivation', 'Deactivated'),
        ('Activation', 'Activated'),
        ('Invoiced', 'Invoiced'),
    ], 'state', index=True, readonly=False, default="Draft", copy=False,
                                           track_visibility='always')

    operation_type = fields.Selection([
        ('Activation', 'Activation'),
        ('Deactivation', 'Deactivation'),
    ], 'Operation type', default="Deactivation", index=True, required=True, readonly=False, copy=False,
                                           track_visibility='always')
    date_start = fields.Datetime('Filter From', required="True",
                                 default=lambda *a: (datetime.now() - relativedelta(days=29)).strftime('%Y-%m-%d %H:%M:%S'))
    date_end = fields.Datetime('Filter To', required=True,
                                default=lambda *a: (datetime.now() + relativedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'))
    get_member_ids = fields.Many2many("member.app", string='Members')
    policy_member_ids = fields.One2many("member.policy.line", 'policy_line_id', 
                                        string='Members Policy')
    active = fields.Boolean('Active', default=True)

    # Button to generate members records based on filter date of last subscription
    # @api.onchange('periods_month', 'date_start', 'date_end')
    def preview_changes(self):
        if (self.periods_month) and (self.date_start):
            if not (self.date_start > self.date_end):
                recs = []
                orders = self.env['member.app'].search([('date_of_last_sub', '>=', self.date_start), ('date_of_last_sub', '<=', self.date_end)])
                if len(orders) > 0:
                    for rec in orders:
                        # if (self.date_start <= rec.date_of_last_sub) and (self.date_end >= rec.date_of_last_sub):# and (rec.periods_month == self.periods_month):
                        recs.append(rec.id)
                        self.write({'get_member_ids': [(4, recs)]})
                        # else:
                        #     raise ValidationError('No record found for the filtered date')
            else:
                raise ValidationError('Start date cannot be greater than end start')
        else:
            raise ValidationError('Please insert Period and start date')

    @api.one
    def confirm_deactivation(self):
        if self.operation_type == "Deactivation":
            if self.get_member_ids:
                orders = self.env['member.app'].search([('date_of_last_sub', '>=', self.date_start), ('date_of_last_sub', '<=', self.date_end)])
                if orders:
                    for rec in orders:
                        # self.get_member_ids:
                        if rec.balance_total < 0:
                            rec.write({'activity': 'act'})
                        else:
                            rec.write({'activity': 'inact', 'date_of_last_sub': fields.Datetime.now()})
                else:
                    raise ValidationError('Start date cannot be greater than end start')
            else:
                raise ValidationError("No record generated")
            self.state = 'Deactivation'
        else:
            raise ValidationError("Please ensure you select Operation Type: Activation")
    
    @api.multi
    def confirm_activation(self):
        if self.operation_type == "Activation":
            if self.get_member_ids:
                member_list = []
                orders = self.env['member.app'].search([('date_of_last_sub', '>=', self.date_start), ('date_of_last_sub', '<=', self.date_end)])
                for partner in orders:
                    member_list.append((0, 0, {
                        'member_id': partner.id,
                        'activation_date': fields.Datetime.now(),
                        'depend_name': [(6, 0, [rec.id for rec in partner.mapped('depend_name')])]
                        }))
                self.write({'policy_member_ids': member_list})
                if len(self.policy_member_ids) > 0:
                    for each in self.policy_member_ids:
                        if each.member_id.section_line:
                            each.create_generate_invoice()
            else:
                raise ValidationError("No record found")
            self.state = "Activation"
        else:
            raise ValidationError("Please ensure you select Operation Type: Activation")
    
    @api.multi 
    def calculate_bill(self):
        for bill in self.policy_member_ids:
            bill.calculate_bill()
        self.state = "Invoiced"

 
class MemberShipPolicyLine(models.Model):
    _name = "member.policy.line"
    _order = "id desc"
    
    policy_line_id = fields.Many2one('member.policy', ondelete="cascade")
    member_id = fields.Many2one(
        'member.app',
        'Member ID',
        required=True,
        domain=[
            ('state',
             '!=',
             'suspension')],
        readonly=False)    
    identification = fields.Char('Member ID.', size=6, related="member_id.identification")
    state = fields.Selection([
        ('Draft', 'Draft'),
        ('Generated', 'Generated'),
        
    ], 'state', index=True, readonly=False, default="Draft", copy=False,
                                           track_visibility='always')
    invoice_id = fields.Many2one('account.invoice', string='Invoice', ondelete="cascade", store=True)    
    activation_date = fields.Datetime('Subscription Date')
    due_dates = fields.Datetime('Due Date')
    subscription = fields.Many2many(
        'subscription.payment',
        string='Add Sections') #, compute='get_all_packages', store=True)
    
    depend_name = fields.Many2many(
        'register.spouse.member',
        string="Dependents",store=True) # compute='get_all_packages', store=True)
    email = fields.Char('Email', related="member_id.email")
    section_line = fields.Many2many('section.line', string='Add Sections', compute='get_all_packages')
    package = fields.Many2many(
        'package.model',
        string='Packages',
        readonly=False,
        store=True,)
        # compute='get_all_packages')

    total = fields.Float('Total', default =0, compute="gen_total")
    balance_total = fields.Float('Outstanding', default =0)#, compute="gen_total")
    
    def button_confirm_member(self):
        self.member_id.date_of_last_sub = fields.Datetime.now()
        self.member_id.subscription_period = self.policy_line_id.periods_month
        self.member_id.activity = "act"
        self.member_id.biostar_status = False
        for dep in self.member_id.depend_name:
            dep.biostar_status = False


    @api.multi
    def see_breakdown_invoice(self): 
        search_view_ref = self.env.ref(
            'account.view_account_invoice_filter', False)
        form_view_ref = self.env.ref('account.invoice_form', False)
        tree_view_ref = self.env.ref('account.invoice_tree', False)

        return {
            'domain': [('id', 'in', [self.invoice_id.id])],
            'name': 'Membership Invoices',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            #  'views': [(form_view_ref.id, 'form')],
            'views': [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')],
            'search_view_id': search_view_ref and search_view_ref.id,
        }

    # @api.one
    # @api.depends("subscription","package", "depend_name")
    # def gen_total(self):
    #     # pass
    #     # self.balance_total += [self.member_id.balance_total
    #     subscription_cost, package_cost, depends_cost= 0,0,0
    #     for rec in self.subscription:
    #         subscription_cost += rec.total_cost
    #     for tec in self.package:
    #         package_cost += tec.package_cost
    #     for yec in self.depend_name:
    #         depends_cost += yec.total
    #     self.total = subscription_cost + package_cost + depends_cost

    @api.one
    @api.depends("section_line")
    def gen_total(self):
        member_line = self.member_id.mapped('section_line').filtered(lambda x: x.sub_payment_id.paytype not in ['main_house'])
        depends = self.member_id.mapped('depend_name')
        depends_total = 0
        for rec in depends:
            depend_line = rec.mapped('section_line').filtered(lambda x: x.sub_payment_id.paytype not in ['main_house'])
            depends_total = sum([amt.amount for amt in depend_line])

        subscription_cost = sum([amt.amount for amt in member_line])
        self.total = subscription_cost + depends_total
        self.balance_total = self.member_id.balance_total

    @api.onchange('member_id')
    def get_all_packages(self):
        """This will filter list of subscription that is not of type levy, entry fee, additional fee"""
        get_package = self.env['member.app'].search(
            [('id', '=', self.member_id.id)], limit=1)
        
        section_line = self.member_id.mapped('section_line').filtered(lambda x: x.sub_payment_id.paytype not in ['addition', 'entry_fee'])
        if section_line:
            self.section_line = section_line
        self.depend_name = get_package.depend_name
         
    # @api.one
    # @api.depends('member_id')
    # def get_all_packages(self):
    #     appends = []
    #     appends2 = []
    #     appends3 = []
    #     for ret in self.member_id.package:
    #         appends.append(ret.id)
    #     for rett in self.member_id.subscription:
    #         appends2.append(rett.id)
    #         self.subscription = appends2
    #     for spouse in self.member_id.depend_name:
    #         appends3.append(spouse.id)
    #         for spouse_subs in spouse.spouse_subscription:
    #             appends2.append(spouse_subs.subscription.id)
    #     for r in appends:
    #         self.package = [(4, r)] 
    #     for r2 in appends2:
    #         self.subscription = [(4, r2)]
    #     for r3 in appends3:
    #         self.depend_name = [(4, r3)]

    # def create_product(self, name):
    #     product = 0
    #     product = self.env['product.product'].search([('name', '=ilike', name)], limit=1)
    #     product = product.id
    #     if not product:
    #         product = self.env['product.product'].create({
    #             'name': name,
    #         }).id 
    #     return product
    
    # def create_branch(self):
    #     branch_id = 0
    #     branch = self.env['res.branch']
    #     branch_search = branch.search([('name', 'ilike', 'Ikoyi Club Lagos')], limit=1)
    #     if not branch_search:
    #         branch_create = branch.create(
    #             {'name': 'Ikoyi Club Lagos', 'company_id': self.env.user.company_id.id or 1})
    #         branch_id = branch_create.id
    #     else:
    #         branch_id = branch_search.id
    #     return branch_id

    @api.multi
    def create_generate_invoice(self):
        for each_depend in self.depend_name:
            depends = self.mapped('depend_name').filtered(lambda a: a.partner_id.property_account_receivable_id == False or a.partner_id.property_account_payable_id == False)
            if depends:
                for rec in depends:
                    rec.partner_id.property_account_receivable_id = self.env['account.account'].search([('user_type_id', '=', 1)], limit=1).id,
                    rec.partner_id.property_account_payable_id = self.env['account.account'].search([('user_type_id', '=', 2)], limit=1).id,
        memberObj = self.env['member.app'].search([('id', '=', self.member_id.id)])
        memberObj.create_white_member_bill()

        self.invoice_id = memberObj.invoice_id[0].id
        
        # invoice_list, array = [], []
        # invoice = self.env['account.invoice'].create({
        #         'partner_id': self.member_id.partner_id.id,
        #         #  partner.partner_id.property_account_receivable_id.id,
        #         # property_account_payable_id
        #         'account_id': self.member_id.account_id.id,
        #         'fiscal_position_id': self.member_id.partner_id.property_account_position_id.id,
        #         'branch_id': self.env.user.branch_id.id,
        #     })
        # # self.member_id.date_of_last_sub = fields.Datetime.now()
        # self.member_id.activity = "act"
        # self.member_id.invoice_id = [(4, invoice.id)]
        # if self.member_id.balance_total > 0:
        #     array.append((0, 0, {
        #         # 'product_id': self.create_product(each_subscription.name),
        #         'name': "Outanding Credits",
        #         'price_unit': self.member_id.balance_total,
        #         'invoice_id': invoice.id,
        #         'account_id': self.member_id.account_id.id or self.member_id.partner_id.property_account_payable_id.id,
        #         }))
        # for each_subscription in self.subscription:
        #     array.append((0, 0, {
        #         'product_id': self.create_product(each_subscription.name),
        #         'name': "Bills",
        #         'price_unit': each_subscription.total_cost,
        #         'invoice_id': invoice.id,
        #         'account_id': self.member_id.account_id.id or self.member_id.partner_id.property_account_payable_id.id,
        #         }))
         
        # for each_depend in self.depend_name:
        #     each_depend.partner_id.property_account_receivable_id=self.env['account.account'].search([('user_type_id', '=', 1)], limit=1).id,
        #     each_depend.partner_id.property_account_payable_id=self.env['account.account'].search([('user_type_id', '=', 2)], limit=1).id,
            
        #     for rex in each_depend.spouse_subscription:

        #         if each_depend.relationship == "Child":
        #             if rex.subscription.name == "Library (Child) -  Subscription" or rex.subscription.name == "Swimming (Child) - Subscription" or rex.subscription.is_child == True:
        #                 array.append((0, 0, {
        #                     'product_id': self.create_product(rex.subscription.name),
        #                     'name': "Child Bills",
        #                     'price_unit': rex.total_fee,
        #                     'invoice_id': invoice.id,
        #                     'account_id': self.member_id.account_id.id if self.member_id.account_id else self.env['account.account'].search([('user_type_id', '=', 1)], limit=1).id, # or self.member_id.partner_id.property_account_payable_id.id,
        #                     }))
        #         else:
        #             array.append((0, 0, {
        #                     'product_id': self.create_product(rex.subscription.name),
        #                     'name': "Dependent Bills for {}".format(each_depend.partner_id.name),
        #                     'price_unit': rex.total_fee,
        #                     'invoice_id': invoice.id,
        #                     'account_id': self.member_id.account_id.id if self.member_id.account_id else self.env['account.account'].search([('user_type_id', '=', 1)], limit=1).id, # or self.member_id.partner_id.property_account_payable_id.id,
        #                     }))
                
        # invoice.write({'invoice_line_ids': array})
        # self.invoice_id = invoice.id
         
    def generate_bill(self, amount, product_name):
        array = []
        values = {
                # 'product_id': self.create_product(product_name),
                'price_unit': amount,
                'name': "Desc: "+product_name,
                'invoice_id': self.invoice_id.id,
                'account_id': self.member_id.partner_id.property_account_payable_id.id,
                }
        array.append((0, 0, values))
        self.invoice_id.write({'invoice_line_ids': array}) 

    @api.multi 
    def calculate_bill(self):
        if self.activation_date or self.invoice_id:
            start = datetime.strptime(self.activation_date, "%Y-%m-%d %H:%M:%S")
            end_date = datetime.strptime(fields.Datetime.now(), "%Y-%m-%d %H:%M:%S")
            duration = end_date - start 
            duration = int(duration.days)
            if (duration > 89) and (duration in range(89, 91)): 
                if self.invoice_id.state != "paid":
                    self.generate_bill(10000, 'Penalty')
                    self.send_mail_to_member()
                    #raise ValidationError("1")
                    
            elif (duration > 90) and (duration in range(90, 180)): ## Session one
                if self.invoice_id.state != "paid":
                    self.generate_bill(110000, 'New Session Extra Charge')
                    self.send_mail_to_member()
                
            elif (duration > 180) and (duration in range(180, 360)): ## Session two 1year
                total = 0.0
                if self.invoice_id.state != "paid":
                    for rec in self.invoice_id.invoice_line_ids:
                        total += rec.amount_total
                    amount = (total * 0.1) - (10000) # 10% of the total bill - the initial penalty (10000)
                    amount = amount + 100000
                    self.generate_bill(amount, '10% Penalty Fee')
                    self.send_mail_to_member()
                    
            elif (duration > 360) and (duration in range(360, 540)): ## Session three
                total = 0.0
                if self.invoice_id.state != "paid":
                    for rec in self.invoice_id.invoice_line_ids:
                        total += rec.amount_total
                    amount = (total * 0.1) 
                    amount = amount + 100000
                    self.generate_bill(amount, '10% Penalty Fee - Extra')
                    self.send_mail_to_member()
            
            elif (duration > 540) and (duration in range(540, 720)):   ## Session four 2year
                total = 0.0
                if self.invoice_id.state != "paid":
                    for rec in self.invoice_id.invoice_line_ids:
                        total += rec.amount_total
                    amount = (total * 0.05)
                    amount = amount + 100000
                    self.generate_bill(amount, '5% Penalty Fee - Extra')
                    self.send_mail_to_member()
            
            elif (duration > 720) and (duration in range(720, 900)):  ## Session five  
                total = 0.0
                if self.invoice_id.state != "paid":
                    for rec in self.invoice_id.invoice_line_ids:
                        total += rec.amount_total
                    amount = (total * 0.05)  # 5% of the total bill -
                    amount = amount + 100000
                    self.generate_bill(amount, '5% Penalty Fee - Extra')
                    self.send_mail_to_member()
                                    
            elif (duration > 900) and (duration in range(720, 1080)): ## Session six 3year
                total = 0.0
                if self.invoice_id.state != "paid":
                    for rec in self.invoice_id.invoice_line_ids:
                        total += rec.amount_total
                    amount = (total * 0.05)  # 5% of the total bill -
                    amount = amount + 100000
                    self.generate_bill(amount, '5% Penalty Fee - Extra')
                    self.send_mail_to_member()
                    
            elif (duration > 1080) and (duration in range(1080, 1260)):  ## Session seven   
                total = 0.0
                if self.invoice_id.state != "paid":
                    for rec in self.invoice_id.invoice_line_ids:
                        total += rec.amount_total
                    amount = (total * 0.05)  # 5% of the total bill -
                    amount = amount + 100000
                    self.generate_bill(amount, '5% Penalty Fee - Extra')
                    self.send_mail_to_member()
                            
            elif (duration > 1260) and (duration in range(720, 1440)): ## Session eight 4year
                total = 0.0
                if self.invoice_id.state != "paid":
                    for rec in self.invoice_id.invoice_line_ids:
                        total += rec.amount_total
                    amount = (total * 0.05)  # 5% of the total bill -
                    amount = amount + 100000
                    self.generate_bill(amount, '5% Penalty Fee - Extra')
                    self.send_mail_to_member()
            else:
                pass
                # self.member_id.active = False
                # self.member_id.activity = False
        else: 
            raise ValidationError("Oops! No activation Date set for the record.")
  
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

    @api.multi
    def send_mail_to_member(self, force=False):  #  draft
        email_from = self.env.user.company_id.email
        group_user_id = self.env.ref('member_app.manager_member_ikoyi').id
        # extra = self.env.ref('ikoyi_module.inventory_officer_ikoyi').id
        extra = self.email
        bodyx = "Dear Sir/Madam, </br>We wish to notify that you -ID {} , that your membership subscription is \
        due for payment. An extra Penalty charge have been added to you bill: {} </br> Kindly contact the Ikoyi Club 1968 for any further enquires. \
        </br>Thanks" .format(self.member_id.identification, fields.Datetime.now())
        self.mail_sending(email_from, group_user_id, extra, bodyx)

    # @api.multi
    # def print_receipt_sus(self):
    #     report = self.env["ir.actions.report.xml"].search(
    #         [('report_name', '=', 'member_app.subscription_receipt_template')], limit=1)
    #     if report:
    #         report.write({'report_type': 'qweb-pdf'})
    #     return self.env['report'].get_action(
    #         self.id, 'member_app.subscription_receipt_template')

# #  FUNCTIONS # # # #
    # @api.multi
    # def send_mail_suspend(self, force=False):
    #     email_from = self.env.user.company_id.email
    #     group_user_id = self.env.ref('member_app.manager_member_ikoyi').id
    #     # extra = self.env.ref('ikoyi_module.inventory_officer_ikoyi').id
    #     extra = self.email
    #     bodyx = "Dear Sir/Madam, </br>We wish to notify that the member with ID {} have been Suspended from Ikoyi Club on the date: {} </br>\
    #          Kindly contact the Ikoyi Club 1968 for any further enquires. </br><a href={}> </b>Click <a/> to review. Thanks"\
    #          .format(self.member_id.identification, fields.Datetime.now(), self.get_url(self.id, self._name))
    #     self.mail_sending(email_from, group_user_id, extra, bodyx)

    # def get_url(self, id, model):
    #     base_url = http.request.env['ir.config_parameter'].sudo(
    #     ).get_param('web.base.url')
    #     base_url += '/web# id=%d&view_type=form&model=%s' % (id, model)

    def mail_sending(self, email_from, group_user_id, extra, bodyx):
        from_browse = self.env.user.name
        groups = self.env['res.groups']
        for order in self:
            group_users = groups.search([('id', '=', group_user_id)])
            group_emails = group_users.users
            # followers = []
            email_to = []
            # for group_mail in self.users_followers:
            #     followers.append(group_mail.work_email)
            for gec in group_emails:
                email_to.append(gec.login)
            email_froms = str(from_browse) + " <" + str(email_from) + ">"
            # mail_appends = (', '.join(str(item)for item in followers))
            mail_to = (','.join(str(item2)for item2 in email_to))
            subject = "Membership Suscription Notification"
            mail_data = {
                'email_from': email_froms,
                'subject': subject,
                'email_to': mail_to,
                'reply_to': email_from,
                'body_html': bodyx
            }
            mail_id = order.env['mail.mail'].create(mail_data)
            order.env['mail.mail'].send(mail_id)
