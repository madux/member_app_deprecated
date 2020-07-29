import time
from odoo import models, fields, api, _
from odoo.exceptions import except_orm, ValidationError
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta

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

    include_spouse = fields.Boolean(string="Include Spouse Bill", default=False)
    limit = fields.Integer('Set Limit', default=1000, required=True)
    member_ids = fields.Many2many('member.app', string='Member Lines')
    
    @api.onchange('subscription_period')
    def action_display_records(self):
        if self.subscription_period:
            member_ids = self.env['member.app'].search([('subscription_period', '!=', self.subscription_period)], limit=self.limit)
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
        
        for rec in self.env['member.app'].search([('subscription_period', '!=', self.subscription_period)], limit=self.limit):
            invoice = account_obj.create({
                'partner_id': rec.partner_id.id,
                'journal_id': journal_id.id,
                'account_id': rec.partner_id.property_account_payable_id.id if rec.partner_id else 13,# inv.partner_id.property_account_payable_id.id, 
                'branch_id': self.branch_id.id or self.env.user.branch_id.id, # if not self.env.user.branch_id.id, 
                'date_invoice': datetime.today(),
                'type': 'out_invoice', 
                'invoice_line_ids': [(0, 0, {
                                    'product_id': rex.product_id.id,
                                    'price_unit': rex.total_cost - rex.entry_price,
                                    'name': "Section Charge for "+ str(rex.product_id.name) + ": Period-"+(self.subscription_period),
                                    'account_id': invoice_line.with_context({'journal_id': journal_id.id, 'type': 'in_invoice'})._default_account(),
                                    # 'account_id': rex.product_id.categ_id.property_account_income_categ_id.id or record.account_id.id,
                                    'quantity': 1.0,
                                    
                                    }) for rex in rec.mapped('subscription')] #.filtered(lambda  self: self.name not in list_of_names)]
            })
            # self.subscription_line(rec, invoice) 
            self.spouse_bill_line(rec, invoice) 
            self.packages_bill(rec, invoice) 
            # self.child_bill_line(rec, invoice) 
            rec.subscription_period = self.subscription_period
            # tablebody = self.table_invoice_lines(invoice.invoice_line_ids)
            # self.send_mail(rec, tablebody)
            rec.write({'invoice_id': [(4, [invoice.id])]})
            rec.batch_mailing(self.subscription_period)
            
    @api.multi
    def batch_emailing(self):
        member_ids = self.env['member.app'].search([('subscription_period', '!=', self.subscription_period), ('state', 'in', ['temp', 'ord'])])
        ctx = dict()
        for rec in member_ids:
            template = self.env['ir.model.data'].get_object('member_app', 'email_template_for_member')[1]
            ctx.update({
                        'default_model': 'member.app',
                        'default_res_id': rec.id,
                        'default_use_template': bool(template),
                        'default_template_id': template,
                        'default_composition_mode': 'comment',
                        'email_to': rec.email,
                        'subscription': self.subscription_period,
                    })
            sender =self.env['mail.template'].browse(template.id).with_context(ctx).send_mail(rec.id)
            self.env['mail.mail'].browse(sender).send(sender)
        return True
    
    

    @api.multi
    def send_mail(self, record, tablebody, force=False,):
        email_from = self.env.user.company_id.email
        mail_to = record.email
        subject = "Ikoyi Club Bill"
        bodyx = "This is a bill notification message for the period of {} <br/>\
            For further enquires, kindly contact {} <br/> {} <br/>{}\
        Thanks".format(self.subscription_period, self.env.user.company_id.name, self.env.user.company_id.phone, tablebody)
        self.mail_sending_one(email_from, mail_to, bodyx, subject)
    
    def mail_sending_one(self, email_from, mail_to, bodyx, subject):
        for order in self:
            mail_tos = str(mail_to)
            email_froms = "Ikoyi Club " + " <" + str(email_from) + ">"
            subject = subject
            mail_data = {
                'email_from': email_froms,
                'subject': subject,
                'email_to': mail_tos,
                'reply_to': email_from,
                'body_html': bodyx
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
                                        'account_id': product_child.categ_id.property_account_income_categ_id.id or record.account_id.id,
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
                                        'account_id': product_child.categ_id.property_account_income_categ_id.id or record.account_id.id,
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
                                        'account_id': product_spouse.categ_id.property_account_income_categ_id.id or record.account_id.id,
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
                                        'account_id': product_spouse.categ_id.property_account_income_categ_id.id or record.account_id.id,
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
                                'account_id': product_pack_search.categ_id.property_account_income_categ_id.id or record.account_id.id,
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
                

    # def subscription_line(self, record, invoice):
    #     products = self.env['product.product']
    #     invoice_line_obj = self.env["account.invoice.line"]
    #     price = 0.0
    #     price1 = 0.0
    #     price2 = 0.0
    #     total = 0.0
    #     product_id = 1 
    #     inv_id = invoice.id
    #     for subs in record.subscription:
    #         product_search = products.search([('name', '=ilike', subs.name)], limit=1)
    #         if product_search:   
    #             if record.duration_period == "Months":
    #                 if subs.special_subscription != True:
    #                     total = (subs.total_cost / 6) * record.number_period
    #                     price = total
    #                 if subs.special_subscription == True:
    #                     total = subs.total_cost
    #                     price = total
    #                 curr_invoice_subs = {
    #                         'product_id': product_search.id,
    #                         'name': "Charge for "+ str(product_search.name) + ": Period-"+(self.subscription_period),
    #                         'price_unit': price,
    #                         'quantity': 1.0,
    #                         'account_id': product_search.categ_id.property_account_income_categ_id.id or record.account_id.id,
    #                         'invoice_id': inv_id,
    #                         }
    #             elif record.duration_period == "Full Year":
    #                 if subs.special_subscription != True:
    #                     total = (subs.total_cost * 2) * record.number_period
    #                     price += total
    #                 else:
    #                     total = (subs.total_cost * 2) * record.number_period
    #                     price += total 
                     
    #                 curr_invoice_subs = {
    #                         'product_id': product_search.id,
    #                         'name': "Charge for "+ str(product_search.name) + ": Period-"+(self.subscription_period),
    #                         'price_unit': price,
    #                         'quantity': 1.0,
    #                         'account_id': product_search.categ_id.property_account_income_categ_id.id or record.account_id.id,
    #                         'invoice_id': inv_id,
    #                         } 
    #                 invoice_line_obj.create(curr_invoice_subs)
