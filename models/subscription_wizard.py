import time
from odoo import models, fields, api, _
from odoo.exceptions import except_orm, ValidationError
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
import base64
from fpdf import FPDF

 
class SubscriptionWizardExcel(models.TransientModel):
    _name = "subscription.excel"

    datefrom = fields.Datetime('Date', required=True)
    dateto = fields.Datetime('Date', required=True)

    @api.multi
    def generate_records(self):
        domain = []

        sub = self.env['subscription.model'].search([
            ('date_of_last_sub', '>=', self.datefrom), 
            ('date_of_last_sub', '<=', self.dateto)])
        # for rec in sub:
        #     domain.append(rec.id)
        if sub:
            search_view_ref = self.env.ref(
                'member_app.memapp_search_subscription', False)
            form_view_ref = self.env.ref('member_app.subscription_formxfvv', False)
            tree_view_ref = self.env.ref('member_app.subscription_maintreex', False)
            return {
                'name': "Subscription Renewal",
                'view_type': 'form',
                "view_mode": 'tree,form',
                'domain': [('id', 'in', [rec.id for rec in sub])],
                'res_model': 'subscription.model',
                'type': 'ir.actions.act_window',
                'target': 'current',
                 
            }
        else:
            raise ValidationError('Ops! Sorry, no renewal was found within the date range')
     


class GenerateInvoice(models.TransientModel):
    _name = "generate.member.invoice"

    branch_id = fields.Many2one('res.branch', required=True, string='Branch', default=lambda self: self.env.user.branch_id.id)
    subscription_period = fields.Selection([
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

    is_mail = fields.Selection([
        ('mail', 'mail'),
        ('invoice', 'invoice'),
        ('all', 'All'),
    ], 'type', required=False, readonly=False, copy=False, track_visibility='always')

    include_spouse = fields.Boolean(string="Include Dependent's Bill", default=False)
    include_mailing = fields.Boolean(string="Send Mail", default=False)
    limit = fields.Integer('Set Limit', default=1000, required=True)
    member_ids = fields.Many2many('member.app', string='Member Lines', store=True)
    text_editor = fields.Html('Enter Information here', default=lambda self: self._html_body())

    def _html_body(self):
        body = """
                <h5><strong>ATTENTION:-</strong></h5>
									<p>
										At the emergency meeting of the GC which held on the 6th of July, 2020 it was magnanimously

										resolved that:
										<ol> 
											<li> That the increase of N10,000 in subscription for July/Dec 2020 cycle be reversed;</li>
											<li> That Main House and Sectional levies be suspended for this July/Dec 2020 subscription cycle.</li>
											<li> That fresh bills be issued to all members to replace the earlier ones, taking into consideration items (1) and (2) above; and </li>
											<li> That members who have already paid the bills for July/Dec 2020 cycle be credited with the total amount of the reversed
												subscription increase and suspended levies in the Jan/June 2021 bill.</li>
										</ol>
									</p>
									<p>
										<strong><u>MEDICAL INSURANCE SCHEME  (Optional)</u></strong><br/>
										Medical Insurance Scheme payable at the rate of N2,500 per subscription cycle for N1,000,000(One Million

										Naira) covers injury and death within the club premises for any participating member of the club.

										Please pay immediately and update your bio-data form for proper record keeping.<br/>
									
										Bankers' cheque(s) should be addressed to Ikoyi Club 1938 with your name and membership number clearly stated at the back.<br/>
										Membership Services Tel:01-2919507, 2919508. 07083709076 is for whatsapp only.<br/>
										Email: membershipservices@ikoyiclub1938.net<br/>
										Subscription shall be payable in advance and no member shall enjoy any privilege of membership one month
										after the subscription is due for payment.<br/>
									
										Payment can also be made through any of the bank accounts stated below. However Membership Services must be notified of such payment immediately.
										<ol>
											<li> Union Bank of Nigeria a/c no - 0007278199(Operations)</li>
											<li> United Bank of Africa a/c no - 100-041105-8</li>
											<li> Guaranty Trust Bank a/c no - 0001859873</li>
											<li> First Bank of Nigeria a/c no - 2001751035</li>
											<li> Zenith Bank Plc  a/c no - 1010231837</li>
										</ol>
									</p>
									<p>
										For ease of payment, On-line payment option is now available on<br/>
										<u>www.quickteller.com/ikoyiclub</u> or other quickteller enabled ATM.<br/>

										N/B late payment after 3 months attracts a penalty of N10,000<br/>

										<strong>PLEASE RETURN BILL WITH YOUR BANK DRAFT/EVIDENCE OF FUNDS TRANSFER</strong>
									</p>
        """
        return body
    
    @api.onchange('subscription_period')
    def action_display_records(self):
        if self.subscription_period:
            member_ids =  self.env['member.app'].search([('subscription_period', '!=', self.subscription_period), ('state', 'in', ['ord', 'temp'])], limit=self.limit)
            self.update({'member_ids': [(6, 0, [rec.id for rec in member_ids])]})

    # @api.model
    def migrate_data(self):
        members = self.env['member.app'].search([('partner_id', '=', False)])
        partner_cr = self.env['res.partner']
        # try:
        for record in members:
            surname = str(record.surname)
            firstname = str(record.first_name)
            names = surname +' '+ firstname
            email = record.email
            partner_record = partner_cr.search([('email', '=', email)])
            if not partner_record:
                partner = partner_cr.create({
                    'name': names,
                    'is_member': True,
                    'email': email, 
                    'property_account_payable_id': 13,
                    'property_account_receivable_id': 7,
                })
                record.write({'partner_id': partner.id})
                # raise ValidationError('A')
            else:
                record.write({'partner_id': partner_record.id})
                    
    @api.multi
    def generate_membership_invoice(self):
        account_obj = self.env['account.invoice']
        invoice_line = self.env['account.invoice.line']
        journal_id = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        members = self.env['member.app'].search([('subscription_period', '!=', self.subscription_period), ('state', 'in', ['ord', 'temp'])], limit=self.limit)
        for rec in members:
            # self.env['member.app'].search([('subscription_period', '!=', self.subscription_period)], limit=self.limit):
            
            property_account_receivable_id = self.env['account.account'].search([('user_type_id.name','ilike', 'Receivable')], limit=1).id if not rec.partner_id.property_account_receivable_id else rec.partner_id.property_account_receivable_id.id
            property_account_payable_id = self.env['account.account'].search([('user_type_id.name','=ilike', 'Payable')], limit=1).id if not rec.partner_id.property_account_payable_id else rec.partner_id.property_account_payable_id.id
        
            invoice = account_obj.create({
                'partner_id': rec.partner_id.id,
                'journal_id': journal_id.id,
                'account_id': property_account_receivable_id, # rec.partner_id.property_account_receivable_id.id if rec.partner_id else 13,# inv.partner_id.property_account_payable_id.id, 
                'branch_id': self.branch_id.id or self.env.user.branch_id.id, # if not self.env.user.branch_id.id, 
                'date_invoice': datetime.today(),
                'type': 'out_invoice', 
                'invoice_line_ids': [(0, 0, {
                                    'product_id': rex.product_id.id if rex.product_id else False,
                                    'price_unit': rex.total_cost - rex.entry_price,
                                    'name': "Section Charge for "+ str(rex.product_id.name) + ": Period-"+(self.subscription_period),
                                    'account_id': invoice_line.with_context({'journal_id': journal_id.id, 'type': 'out_invoice'})._default_account(),
                                    # 'account_id': rex.product_id.categ_id.property_account_income_categ_id.id or record.account_id.id,
                                    'quantity': 1.0,
                                    
                                    }) for rex in rec.mapped('subscription')] #.filtered(lambda  self: self.name not in list_of_names)]
            })
            self.spouse_bill_line(rec, invoice) 
            self.create_outstanding_line(invoice.id, rec.id)
            rec.subscription_period = self.subscription_period
            rec.write({'invoice_id': [(4, [invoice.id])]})
            if self.include_mailing:
                rec.batch_mailing(self.subscription_period)


    def create_outstanding_line(self, inv_id, rec):
        account_obj = self.env['account.invoice']
        invoice_line_obj = self.env["account.invoice.line"] 
        members_search = self.env['member.app'].search([('id', '=', rec)])
        accounts = account_obj.browse([inv_id]).journal_id.default_credit_account_id.id
        income_account = self.env['account.account'].search([('user_type_id.name', '=ilike', 'Income')], limit=1)
        balance = members_search.balance_total
        if balance != 0:
            curr_invoice_subs = {
                                'name': "Added Outstanding",
                                'price_unit': balance, #-members_search.balance_total if members_search.balance_total > 0 else members_search.balance_total, 
                                'quantity': 1,
                                'account_id': accounts if accounts else income_account.id,
                                'invoice_id': inv_id,
                                }

            invoice_line_obj.create(curr_invoice_subs)
            members_search.balance_total -= balance
 

    @api.multi
    def batch_emailing(self):
        members = self.env['member.app'].search([('subscription_period', '!=', self.subscription_period)], limit=self.limit)
        for rec in members:
            rec.batch_mailing(self.subscription_period)
    
    @api.multi
    def send_mail(self, record, invoice, attachment_id,force=False,):
        email_from = self.env.user.company_id.email
        mail_to = record.email
        subject = "Ikoyi Club Bill"
        bodyx = "This is a bill notification <br/><br/>" + self.generate_pdf(record, invoice)
        self.mail_sending_one(email_from, mail_to, bodyx, subject, attachment_id)

    
    def mail_sending_one(self, email_from, mail_to, bodyx, subject, attachment_id):
        for order in self:
            mail_tos = str(mail_to)
            email_froms = "Ikoyi Club " + " <" + str(email_from) + ">"
            subject = subject
            mail_data = {
                'email_from': email_froms,
                'subject': subject,
                'email_to': mail_tos,
                'reply_to': email_from,
                'body_html': bodyx,
                'attachment_ids': [(6, 0, [attachment_id])] or None,
            }
            mail_id = order.env['mail.mail'].create(mail_data)
            order.env['mail.mail'].send(mail_id)       

    def spouse_bill_line(self, record, invoice):
        if self.include_spouse:
            invoice_line_obj = self.env["account.invoice.line"]
            inv_id = invoice.id
            products = self.env['product.product']
            spouse_total = 0.0
            child_total = 0.0

            if record.depend_name:
                for subscribe in record.depend_name:
                    if subscribe.relationship == "Child":
                        
                        if record.duration_period == "Months":
                            for sub in subscribe.spouse_subscription:
                                if sub.subscription.name == "Library (Child) -  Subscription" or sub.subscription.name == "Swimming (Child) - Subscription" or sub.subscription.is_child == True:

                                    product_child = products.search([('name', '=ilike', sub.subscription.name)], limit=1)
                                
                                    if sub.subscription.special_subscription != True:
                                        total = (sub.total_fee / 6) * record.number_period
                                        child_total = total - sub.subscription.entry_price
                                    else:
                                        total = sub.total_fee - sub.subscription.entry_price
                                        child_total = total 
                                    # spouse_total = (sub.total_fee / 6) * self.number_period
                                    curr_invoice_spouse_subs = {
                                        'product_id': product_child.id,
                                        'name': "Child Charge for "+ str(product_child.name)+ ": Period-"+(self.subscription_period),
                                        'price_unit': child_total,
                                        'quantity': 1.0,
                                        'account_id': invoice.journal_id.default_credit_account_id.id if invoice.journal_id.default_credit_account_id else product_child.categ_id.property_account_income_categ_id.id,
                                        'invoice_id': inv_id,
                                    }
                                    invoice_line_obj.create(curr_invoice_spouse_subs)

                        elif record.duration_period == "Full Year":
                            for sub2 in subscribe.spouse_subscription:
                                if sub2.subscription.name == "Library (Child) -  Subscription" or sub2.subscription.name == "Swimming (Child) - Subscription" or sub2.subscription.is_child == True:

                                # if sub2.subscription.name in ["Library (Child) -  Subscription", "Swimming (Child) - Subscription"] or sub2.subscription.is_child == True:
                                    product_child = products.search([('name', '=ilike', sub2.subscription.name)], limit=1)
                                    
                                    child_total = (sub2.total_fee * 2) * record.number_period 
                                    curr_invoice_spouse_subs2 = {
                                        'product_id': product_child.id,
                                        'name': "Child Charge for "+ str(product_child.name)+ ": Period-"+(self.subscription_period),
                                        'price_unit': child_total - sub2.subscription.entry_price,
                                        'quantity': 1.0,
                                        'account_id': invoice.journal_id.default_credit_account_id.id if invoice.journal_id.default_credit_account_id else product_child.categ_id.property_account_income_categ_id.id,
                                        'invoice_id': inv_id,
                                    }
                                    invoice_line_obj.create(curr_invoice_spouse_subs2)
                        else:
                            child_total = 0.0

                    elif subscribe.relationship != 'Child':

                        if record.duration_period == "Months":
                            for sub in subscribe.spouse_subscription:
                                
                                product_spouse = products.search([('name', '=ilike', sub.subscription.name)], limit=1)
                                if sub.total_fee == 0:
                                    pass
                                    # raise ValidationError('There is no subscription amount in one of the selected dependents')
                                else:
                                    if sub.subscription.special_subscription != True:
                                        total = (sub.total_fee / 6) * record.number_period
                                        spouse_total = total - sub.subscription.entry_price
                                    else:
                                        total = sub.total_fee - sub.subscription.entry_price
                                        spouse_total = total 
                                    # spouse_total = (sub.total_fee / 6) * self.number_period
                                    curr_invoice_spouse_subs = {
                                        'product_id': product_spouse.id,
                                        'name': "Spouse Charge for "+ str(product_spouse.name)+ ": Period-"+(self.subscription_period),
                                        'price_unit': spouse_total,
                                        'quantity': 1.0,
                                        'account_id': invoice.journal_id.default_credit_account_id.id if invoice.journal_id.default_credit_account_id else product_spouse.categ_id.property_account_income_categ_id.id,
                                        'invoice_id': inv_id,
                                    }
                                    invoice_line_obj.create(curr_invoice_spouse_subs)

                        elif record.duration_period == "Full Year":
                            for sub2 in subscribe.spouse_subscription:
                                product_spouse = products.search([('name', '=ilike', sub2.subscription.name)], limit=1)
                                if sub2.total_fee == 0:
                                    pass
                                else:
                                    spouse_total = (sub2.total_fee * 2) * record.number_period 
                                    curr_invoice_spouse_subs2 = {
                                        'product_id': product_spouse.id,
                                        'name': "Spouse Charge for "+ str(product_spouse.name)+ ": Period-"+(self.subscription_period),
                                        'price_unit': spouse_total - sub2.subscription.entry_price,
                                        'quantity': 1.0,
                                        'account_id': invoice.journal_id.default_credit_account_id.id if invoice.journal_id.default_credit_account_id else product_spouse.categ_id.property_account_income_categ_id.id,
                                        'invoice_id': inv_id,
                                    }
                                    invoice_line_obj.create(curr_invoice_spouse_subs2)
            else:
                spouse_total = 0.0

            record.child_amount = spouse_total
            record.spouse_amount = child_total

     

    def packages_bill(self, record, invoice):
        inv_id = invoice.id

        products = self.env['product.product']
        invoice_line_obj = self.env["account.invoice.line"]
        for pack in record.package:
            product_pack_search = products.search([('name', '=ilike', pack.name)], limit=1)        
            if product_pack_search:
                curr_invoice_pack = {
                                'product_id': product_pack_search.id,
                                'name': "Charge for "+ str(product_pack_search.name)+ ": Period-"+(self.subscription_period),
                                'price_unit': product_pack_search.list_price,
                                'quantity': 1.0,
                                'account_id': invoice.journal_id.default_credit_account_id.id if invoice.journal_id.default_credit_account_id else product_pack_search.categ_id.property_account_income_categ_id.id,
                                'invoice_id': inv_id,
                            } 
                invoice_line_obj.create(curr_invoice_pack) 

    def table_invoice_lines(self, invoice_lines):
        table_content = ""
        for rec in invoice_lines:
            product,name,qty,price= rec.product_id.name if rec.product_id.name else "-", rec.product_id.name if rec.product_id.name else "-", \
                rec.quantity if rec.quantity else "-",rec.price_unit if rec.price_unit else "-"
            table_content += """<tr>
                                    <td style="white-space: text-nowrap;">{}</td>
                                    <td style="white-space: text-nowrap;">{}</td>
                                    <td style="white-space: text-nowrap;">{}</td>
                                    <td style="white-space: text-nowrap;">{}</td> 
                                </tr></br>""".format(product,name,qty,price)
        table = """<h3><b>Invoice Lines </b></h3><br/>
                <div class="table-responsive">
                <table class="table table-bordered">
                    <thead>
                        <tr>
                            <th class="text-right">Section/Package</th>
                            <th class="text-right">Description</th>
                            <th class="text-right">Qty</th> 
                            <th class="text-right">Amount</th>
                        </tr>
                    </thead> 
                    <tbody>
                        {}
                    </tbody> </table> </div>""".format(table_content) 

        
        return table 


    def generate_pdf(self, record, invoice):
        table_content = ""
        for rec in invoice.invoice_line_ids:
            product,name,qty,price= rec.product_id.name if rec.product_id.name else "-", rec.product_id.name if rec.product_id.name else "-", \
                rec.quantity if rec.quantity else "-",rec.price_unit if rec.price_unit else "-"
            table_content += """<tr>
                                    <td>{0}</td>
                                    <td>  -----------------------------  </td>
                                    <td> {1}</td>
                                        
                                </tr>""".format(product, price)

        table = """<div class="row" style="font-size: 20px;">
                        <center><strong>Billing Notice</strong></center>

                        <div class="col-2" style="border:solid; border-radius:15px; font-size: 14px;">
                            <p>MEMBER NAME: {}</p> 
                            <p>ADDRESS: {}</p>
                        </div>
                        <div class="col-xs-4 pull-right mt8" name ="right_name" style="font-size: 11px;">
                            <p>Period:{}</p>
                            <strong>Membership No: {}</strong><br/>
                            <strong>Printed on: {}</strong><br/>
                            
                        </div>
                        
                    </div><br/>
                    <div class="row" style="font-size: 16px;">		
                        <table class="table table-condensed"> 
                            <thead>
                                <tr>
                                    <th><strong>Item Description</strong></th>
                                    <td>                                 </td>
                                    <th><strong>Amount</strong></th>
                                </tr>
                            </thead>
                            <tbody>
                                {}
                            </tbody>
                            <t> 
                                <td><b>Total:<b/></td>
                                <td>  -----------------------------  </td>
                                <td>
                                    {}
                                </td>
                                
                            </t>
                        </table> 
                    </div>

                    <div class="row">
                        <div class="col-xs-12" style="font-size: 12px;">
                            {}
                        </div>
                    </div>
                    <div class="row">
                        <div class="col-xs-3" style="font-size: 17px;"><br/>
                            <strong>Signature: .................</strong><br/>
                            <strong>General Manager</strong>

                        </div>
                    </div>""".format(invoice.partner_id.name, invoice.partner_id.street, self.subscription_period,
                    record.identification, fields.Date.today(),table_content,invoice.amount_total, self.text_editor)
        return table
 