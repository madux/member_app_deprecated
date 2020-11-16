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


class Suspend_Member(models.Model):
    _name= "suspension.model"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _rec_name = "partner_id"

    _sql_constraints = [
        ('name_unique',
         'UNIQUE(partner_id)',
         'Partner must be unique')
    ]
    @api.constrains('partner_id')
    def check_suspended(self):
        self.ensure_one()
        member = self.env['member.app'].search(
                [('partner_id', '=', self.partner_id.id)])
        if member:
            if member.activity in ['inact', 'dom'] or member.state == "suspension":
                raise ValidationError('Member is already an inactive / suspended member')
        
    @api.multi
    def name_get(self):
        result = []
        for record in self:
            result.append(
                (record.id,u"%s - %s" % (record.member_id.partner_id.name, record.identification) 
                 ))
            record.name = result
        return result
        
    partner_id = fields.Many2one('res.partner', 'Name', domain=[('is_member','=', True)])
    member_id = fields.Many2one('member.app', 'Member Name', domain=[('state','!=', 'suspension')], readonly=False, compute="Domain_Member_Field")
    identification = fields.Char('identification.', size=7)
    email = fields.Char('Email', store=True)
    account_id = fields.Many2one('account.account', 'Account')
    date = fields.Datetime('Date', required=True)
    suspension_date = fields.Datetime('Suspension Date')
    users_followers = fields.Many2many('hr.employee', string='Add followers')
    subscription = fields.Many2many('subscription.payment', string ='Add Sections') # , compute='get_all_packages')
    package = fields.Many2many('package.model', string ='Packages', readonly=False)#  compute='get_all_packages')# ,compute='get_all_packages')
    state = fields.Selection([('draft','Draft'),
                                ('hon_sec','Honourary'),
                                ('member','Membership Officer'),
                                ('manager_approve','Manager'),
                                ('suspend','Suspended'),
                                ], default = 'draft', string='Status')
    mode= fields.Selection(
                string=u'Suspension Type', 
                required=True,
                selection=[('no_self_suspend', 'Self Suspension'), ('club_suspension', 'Club Suspension')]
            )
    main_house_cost = fields.Float('Main House Fee',required=False)
    payment_ids = fields.Many2many(
        'account.payment',
        string='All Payments', compute="_get_record_ids")
    invoice_id = fields.Many2many('account.invoice', string='Invoice', store=True)
    balance_total = fields.Integer(
        'Outstandings',  compute="_get_record_ids"
        )

    @api.depends('member_id')
    def _get_record_ids(self):
        payment_list = []
        for rec in self.member_id.payment_ids:
            payment_list.append(rec.id) 
        self.payment_ids = payment_list
        self.balance_total = self.member_id.balance_total

        
    @api.depends('member_id')
    def get_all_packages(self):
        pass
         
    @api.one
    @api.depends('partner_id')
    def Domain_Member_Field(self):
        if self.partner_id:
            member = self.env['member.app'].search([('partner_id', '=', self.partner_id.id)], limit=1)
            
            if member:
                for tec in member:
                    self.identification = tec.identification
                    self.email = tec.email
                    self.member_id = tec.id
            else:
                raise ValidationError('No Member record matched')

    @api.multi
    def send_to_hon(self):
        self.write({'state':'hon_sec'})
        self.send_mail_to_manager()
        
    @api.multi
    def send_to_hon_back(self):
        self.write({'state':'draft'})
        # self.send_mail_to_manager()
        
    @api.multi
    def send_hon_to_manager(self):
        self.write({'state':'member'})
        self.send_mail_officer()
        
        
    @api.multi
    def send_manager_to_approve(self):
        memberx = self.env['member.app'].search([('partner_id', '=', self.partner_id.id)]) 
        if memberx:
            for rec in memberx:
                rec.write({'state': "suspension", 'activity':'inact'})
            self.write({'state':'suspend', 'suspension_date':fields.Datetime.now()})
            
            spouse = self.env['register.spouse.member'].search([('sponsor','=',self.member_id.id)])
            for spouses in spouse:
                spouses.write({'active':False})
            
            self.send_mail_suspend()
        else:
            raise ValidationError('No member record found')
        
        
# #  FUNCTIONS # # # # #     
    @api.multi
    def send_mail_suspend(self, force=False):
        email_from = self.env.user.company_id.email
        group_user_id = self.env.ref('member_app.manager_member_ikoyi').id
        # extra = self.env.ref('ikoyi_module.inventory_officer_ikoyi').id
        extra=self.email
        bodyx = "Dear Sir/Madam, </br>We wish to notify that the member with ID {} have been Suspended from Ikoyi Club on the date: {} </br>\
             Kindly contact the Ikoyi Club 1938 for any further enquires. </br><a href={}> </b>Click <a/> to review. Thanks"\
             .format(self.identification,fields.Datetime.now(),self.get_url(self.id, self._name))
        self.mail_sending(email_from,group_user_id,extra,bodyx) 
    
    @api.multi
    def send_mail_officer(self, force=False):
        email_from = self.env.user.company_id.email
        group_user_id = self.env.ref('member_app.membership_officer_ikoyi').id
        # extra = self.env.ref('ikoyi_module.inventory_officer_ikoyi').id
        extra=self.env.user.company_id.email
        bodyx = "Dear Sir/Madam, </br>We wish to notify that the member with ID {} have requested for self suspension from Ikoyi Club on the date: {} </br>\
             Kindly </br><a href={}> </b>Click <a/> to review. Thanks"\
             .format(self.identification,fields.Datetime.now(),self.get_url(self.id, self._name))
        self.mail_sending(email_from,group_user_id,extra,bodyx) 
       
    @api.multi
    def send_mail_to_manager(self, force=False):
        email_from = self.env.user.company_id.email
        group_user_id = self.env.ref('member_app.membership_honour_ikoyi').id
        # extra = self.env.ref('ikoyi_module.inventory_officer_ikoyi').id
        
        extra=self.email
        bodyx = "Sir/Madam, </br>We wish to notify you that a member with ID: {} have been Suspended from Ikoyi Club on the date: {} </br>\
             Kindly <a href={}> </b>Click <a/> to Login to the ERP to view</br> \
             Thanks".format(self.identification,fields.Datetime.now(),self.get_url(self.id, self._name))
        self.mail_sending(email_from,group_user_id,extra,bodyx) 
            
        
    def get_url(self, id, model):    
        base_url = http.request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        base_url += '/web# id=%d&view_type=form&model=%s' % (id, model)
        
    def mail_sending(self, email_from,group_user_id,extra, bodyx):
        from_browse =self.env.user.name
        groups = self.env['res.groups']
        for order in self:
            group_users = groups.search([('id','=',group_user_id)])
            group_emails = group_users.users
            followers = []
            email_to=[]
            for group_mail in self.users_followers:
                followers.append(group_mail.work_email)

            for gec in group_emails:
                email_to.append(gec.login)

            email_froms = str(from_browse) + " <"+str(email_from)+">"
            mail_appends = (', '.join(str(item)for item in followers))
            mail_to = (','.join(str(item2)for item2 in email_to))
            subject = "Membership Suspension Notification"

            extrax = (', '.join(str(extra)))
            followers.append(extrax)
            mail_data={
                'email_from': email_froms,
                'subject':subject,
                'email_to':mail_to,
                'email_cc':mail_appends,#  + (','.join(str(extra)),
                'reply_to': email_from,
                'body_html':bodyx
                }
            mail_id =  order.env['mail.mail'].create(mail_data)
            order.env['mail.mail'].send(mail_id)
    
    # def define_package_invoice_line(self,invoice):
    #     products = self.env['product.product']
    #     invoice_line_obj = self.env["account.invoice.line"]
         
    #     inv_id = invoice.id
    #     for pack in self.package:
    #         product_search = products.search([('name', '=ilike', pack.name)], limit=1)
    #         if product_search:      
    #             total = product_search.list_price # * self.number_period
    #             curr_invoice_pack = {
    #                             'product_id': product_search.id,
    #                             'name': "Charge for "+ str(product_search.name),
    #                             'price_unit': total, 
    #                             'quantity': 1.0,
    #                             'account_id': invoice.journal_id.default_credit_account_id.id, # product_search.categ_id.property_account_income_categ_id.id or self.account_id.id,
    #                             'invoice_id': inv_id,
    #                                 }
    #             invoice_line_obj.create(curr_invoice_pack) 
  
    @api.multi
    def create_member_bill(self):
        
        """ Create Customer Invoice for members.
        """
        invoice_list = [] 
        products = self.env['product.product']
        invoice_line_obj = self.env["account.invoice.line"]
        invoice_obj = self.env["account.invoice"]
        amount = 0.0
        for inv in self:
            invoice = invoice_obj.create({
                'partner_id': inv.partner_id.id,
                'account_id': inv.partner_id.property_account_receivable_id.id,
                'fiscal_position_id': inv.partner_id.property_account_position_id.id,
                'branch_id': self.env.user.branch_id.id, 
                'date_invoice': datetime.today(),
                'type': 'out_invoice',  
                'company_id': self.env.user.company_id.id,
                # 'type': 'out_invoice', # customer
            }) 
             
            self.define_invoice_line(invoice)
            self.dependent_invoice_line(invoice)
            invoice_list.append(invoice.id) 
            member_get = self.env['member.app'].search([('id','=',self.member_id.id)])
            if member_get:       
                member_get.write({'invoice_id':[(4, invoice_list)]}) 
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
    
    @api.multi
    def payment_button(self):
        return self.create_member_bill()


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

        section_lines = self.member_id.mapped('section_line') #.filtered(lambda self: self.sub_payment_id.paytype in ['others'])
        if section_lines:
            for record in section_lines:
                curr_invoice_line = {
                        'name': "Member Charge for "+ str(record.sub_payment_id.name) + ' -- ' +str(record.section_ids.name),
                        'price_unit': record.amount,
                        'quantity': 1.0,
                        'account_id': invoice.journal_id.default_credit_account_id.id if invoice.journal_id.default_credit_account_id else prd_account_id, #product_search.categ_id.property_account_income_categ_id.id,
                        'invoice_id': inv_id,
                            }
                invoice_line_obj.create(curr_invoice_line)
        else:
            raise ValidationError('There is no section attached for this member. \n\
                Kindly add one and continue.')

    def dependent_invoice_line(self, invoice):
        child_total = 0.0
        spouse_total = 0.0
        inv_id = invoice.id
        percentage_cut = 50/100
        invoice_line_obj = self.env["account.invoice.line"]
         
        if self.member_id.depend_name:
            child_lines = self.member_id.mapped('depend_name').filtered(lambda self: self.relationship == 'Child')
            spouse_lines = self.member_id.mapped('depend_name').filtered(lambda self: self.relationship != 'Child')
            if child_lines:
                for child in child_lines:
                    
                    section_lines = child.mapped('section_line')#.filtered(lambda self: self.sub_payment_id.paytype in ['special'])
                    for sub2 in section_lines:
                        total = 0.0
                        if sub2.is_child != True:
                            if sub2.sub_payment_id.paytype == "main_house" and child.mode in ["jun", "new"]:
                                discount = percentage_cut * sub2.amount 
                                total = (discount / 6) * self.member_id.number_period if self.member_id.duration_period == "Months" else (sub2.price_mainhouse * 2) * self.member_id.number_period 
                                child_total += total

                            else: # sub2.sub_payment_id.paytype == "main_house" and not child.mode in ["jun", "new"]:
                                total = (sub2.amount / 6) * self.member_id.number_period if self.member_id.duration_period == "Months" else (sub2.amount * 2) * self.member_id.number_period 
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
                                spousetotal = (discount / 6) * self.member_id.number_period if self.member_id.duration_period == "Months" else (sub2.price_mainhouse * 2) * self.member_id.number_period 
                                spouse_total += spousetotal

                            else: # sub2.sub_payment_id.paytype == "main_house" and not child.mode in ["jun", "new"]:
                                spousetotal = (sub2.amount / 6) * self.member_id.number_period if self.member_id.duration_period == "Months" else (sub2.amount * 2) * self.member_id.number_period 
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
     
    @api.multi
    def button_payments(self,name,amount,level):#  Send memo back
        return {
              'name':name,
              'view_type': 'form',
              "view_mode": 'form',
              'res_model': 'register.payment.member',
              'type': 'ir.actions.act_window',
              'target': 'new',
              'context': {
                  'default_payment_type': "outbound",
                  'default_date': fields.Datetime.now(),
                  'default_amount':amount,
                  
                  'default_partner_id':self.partner_id.id,
                  'default_member_ref':self.member_id.id,
                  'default_name':name,
                  'default_level':level,
                  'default_to_pay':amount,
                  'default_num':self.id,

                  # 'default_communication':self.number
              },
        }
    @api.multi
    def send_mail_officer_main(self, force=False):
        email_from = self.env.user.company_id.email
        group_user_id = self.env.ref('member_app.manager_member_ikoyi').id 
        extra=self.env.user.company_id.email
        bodyx = "Dear Sir/Madam, </br>We wish to notify that the member with ID {} have requested for self suspension from Ikoyi Club on the date: {} </br>\
             He has also completed his payments.</br> Kindly </br><a href={}> </b>Click <a/> to review. Thanks"\
             .format(self.identification,fields.Datetime.now(),self.get_url(self.id, self._name))
        self.mail_sending(email_from,group_user_id,extra,bodyx) 
          
    def state_payment_inv(self):
        self.send_mail_officer_main()
        self.write({'state':'manager_approve'})
         