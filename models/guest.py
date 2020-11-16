import time
from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import except_orm, ValidationError
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from odoo import http


class RegisterGuest(models.Model):
    _name = 'register.guest'
    _description = 'Register Guest'

    @api.multi
    def name_get(self):
        if not self.ids:
            return []
        res = []
        for field6 in self.browse(self.ids):
            partner = str(field6.partner_id.name)
            res.append((field6.id, partner))
        return res

    _sql_constraints = [
        ('partner_id_unique',
         'UNIQUE(partner_id)',
         'Partner Name must be unique')
    ]
    @api.onchange('partner_id')
    def _get_state(self):
        for r in self.partner_id: 
            street = r.street
            country = r.country_id.id
            city = r.city
            post = r.function
            phone = r.phone
            state = r.state_id
            title = r.title.id
            email = r.email
            image = r.image
            self.country_id = country
            self.state_id = state
            self.city = city
            self.phone = phone
            self.title = title
            self.image = image
            self.occupation = post
            self.email = email

    image = fields.Binary(
        "Image",
        attachment=True,
        help="This field holds the image used as avatar for this contact, \
         limited to 1024x1024px",
    )
    image_medium = fields.Binary(
        "Medium-sized image",
        attachment=True,
        help="Medium-sized image of this contact. It is automatically "
        "resized as a 128x128px image, with aspect ratio preserved. "
        "Use this field in form views or some kanban views.")
    image_small = fields.Binary(
        "Small-sized image",
        attachment=True,
        help="Small-sized image of this contact. It is automatically "
        "resized as a 64x64px image, with aspect ratio preserved. "
        "Use this field anywhere a small image is required.")
    partner_id = fields.Many2one(
        'res.partner', 'Name', domain=[
            ('is_member', '=', True)])

    surname = fields.Char(string='Surname', required=True)
    first_name = fields.Char(string='First Name', required=True)
    middle_name = fields.Char(string="Middle Name")
    city = fields.Char('City')
    street = fields.Char('Street')
    url = fields.Char('Website')
    phone = fields.Char('Phone')
    state_id = fields.Many2one('res.country.state', store=True)
    country_id = fields.Many2one('res.country', 'Country', store=True)
    dob = fields.Datetime('Date Of Birth', required=True)
    email = fields.Char('Email', required=True, store=True)
    occupation = fields.Char('Job title')
    nok = fields.Many2one('res.partner', 'Next of Kin', store=True)
    title = fields.Many2one('res.partner.title', 'Title', store=True)
    sponsor = fields.Many2one(
        'member.app',
        string='Parent Member',
        required=True)
    account_id = fields.Many2one('account.account', 'Account')
    invoice_id = fields.Many2many('account.invoice', string='Invoice', store=True)

    product_id = fields.Many2one(
        'product.product', string='Membership type', domain=[
            ('membershipx', '=', True)], required=False)
    member_price = fields.Float(
        string='Section Cost',
        required=False,
        readonly=False)
    total = fields.Integer('Total Amount', default=60000, required=True)#compute='get_totals')
    date_order = fields.Datetime('Offer Date', default=fields.Datetime.now())
    member_age = fields.Integer(
        'Age',
        required=True,
        compute="get_duration_age")
    subscription = fields.Many2many(
        'subscription.payment',
        readonly=False,
        string='Add Sections',
        compute='get_package_cost')

    #  ,compute='get_all_packages')
    package = fields.Many2many('package.model', string='Compulsory Packages')
    package_cost = fields.Float(
        'Package Cost',
        required=False,
        compute='get_package_cost')
    users_followers = fields.Many2many('res.users', string='Add followers')
    payment_idss = fields.Many2many('account.payment',
                                   string="Payment")
    #  3333
    place_of_work = fields.Char('Name of Work Place')
    work_place_manager_name = fields.Char('Name of Work Place')
    email_work = fields.Char('Work Place Email', required=True)
    binary_attach_letter = fields.Binary('Attach Verification Letter')
    binary_fname_letter = fields.Char('Binary Letter')
    address_work = fields.Text('Work Address')

    binary_attach_receipt = fields.Binary('Attach Payment Teller')
    binary_fname_receipt = fields.Char('Binary receipt')
    
    purpose_visit = fields.Text('Purpose of Visit')
    abroad_address = fields.Text('Address abroad')
    passport_number = fields.Char('Passport Number')
    
    resident_permit = fields.Char('Resident Permit Number')
    position_holder = fields.Char('Position in Company')
    
    member_condition = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
        ], 'Have you ever been a member of Ikoyi Club 1938', default='no', index=True, required=False, readonly=False, \
        copy=False, track_visibility='always')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('honourary', 'Honorary Secretary'),
        ('invoice', 'Invoicing'),
        ('wait', 'Waiting'),
        ('general_manager', 'General Manager'),
        ('honourary_two', 'Honorary Secretary'),
        ('verify', 'Verification'),
        ('confirm', 'Confirmed'),
    ], 'Status', default='draft', index=True, required=True, readonly=False,
                              copy=False, track_visibility='always')
    relationship = fields.Selection([('Child',
                                      'Child'),
                                     ('Brother',
                                      'Brother'),
                                     ('Sister',
                                      'Sister'),
                                     ('Friend',
                                      'Friend'),
                                     ('Spouse',
                                      'Spouse'),
                                     ],
                                    'Sponsor Relationship',
                                    index=True,
                                    required=True,
                                    readonly=False,
                                    copy=False,
                                    track_visibility='always')

    def define_invoice_line(self, product_name,invoice, amount):
        products = self.env['product.product']
        invoice_line_obj = self.env["account.invoice.line"]
        product_ids = products.search([('name', '=ilike', product_name)], limit=1)
        # if not product_ids:
        #     product_id = products.create({'name': product_name, 'list_price': self.total}).id
        # product_id = product_ids.id
        # product_search = products.browse([product_id])
        # journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        prd_account_id = invoice.journal_id.default_credit_account_id.id
        curr_invoice_line = {
                                'product_id': product_ids.id if product_ids else False,
                                'name': "Charge for "+ str(product_ids.name) if product_ids else product_name,
                                'price_unit': self.total,
                                'quantity': 1.0,
                                'price_subtotal': 1.0 * self.total,
                                'account_id': prd_account_id, # product_search.categ_id.property_account_income_categ_id.id,
                                'invoice_id': invoice.id,
                                'branch_id': self.env.user.branch_id.id,
                            }

        invoice_line_obj.create(curr_invoice_line)
       
    @api.multi
    def create_member_bill(self, product_name):
        product_name = product_name
        """ Create Customer Invoice for members.
        """
        invoice_list = []
        qty = 1
        products = self.env['product.product']
        invoice_line_obj = self.env["account.invoice.line"]
        invoice_obj = self.env["account.invoice"] 
        product_search = products.search([('name', '=ilike', product_name)], limit=1)
        
        for inv in self:
            invoice = invoice_obj.create({
                'partner_id': inv.partner_id.id,
                'account_id': inv.partner_id.property_account_receivable_id.id,  
                'fiscal_position_id': inv.partner_id.property_account_position_id.id,
                'branch_id': self.env.user.branch_id.id, 
                'date_invoice': datetime.today(),
                'type': 'out_invoice', # vendor
                'residual': 1.0 * self.total,
                'branch_id': self.env.user.branch_id.id,
                'company_id': self.company_id.id,
                
                # 'type': 'out_invoice', # customer
            }) 
            if self.state == 'invoice':
                amount = self.total #+ product_harmony.list_price # 
                self.define_invoice_line(product_name, invoice, amount)
            
            invoice_list.append(invoice.id) 
            form_view_ref = self.env.ref('account.invoice_form', False)
            tree_view_ref = self.env.ref('account.invoice_tree', False)
            self.write({'invoice_id':[(4, invoice_list)]}) 
            return {
                    'domain': [('id', '=', [item.id for item in self.invoice_id])],
                    'name': 'Invoices',
                    'view_mode': 'form',
                    'res_model': 'account.invoice',
                    'type': 'ir.actions.act_window',
                    'views': [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')],
                } 

    @api.depends('dob')
    def get_duration_age(self):
        for rec in self:
            start = rec.dob
            end = fields.Datetime.now()
            if start and end:
                server_dt = DEFAULT_SERVER_DATETIME_FORMAT
                strt = datetime.strptime(start, server_dt)
                ends = datetime.strptime(end, server_dt)
                durations = ends - strt
                rec.member_age = durations.days / 365

    @api.multi
    @api.depends('member_price', 'package_cost')
    def get_totals(self):
        for rec in self:
            rec.total = rec.member_price + rec.package_cost
    @api.one
    @api.depends('package', 'subscription')
    def get_package_cost(self):
        total1 = 0.0
        total2 = 0.
        for ret in self.package:
            total1 += ret.package_cost
        for rm in self.subscription:
            total2 += rm.total_cost
        self.member_price = total2
        self.package_cost = total1

    @api.multi
    def button_send_hon(self): # draft memoffice
        self.write({'state': 'invoice'})
        self.fetch_followers()
        partner = self.env['res.partner']#.search([('id', '=', self.partner_id.id)])
        account_receivable = self.env['account.account'].search([('user_type_id.name', '=', 'Receivable')], limit=1)
        account_payable = self.env['account.account'].search([('user_type_id.name', '=', 'Payable')], limit=1)
        name, first, middle = self.surname, self.first_name, self.middle_name # vals.get('surname'),vals.get('middle_name'), vals.get('first_name')
        names = str(name) +' '+str(middle)+' '+str(first)
        partner = self.env['res.partner']
        
        part = partner.create({'street': self.street,
                        'email': self.email,
                        'state_id': self.state_id.id,
                        'title':self.title.id,
                        'city':self.city,
                        'image': self.image,
                        'phone':self.phone,
                        'function': self.occupation,
                        'name': names,
                        'is_member': True,
                        'property_account_receivable_id': account_receivable.id,
                        'property_account_payable_id': account_payable.id,
                        })
        self.write({'state': 'invoice', 'partner_id': part.id})
        return self.send_honour_mail()

    def fetch_followers(self):
        group1 = self.env.ref('member_app.manager_member_ikoyi').id
        group2 = self.env.ref('member_app.membership_honour_ikoyi').id
        group3 = self.env.ref('ikoyi_module.gm_ikoyi').id
        group4 = self.env.ref('member_app.membership_officer_ikoyi').id
        groups_lists = [group1, group2, group3, group4]
        groups_obj = self.env['res.groups']
        users = []
        for each in groups_lists:
            group_users = groups_obj.search([('id', '=', each)])
            if group_users:
                for user in group_users.users:
                    users.append(user.id)
                    self.users_followers = [(6, 0, users)]
            else:
                pass

    @api.multi
    def send_honour_mail(self, force=False):
        email_from = self.env.user.company_id.email
        group_user_id = self.env.ref('member_app.membership_honour_ikoyi').id
        extra_user = self.env.ref('member_app.manager_member_ikoyi').id
        groups = self.env['res.groups']
        group_users = groups.search([('id', '=', extra_user)])
        extra = str(email_from)
        if group_users:
            group_emails = group_users.users[0] or ''
            extra = group_emails.login
        bodyx = "Sir/Madam, </br>We wish to notify you that a guest with name:\
         {} applies for guest membership on the date: {}.</br>\
             Kindly <a href={}> </b>Click <a/> to Login to the ERP to view \
        </br> Thanks".format(self.partner_id.name, fields.Datetime.now(),
                             self.get_url(self.id, self._name))
        self.mail_sending(email_from, group_user_id, extra, bodyx)

    # # # # # # # # # # # # # # # # # # # # # # # # #
    @api.multi
    def button_send_hon_invocie(self):  # honourary memberhou sec
        self.write({'state': 'invoice'})
        return self.send_memofficer_mail()

    @api.multi
    def send_memofficer_mail(self, force=False):
        email_from = self.env.user.company_id.email
        group_user_id = self.env.ref('member_app.membership_officer_ikoyi').id
        extra_user = self.env.ref('member_app.manager_member_ikoyi').id
        groups = self.env['res.groups']
        group_users = groups.search([('id', '=', extra_user)])
        extra = str(email_from)
        if group_users:
            group_emails = group_users.users[0]
            extra = group_emails.login

        bodyx = "Sir/Madam, </br>I wish to notify you that a request for guest \
         membership with name: {} have been approve on the date: {}.</br>\
             Kindly <a href={}> </b>Click <a/> to Login to the \
             ERP to view</br> Thanks".format(self.partner_id.name, fields.Datetime.now(), self.get_url(self.id, self._name))
        self.mail_sending(email_from, group_user_id, extra, bodyx)

    # # # # # # # # # # # # # # # # # # # # # # # # #
    
    @api.multi
    def button_send_invocie_wait(self):
        self.send_mail_workplace()
        dummy, view_id = self.env['ir.model.data'].get_object_reference('account', 'view_account_payment_form')
        ret = {
                'name':'Guest Ticket Payment',
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'account.payment',
                'type': 'ir.actions.act_window',
                'domain': [],
                'context': {
                        'default_amount': self.total,
                        'default_payment_type': 'inbound',
                        'default_partner_id':self.partner_id.id, 
                        'default_communication': self.id, 
                        'default_narration': 'Guest Subscription Payment',
                },
                'target': 'new'
                }
        return ret

    @api.multi
    def send_mail_workplace(self, force=False):
        email_from = self.env.user.company_id.email
        mail_to = self.email_work
        subject = "Ikoyi Club Member Verification"
        bodyx = "This is a verification message to verify that {} is a noble employer in {}, if (or not) so, kindly indicate and give us a feedback \
        so that we could continue our processes. </br> For further enquires, kindly contact {} </br> {} </br>\
        Thanks".format(self.partner_id.name, self.place_of_work, self.env.user.company_id.name, self.env.user.company_id.phone)
        self.mail_sending_one(email_from, mail_to, bodyx, subject)
    # # # # # # # # # # # # # # # # # # # # # # # # # #

    @api.multi
    def button_send_gen_Manager(self):  # wait memberoficerc
        self.write({'state': 'general_manager'})
    # # # # # # # # # # # # # # # # # # # # # # # # # #

    @api.multi
    def button_gen_Manager_hon2(self):  # general_manager gm_ikoyi
        self.write({'state': 'honourary_two'})

    @api.multi
    def button_hon2_approve(self):  # honourary_two honsec
        self.write({'state': 'verify'})

    @api.multi
    def button_officer_confirm(self):  # verify memofficer
        self.write({'state': 'confirm'})
        self.send_mail_guest()

    @api.multi
    def send_mail_guest(self, force=False):
        email_from = self.env.user.company_id.email
        mail_to = self.email
        subject = "Ikoyi Club Guest Confirmation"
        bodyx = "This is a notification message that you have been confirmed as a guest of Ikoyi Club on the date: {}. </br> For further enquires,\
         kindly contact {} </br> {} </br>\
        Thanks".format(fields.Date.today(), self.env.user.company_id.name, self.env.user.company_id.phone)
        self.mail_sending_one(email_from, mail_to, bodyx, subject)

    # @api.model
    # def create(self, vals):
    #     res = super(RegisterGuest, self).create(vals)
    #     # vals = {}
    #     account_receivable = self.env['account.account'].search([('user_type_id.name', '=', 'Receivable')], limit=1)
    #     account_payable = self.env['account.account'].search([('user_type_id.name', '=', 'Payable')], limit=1)
    #     name, first, middle = vals.get('surname'),vals.get('middle_name'), vals.get('first_name')
    #     names = str(name) +' '+str(first)+' '+str(middle)
    #     partner = self.env['res.partner']
    #     partner_search = partner.search([('name', '=ilike', names)], limit= 1)
        
    #     if not partner_search:
    #         partners = partner.create({
    #                     'street': vals.get('street'),
    #                     'name': names,
    #                     'street2': vals.get('street'),
    #                     'email': vals.get('email'),
    #                     'state_id': vals.get('state_id'),
    #                     'title': vals.get('title'),
    #                     'image': vals.get('image'),
    #                     'phone': vals.get('phone'),
    #                     'function': vals.get('occupation'),
    #                     'property_account_receivable_id': account_receivable.id,
    #                     'property_account_payable_id': account_payable.id,
    #                    })
    #         for rec in self:
    #             rec.update({'partner_id': partners.id})
    #     return res
    

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
                'views': [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')],
                'search_view_id': search_view_ref and search_view_ref.id,
            }

    @api.multi
    def create_membership_invoice(self):
        """ Create Customer Invoice of Membership for partners.
        @param datas: datas has dictionary value which consist Id of Membership product and Cost Amount of Membership.
                      datas = {'membership_product_id': None, 'amount': None}
        """
        amount = self.total
        product = 0
        state_now = str(self.state).replace('_', ' ').capitalize()
        products = self.env['product.product']
        product_search = products.search(
            [('name', 'ilike', 'Guest Membership')])
        if product_search:
            #  product.append(product_search.id)
            product = product_search[0].id
        else:
            pro = products.create(
                {'name': 'Guest Membership', 'membershipx': True, 'list_price': amount})
            product = pro.id
        product_id = product
        self.write({'product_id': product})

        invoice_list = []
        branch_id = 0
        branch = self.env['res.branch']
        branch_search = branch.search([('name', 'ilike', 'Ikoyi Club Lagos')])
        if branch_search:
            branch_id = branch_search[0].id

        else:
            branch_create = branch.create(
                {'name': 'Ikoyi Club Lagos', 'company_id': self.env.user.company_id.id or 1})
            branch_id = branch_create.id

        for partner in self:
            invoice = self.env['account.invoice'].create({
                'partner_id': partner.partner_id.id,
                #  partner.partner_id.property_account_receivable_id.id,
                'account_id': partner.account_id.id,
                'fiscal_position_id': partner.partner_id.property_account_position_id.id,
                'branch_id': branch_id,
                'company_id': self.company_id.id,
            })
            line_values = {
                'product_id': product_id,  # partner.product_id.id,
                'price_unit': amount,
                'invoice_id': invoice.id,
                'account_id': partner.account_id.id or partner.partner_id.property_account_payable_id.id,

            }
            #  create a record in cache, apply onchange then revert back to a
            #  dictionnary
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
            'name': 'Guest Membership Invoices',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            #  'views': [(form_view_ref.id, 'form')],
            'views': [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')],
            'search_view_id': search_view_ref and search_view_ref.id,
        }

    @api.multi
    def see_breakdown_invoice(self):  # vis_account,

        search_view_ref = self.env.ref(
            'account.view_account_payment_search', False)
        form_view_ref = self.env.ref('account.view_account_payment_form', False)
        tree_view_ref = self.env.ref('account.view_account_payment_tree', False)

        return {
            'domain': [('communication', '=', str(self.id))],
            'name': 'Guest Payments',
            'res_model': 'account.payment',
            'type': 'ir.actions.act_window',
            #  'views': [(form_view_ref.id, 'form')],
            'views': [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')],
            'search_view_id': search_view_ref and search_view_ref.id,
        }

    @api.multi
    def print_membership_payment_receipt(self):
        report = self.env["ir.actions.report.xml"].search(
            [('report_name', '=', 'member_app.receipt_guest_payment_template')], limit=1)
        if report:
            report.write({'report_type': 'qweb-pdf'})
        return self.env['report'].get_action(
            self.id, 'member_app.receipt_guest_payment_template')
        
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
                followers.append(group_mail.login)

            for gec in group_emails:
                email_to.append(gec.login)

            email_froms = str(from_browse) + " <" + str(email_from) + ">"
            mail_appends = (', '.join(str(item)for item in followers))
            mail_to = (','.join(str(item2)for item2 in email_to))
            subject = "Guest Membership Notification"

            extrax = (', '.join(str(extra)))
            followers.append(extrax)
            mail_data = {
                'email_from': email_froms,
                'subject': subject,
                'email_to': mail_to,
                'email_cc': mail_appends,  # + (','.join(str(extra)),
                'reply_to': email_from,
                'body_html': bodyx
            }
            mail_id = order.env['mail.mail'].create(mail_data)
            order.env['mail.mail'].send(mail_id)

    def mail_sending_one(self, email_from, mail_to, bodyx, subject):
        for order in self:
            mail_tos = str(mail_to)
            email_froms = "Ikoyi Club " + " <" + str(email_from) + ">"
            subject = subject
            mail_data = {
                'email_from': email_froms,
                'subject': subject,
                'email_to': mail_tos,
                #  'email_cc':,#  + (','.join(str(extra)),
                'reply_to': email_from,
                'body_html': bodyx
            }
            mail_id = order.env['mail.mail'].create(mail_data)
            order.env['mail.mail'].send(mail_id)
