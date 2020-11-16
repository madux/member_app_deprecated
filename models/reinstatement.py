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
        readonly=False,
        )#domain=['|', ('active', '=', False), ('activity', 'in', ['dom','inact'])]
    identification = fields.Char('Identification.', compute="GET_Member_Field", store=True, size=6)
    email = fields.Char('Email', compute="GET_Member_Field",store=True) 
    date = fields.Datetime('Date', required=True) 
    description_two = fields.Text('Refusal Reasons') 
    users_followers = fields.Many2many('hr.employee', string='Add followers')
     
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
     
    p_type = fields.Selection([('yes', 'No'),
                               ('no', 'Yes'),
                               
                               ], default='no', string='Anomaly') 
    # payment_renew = fields.Many2many(
    #     'subscription.line',
    #     string='Renewals Payments',
    #     readonly=False,
    #     ) 
    addition = fields.Float(
        'Extra Charge', default=100000, required=True,
        )
    last_date = fields.Date('Last Subscribed Date', store=True, compute='lastdate', required=False)
    # account_id = fields.Many2one('account.account', string='Account')
    invoice_id = fields.Many2one('account.invoice', 'Invoice', store=True)

    binary_attach_proof = fields.Binary('Payment Proof') # required in wait
    binary_fname_proof = fields.Char('Attach Proof')
    payment_ids = fields.Many2many(
        'account.payment',
        string='All Payments', compute="GET_Member_Field")

    @api.onchange('member_id')
    def onchange_member_id(self):
        res = {}
        if self.member_id:
            res['domain'] = {
                'invoice_id': [('partner_id', '=', self.member_id.partner_id.id), ('state', '!=', 'paid')],
                }
        return res
 
    @api.depends('member_id')
    def GET_Member_Field(self):
        for record in self:
            member = self.env['member.app'].search(
                [('id', '=', record.member_id.id)], limit = 1)
            record.identification = member.identification
            record.email = member.email
            record.payment_ids = [(6, 0, [rec.id for rec in record.member_id.mapped('payment_ids')])]
    
    @api.depends('payment_ids')        
    def lastdate(self):
        for rec in self:
            if rec.payment_ids: 
                last_date = rec.payment_ids[-1].payment_date
                self.last_date = last_date
    # ######### MEMBERSHIP CREATES INVOICE ON DRAFT ###############
    
    @api.multi
    def send_mail_to_internal_control(self, force=False):  
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
    def send_mail_member_two(self, force=False):
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
    def send_mail_member(self, force=False):
        email_from = self.env.user.login
        group_user_id = self.env.ref('member_app.membership_officer_ikoyi').id
        # extra = self.env.ref('ikoyi_module.inventory_officer_ikoyi').id 
        # email = self.env.ref('ikoyi_module.manager_member_ikoyi').id
        bills = self.member_id.balance_total + self.addition
        email = self.email
        bodyx = "Dear Sir/Madam, </br>I wish to notify you (-ID {} ), that prior to your request for reinstatement, you have been billed \
        the sum of {} on the date: {} </br> Kindly contact the Ikoyi Club 1938 for any further enquires.\
        </br>Thanks" .format(self.identification,bills, fields.Datetime.now())
        self.mail_sending_single(email_from, group_user_id, email, bodyx)
    
    
    @api.multi
    def manager_send_mail_member(self, force=False): 
        email_from = self.env.user.login
        group_user_id = self.env.ref('member_app.membership_officer_ikoyi').id
    
        email = self.email
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
         
        email = self.email
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
    def confirm_invoice_payment(self):
        self.write({'state': 'paid'})
        return self.send_mail_biodata_to_member()

    @api.multi
    def generate_bio_data(self):  

        report = self.env['ir.actions.report.xml'].search([('report_name','=', 'member_app.print_biodata_template')])
        if report:
            report.write({'report_type':'qweb-html'})
        return self.env['report'].get_action(self, 'member_app.print_biodata_template')
    
    @api.multi 
    def send_mail_manager_biodata(self, force=False): 
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
    def reject_mail(self, force=False):
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
    def button_rejects(self): 
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
            member.write({'active':True, 'activity':'act', 'state': 'ord'})

        else:
            raise ValidationError('No member record found to Reinstate')
        
        depends_member = self.env['register.spouse.member'].search([('sponsor', '=', self.member_id.id)])
        if depends_member:
            for rec in depends_member:
                rec.write({'active':True})
        
    # ANOMALY
    @api.multi
    def ano_send_fa(self):
        self.write({'state':'finance'})
        return self.send_anomaly_to_fa()
    
    @api.multi
    def send_Finmanager_Fine(self):  #  finance , accountboss
        member = self.env['member.app'].search([('id', '=', self.member_id.id)])
        depends_member = self.env['register.spouse.member'].search([('sponsor', '=', self.member_id.id)])
        if member:
            member.write({'active':True, 'activity':'inact'})
        if depends_member:
            for rec in depends_member:
                rec.write({'active':True})
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
        amount = percent * (self.addition + self.member_id.balance_total)
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
      
    @api.multi
    def create_invoice(self):  
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

    @api.multi
    def create_membership_invoice(self):
        """ Create Customer Invoice of Membership reinstatement.
        """
        amount = self.member_id.balance_total + self.addition
        invoice_list = []
        for partner in self:
            invoice = self.env['account.invoice'].create({
                'partner_id': partner.member_id.partner_id.id,
                #  partner.partner_id.property_account_receivable_id.id,
                'account_id': partner.member_id.partner_id.property_account_receivable_id.id,#partner.account_id.id,
                'fiscal_position_id': partner.member_id.partner_id.property_account_position_id.id,
                'branch_id': self.env.user.branch_id.id,
                'company_id': self.env.user.company_id.id, 
            })
            line_values = {
                'name': 'Charge for Reinstatement',
                # 'product_id': product_id,  # partner.product_id.id,
                'price_unit': amount,
                'invoice_id': invoice.id,
                #'invoice_line_tax_ids': [],
                'account_id': invoice.journal_id.default_credit_account_id.id, # partner.member_id.partner_id.property_account_payable_id.id or partner.account_id.id,
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
