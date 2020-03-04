import time
from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import except_orm, ValidationError
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from odoo import http
import base64
TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale',
    'in_refund': 'purchase',
}


class Reinstate_Member(models.Model):
    _name = "reinstatement.model"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _rec_name = "member_id"

    _sql_constraints = [
        ('name_unique',
         'UNIQUE(member_id)',
         'Member must be unique')
    ]
    @api.multi
    def name_get(self):
        result = []
        for record in self:
            result.append(
                (record.id,u"%s - %s" % (record.member_id.partner_id.name, record.identification) 
                 ))
            record.name = result
        return result

    binary_attach_letter = fields.Binary('Attach letter')
    binary_fname_letter = fields.Char('Attach Report') 
    member_id = fields.Many2one(
        'member.app',
        'Member ID',
        domain=['|', ('active', '=', False), ('activity', 'in', ['dom','inact'])],
        readonly=False,
        )
    identification = fields.Char('Identification.', compute="GET_Member_Field", store=True, size=6)
    email = fields.Char('Email', compute="GET_Member_Field",store=True) 
    date = fields.Datetime('Date', required=True) 
    description_two = fields.Text('Refusal Reasons') 
    users_followers = fields.Many2many('hr.employee', string='Add followers')
    subscription = fields.Many2many(
        'subscription.payment',
        string='Add Sections',
        readonly=False,
        store=True,
        compute='get_all_packages')
    package = fields.Many2many(
        'package.model',
        string='Packages',
        readonly=False,
        store=True,
        compute='get_all_packages')  #  ,compute='get_all_packages')
    state = fields.Selection([('draft', 'Draft'),
                              ('internalcontrol', 'Internal Control'),
                              ('mem_two', 'Membership'),
                              ('wait', 'Waiting'),
                              ('paid', 'Paid'),
                              ('finance', 'F&A'),
                              ('fined', 'Fined'),
                              ('manager_approve', 'Manager'),
                              ('done', 'Done'),
                              ], default='draft', string='Status')
    payments_all = fields.Many2many(
        'member.payment.new',
        string='All Payments',
        readonly=False,
        store=True,compute='get_all_packages')
    p_type = fields.Selection([('yes', 'No'),
                               ('no', 'Yes'),
                               
                               ], default='no', string='Anomaly') 
    payment_renew = fields.Many2many(
        'subscription.line',
        string='Renewals Payments',
        readonly=False,compute='get_all_packages',
        store=True,
        ) 
    balance = fields.Float(string='Balance',store=True, compute='get_all_cost', default=0.0)
    total = fields.Float(
        'Total paid Fee', store=True, compute='get_all_cost')
    addition = fields.Float(
        'Extra Charge', default=100000, required=True,
        )
    last_date = fields.Date('Last Subscribed Date', store=True, compute='lastdate', required=False)
    account_id = fields.Many2one('account.account', compute="GET_Member_Field",
    string='Account')
    invoice_id = fields.Many2one('account.invoice', 'Invoice', store=True)

    binary_attach_proof = fields.Binary('Payment Proof') # required in wait
    binary_fname_proof = fields.Char('Attach Proof')

    @api.onchange('member_id')
    def onchange_member_id(self):
        res = {}
        if self.member_id:
            res['domain'] = {
                'invoice_id': [('partner_id', '=', self.member_id.partner_id.id), ('state', '!=', 'paid')],
                }
        return res
 
    @api.depends('payment_renew','payments_all')
    def get_all_cost(self):
        total_bal = 0.0
        total1 = 0.0 
        total_bal2 = 0.0
        total2 = 0.0
        for rec in self.payment_renew:
            total_bal += rec.balance
            total1 += rec.paid_amount
        for tec in self.payments_all:
            total_bal2 += tec.balance
            total2 += tec.paid_amount 
        self.balance = total_bal + total_bal2
        self.total = total1 + total2
    
    @api.depends('member_id')
    def GET_Member_Field(self):
        for record in self:
            member = self.env['member.app'].search(
                [('id', '=', record.member_id.id)])
            for tec in member:
                # record.main_house_cost = tec.main_house_cost
                record.account_id = tec.account_id.id
                record.identification = tec.identification
                record.email = tec.email
                
    @api.depends('member_id')
    def get_all_packages(self):
        get_package = self.env['member.app'].search(
            [('id', '=', self.member_id.id)])
        appends = []
        appends2 = []
        appends3 = []
        appends4 = []
        #  for rec in self:
        for ret in get_package.package:
            appends.append(ret.id)
        for rett in get_package.subscription:
            appends2.append(rett.id)
        for cec in get_package.payment_line2:
            appends3.append(cec.id)
        for pec in get_package.sub_line:
            appends4.append(pec.id)
                 
        self.package = [(6, 0, appends)] 
        self.subscription = [(6, 0, appends2)]  
        self.payments_all = [(6, 0,appends3)] 
        self.payment_renew = [(6, 0,appends4)] 
    
    @api.depends('payment_renew')        
    def lastdate(self):
        for rec in self:  
            for date in rec.payment_renew:
                last_date = date[-1].pdate
                self.last_date = last_date 
    # ######### MEMBERSHIP CREATES INVOICE ON DRAFT ###############
    
    @api.multi
    def send_mail_to_internal_control(self, force=False):  #  draft 
        email_from = self.env.user.login
        group_user_id = self.env.ref('member_app.membership_honour_ikoyi').id
        # extra = self.env.ref('ikoyi_module.inventory_officer_ikoyi').id
        email = self.env.ref('ikoyi_module.audit_boss_ikoyi')[0].id
        
        extra = email
        bodyx = "Dear Sir/Madam, </br>I wish to notify you that a member with-ID {} , has requested for reinstatement and \
        an invoice has been generated for payment on the date: {} </br> Kindly <a href={}> </b>Click <a/> to Login to the ERP to view</br> \
        </br>Thanks" .format(self.identification, fields.Datetime.now(), self.get_url(self.id, self._name))
        self.mail_sending(email_from, group_user_id, extra, bodyx)
        
    @api.multi
    def send_mail_member_two(self, force=False):  #  draft 
        email_from = self.env.user.login
        group_user_id = self.env.ref('member_app.membership_officer_ikoyi').id
        # extra = self.env.ref('ikoyi_module.inventory_officer_ikoyi').id 
        email = self.env.ref('member_app.manager_member_ikoyi')[0].id
        extra = email 
        bodyx = "Dear Sir/Madam, </br>I wish to notify you that a member with-ID {} , requesting for reinstatement have \
        been approved by Internal control on the date: {} </br> Kindly <a href={}> </b>Click <a/> to Login to the ERP to view</br> \
        </br>Thanks" .format(self.identification, fields.Datetime.now(), self.get_url(self.id, self._name))
        self.mail_sending(email_from, group_user_id, extra, bodyx)
    
    @api.multi
    def send_mail_member(self, force=False):  #  draft 
        email_from = self.env.user.login
        group_user_id = self.env.ref('member_app.membership_officer_ikoyi').id
        # extra = self.env.ref('ikoyi_module.inventory_officer_ikoyi').id 
        # email = self.env.ref('ikoyi_module.manager_member_ikoyi').id
        bills = self.balance + self.addition
        email = self.email #email[0].login
        bodyx = "Dear Sir/Madam, </br>I wish to notify you (-ID {} ), that prior to your request for reinstatement, you have been billed \
        the sum of {} on the date: {} </br> Kindly contact the Ikoyi Club 1938 for any further enquires.\
        </br>Thanks" .format(self.identification,bills, fields.Datetime.now())
        self.mail_sending_single(email_from, group_user_id, email, bodyx)
    
    
    @api.multi
    def manager_send_mail_member(self, force=False):  #   
        email_from = self.env.user.login
        group_user_id = self.env.ref('member_app.membership_officer_ikoyi').id
    
        email = self.email #email[0].login
        bodyx = "Dear Sir/Madam, </br>I wish to notify you (-ID {} ), that prior to your request for reinstatement,\
        you have been confirmed as an \
        active member on the date: {} </br> Kindly contact the Ikoyi Club 1938 for any further enquires.\
        </br>Thanks" .format(self.identification, fields.Datetime.now())
        self.mail_sending_single(email_from, group_user_id, email, bodyx)
    
    @api.multi
    def send_anomaly_to_fa(self, force=False):  #  draft 
        email_from = self.env.user.login
        group_user_id = self.env.ref('ikoyi_module.account_boss_ikoyi').id
        # extra = self.env.ref('ikoyi_module.inventory_officer_ikoyi').id
        email = self.env.ref('ikoyi_module.accountant_ikoyi')[0].id
        
        extra = email
        bodyx = "Dear Sir/Madam, </br>I wish to notify you that a member with-ID {} , has Anomalies on his payment with invoice Ref: {} \
        paid on the date: {} </br> Kindly <a href={}> </b>Click <a/> to Login to the ERP to view</br> \
        </br>Thanks" .format(self.identification, self.invoice_id.name, self.invoice_id.date_invoice, self.get_url(self.id, self._name))
        self.mail_sending(email_from, group_user_id, extra, bodyx) 
     
    @api.multi
    def send_mail_ano_member_officer(self, force=False):  #  draft 
        email_from = self.env.user.login
        group_user_id = self.env.ref('member_app.membership_officer_ikoyi').id
        # extra = self.env.ref('ikoyi_module.inventory_officer_ikoyi').id 
        # email = self.env.ref('ikoyi_module.manager_member_ikoyi').id
         
        email = self.email #email[0].login
        bodyx = "Dear Sir/Madam, </br>I wish to notify you that a member with-ID {} , has  been fined 12.5 % for \
        Anomalies in your payment. \
        </br>Thanks" .format(self.identification)
        self.mail_sending_single(email_from, group_user_id, email, bodyx) 
            
    @api.multi
    def button_create_invoice(self):  # invoice memberofficer
        return self.create_invoice()           
    
    @api.multi
    def button_send_to_IC(self):  # invoice memberofficer
        self.write({'state': 'internalcontrol'})
        self.send_mail_to_internal_control()
        #return self.create_invoice()
        
    @api.multi
    def IC_send_to_memberofficer(self):  # invoice memberofficer
        self.write({'state': 'mem_two'})
        self.send_mail_member_two()    

    @api.multi
    def memberofficer_send_to_member(self):  #  invoice memberofficer
        self.write({'state': 'wait'})
        return self.view_and_send_invoice()  ### Here should be send invoice by mail
        
    # @api.multi
    def view_and_send_invoice(self):  #  Send memo back view_and_send_invoice
        form_view_ref = self.env.ref('account.invoice_form', True)
        return {
            'name': "Invoice",
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'views': [(form_view_ref.id, 'form')],
    
            'res_id': self.invoice_id.id,
            #'domain': [('id', '=', self.invoice_id.id)],
        }

    @api.multi
    def confirm_invoice_payment(self):  #  invoice memberofficer wait
        self.write({'state': 'paid'})
        return self.send_mail_biodata_to_member()

    @api.multi
    def generate_bio_data(self): #  paid

        report = self.env['ir.actions.report.xml'].search([('report_name','=', 'member_app.print_biodata_template')])
        if report:
            report.write({'report_type':'qweb-html'})
        return self.env['report'].get_action(self, 'member_app.print_biodata_template')
    
    @api.multi 
    def send_mail_manager_biodata(self, force=False):  # paid
        self.write({'state': 'manager_approve'})
        email_from = self.env.user.login
        group_user_id = self.env.ref('member_app.membership_officer_ikoyi').id
        # extra = self.env.ref('ikoyi_module.inventory_officer_ikoyi').id
        email = self.env.ref('member_app.membership_honour_ikoyi')[0].id
        extra = email
        subject = "Member Reinstatement Notification"
        bodyx = "Dear Sir/Madam, </br>I wish to notify you that a member with ID {}, have requested for reinstatement. After due approvals and payments, \
        a bio-data for have been generated on the date: {} </br> Kindly <a href={}> </b>Click <a/> to Login to the ERP to Approve</br>\
        </br>Thanks" .format(self.identification, fields.Datetime.now(), self.get_url(self.id, self._name))
        return self.mail_sending_one(email_from, extra, bodyx, subject)
    
    @api.multi
    def reject_mail(self, force=False):  #  draft 
        email_from = self.env.user.login
        group_user_id = self.env.ref('member_app.membership_honour_ikoyi').id
        # extra = self.env.ref('ikoyi_module.inventory_officer_ikoyi').id
        email = self.env.ref('member_app.membership_honour_ikoyi')[0].id
        
        extra = email
        bodyx = "Dear Sir/Madam, </br>I wish to notify you that a reinstatement request for a member with-ID {} ,has been rejected by the internal control officer: '{}'\
        on the date: {} </br> Kindly <a href={}> </b>Click <a/> to Login to the ERP to view</br> \
        </br>Thanks" .format(self.identification, self.env.user.name, fields.Date.today(), self.get_url(self.id, self._name))
        self.mail_sending(email_from, group_user_id, extra, bodyx)
    
    @api.multi
    def button_rejects(self):  #  store_manager,manager_two,
        if not self.description_two:
            raise ValidationError(
                'Please Add a Remark in the Refusal Note tab below')
        else:
            if self.state == "internalcontrol":
                self.state = "draft"
                self.reject_mail() 
    
    @api.multi 
    def send_mail_biodata_to_member(self, force=False):  # paid
        email_from = self.env.user.login
        group_user_id = self.env.ref('member_app.manager_member_ikoyi').id
        # extra = self.env.ref('ikoyi_module.inventory_officer_ikoyi').id
        #email = self.env.ref('member_app.membership_honour_ikoyi').id
        extra = self.email
        subject = "Member Reinstatement Notification"
        bodyx = "Dear Sir/Madam, </br>I wish to notify you that your Bio-data have been sent to you after your request for reinstatement.</br> \
        Kindly contact Ikoyi Club 1938 for further enquires</br>\
        </br>Thanks"# .format(self.identification, fields.Datetime.now(), self.get_url(self.id, self._name))
        return self.mail_sending_one(email_from, extra, bodyx, subject)
        
    @api.multi
    def manager_send_approve(self): 
         # manager_approve
        member = self.env['member.app'].search(
                [('id', '=', self.member_id.id)])
        if member:
            
            self.write({'state': 'done'})
            return member.write({'activity':'act'})
        else:
            raise ValidationError('No member record found to Reinstate')
        
    # ANOMALY
    @api.multi
    def ano_send_fa(self):
        self.write({'state':'finance'})
        return self.send_anomaly_to_fa()
    
    @api.multi
    def send_Finmanager_Fine(self):  #  finance , accountboss
        member = self.env['member.app'].search([('id', '=', self.member_id.id)])
        if member:
            member.write({'active':True, 'activity':'inact'})
        self.write({'state': 'fined', })
        self.send_mail_ano_member_officer()
        return self.button_payments()
    
    @api.multi
    def send_back(self):
        self.write({'state': 'paid'})
        return self.create_invoice()
   
    def button_payments(self):
        name = "."
        percent = 12.5 / 100
        amount = 0.0
        amount = percent * (self.addition + self.balance)
        name = "Fine" 
        form_view_ref = self.env.ref('account.view_account_payment_form', True)
        return {
            'name': name,
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'account.payment',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'views': [(form_view_ref.id, 'form')],
    
            #'res_id': self.invoice_id.id,
            #'domain': [('id', '=', self.invoice_id.id)],
            'context': {
                'default_payment_type': "inbound",
                'default_payment_date': fields.Datetime.now(),
                'default_amount': amount,
                'default_payment_type': "inbound",
                'default_payment_date': fields.Datetime.now(),

                'default_partner_id': self.member_id.partner_id.id,
                 
                'default_name': "Fined Payments", 
            }
        }
################# Anomaly ############################
     
    def mail_sending_one(self, email_from, mail_to, bodyx, subject):
        REPORT_NAME = 'member_app.print_biodata_template' #ikoyi_module.print_creditdebit_template
        # pdf = self.env['report'].sudo().get_pdf([invoice.id], 'ikoyi_module.print_credit_report')
        pdf = self.env['report'].get_pdf(self.ids, REPORT_NAME) # 
        b64_pdf = base64.encodestring(pdf)
        lists= []
        # save pdf as attachment 
        ATTACHMENT_NAME = "BIO DATA FORM"
        tech = self.env['ir.attachment'].create({
            'name': ATTACHMENT_NAME,
            'type': 'binary',
            'datas': b64_pdf,
            'datas_fname': ATTACHMENT_NAME + '.pdf',
            'store_fname': ATTACHMENT_NAME,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype' : 'application/x-pdf'
        })
        lists.append(tech.id)
        
        for order in self:
            # report_ref = self.env.ref('ikoyi_module.print_credit_report').id #'report_template':report_ref,
            mail_tos = str(mail_to)
            email_froms = "Ikoyi Club " + " <" + str(email_from) + ">"
            subject = subject
            mail_data = {
                'email_from': email_froms,
                'subject': subject,
                'email_to': mail_tos,
                # 'email_cc':,#  + (','.join(str(extra)),<field name="report_template" ref="YOUR_report_xml_id"/>
                'reply_to': email_from,
                'attachment_ids': [(6,0,lists)],#tech.id,
                # 'report_template':report_ref,
                'body_html': bodyx,
                        }
            mail_id = order.env['mail.mail'].create(mail_data)
            order.env['mail.mail'].send(mail_id) 
      
    # ###########   #######   #######   ############### INVOICING ################################# # 
    @api.multi
    def create_invoice(self):  # invoice memoficer
        if self:
            invoice_list = self.create_membership_invoice()
            search_view_ref = self.env.ref(
                'account.view_account_invoice_filter', False)
            form_view_ref = self.env.ref('account.invoice_form', False)
            tree_view_ref = self.env.ref('account.invoice_tree', False)
            return {
                'domain': [('id', '=', self.invoice_id.id)],
                'name': 'Membership Invoices',
                'res_model': 'account.invoice',
                'type': 'ir.actions.act_window',
                'views': [(tree_view_ref.id, 'tree'),(form_view_ref.id, 'form')],
                'search_view_id': search_view_ref and search_view_ref.id,
            }
# account.invoice_form form_view_ref = self.env.ref('account.invoice_form', False) form_view_ref = self.env.ref('account.invoice_form', False)
    @api.multi
    def create_membership_invoice(self):
        """ Create Customer Invoice of Membership for partners.
        @param datas: datas has dictionary value which consist Id of Membership product and Cost Amount of Membership.
                      datas = {'membership_product_id': None, 'amount': None}
        """
        amount = self.balance + self.addition
        product = 0
        state_now = str(self.state).replace('_', ' ').capitalize()
        products = self.env['product.product']
        product_search = products.search(
            [('name', '=ilike', 'Reinstatement')])
        if product_search:
            product = product_search[0].id
        else:
            pro = products.create(
                {'name': 'Reinstatement', 'type':'service', 'membershipx': True, 'list_price': amount})
            product = pro.id
        product_id = product
        self.write({'product_id': product})

        invoice_list = []
        branch_id = 0
        branch = self.env['res.branch']
        branch_search = branch.search([('name', '=ilike', 'Ikoyi Club Lagos')])
        if branch_search:
            branch_id = branch_search[0].id

        else:
            branch_create = branch.create(
                {'name': 'Ikoyi Club Lagos', 'company_id': self.env.user.company_id.id or 1})
            branch_id = branch_create.id

        for partner in self:
            invoice = self.env['account.invoice'].create({
                'partner_id': partner.member_id.partner_id.id,
                #  partner.partner_id.property_account_receivable_id.id,
                'account_id': partner.member_id.partner_id.property_account_payable_id.id,#partner.account_id.id,
                'fiscal_position_id': partner.member_id.partner_id.property_account_position_id.id,
                'branch_id': self.env.user.branch_id.id or branch_id
            })
            line_values = {
                'product_id': product_id,  # partner.product_id.id,
                'price_unit': amount,
                'invoice_id': invoice.id,
                #'invoice_line_tax_ids': [],
                'account_id': partner.member_id.partner_id.property_account_payable_id.id or partner.account_id.id,

            } 
            invoice_line = self.env['account.invoice.line'].new(line_values)
            invoice_line._onchange_product_id()
            line_values = invoice_line._convert_to_write(
                {name: invoice_line[name] for name in invoice_line._cache})
            line_values['price_unit'] = amount
            invoice.write({'invoice_line_ids': [(0, 0, line_values)]})
            invoice_list.append(invoice.id)
            # invoice.compute_taxes()

            partner.invoice_id = invoice.id

            find_id = self.env['account.invoice'].search(
                [('id', '=', invoice.id)])
            find_id.action_invoice_open()

        return invoice_list

    @api.multi
    def generate_receipt(self):  # verify,

        search_view_ref = self.env.ref(
            'account.view_account_invoice_filter', False)
        form_view_ref = self.env.ref('account.invoice_form', False)
        tree_view_ref = self.env.ref('account.invoice_tree', False)

        return {
            'domain': [('id', '=', self.invoice_id.id)],
            'name': 'Invoices',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            #  'views': [(form_view_ref.id, 'form')],
            'views': [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')],
            'search_view_id': search_view_ref and search_view_ref.id,
        }

    @api.multi
    def see_breakdown_invoice(self): 
        search_view_ref = self.env.ref(
            'account.view_account_invoice_filter', False)
        form_view_ref = self.env.ref('account.invoice_form', False)
        tree_view_ref = self.env.ref('account.invoice_tree', False)

        return {
            'domain': [('id', '=', self.invoice_id.id)],
            'name': 'Invoices',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            #  'views': [(form_view_ref.id, 'form')],
            'views': [(form_view_ref.id, 'form'),(tree_view_ref.id, 'tree')],
            'search_view_id': search_view_ref and search_view_ref.id,
        }
        
    def mail_sending(self, email_from, group_user_id, extra, bodyx):
        from_browse = self.env.user.name
        groups = self.env['res.groups']
        for order in self:
            group_users = groups.search([('id', '=', group_user_id)])
            group_users2 = groups.search([('id', '=', extra)])
            group_emails = group_users.users
            group_emails2 = group_users2.users
            followers = []
            email_to = []
            email_to2 =[]
            for group_mail in self.users_followers:
                followers.append(group_mail.work_email)

            for gec in group_emails:
                email_to.append(gec.login)
                
            for gec2 in group_emails2:
                email_to2.append(gec2.login)

            email_froms = str(from_browse) + " <" + str(email_from) + ">"
            mail_appends = (', '.join(str(item)for item in followers))
            mail_to = (','.join(str(item2)for item2 in email_to))
            mail_to2 = (','.join(str(item2)for item2 in email_to2))
            subject = "Member Reinstatement Notification"

            extrax = (', '.join(str(extra)))
            followers.append(extrax)
            mail_data = {
                'email_from': email_froms,
                'subject': subject,
                'email_to': mail_to,
                'email_cc': mail_to2,  #  + (','.join(str(extra)),
                'reply_to': email_from,
                'body_html': bodyx
            }
            mail_id = order.env['mail.mail'].create(mail_data)
            order.env['mail.mail'].send(mail_id)
            
    def mail_sending_single(self, email_from, group_user_id, email, bodyx):
        from_browse = self.env.user.name
        groups = self.env['res.groups']
        for order in self:
            group_users = groups.search([('id', '=', group_user_id)])
             
            group_emails = group_users.users
             
            email_to = []
             
            for gec in group_emails:
                email_to.append(gec.login) 
            email_froms = str(from_browse) + " <" + str(email_from) + ">"
            #mail_appends = (', '.join(str(item)for item in followers))
            mail_to = (','.join(str(item2)for item2 in email_to))
             
            subject = "Member Reinstatement Notification" 
            mail_data = {
                'email_from': email_froms,
                'subject': subject,
                'email_to': email,
                'email_cc': mail_to,  #  + (','.join(str(extra)),
                'reply_to': email_from,
                'body_html': bodyx
            }
            mail_id = order.env['mail.mail'].create(mail_data)
            order.env['mail.mail'].send(mail_id)
            
    def get_url(self, id, model):
        base_url = http.request.env['ir.config_parameter'].sudo(
        ).get_param('web.base.url')
        base_url += '/web# id=%d&view_type=form&model=%s' % (id, model)

 #  BUTTON S
     
