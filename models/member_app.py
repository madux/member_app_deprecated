from __future__ import division
import time
from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import except_orm, ValidationError
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from odoo import http
import re
import requests
import json
import ssl


TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale',
    'in_refund': 'purchase',
}

class MemberAccountMigration(models.Model):
    _name = "member.account.migration"

    reference_number = fields.Char(string='Reference Number')# 0
    details = fields.Char(string='Details')# 1
    trans_date = fields.Date(string='Transaction Date')# 2 
    account_id = fields.Char(string="Account ID")# 3
    gl_description = fields.Char(string="GL Description") # 4 
    company_id = fields.Char(string="Company ID")# 6
    analytic_account_id = fields.Char(string="Analytic Account")# 8
    cost_center = fields.Char(string="Cot center")# 9
    debit_amount = fields.Float(string="Debit Amount")# 12
    amount = fields.Float(string="Amount")# 12
    credit_amount =fields.Float(string="Credit amount") # 13
    source = fields.Char(string='Source')#16
    source_description = fields.Char(string='Source description')#17
    source_code = fields.Char(string="Source code")# 28
    name = fields.Char(string="Name")# 30
    partner_id = fields.Char(string='Partner ID')# 31


class Account_payment(models.Model):
    _inherit = "account.payment"
    _order = "id desc"

    member_id = fields.Many2one('member.app', string="Payment Ref.")
    filex = fields.Binary("Evidence of Payment")
    file_namex = fields.Char("FileName")
    additional_ref = fields.Char("Additional Reference")
    bank = fields.Many2one(
        'res.bank',
        string='Bank',
        readonly=False)


class App_Member(models.Model):
    _name = "member.app"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _rec_name = "surname"
    _order = "id desc"

   
    @api.constrains('phone','email','depend_name','number_period')
    def _check_dependant(self):
        '''if self.depend_name:
            if self.state in ['white', 'draft', 'issue_green', 'green', 'wait', 'interview']:
                for rec in self:
                    if len(rec.depend_name) > 1:
                        raise ValidationError('Spouse at this stage cannot be more than one')
        if self.phone:
            phone_valid = self.phone.strip().isdigit()
            if phone_valid:
                pass
            else:
                raise ValidationError('Please input the correct phone Number')
        
        if self.email:
            rematch = re.match("^.+@(\[?)[a-zA-Z0-9-.]+.([a-zA-Z]{2,3}|[0-9]{1,3})(]?)$", self.email,re.IGNORECASE)
            if rematch != None:
                pass
            else:
                raise ValidationError('Please input the correct Email Address')
        if self.number_period:
            if self.duration_period == "Months":
                if self.number_period in [6, 12]:
                    pass
                else:
                    raise ValidationError("'6' or '12' must be the value to enter in Number Period if duration type is in Months",)'''
        pass

    @api.model
    def _needaction_domain_get(self):
        if self.env.user.name == "Administrator":
            return False
        return [('state', 'in', ['white', 'green', 'ord', 'life'])]

    #  CANNOT DELETE MEMBERS ON LIFE
    @api.multi
    def unlink(self):
        for holiday in self.filtered(
            lambda holiday: holiday.state in ['green','manager','manager_two','ord','issue_green','temp','life']):
            raise ValidationError(
                _('You cannot delete a Member who is in %s state.') %
                (holiday.state,))
        return super(App_Member, self).unlink()

    def _get_requester(self):
        for i in self:
            empl_obj = self.env['product.template'].search(
                [('membershipx_white', '=', True)])
            pro_id = empl_obj.id
            return pro_id

    @api.onchange('first_name', 'surname')
    def _onchange_name(self):
        if self.first_name:
            self.first_name = self.first_name.strip()
        if self.surname:
            self.surname = self.surname.strip()
    
    #  GETS THE COUNTRY FROM STATE_ID
    @api.multi
    def name_get(self):
        if not self.ids:
            return []
        res = []
        for record in self.browse(self.ids):
            partner = str(record.partner_id.name)
            res.append((record.id, partner))
        return res
 
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
        help="This field holds the image used as avatar for this contact, limited to 1024x1024px",
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
        'res.partner', 'Surname Name', domain=[
            ('is_member', '=', True)])

    surname = fields.Char(string='Surname')
    first_name = fields.Char(string='First Name')
    middle_name = fields.Char(string="Middle Name")

    account_id = fields.Many2one('account.account', 'Account')
    city = fields.Char('City')
    street = fields.Char('Street')
    url = fields.Char('Website')
    phone = fields.Char('Phone')

    state_id = fields.Many2one('res.country.state', store=True)
    country_id = fields.Many2one('res.country', 'Country', store=True)
    dob = fields.Datetime('Date Of Birth', required=True)
    email = fields.Char('Email', store=True)
    occupation = fields.Char('Job title')
    nok = fields.Many2one('res.partner', 'Next of Kin', store=True)
    title = fields.Many2one('res.partner.title', 'Title', store=True)
    #  GET MEMBERS FROM MEMBERS APP
    # sponsor = fields.Many2one('res.partner',string='Sponsors', domain=[('is_member','=', True)])
    sponsor = fields.Many2many('res.partner', string='Sponsors')
    #  IF MEDICAL STATUS SELECTED, MEDICAL DESC APPEARS TO ADD DESC.
    medical_status = fields.Boolean('Medical Issues')
    medical_desc = fields.Text('Describe Health Status')
    associate_member = fields.Many2one('member.app', 'Associate Member Name')
    payment_status = fields.Selection([('draft','Draft'), ('open', 'Prospect'),
                                       ('gpaid', 'Green Prospect'), ('issue', 'Green Issued'),
                                       ('white_fee_delay','Delay Fee Paid'),
                                       ('green_fee_delay','Delay Fee Paid'), ('paid', 'Paid')], default='draft', string='Payment status')
    identification = fields.Char('ID No.', size=8)
    payment_line = fields.One2many('member.payment', 'member_id', string='Payment line ids')
    payment_line2 = fields.One2many(
        'member.payment.new',
        'member_idx', readonly=True,
        string='Payment line ids')
    # company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.default_company_get())

    # def default_company_get(self):
    #     company = self.env['res.company'].search([('name', '=', 'Company Membership')],limit=1)
    #     if company:
    #         return company_id

    #     else: 
    #         return False
        # return self.env.ref('member_app.default_company_membership').id
        # usr = self.env['res.users'].browse([self.env.uid])
        # member_officer = usr.has_group("member_app.membership_officer_ikoyi")
        # member_manager = usr.has_group("member_app.manager_member_ikoyi")
        # member_honor = usr.has_group("member_app.membership_honour_ikoyi")

        # if member_officer or member_honor or member_manager:
        #     return self.env.ref('member_app.default_company_membership').id
        # else:
        #     return False

    product_id = fields.Many2one(
        'product.product', string='Membership type', default=_get_requester, domain=[
            ('membershipx', '=', True)], required=False)
    member_price = fields.Float(string='Member Price')
    white_member_price = fields.Float(
        string='White Membership cost', default=2000.00)
    payment_plan = fields.Many2one('account.payment.term', 'Payment Terms')
    
    payment_type = fields.Selection([('installment', 'Installment'),
                                     ('outright', 'OutRight Payment')],
                                    "Payment Type")
    sex = fields.Selection([('Male', 'Male'), ('Female', 'Female')],"Sex")
    marital_status = fields.Selection([('Single', 'Single'), ('Married', 'Married')], "Marital Status")
    nok_relationship = fields.Char("NOK Relationship")

    #  CALCULATE MMBER SUBSCRIPTION
    total = fields.Integer(
        'Total Including Subscription',
        compute='get_totals')
    total_subsequent = fields.Integer(
        'Total Subsequent Subscription',
        compute='get_pay_balance_total')
    balance_total = fields.Integer('Outstandings')
    due_date = fields.Datetime('Due payment date ')
    date_order = fields.Date('Offer Date', default=fields.Date.today())
    membership_date_from = fields.Date(string='Membership Start Date', help='Date from which membership becomes active.')
    membership_date_to = fields.Date(string='Membership End Date', help='Date until which membership remains active.')
    invoice_id = fields.Many2many('account.invoice', string='Invoice', store=True)
    asso_member = fields.Boolean(string='Associate Member')
    active = fields.Boolean(string='Active', default=True)
    is_existing = fields.Boolean(string='Is Existing', default=False) #  domain=[('is_member','=', True)]))
    depend_name = fields.Many2many('register.spouse.member', string="Dependents", domain=lambda self: self.get_parent_dependents())
    binary_attach_cv = fields.Binary('Attach CV')
    binary_fname_cv = fields.Char('Binary Name')
    # tester_muliple_file = fields.Many2many("ir.attachment", string="Upload multiple Files")
    binary_attach_letter = fields.Binary('Attach Letter')
    binary_fname_letter = fields.Char('Binary Name')
    users_followers = fields.Many2many('hr.employee', string='Add followers')
    date_pickup = fields.Datetime('Date of Form Pickup')
    date_issue_green = fields.Datetime('Green Card Issued on')
    date_issue_white = fields.Datetime('White Form Issued on')
    duration_pick = fields.Float('Pickup Duration', store=True, compute='get_duration_pick')
    delay_charges = fields.Float('Delay Charges', store=True, compute='check_pickupp_duration')
    int_form_price = fields.Float('Intending Member Form Price', required=True, default=8000)
    section_heads = fields.Many2many('res.partner', 'name_customer_rel', 'name_id', 'customer_id', string='Section Heads') 
    subscription = fields.Many2many('subscription.payment', string='Add Sections')
    summary_line = fields.Many2many('summary.section.line', string='Cost Summary')
    section_line = fields.Many2many('section.line', string='Add Sections')
    account_migration_line = fields.Many2many('member.account.migration', string='Account Migrations')
    email_ids = fields.Many2many('member.emailing.status', string="Email Status")
    payment_ids = fields.Many2many('account.payment', string='All Payments')# , compute="get_payment_ids")
    
    def button_filter_outstanding(self):
        for rec in self:
            mig_line = rec.mapped('account_migration_line').filtered(lambda amt: amt.amount < 0)
            total = sum([amt.amount for amt in mig_line])
            rec.balance_total += total
            # raise ValidationError('Total is '+str(total))
            
    # @api.one
    @api.depends('invoice_id')
    def get_payment_ids(self):
        payment_list = []
        for ref in self.invoice_id:
            for rec in ref.payment_ids:
                payment_list.append(rec.id)
        self.payment_ids = payment_list

    member_age = fields.Integer(
        'Age', required=True, compute="get_duration_age")
    date_green_pickup = fields.Datetime('Date of Green Form')
    penalty_charges = fields.Float('Penalty Charges', store=True, compute='check_pickupp_duration')
    duration_pick_green = fields.Float('Green Pickup Duration', store=True, compute='get_green_duration_pick')
    green_form_price = fields.Float('Green Form Price', required=True,  default=20000)
    activity = fields.Selection([('act', 'Active'),
                                 ('inact', 'InActive'),
                                 ('dom', 'Dormant'),
                                 ], 'Active Status', default='act', index=True, required=True,  
                                 readonly=False, copy=False, track_visibility='always')

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
    ], 'Period', index=True, required=False, readonly=False, copy=False, track_visibility='always')

#  Depends on Periods
    package = fields.Many2many(
        'package.model',
        string='Compulsory Packages',
        readonly=False,
        store=True)
        # compute='get_all_packages')
        
    package_cost = fields.Float('Package Cost', readonly=False)
    biostar_user_id = fields.Integer('BioStar User ID', readonly=False)
    biostar_status = fields.Char('BioStar Status Code', readonly=True)
    biostar_start_date = fields.Datetime('BioStar Start Date', default=lambda * a: (datetime.now() + relativedelta(months=3)).strftime('%Y-%m-%d %H:%M:%S'))
    biostar_expiry_date = fields.Datetime('BioStar Expiry')

    green_id = fields.Char('Green Card ID.', size=9)
    temp_id = fields.Char('Temporary ID No.', size=9)
    date_of_temp = fields.Datetime('Date of Temp. Confirmation')
    date_of_last_sub = fields.Datetime('Last Subscription Date')
    due_dates = fields.Datetime('Due Date', compute="get_due_date")

    coffee = fields.Boolean('Coffee Fee', default=True)
    
    @api.depends('date_of_last_sub','number_period')
    def get_due_date(self):
        if self.date_of_last_sub:
            last_date = datetime.strptime(self.date_of_last_sub, '%Y-%m-%d %H:%M:%S')
            due_date = last_date + timedelta(days=int(self.number_period * 30))
            self.due_dates = due_date
     
    main_house_cost = fields.Float('Main House Fee', required=False) 
    state = fields.Selection([('draft', 'Draft'),
                              ('white', 'White Prospect'),
                              ('white_form_issued', 'Form issued'),
                              ('wait', 'Waiting List'),
                              ('interview', 'Interview'),
                              ('issue_green', 'Green Card Issue'),
                              ('green penalty', 'Penalty'),
                              ('account', 'Account&Finance'),
                              ('green', 'Green'),
                              ('temp', 'Temporal'),
                              ('induction', 'Induction'),
                              ('manager', 'Manager'),
                              ('manager_two', 'Manager'),
                              ('ord', 'Ordinary'),
                              ('jun', 'Junior'),
                              ('life', 'Life'),
                              ('hon', 'Honorary'),
                              ('suspension', 'Suspension'),
                              ], default='draft', string='Status')

    sub_line = fields.One2many('subscription.line', 'member_id', string='Sub Lines')
    date_of_interview = fields.Datetime('Date of Interview')
    coffee_book = fields.Float('Coffee Book Fee', default=10000.00, required=True)
    spouse_amount = fields.Float('Spouse Total Amount(Prorated)')#compute="get_spouse_proprated_price")
    child_amount = fields.Float('Child Total Amount(Prorated)')
    section_duration = fields.Selection([('bi_annual', 'Bi-Annual'), ('Yearly', 'Yearly'),
    ], 'Subscription Mode', default="bi_annual", compute="get_duration_period", 
    index=True, required=False, readonly=False, copy=False, track_visibility='onchange', 
    help="Select to add set up for bi annual or yearly subscription for club")

    section_int = fields.Integer('Section Figure', 
                                 default=6, 
                                 compute="get_section_duration",
                                 help="On change of subscription mode, the it sets the right value ")
    entry_fee = fields.Float('Entry', default=0.0)
    special_levy = fields.Float('Special levy', default=0.0)
    sub_levy = fields.Float('Subscription levy',default=0.0)
    duration_period = fields.Selection([
        ('Months', 'Months'),
        ('Full Year', 'Full Year')], 'Duration to Pay', default='Months', 
        index=True, required=False, readonly=False, copy=False, track_visibility='always')
    
    number_period = fields.Integer('Number of Years/Months', default=6)
    harmony = fields.Float('Harmony Magazine Fee', default=2000.00, required=True)
    binary_attach_interview = fields.Binary('Attach Upload Report')
    binary_fname_interview = fields.Char('Interview Report')
    
    # ################## MEMBER INFORMATION ####################3
    place_of_work = fields.Char('Name of Work Place')
    work_place_manager_name = fields.Char('Manager')
    email_work = fields.Char('Work Place Email', required=False)
    address_work = fields.Text('Work Address') 
    business_address = fields.Text('Business Address') 
    passport_number = fields.Char('Passport Number')
    nationality = fields.Many2one('res.country', 'Country')
    
    resident_permit = fields.Char('Resident Permit Number')
    position_holder = fields.Char('Position in Company')
    nok_address_work = fields.Text('Next of Kin Address') 
    
    @api.one
    @api.depends('section_duration')
    def get_section_duration(self):
        if self.section_duration == "bi_annual":
            self.section_int = 6
        elif self.section_duration == "Yearly":
            self.section_int = 1

    @api.depends('duration_period')
    def get_duration_period(self):
        for rec in self:
            if rec.duration_period == "Months":
                rec.write({'section_int': 6})
            elif rec.section_duration == "Full Year":
                rec.write({'section_int': 1})

    def get_parent_dependents(self):
        domain = [('sponsor','=', self.id)]
        return domain

    @api.one
    @api.depends('number_period', 'depend_name')
    def get_spouse_proprated_price(self): 
        sub_total = 0.0
        for subscribe in self.depend_name:
            if subscribe.relationship == 'Child':
                sub_total += 0.0
            else:
                if self.duration_period == "Months":
                    for sub in subscribe.spouse_subscription:
                        if sub.amount == 0:
                            raise ValidationError('There is no subscription amount in one of the selected dependents')
                        else:
                            sub_total += (sub.amount / 6) * self.number_period
                elif self.duration_period == "Full Year":
                    for sub2 in subscribe.spouse_subscription:
                        if sub2.amount == 0:
                            raise ValidationError('There is no subscription \
                                amount in one of the selected dependents')
                        else:
                            sub_total += (sub2.amount * 2) * self.number_period                    
        self.spouse_amount = sub_total

    # @api.multi 
    # def migrate_company_button(self):
    #     '''DOC: Used to migrate existing company id'''
    #     company = self.env['res.company'].search([('name', '=', 'Company Membership')],limit=1)
    #     member_ids = self.env['member.app'].search([])
    #     for rec in member_ids:
    #         rec.company_id = company.id

    @api.multi 
    def migration_subscription(self):
        '''DOCS: Create a section line, open the section ids column and select a product that is related 
        to the section name in the previous subscription product
        ''' 
        members = self.env['member.app'].search([])
        spouse_dependents = self.env['register.spouse.member'].search([])
         
        if members:
            for rec in members: # searches all members
                records_amend = []
                member_old_subscription = rec.mapped('subscription') # gets the previous subscription lines NOTE: It is now hidden make it visible in order to see what you are doing
                for prods in member_old_subscription:
                    member_section_line = self.env['section.line'].search([('section_ids.product_id', '=', prods.product_id.id), ('dependent_type', '=', "member")])
                    if member_section_line:
                        for lines in member_section_line:
                            records_amend.append(lines.id)
                rec.write({'section_line': [(6, 0, records_amend)]})

        if spouse_dependents:
            for rec in spouse_dependents: # searches all members
                records = []
                member_old_subscription = rec.mapped('spouse_subscription') # gets the previous subscription lines NOTE: It is now hidden make it visible in order to see what you are doing
                for prods in member_old_subscription:
                    member_section_line = self.env['section.line'].search([('section_ids.product_id', '=', prods.subscription.product_id.id), ('dependent_type', '=', "spouse")])
                    if member_section_line:
                        for lines in member_section_line:
                            records.append(lines.id)
                rec.write({'section_line': [(6, 0, records)]})

        
    @api.one
    def migrationcron(self):
        section_line = self.env['section.line']
        subscription = self.env['subscription.payment'].search([])

        # all members record 
        members = self.env['member.app'].search([])
        spouse_dependents = self.env['register.spouse.member'].search([('relationship', '=', 'spouse')])
        child_dependents = self.env['register.spouse.member'].search([('relationship', '=', 'child')])

        if members:
            for rec in members: # searches all members
                    member_old_subscription = rec.mapped('subscription') # gets the previous subscription lines NOTE: It is now hidden make it visible in order to see what you are doing
                    for prods in member_old_subscription:
                        member_section_line = self.env['section.line'].search([('section_ids', '=', prods.product_id.id), ('dependent_type', '=', "member")])
                        if member_section_line:
                            for lines in member_section_line:
                                rec.write({'section_line': [(4, lines.id)]})

        if spouse_dependents:
            for rec in spouse_dependents: # searches all members
                member_old_subscription = rec.mapped('subscription') # gets the previous subscription lines NOTE: It is now hidden make it visible in order to see what you are doing
                for prods in member_old_subscription:
                    member_section_line = self.env['section.line'].search([('section_ids', '=', prods.product_id.id), ('dependent_type', '=', "spouse")])
                    if member_section_line:
                        for lines in member_section_line:
                            rec.write({'section_line': [(4, lines.id)]})

        if child_dependents:
            for rec in child_dependents: # searches all members
                member_old_subscription = rec.mapped('subscription') # gets the previous subscription lines NOTE: It is now hidden make it visible in order to see what you are doing
                for prods in member_old_subscription:
                    member_section_line = self.env['section.line'].search([('section_ids', '=', prods.product_id.id), ('dependent_type', '=', "child")])
                    if member_section_line:
                        for lines in member_section_line:
                            rec.write({'section_line': [(4, lines.id)]})

    @api.onchange('duration_period')
    def change_number_period(self):
        if self.duration_period == "Full Year":
            self.number_period = 1
        else:
            self.number_period = 6

    def summary_line_func(self, sub_payment_id, section_ids_id, section_ids, member_amountt, spouse_amountt, child_amountt):
        summary_line_obj = self.env['summary.section.line']
        check_lines = self.mapped('summary_line').filtered(lambda s: s.section_ids.name == section_ids and s.sub_payment_id.id == sub_payment_id)
        if check_lines:
            for check in check_lines:
                check_lines.write({
                    'child_cost': child_amountt if child_amountt != 0 else check_lines.child_cost,
                    'member_cost': member_amountt if member_amountt != 0 else check_lines.member_cost,
                    'spouse_cost': spouse_amountt if spouse_amountt != 0 else check_lines.spouse_cost,
                })
        else:
            summary_line_id = summary_line_obj.create({
                'sub_payment_id': sub_payment_id, 
                'section_ids': section_ids_id, 
                'child_cost': child_amountt,
                'member_cost': member_amountt,
                'spouse_cost': spouse_amountt,
            })
            self.summary_line = [(4, summary_line_id.id)]

    def generate_member_summary_line(self, sub_payment_id, section_ids, amount):
        # lines =[]
        summary_line_obj = self.env['summary.section.line']
        summary_line_id = summary_line_obj.create({
                'sub_payment_id': sub_payment_id,
                'section_ids': section_ids,
                'member_cost': amount,
                'spouse_cost': 0,
                'child_cost': 0,

            })
        # lines.append(summary_line_id.id)
        self.summary_line = [(4, summary_line_id.id)]

    def calculate_overall_bill(self):
        '''TEST FOR THE METHOD: 
            Create member, add section line with type subscription and section id as eg. QUASH.
            Add a dependent, create a section line with type subscription and add section ID eg. QUASH
            
            Repeat process for type Levy, and Entry FEE,
            Create child dependent dont add Entry Fee line, and test
        '''
         
        spouse_subscription_lines = None
        child_subscription_line = None
        member_subscription_line = None
        member_levy_line = None
        spouse_levy_lines = None
        child_levy_line = None
        child_entry_line = None 
        spouse_entry_line = None 
        member_entry_line = None
        
        spouse_added_line = None
        child_added_line = None
        member_added_line = None
         
        lines =[]

        dependants = self.mapped('depend_name')
        for dep in dependants:
            if dep.relationship == 'Child':
                child_subscription_line = dep.mapped('section_line').filtered(lambda s: s.sub_payment_id.paytype == "subscription")
                child_levy_line = dep.mapped('section_line').filtered(lambda s: s.sub_payment_id.paytype == "levy")
                child_entry_line = dep.mapped('section_line').filtered(lambda s: s.sub_payment_id.paytype == "entry_fee")
                child_added_line = dep.mapped('section_line').filtered(lambda s: s.sub_payment_id.paytype in ["others","special", "addition"])
            else:
                spouse_subscription_lines = dep.mapped('section_line').filtered(lambda s: s.sub_payment_id.paytype == "subscription")
                spouse_levy_lines = dep.mapped('section_line').filtered(lambda s: s.sub_payment_id.paytype == "levy")
                spouse_entry_line = dep.mapped('section_line').filtered(lambda s: s.sub_payment_id.paytype == "entry_fee")
                spouse_added_line = dep.mapped('section_line').filtered(lambda s: s.sub_payment_id.paytype in ["others","special", "addition"])

        member_subscription_line = self.mapped('section_line').filtered(lambda s: s.sub_payment_id.paytype == "subscription")
        member_levy_line = self.mapped('section_line').filtered(lambda s: s.sub_payment_id.paytype == "levy")
        member_entry_line = self.mapped('section_line').filtered(lambda s: s.sub_payment_id.paytype == "entry_fee")
        member_added_line = self.mapped('section_line').filtered(lambda s: s.sub_payment_id.paytype in ["others","special", "addition"])
        
        summary_line_obj = self.env['summary.section.line']
        if member_subscription_line:
            for rec in member_subscription_line:
                summary_line_id = summary_line_obj.create({
                    'sub_payment_id': rec.sub_payment_id.id,
                    'section_ids': rec.section_ids.id,
                    'member_cost': rec.amount,
                    'spouse_cost': 0,
                    'child_cost': 0,

                })
                lines.append(summary_line_id.id)

            # Adds the summary_object to the summary
            self.summary_line = [(6, 0, lines)] 

        if spouse_subscription_lines:
            for spo in spouse_subscription_lines: 
                self.summary_line_func(spo.sub_payment_id.id, spo.section_ids.id, spo.section_ids.name, 0, spo.amount, 0)
       

        if child_subscription_line:
            for chd in child_subscription_line: 
                self.summary_line_func(chd.sub_payment_id.id, chd.section_ids.id, chd.section_ids.name, 0, 0, chd.amount)
                
        if member_levy_line:
            for rec in member_levy_line:
                self.generate_member_summary_line(rec.sub_payment_id.id, rec.section_ids.id, rec.amount)
        
        if spouse_levy_lines:
            for spo in spouse_levy_lines: 
                self.summary_line_func(spo.sub_payment_id.id, spo.section_ids.id, spo.section_ids.name, 0, spo.amount, 0)
       
        if child_levy_line:
            for chd in child_levy_line: 
                self.summary_line_func(chd.sub_payment_id.id, chd.section_ids.id, chd.section_ids.name, 0, 0, chd.amount)
         
        if member_entry_line:
            for rec in member_entry_line:
                self.generate_member_summary_line(rec.sub_payment_id.id, rec.section_ids.id, rec.amount)

        if spouse_entry_line:
            for spo in spouse_entry_line: 
                self.summary_line_func(spo.sub_payment_id.id, spo.section_ids.id, spo.section_ids.name, 0, spo.amount, 0)
                 
        if child_entry_line:
            for chd in child_entry_line: 
                self.summary_line_func(chd.sub_payment_id.id, chd.section_ids.id, chd.section_ids.name, 0, 0, chd.amount)
         
        if member_added_line:
            for mem in member_added_line: 
                self.summary_line_func(mem.sub_payment_id.id, mem.section_ids.id, mem.section_ids.name, mem.amount, 0, 0)
        
        if spouse_added_line:
            for spo in spouse_added_line: 
                self.summary_line_func(spo.sub_payment_id.id, spo.section_ids.id, spo.section_ids.name, 0, spo.amount, 0)
       
        if child_added_line:
            for chd in child_added_line: 
                self.summary_line_func(chd.sub_payment_id.id, chd.section_ids.id, chd.section_ids.name, 0, 0, chd.amount)
        
    @api.multi
    def mass_mailing(self):
        # self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        MemberObj = self.env['member.app']
        ids = self.env.context.get('active_ids', [])
        ctx = dict()
        fail_to_send = []
        for memberId in ids:
            memberId = MemberObj.browse([memberId]) 
            if memberId.state == 'ord':
                if memberId.email:
                    try:
                        template_id = ir_model_data.get_object_reference('member_app', 'email_template_for_member')
                    except ValueError:
                        template_id = False

                    ctx.update({
                        'default_model': 'member.app',
                        'default_res_id': memberId.id,
                        'default_use_template': bool(template_id),
                        'default_template_id': template_id,
                        'default_composition_mode': 'comment',
                        'email_to': memberId.email,
                        'subscription': '-',
                    })
                    self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(memberId.id, True)
                else:
                    fail_to_send.append(memberId.identification)
            else: 
                pass 
        if fail_to_send:
            raise ValidationError(_("Mail failed for these members because they don't have email address" + str(fail_to_send)))
        return True   
 
    @api.one
    @api.depends('subscription')
    def get_totals(self):
        section = 0.0
        total = 0.0
        for sub in self.section_line:
            total += sub.amount
        self.total = total
        
    @api.one
    @api.depends('invoice_id')
    def get_pay_balance_total(self):
        balance = 0.0
        paid =0.0
         
        for fec in self.invoice_id:
            for tec in fec.payment_ids:
                paid += tec.amount
                balance += tec.balances 
        self.total_subsequent = paid
 
    @api.onchange('partner_id')
    def get_partner_account(self):
        for rex in self:
            rex.account_id = rex.partner_id.property_account_receivable_id.id
 
    # # # # Date check # # # # # 
    @api.depends('date_pickup')
    def get_duration_pick(self):
        for rec in self:
            start = rec.date_pickup
            end = fields.Datetime.now()
            if start and end:
                server_dt = DEFAULT_SERVER_DATETIME_FORMAT
                strt = datetime.strptime(start, server_dt)
                ends = datetime.strptime(end, server_dt)
                durations = ends - strt
                rec.duration_pick = durations.days
    
    @api.model
    def _run_cron(self):
        return self.run_crons()
            
    #@api.multi
    def run_crons(self):
        '''The cron runs to check if the difference in year between the last payment and the current date
        is between the range of 4 - 5, if true, sets the member to inactive, if greater than 5 years, sets
        the member to dormant'''
        for rec in self: 
            current_date = fields.Date.today()
            for date in rec.payment_ids: # payment_line2:
                last_date = date[-1].payment_date
            if current_date and last_date:
                server_dt = DEFAULT_SERVER_DATETIME_FORMAT
                start = datetime.strptime(last_date, '%Y-%m-%d')
                end = datetime.strptime(current_date,'%Y-%m-%d')
                diff = end - start
                duration = diff.days/365
                if duration in range(4,6): 
                    rec.write({'activity': "inact", "active":False})
                    
                elif duration > 5:
                    rec.write({'activity': "dom", "active":False}) 
                    
                else:
                    rec.write({'activity': "act", "active":False})
                    
    @api.multi
    @api.depends('date_green_pickup')
    def get_green_duration_pick(self):
        for rec in self:
            start = rec.date_green_pickup
            end = fields.Datetime.now()
            if start and end:
                server_dt = DEFAULT_SERVER_DATETIME_FORMAT
                strt = datetime.strptime(start, server_dt)
                ends = datetime.strptime(end, server_dt)
                durations = ends - strt
                rec.duration_pick_green = durations.days

    # # # # Date check # # # # # 
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

    @api.depends('duration_pick')
    def check_pickupp_duration(self):
        for rec in self:
            if rec.duration_pick > 3:
                if self.state == "wait":
                    rec.delay_charges = 5000
                elif self.state == "issue_green":
                    rec.delay_charges = 15000
                return rec.int_form_price + rec.delay_charges

    @api.multi
    def button_register_spouse(self):  #  Send memo back
        return {
            'name': "Register Dependant",
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'register.spouse.member',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {
                'default_sponsor': self.id,
            },
        }

#  TREAT IMPORTANT REGISTER WHITE
    @api.multi
    def button_white_payments(self):  #  state draft
        self.state = 'white'
        
        if not self.is_existing:
            account_receivable = self.env['account.account'].search([('user_type_id.name','ilike', 'Receivable')], limit=1).id
            account_payable = self.env['account.account'].search([('user_type_id.name','=ilike', 'Payable')], limit=1).id
        
            partner = self.env['res.partner']
            part = partner.create({'street': self.street, 'email': self.email, 'state_id': self.state_id.id,
                                    'title':self.title.id, 'city':self.city, 'image': self.image,
                                    'phone':self.phone, 'function': self.occupation,
                                    'name': str(self.surname) +' '+ str(self.first_name) +' '+ str(self.middle_name),
                                    'property_account_receivable_id': account_receivable,
                                    'property_account_payable_id': account_payable,
                                    })
            self.partner_id = part.id
            # middle_name = " "
            # if self.middle_name:
            #     middle_name = self.middle_name
            # names = str(self.first_name) +' '+str(self.middle_name)+' '+str(self.middle_name)
            
            # partner_search = self.env['res.partner'].search([('name', '=', names)])
            # if not partner_search:
            # part = partner.create({'street': self.street, 'email': self.email, 'state_id': self.state_id.id,
            #                         'title':self.title.id, 'city':self.city, 'image': self.image,
            #                         'phone':self.phone, 'function': self.occupation,
            #                         'name': str(self.surname) +' '+ str(self.first_name) +' '+ middle_name,
            #                         'property_account_receivable_id': self.account_id.id,
            #                         'property_account_payable_id':self.account_id.id
            #                         })
            # self.partner_id = part.id
            # else:
            #     raise ValidationError('Member Already Existing, Kindly click the existing checkbox')
            
        else:
            pass 
        self.date_issue_white = fields.Datetime.now()
        return self.sendmail_white_confirm()
          
    @api.one
    def state_payment_inv(self,amount,pay_date):
        if self.state == "white":
            self.write({'state': 'white_form_issued'})
            self.section_line = False
        
        elif self.state == "white_form_issued": 
            self.write({'state': 'wait'})
            self.section_line = False
        
        elif self.state == "interview": 
            self.write({'date_issue_green': fields.Datetime.now(), 'state': 'issue_green'})
            self.section_line = False
        
        elif self.state == "green penalty": 
            self.write({'state': 'green'})
            self.section_line = False

        elif self.state == "green":
            self.write({'temp_id':self.green_id, 
                        'date_of_last_sub': fields.Datetime.now(),
                        'date_of_temp': fields.Datetime.now(),
                        'state': 'temp'}) 

    def define_invoice_line(self,invoice):
        inv_id = invoice.id
        invoice_line_obj = self.env["account.invoice.line"]
        journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        prd_account_id = journal.default_credit_account_id.id
        # section_lines = self.mapped('section_line') #.filtered(lambda self: self.sub_payment_id.paytype in ['others'])
        section_lines = self.mapped('section_line') if self.state not in  ['ord'] else self.mapped('section_line').filtered(lambda self: self.sub_payment_id.paytype not in ['main_house', 'entry_fee', 'addition'])
        if section_lines:
            for record in section_lines:
                curr_invoice_line = {
                        'product_id': record.section_ids.product_id.id if record.section_ids.product_id.id else False, #product_search.id if product_search else False,
                        'name': "Charge for "+ str(record.sub_payment_id.name) + ' -- ' +str(record.section_ids.name),
                        'price_unit': record.amount,
                        'quantity': 1.0,
                        'account_id': invoice.journal_id.default_credit_account_id.id if invoice.journal_id.default_credit_account_id else prd_account_id, #product_search.categ_id.property_account_income_categ_id.id,
                        'invoice_id': inv_id,
                            }
                invoice_line_obj.create(curr_invoice_line)
        else:
            raise ValidationError('Please ensure at the stage, \n \
                that section line with paytype as others is set\n \
                e.g Coffee Fee\n \
                    magazine fee \n\
                    Harmony fee.')

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
                    section_lines = child.mapped('section_line') if self.state not in  ['ord'] else child.mapped('section_line').filtered(lambda self: self.sub_payment_id.paytype not in ['main_house', 'entry_fee', 'addition'])
                    child.biostar_status = False
                    for sub2 in section_lines:
                        total = 0
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
                            'product_id': sub2.section_ids.product_id.id if sub2.section_ids.product_id.id else False,
                            'name': "Child Charge for "+ str(sub2.sub_payment_id.name) + ' -- ' + str(sub2.section_ids.name), # if product_child else sub2.subscription.name)+ ": Period-"+(self.subscription_period),
                            'price_unit': total,
                            'quantity': 1.0,
                            'account_id': sub2.section_ids.debit_account_id.id if sub2.section_ids.debit_account_id else invoice.journal_id.default_credit_account_id.id, # product_child.categ_id.property_account_income_categ_id.id or record.account_id.id,
                            'invoice_id': inv_id,
                        }
                        invoice_line_obj.create(curr_invoice_child_subs)
                        '''writes on dependents record to confirm the dependent if not done.'''
                        child.state = 'confirm'

            if spouse_lines:
                for spouse in spouse_lines:
                    spouse.biostar_status = False
                    section_lines = spouse.mapped('section_line') if self.state not in  ['ord'] else spouse.mapped('section_line').filtered(lambda self: self.sub_payment_id.paytype not in ['main_house', 'entry_fee', 'addition'])
                    # section_lines = spouse.mapped('section_line')#.filtered(lambda self: self.sub_payment_id.paytype in ['special'])
                    for sub2 in section_lines:
                        spousetotal = 0
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
                            'product_id': sub2.section_ids.product_id.id if sub2.section_ids.product_id.id else False,
                            'name': "Spouse Charge for "+ str(sub2.sub_payment_id.name) + ' -- ' + str(sub2.section_ids.name), # if product_child else sub2.subscription.name)+ ": Period-"+(self.subscription_period),
                            'price_unit': spousetotal,
                            'quantity': 1.0,
                            'account_id': sub2.section_ids.debit_account_id.id if sub2.section_ids.debit_account_id else invoice.journal_id.default_credit_account_id.id,# product_child.categ_id.property_account_income_categ_id.id or record.account_id.id,
                            'invoice_id': inv_id,
                        }
                        invoice_line_obj.create(curr_invoice_spouse_subs)
                        '''writes on dependents record to
                            confirm the dependent if not done.
                        '''
                        spouse.state = 'confirm'
        
    @api.multi
    def dummy_back_green(self):
        self.state = 'green'
        
    @api.multi
    def dummy_back_issue_green(self):
        self.state = 'issue_green'
    @api.multi
    def dummy_back_interview(self):
        self.state = 'interview'
    
    @api.multi
    def create_white_member_bill(self):
          
        # product_name = product_name
        """ Create Customer Invoice for members.
        """
        invoice_list = []
        qty = 1
        invoice_line_obj = self.env["account.invoice.line"]
        invoice_obj = self.env["account.invoice"]
         
        for inv in self:
            inv.biostar_status = False
            invoice = invoice_obj.create({
                'partner_id': inv.partner_id.id,
                'account_id': inv.partner_id.property_account_receivable_id.id, # inv.partner_id.property_account_payable_id.id, 
                'fiscal_position_id': inv.partner_id.property_account_position_id.id,
                'branch_id': self.env.user.branch_id.id, 
                'date_invoice': datetime.today(),
                'type': 'out_invoice',
                'company_id': self.env.user.company_id.id, #self.company_id.id,
                # 'type': 'out_invoice', # customer
            }) 
            if self.state == 'white':
                section_lines = self.mapped('section_line').filtered(lambda self: self.sub_payment_id.paytype in ['addition'])
                if not section_lines:
                    raise ValidationError("Please ensure a section line contains an addtitional fee type such as:\n\
                        Coffee, Magazine, Harmony fee, Penalty fee etc.")
                self.define_invoice_line(invoice)
                
            elif self.state == 'white_form_issued':
                section_lines = self.mapped('section_line').filtered(lambda self: self.sub_payment_id.paytype in ['addition'])
                if not section_lines:
                    raise ValidationError("Please ensure a section line contains an addtitional fee type such as:\n\
                        Coffee, Magazine, Harmony fee, Penalty fee, Green Card Fee etc.") 
                self.define_invoice_line(invoice)

            elif self.state == 'interview':
                section_lines = self.mapped('section_line').filtered(lambda self: self.sub_payment_id.paytype in ['addition'])
                if not section_lines:
                    raise ValidationError("Please ensure a section line contains an addtitional fee type such as:\n\
                        Coffee, Magazine, Harmony fee, Penalty fee, Green Card Feeetc.")
                self.define_invoice_line(invoice) 

            elif self.state == 'green penalty':
                section_lines = self.mapped('section_line').filtered(lambda self: self.sub_payment_id.paytype in ['addition'])
                if not section_lines:
                    raise ValidationError("Please ensure a section line contains an addtitional fee type such as:\n\
                        Coffee, Magazine, Harmony fee, Penalty fee, Green Card Fee etc.") 
                self.define_invoice_line(invoice)

            elif self.state == 'green':
                # self.define_subscriptions_invoice_line(invoice)
                section_lines = self.mapped('section_line').filtered(lambda self: self.sub_payment_id.paytype not in ['addition','main_house'])
                if not section_lines:
                    raise ValidationError("Please ensure a section line contains fee of type such as:\n\
                        Subscription fee, Levy, Entry fee etc.")
                    
                self.define_invoice_line(invoice) 
                self.dependent_invoice_line(invoice)
            
            elif self.state not in ['green', 'green penalty', 'interview', 'white_form_issued', 'white']:
                self.define_invoice_line(invoice) 
                self.dependent_invoice_line(invoice)

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

    @api.multi
    def generate_receipt(self): 
        search_view_ref = self.env.ref(
            'account.view_account_invoice_filter', False)
        form_view_ref = self.env.ref('account.invoice_form', False)
        tree_view_ref = self.env.ref('account.invoice_tree', False) 
        return {
            'domain': [('id', '=', [item.id for item in self.invoice_id])],
            'name': 'Invoices',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'views': [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')],
            'search_view_id': search_view_ref and search_view_ref.id,
        } 
    @api.multi
    def button_confirm_white_payments_first(self): 
        product_name = "White Form" 
        self.write({'payment_status': 'open'}) 
        self.partner_id.property_account_receivable_id = self.env['account.account'].search([('user_type_id.name','ilike', 'Receivable')], limit=1).id if not self.partner_id.property_account_receivable_id else self.partner_id.property_account_receivable_id.id
        self.partner_id.property_account_payable_id = self.env['account.account'].search([('user_type_id.name','=ilike', 'Payable')], limit=1).id if not self.partner_id.property_account_payable_id else self.partner_id.property_account_payable_id.id
        
        self.sendmail_white_confirm()
        return self.create_white_member_bill() # self.button_payments(name, amount, level)
  
    @api.multi
    def button_confirm_white_delay_payments(self):
        product_name = "White Card Delay"
        popup_message = "Hurray!!!... There is no penalty charge for the member"
        
        if self.date_pickup:
            total_duration = 0.0
            start = self.date_issue_white
            end = self.date_pickup# fields.Datetime.now()
            if start and end:
                server_dt = DEFAULT_SERVER_DATETIME_FORMAT
                strt = datetime.strptime(start, server_dt)
                ends = datetime.strptime(end, server_dt)
                durations = ends - strt
                total_duration = durations.days # / 365 
                
            if total_duration > 30:
                self.state = 'white_form_issued' 
                self.write({'payment_status': 'gpaid'})
                name = "White form Revalidation Fee"
                self.send_mail_green(name)
                if self.state == 'white_form_issued':
                    return self.create_white_member_bill()
                 
            elif total_duration < 30:
                self.write({'state': 'wait'})
                return self.popup_notification(popup_message)
        else:
            raise ValidationError('Please Add the fields: "White Form submission date"')
    
    def sendmail_white_confirm(self, force=False):
        email_from = self.env.user.company_id.email
        group_user_id = self.env.ref('member_app.manager_member_ikoyi').id
        #  extra = self.env.ref('ikoyi_module.inventory_officer_ikoyi').id
        #  bodyxx
        extra = self.email
        bodyx = "Dear Sir/Madam, </br>We wish to notify that you have been issued a white prospect Card on the date: {}.</br>\
             </br> Please Endure to submit the card on or before the range of 3 months of the pickup date.</br>\
             Kindly contact the Ikoyi Club 1938 for further enquires </br> Thanks".format(fields.Datetime.now())
        self.mail_sending(email_from, group_user_id, extra, bodyx)
 
    @api.one
    def button_send_interview(self):  #  state wait
        if self.date_of_interview == False:
            raise ValidationError('Please you must set the field: "Date of Interview"') 
        else:
            self.write({'state': 'interview'})
            self.send_one_interview()

    def send_one_interview(self, force=False):
        email_from = self.env.user.company_id.email
        group_user_id = self.env.ref('member_app.manager_member_ikoyi').id
        # extra = self.env.ref('ikoyi_module.inventory_officer_ikoyi').id
        extra = self.email 
        bodyx = "Dear Sir/Madam, </br>We wish to notify that you have been shortlisted for an interview at Ikoyi Club 1938.</br>\
                </br>.</br>\
                Kindly contact the Ikoyi Club 1938 for more enquires </br> Thanks"
        self.mail_sending(email_from, group_user_id, extra, bodyx)

    @api.multi
    def function_sendall_interview(self):  #  state wait
        search_id = self.env['member.app'].search([('state', '=', "wait")])
        for rec in search_id:
            search_id.write({'state': 'interview'})
            search_id.send_mail_set_interview()

    @api.multi
    def send_mail_set_interview(self, force=False):
        for rec in self:
            email_from = self.env.user.company_id.email
            group_user_id = self.env.ref('member_app.manager_member_ikoyi').id
            # extra = self.env.ref('ikoyi_module.inventory_officer_ikoyi').id
            extra = rec.email
            bodyx = "Dear Sir/Madam, </br>We wish to notify that you have \
             been shortlisted for an interview at Ikoyi Club 1938.</br>\
                </br>Interview Dated is {}.</br>\
                Kindly contact the Ikoyi Club 1938 for \
                 more enquires </br> Thanks".format(rec.date_of_interview)
            rec.mail_sending(email_from, group_user_id, extra, bodyx)
    
    @api.multi
    def send_mail_issue_green(self, force=False):
        email_from = self.env.user.company_id.email
        group_user_id = self.env.ref('member_app.manager_member_ikoyi').id
        # extra = self.env.ref('ikoyi_module.inventory_officer_ikoyi').id
        extra = self.email
        bodyx = "Dear Sir/Madam, </br>We wish to notify \
        that you have been promoted to a Green prospect\
        membership on the date: {}.</br>\
        Kindly contact the Ikoyi Club 1938 for further \
        enquires </br> Thanks".format(fields.Datetime.now())
        self.mail_sending(email_from, group_user_id, extra, bodyx)
 
    @api.multi
    def create_invoice_green(self): 
        """ Selects the interview state, make payment for green card collection
            Set state date of green pick up to current date.
            Then set state to issue_green  
            Payment is green form price + coffee book = 30000 
        """   
        product_name = "Green Card" 
        name = "Green card Fee"
        self.send_mail_green(name)
        return self.create_white_member_bill()

    @api.multi
    def set_interview(self):
        self.state = "interview"
        
    @api.multi
    def button_confirmall_green(self):
        search_id = self.env['member.app'].search([('state', '=', "issue_green")])
        if search_id:
            for mem in search_id:
                mem.write({'payment_status': 'issue', 'state': 'green'})
                mem.send_mail_issue_green()

    @api.multi
    def check_green_delay(self):
        product_name = "Green Card Penalty"
        popup_message = "Hurray!!!... There is no penalty charge for the member"
        
        if self.date_issue_green:
            total_duration = 0.0
            start = self.date_issue_green
            end = fields.Datetime.now()
            if start and end:
                server_dt = DEFAULT_SERVER_DATETIME_FORMAT
                strt = datetime.strptime(start, server_dt)
                ends = datetime.strptime(end, server_dt)
                durations = ends - strt
                total_duration = durations.days # / 365

            if total_duration > 30:
                self.state = "green penalty" 
                self.write({'payment_status': 'gpaid'})
                name = "Green Card Revalidation Fee"
                self.send_mail_green(name)
                if self.state == "green penalty":
                    return self.create_white_member_bill() 
            elif total_duration < 30:
                self.write({'state': 'green'})
                return self.popup_notification(popup_message)
        else:        
            raise ValidationError('Please Add the fields: "Green Form submission date"')
      
    def popup_notification(self,popup_message):
        view = self.env.ref('sh_message.sh_message_wizard')
        view_id = view and view.id or False
        context = dict(self._context or {})
        context['message'] = popup_message # 'Successful'
        return {'name':'Checking Alert',
                    'type':'ir.actions.act_window',
                    'view_type':'form',
                    'res_model':'sh.message.wizard',
                    'views':[(view.id, 'form')],
                    'view_id':view.id,
                    'target':'new',
                    'context':context,
                }         
    @api.multi
    def send_mail_green(self, name,force=False):
        email_from = self.env.user.company_id.email
        group_user_id = self.env.ref('member_app.manager_member_ikoyi').id
        # extra = self.env.ref('ikoyi_module.inventory_officer_ikoyi').id
        extra = self.email
        amount = self.green_form_price + 10000
        bodyx = "Dear Sir/Madam, </br>We wish to notify that a {} Card payment of N-{} have been made on the date: {}.</br>\
             Kindly contact the Ikoyi Club 1938 for any further enquires </br> Thanks".format(name, amount, fields.Datetime.now())
        self.mail_sending(email_from, group_user_id, extra, bodyx)

    @api.multi
    def button_print_green_card(self):
        pass

    def _check_fields(self):
        errors = ['Please provide details for the following : ']
        if not self.green_id:
                errors.append('-Green Card ID')
        if not self.section_line:
            errors.append('-Section Line')
 
        if not self.duration_period:
            errors.append('-Duration to Pay')
        
        if not self.subscription_period:
            errors.append('-Please Select subscription')
                
        if len(errors) > 1:
            raise ValidationError('\n'.join(errors))
        
    @api.multi
    def button_account_to_temp_payments(self):  # 
        self._check_fields()
        name = "Subscription Payment Fee"
        return self.create_white_member_bill() #product_name) 
   
    # @api.multi
    def activate_biostar(self, DT=None):
        dtoday = datetime.now() if not DT else DT #Datetime if Datetime != False else datetime.now()
        # raise ValidationError(type(DT))
        
        # datetime(2020, 2, 2, 14, 0, 40, 367000)
        '''TODO- Use datetime.now() when the code runs live. The hardcord datetime
        is to help migrate back to the month of july that ikoyi club member started
        We set the second arg, to be 7 (July) so the interval now becomes 5 i.e 
        july till (december) ''' 
        # datetime.now() + timedelta(days=120) 

        interval = None
        current_month = int(dtoday.month)
        if current_month in range(0, 6):
            """FIX[ME] Find a way to get the current month value and determine the intervals 
            to calculate for the expiry month"""
            if current_month == 1: # ie. current month = 1 (Jan) add 5 to intervals 
                interval = 5

            elif current_month == 2: # ie. current month = 2 (feb) add 5 to intervals
                interval = 4

            elif current_month == 3:
                interval = 3

            elif current_month == 4: 
                interval = 2
            
            elif current_month == 5: 
                interval = 1

            elif current_month == 6: # same month interval
                interval = 0

        elif current_month in range(6, 12):
            if current_month == 7:
                interval = 5

            elif current_month == 8:
                interval = 4

            elif current_month == 9:
                interval = 3

            elif current_month == 10: 
                interval = 2
            
            elif current_month == 11: 
                interval = 1

            elif current_month == 12:
                interval = 0


        exp = dtoday + relativedelta(months=interval)
        expiry_date = exp.replace(day= 30)# .strftime('%Y-%m-%d %H:%M:%S')
        for rec in self:
            if rec.biostar_status not in ["Processed Successfully"]:
                # "2020-06-01T00:00:00.00Z",
                # '2020-12-31T23:59:00.00Z',
                dummy_user_id = 1001111
                userId = rec.biostar_user_id
                # start_date_format = datetime.strftime(rec.biostar_start_date, "%Y-%m-%d") if rec.biostar_start_date else dtoday
                start_date_format = datetime.strftime(dtoday, "%Y-%m-%d")
                start_date = start_date_format + 'T00:00:00.00Z'

                expiry_date_format = datetime.strftime(expiry_date, "%Y-%m-%d") 
                expiry_date = expiry_date_format + 'T23:59:00.00Z'
                result = rec.biostar_connector(dummy_user_id, start_date, expiry_date) # userId
                rec.biostar_expiry_date = expiry_date_format
                rec.biostar_start_date = dtoday
                rec.biostar_status = result

                if rec.depend_name:
                    for dep in rec.depend_name:
                        if dep.biostar_user_id:
                            if dep.biostar_status not in ["Processed Successfully"]:
                                res = rec.biostar_connector(dummy_user_id, start_date, expiry_date) #dep.biostar_user_id
                                dep.biostar_status = res
                                dep.biostar_expiry_date = expiry_date_format
                                dep.biostar_start_date = fields.Datetime.now()

            
    def biostar_connector(self, userId, startDate, expiryDate):
        try:
            '''FOCUS ON: expiry_date'''

            parameters = {
                'name': 'ikoyiclub1938', 
                'password': 'pass2020',
                'user_id': '1001108'
                }
            api = 'https://api.biostar2.com/v2/login'
             
            response = requests.post(api, data = parameters, verify=False) # use verify = False to disable ssl certification issues
            print(response.headers)
            set_cookies = response.headers['Set-Cookie'] # still to get verification from biostar agents
            session_url = 'https://api.biostar2.com/v2/users/{}'.format(str(userId))

            # SECOND REQUEST RETRIVES USER DETAILS
            response2 = requests.get(session_url, headers={'Cookie': set_cookies}, verify=False)
            # print(response2.json())
            resp_val = response2.json()
            #### ENDS HERE ####

            # THIRD REQUEST POSTS THE DETAILS FROM ERP TO BIOSTAR
            user_data = dict(
                            start_datetime = startDate, 
                            expiry_datetime = expiryDate, 
                            name = resp_val['name'],
                            user_group = resp_val['user_group'],
                            access_groups = resp_val['access_groups'],
                            status = resp_val['status'],
                            security_level = resp_val['security_level'],
                            card_count = resp_val['card_count'],
                            fingerprint_template_count = resp_val['fingerprint_template_count'],
                            face_template_count = resp_val['face_template_count'],
                            )
            print(user_data)
            json_data = json.dumps(user_data)
            json_headers = {
                "Content-Type": "application/json",
                'Accept':'application/json',
                'Cookie': set_cookies
            }
            response3 = requests.put(session_url, data = json_data, headers= json_headers, verify=False)
            print(response3.json())
            result = response3.json()
            if result['message'] == "Processed Successfully":
                biostarObj = self.env['biostar.model'].search([('user_id', '=', userId)])
                memObj = self.env['member.app'].search([('biostar_user_id', '=', userId)])
                for bi in biostarObj:
                    bi.biostar_status = result['message']

                for mi in memObj:
                    mi.biostar_status = result['message']
                res = result['message']
                return res

            else:
                False
        except Exception as ex:
            raise ValidationError(ex)


    @api.multi
    def send_mail_temp(self, force=False):
        email_from = self.env.user.company_id.email
        group_user_id = self.env.ref('member_app.manager_member_ikoyi').id
        # extra = self.env.ref('ikoyi_module.inventory_officer_ikoyi').id
        extra = self.email
        bodyx = "Dear Sir/Madam, </br>We wish to notify \
         that you have been promoted to a temporary member on the date: {} \
         </br> Kindly contact the Ikoyi Club 1938 for any further enquires \
         </br> Thanks".format(fields.Datetime.now())
        self.mail_sending(email_from, group_user_id, extra, bodyx)

    # @api.one
    # def button_make_induction(self):
    #     for rec in self:
    #         if self.temp_id:
    #             start = rec.date_of_temp
    #             end = fields.Datetime.now()
    #             if start and end:
    #                 server_dt = DEFAULT_SERVER_DATETIME_FORMAT
    #                 strt = datetime.strptime(start, server_dt)
    #                 ends = datetime.strptime(end, server_dt)
    #                 durations = ends - strt
    #                 days = durations.days
    #                 if days > 90:
    #                     rec.write({'state': "induction"})
    #                     self.send_mail_induction()
    #                 elif days < 90:
    #                     raise ValidationError(
    #                         "You are trying to Set this member for induction,\
    #                          it's not up to 3months validity")
    #                     #  rec.write({'state':"induction"})
    #         else:
    #             raise ValidationError(
    #                         "Please Enter Temporarily ID")
    @api.one
    def button_make_induction(self):
        self.write({'state': "induction"}) 

    @api.multi
    def send_mail_allinduction(self, force=False):
        email_from = self.env.user.company_id.email
        mail_to = self.email
        subject = "Ikoyi Club Induction Notification"
        bodyx = "Dear Sir/Madam, </br>We wish to notify that you have been enlisted for induction on the date: {} </br>\
             Thanks".format(fields.Datetime.now())
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
                #  'email_cc':,#  + (','.join(str(extra)),
                'reply_to': email_from,
                'body_html': bodyx
            }
            mail_id = order.env['mail.mail'].create(mail_data)
            order.env['mail.mail'].send(mail_id)

    @api.multi
    def button_make_induction2(self):    
        members = self.env['member.app'].search([('state','=', 'temp')])
        if members:
            for vals in members:
                vals.write({'state': 'induction'})
                vals.send_mail_allinduction()
    @api.multi
    def action_send_induction(self):    
        members = self.env['member.app'].search([('state','=', 'temp')])
        if members:
            for vals in members:
                vals.send_mail_allinduction()

    @api.multi
    def action_send_mass_mail(self): 
        self.calculate_overall_bill()  
        members = self.env['member.app'].search([('state','=', 'ord')])
        if members:
            for vals in members:
                vals.batch_mailing(self.subscription_period)

    @api.multi
    def batch_mailing(self, subscription):
        ctx = dict()
        template = self.env['ir.model.data'].get_object('member_app', 'email_template_for_member')
        ctx.update({
                    'default_model': 'member.app',
                    'default_res_id': self.id,
                    'default_use_template': bool(template),
                    'default_template_id': template,
                    'default_composition_mode': 'comment',
                    'email_to': self.email,
                    'subscription': subscription,
                })
        sender =self.env['mail.template'].browse(template.id).with_context(ctx).send_mail(self.id)
        self.generate_mail_status()
        # self.env['mail.mail'].browse(sender).send(sender)
        return True

    def generate_mail_status(self):
        mail_status = self.env['member.emailing.status'].create({
                    'date': fields.Date.today(),
                    'status': True,
                    'number_count': 1, 
                    'member_id': self.id,
                    # 'mail_id': mail_id,
                })
        self.sudo().write({'email_ids': [(4, mail_status.id)]})

    @api.multi
    def send_mail_induction(self, force=False):
        email_from = self.env.user.company_id.email
        mail_to = self.email
        subject = "Ikoyi Club Induction Notification"
        bodyx = "Dear Sir/Madam, </br>We wish to notify that you have been enlisted for induction on the date: {} </br>\
             Thanks".format(fields.Datetime.now())
        self.mail_sending_one(email_from, mail_to, bodyx, subject)
        
    @api.multi
    def make_ordinary_or_junior(self):
        # partner = self.partner_id.name[:1]
        # partner_name = str(partner).upper()
        # sequence = self.env['ir.sequence'].next_by_code('member.app')
        # seq = str(sequence) 
        # member = self.env['member.app'].search([('partner_id.name','=ilike', partner_name+'%')])# ([('state', 'not in',['draft','white','wait', 'interview', 'issue_green', 'account','green'])])
        # #self.identification = member[-2].identification[2:]
        # # names = partner_name[::-1].zfill(6)[::-1]
        # names = partner_name + "1"
        # if member:
        #     if len(member) > 1:
        #         identification = member[-2]
        #         ident = identification.identification
        #         if ident:
        #             if len(ident) > 1:     
        #                 iden = str(ident)[1:] 
        #                 iden_num = int(iden) + 1
        #                 self.identification = partner_name + str(iden_num)
        #             else:
        #                 self.identification = names
        #         else:
        #             self.identification = names
        #     else:
        #         self.identification = names
        # else:
        #     self.identification = names 
       
        body = "Ordinary Member Promoted on %s" % (
                datetime.strftime(datetime.today(), '%d-%m-%y'))
        records = self._get_followers()
        followers = records
        self.message_post(
                body=body,
                subtype='mt_comment',
                message_type='notification',
                partner_ids=followers) 
        self.send_mail_manager()
        self.write({'state': 'manager'})
        
    def send_mail_manager(self, force=False):
        email_from = self.env.user.company_id.email
        group_user_id = self.env.ref('member_app.manager_member_ikoyi').id
        # extra = self.env.ref('ikoyi_module.inventory_officer_ikoyi').id
        extra = self.email
        bodyx = "Dear Sir/Madam, </br>I wish to notify you that you have been completed all necessary requirement for Ikoyi Club Membership\
        . The Membership Manager will soon confirm your approval to permanent\
        membership.</br> Kindly contact Ikoyi Club 1938 for further details</br>Thanks"
        self.mail_sending(email_from, group_user_id, extra, bodyx)

    @api.multi
    def make_manager_confirms(self):
        partner = self.partner_id.name[:1]
        partner_ids = self.env['res.partner'].search([('id','=', self.partner_id.id)])
        partner_name = str(partner).upper()
        sequence = self.env['ir.sequence'].next_by_code('member.app')
        seq = str(sequence)
        member = self.env['member.app'].search([('partner_id.name','=ilike', partner_name+'%')])# ([('state', 'not in',['draft','white','wait', 'interview', 'issue_green', 'account','green'])])
        # self.identification = member[-2].identification[2:]
        # names = partner_name[::-1].zfill(6)[::-1]
        names = partner_name + "1"
        if member:
            if len(member) > 1:
                identification = member[-2]
                ident = identification.identification
                if ident:
                    if len(ident) > 1:     
                        iden = str(ident)[1:] 
                        iden_num = int(iden) + 1
                        self.identification = partner_name + str(iden_num)
                    else:
                        self.identification = names
                else:
                    self.identification = names
            else:
                self.identification = names
        else:
            self.identification = names
        
        body = "Ordinary Member Promoted on %s" % (
            datetime.strftime(datetime.today(), '%d-%m-%y'))
        records = self._get_followers()
        followers = records
        self.message_post(
            body=body,
            subtype='mt_comment',
            message_type='notification',
            partner_ids=followers)
        self.send_mail_confirm_final()

        partner_ids = self.env['res.partner'].search(
            [('id', '=', self.partner_id.id)])
        if partner_ids:
            partner_ids.write({'is_member': True, 'identification': names})
        else:
            raise ValidationError('No Partner Record found for this member')
        self.write({'state': 'ord'})

    def send_mail_confirm_final(self, force=False):
        email_from = self.env.user.company_id.email
        group_user_id = self.env.ref('member_app.membership_officer_ikoyi').id
        # extra = self.env.ref('ikoyi_module.inventory_officer_ikoyi').id
        extra = self.email
        bodyx = "Dear Sir/Madam, </br>Congratulations! You have been approved as a permanent\
        member Ikoyi Club with ID. Number {} on the date {}.</br> Kindly contact Ikoyi\
         Club 1938 for further details</br>Thanks".format(self.identification, fields.Datetime.now())
        self.mail_sending(email_from, group_user_id, extra, bodyx)

    # # # # # # # # # # # # # # # # # # # # # # # # #  EMAIL FOR ONE ONLY mail_sending # 
    def get_url(self, id, model):
        base_url = http.request.env['ir.config_parameter'].sudo(
        ).get_param('web.base.url')
        base_url += '/web# id=%d&view_type=form&model=%s' % (id, mmodel)

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
            subject = "Membership Notification"

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

    @api.one
    def life_member(self):
        for rec in self:
            if rec.state == "ord":
                start = rec.date_of_temp
                end = fields.Datetime.now()
                if start and end:
                    server_dt = DEFAULT_SERVER_DATETIME_FORMAT
                    strt = datetime.strptime(start, server_dt)
                    ends = datetime.strptime(end, server_dt)
                    durations = ends - strt
                    days = durations.days
                    if days > 9125 and self.member_age > 65:
                        rec.write({'state': "manager_two"})
                        self.send_mail_life()
                    elif days < 9125 and self.member_age < 65:
                        raise ValidationError(
                            'You cannot confirm to life membership because the\
                                               Member\'s age must not be lower than 65 years<br/>\
                                              and Membership period Must be up to 25 years')
                    else:
                        raise ValidationError(
                                        'Please the date of Temporarily confirmation must be greater than 20 years')
            # return True

    @api.multi
    def send_mail_life(self, force=False):
        email_from = self.env.user.company_id.email
        group_user_id = self.env.ref('member_app.manager_member_ikoyi').id
        # extra = self.env.ref('ikoyi_module.inventory_officer_ikoyi').id
        extra = self.email
        bodyx = "Dear Sir/Madam, </br>We wish to notify that you have been enlisted for promotion to a life member on the date: {} </br>\
             Thanks".format(fields.Datetime.now())
        self.mail_sending(email_from, group_user_id, extra, bodyx)

    @api.multi
    def make_manager_life_confirms(self):
        body = "Ordinary Member Promoted on %s" % (
            datetime.strftime(datetime.today(), '%d-%m-%y'))
        records = self._get_followers()
        followers = records
        self.message_post(
            body=body,
            subtype='mt_comment',
            message_type='notification',
            partner_ids=followers)
        self.send_mail_confirm_final_life()
        self.write({'state': 'life'})

    def send_mail_confirm_final_life(self, force=False):
        email_from = self.env.user.company_id.email
        group_user_id = self.env.ref('member_app.membership_officer_ikoyi').id
        # extra = self.env.ref('ikoyi_module.inventory_officer_ikoyi').id
        extra = self.email
        bodyx = "Dear Sir/Madam, </br>Congratulations! You have been approved as a Life\
        member of Ikoyi Club on the date {}  after serving for 25 years.</br> Kindly contact Ikoyi\
         Club 1938 for further details</br>Thanks".format(fields.Datetime.now())
        self.mail_sending(email_from, group_user_id, extra, bodyx)
    #  Account only confirm payment and makes

     # # # # # # # # # # # # # # # # # # # # # # OLD BUTTON # # # # # # # # # # # 
    @api.multi
    def button_dla_pay(self):  #  vis_post
        self.ensure_one()
        #  self.write({'state':'done'})
        '''res = self.env['ir.actions.act_window'].for_xml_id('account', 'action_account_payments_payable')
        return res '''
        user = self.env.user
        account = user.company_id
        journal = account.bank_journal_ids.id
        account_id = self.account_id.id
        bal = self.total - self.member_price

        product = 0
        state_now = str(self.state).replace('_', ' ').capitalize()
        products = self.env['product.product']
        product_search = products.search([('name', 'ilike', state_now)])
        if product_search:
            #  product.append(product_search.id)
            product = product_search[0].id
        else:
            pro = products.create({'name': state_now, 'membershipx': True})
            product = pro.id

        respx = {'type': 'ir.actions.act_window',
                 'name': _('Membership Payment'),
                 'res_model': 'account.payment',
                 'view_type': 'form',
                 'view_mode': 'form',
                 'target': 'new',
                 'context': {
                     'default_amount': self.total,
                     'default_communication': 'M' + str(self.identification),
                     'default_payment_type': 'inbound',
                     'default_partner_type': 'customer',
                     'default_partner_id': self.partner_id.id,
                     #  'default_journal_id':journal
                 }
                 }

        values = {
            'member_id': self.id,
            'member_price': self.harmony + self.int_form_price,
            'pdate': self.date_order,
            'product_id': product or self.product_id.id,
            'paid_amount': self.total,
            'balance': bal
        }

        self.write({'payment_line2': [(0, 0, values)]}) 
        self.write({'payment_status': 'paid'})
        return respx

    # # # # # # # # # # # # # # # # # # # # # #  PRINT ID CARD # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
    @api.multi
    def print_id_card(self):
        report = self.env["ir.actions.report.xml"].search(
            [('report_name', '=', 'member_app.member_profile_report_template')], limit=1)
        if report:
            report.write({'report_type': 'qweb-pdf'})
        return self.env['report'].get_action(
            self.id, 'member_app.member_profile_report_template')
        
    @api.multi
    def print_receipt(self):
        self.calculate_overall_bill()
        report = self.env["ir.actions.report.xml"].search(
            [('report_name', '=', 'member_app.member_billing_template')], limit=1)
        if report:
            report.write({'report_type': 'qweb-pdf'})
        return self.env['report'].get_action(
            self.id, 'member_app.member_billing_template')

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #  reverse states # # # # # # # # # # # # # # # # # # # # # # # # # 
    @api.multi
    def reverse_draft(self):
        self.write({'state': 'draft'})

    @api.multi
    def reverse_white(self):
        self.write({'state': 'white'})

    @api.multi
    def reverse_green(self):
        self.write({'state': 'green'})

    @api.multi
    def reverse_ord(self):
        self.write({'state': 'ord'})
        
    @api.multi
    def reverse_induction(self):
        self.write({'state': 'induction'})

    @api.multi
    def reverse_life(self):
        self.write({'state': 'life'})

    @api.multi
    def inactivate(self):
        pass
        # self.run_crons()
        # self.write({'activity': "inact"})


    def direct_mail_sending(self, email_from, email_to, bodyx):
        subject = "Ikoyi Membership Notification"
        mail_data = {
            'email_from': email_from,
            'subject': subject,
            'email_to': email_to,
            #  'email_cc':mail_appends,
            'reply_to': email_from,
            'body_html': bodyx,
        }
        mail_id = self.env['mail.mail'].create(mail_data)
        self.env['mail.mail'].send(mail_id)

    @api.multi
    def membership_invoice(self): 
        invoice_list = self.create_membership_invoice()
        # invoice_list = self.env['member.app'].browse(self._context.get('active_ids')).create_membership_invoice()
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

    def branch_checker(self):
        branch = self.env.user.branch_id.id
        if not branch:
            raise ValidationError(
                'Please Ensure that the user has a specific branch')
        else:
            return branch
        
    @api.multi
    def create_membership_invoice(self):
        """ Create Customer Invoice of Membership for partners.
        @param datas: datas has dictionary value which consist Id of Membership product and Cost Amount of Membership.
                      datas = {'membership_product_id': None, 'amount': None}
        """
        product = 0
        state_now = str(self.state).replace('_', ' ').capitalize()
        products = self.env['product.product']
        product_search = products.search([('name', 'ilike', state_now)])
        if product_search:
            #  product.append(product_search.id)
            product = product_search[0].id
        else:
            pro = products.create({'name': state_now, 'membershipx': True})
            product = pro.id
        product_id = product
        #  self.product_id # or datas.get('membership_product_id')
        self.write({'product_id': product})
        amount = self.total  #  datas.get('amount', 0.0)
        invoice_list = []

        for partner in self:
            invoice = self.env['account.invoice'].create({
                'partner_id': partner.partner_id.id,
                'account_id': partner.partner_id.property_account_receivable_id.id,
                'fiscal_position_id': partner.partner_id.property_account_position_id.id,
                'branch_id': self.branch_checker(),
                'company_id': self.env.user.company_id.id #self.company_id.id,
            })
            line_values = {
                'product_id': product_id,  
                'price_unit': amount,
                'invoice_id': invoice.id,
                'account_id': invoice.journal_id.default_credit_account_id.id#partner.account_id.id or partner.partner_id.property_account_payable_id.id,

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
            invoice.compute_taxes()

            partner.invoice_id = invoice.id

            find_id = self.env['account.invoice'].search(
                [('id', '=', invoice.id)])
            find_id.action_invoice_open()
        return invoice_list

    @api.multi
    def see_breakdown_invoice(self): 
        search_view_ref = self.env.ref(
            'account.view_account_invoice_filter', False)
        form_view_ref = self.env.ref('account.invoice_form', False)
        tree_view_ref = self.env.ref('account.invoice_tree', False)

        return {
            'domain': [('id', 'in', [item.id for item in self.invoice_id])],
            'name': 'Membership Invoices',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            #  'views': [(form_view_ref.id, 'form')],
            'views': [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')],
            'search_view_id': search_view_ref and search_view_ref.id,
        }

class App_Member_Line(models.Model):
    _name = "member.payment"
    member_id = fields.Many2one('member.app', 'Member ID')
    name = fields.Char('Membership Type')
    product_id = fields.Many2one(
        'product.product',
        string='Membership',
        required=True)
    member_price = fields.Float(
        string='Member Price',
        digits=dp.get_precision('Product Price'),
        required=True)
    paid_amount = fields.Float(string='Amount Paid', required=True)
    balance = fields.Float(string='Balance', default=0.0)
    pdate = fields.Date('Offer Date', default=fields.Date.today())
    penalty_fee = fields.Float(string='Penalty Fee', default=0.0)

    @api.onchange('paid_amount', 'member_price')
    def balance_change(self):
        cal = self.member_price - self.paid_amount
        self.balance = cal


class App_Member_Line_major(models.Model):
    _name = "member.payment.new"
    member_idx = fields.Many2one('member.app', 'Member ID')
    name = fields.Char('Membership Type')
    product_id = fields.Many2one(
        'product.product',
        string='Membership',
        required=False)
    member_price = fields.Float(
        string='Subscriptions',
        digits=dp.get_precision('Product Price'),
        required=True)
    paid_amount = fields.Float(string='Amount Paid', required=True)
    spouse_amount =fields.Float(string='Spouse Amount')
    balance = fields.Float(string='Balance', default=0.0)
    pdate = fields.Date('Paid Date', default=fields.Date.today())
    penalty_fee = fields.Float(string='Penalty Fee', default=0.0)

    @api.one
    @api.depends('paid_amount', 'member_price')
    def balance_change(self):
        cal = self.member_price - self.paid_amount
        self.balance = cal


class App_Partner_Line(models.Model):
    _inherit = "res.partner"
    is_member = fields.Boolean(string='Is Member')
    identification = fields.Char('ID No.', size=8)


class SummarySectionLine(models.Model):
    _name = "summary.section.line"

    section_ids = fields.Many2one('section.product', string="Sections")
    sub_payment_id = fields.Many2one('subscription.payment', string="Fee")
    spouse_cost =  fields.Float('Spouse Cost')     
    child_cost =  fields.Float('Child Cost')     
    total =  fields.Float('Total Cost', compute="summary_line_total")     
    member_cost =  fields.Float('Member Cost')     

    @api.one
    @api.depends('spouse_cost', 'child_cost', 'member_cost')
    def summary_line_total(self):
        for rec in self:
            rec.total = sum([self.spouse_cost, self.child_cost, self.member_cost])

class SectionLine(models.Model):
    _name = "section.line"
    _rec_name = "section_ids"

    dependent_type = fields.Selection([
        ('member', 'Member'),('spouse', 'Spouse'),
        ('child', 'Child'),
        ('guest', 'Guest'),
        ('relative', 'Relation')], default="member", string="Dependent type", required=True)
    section_ids = fields.Many2one('section.product', string="Sections")
    sub_payment_id = fields.Many2one('subscription.payment', string="Fee")
    amount = fields.Float('Amount', required=True)
    special_subscription = fields.Boolean('Special Subscription', default=False)
    is_child = fields.Boolean('Child Subscription?', default=False)
 

class SectionProduct(models.Model):
    _name = "section.product"
    
    def domain_account(self, income=False, expense=False):
        name = 'Income' if income else 'Expenses'
        domain = []
        income_account = self.env['account.account'].search([('user_type_id.name', '=', name)], limit=1)
        if income_account:
            domain = [('id', 'in', [rec.id for rec in income_account])]
        return False

    name = fields.Char("Name", required=True)
    product_id = fields.Many2one('product.product', string="Sections")
    credit_account_id = fields.Many2one('account.account', string="Credit Account", required=True, domain=lambda self: self.domain_account(True, False))
    debit_account_id = fields.Many2one('account.account', string="Debit Account", required=True, domain=lambda self: self.domain_account(False, True))

class App_subscription_Line(models.Model):
    _name = "subscription.payment"
    
    section_line = fields.One2many('section.line', "sub_payment_id", string="Section Lines")
    active = fields.Boolean('Active', default=True)
    paytype = fields.Selection([
        ('entry_fee', 'Entry Fee'),('others', 'Other Charges'),
        ('special', 'Special'),('addition', 'Additional Fees'),
        ('main_house', 'Main House'),
        ('subscription', 'Subscription'),
        ('levy', 'Levy'),
        ], default="others", string="Type", required=False)
    
    
    
    name = fields.Char('Activity', required=False)
    product_id = fields.Many2one('product.product', string='Subscription Product')
    member_price = fields.Float(
        string= "Subscription Fee",
        digits=dp.get_precision('Product Price'),
        required=False)
    pdate = fields.Date(
        'Set Date',
        default=fields.Date.today(),
        required=False)
    is_child = fields.Boolean('Child Subscription?', default=False)
    
    mainhouse_price = fields.Float('Main House Price', required=False, default=0.0)
    entry_price = fields.Float('Entry Fee', required=False, default=0.0)
    special_levy = fields.Float('Special Levy', required=False, default=0.0)
    sub_levy = fields.Float('Subscription Levy', required=False, default=0.0)
    total_cost = fields.Float('Total', compute="Calculate_Total")
    special_subscription = fields.Boolean('Special Subscription', default=False)
    
    @api.one
    @api.depends('entry_price','special_levy', 'sub_levy','member_price')
    def Calculate_Total(self):
        pass

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

#  $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
    
class Spouse_subscription_Line(models.Model):
    _name = "spouse.subscription.payment"
    
    @api.model
    def create(self, vals):
        res = super(Spouse_subscription_Line, self).create(vals)

    spouse_id = fields.Many2one('register.spouse.member', 'Spouse id ID')
    name = fields.Char('Activity', required=False)
    subscription = fields.Many2one(
        'subscription.payment',
        string='Add Sections', required=True)
    product_id = fields.Many2one('product.product', string='Subscription Product')
    member_price = fields.Float(
        string= "Subscription Fee",
        digits=dp.get_precision('Product Price'),
        required=True, compute="get_subscription")
    # mainhouse_price = fields.Float('Main House Price', required=True, default=0.0)
    entry_price = fields.Float('Entry Fee', required=True, compute="get_subscription", default=0.0)
    special_levy = fields.Float('Special Levy', compute="get_subscription", required=True, default=0.0)
    sub_levy = fields.Float('Subscription Levy', compute="get_subscription", required=True, default=0.0)
    total_fee = fields.Float('Total', compute="get_line_total", default=0.0)
    
    @api.one
    @api.depends('entry_price','special_levy','sub_levy','member_price')
    def get_line_total(self):
        total = self.entry_price + self.special_levy + self.member_price + self.sub_levy
        self.total_fee = total

    @api.one
    @api.depends('subscription')
    def get_subscription(self):
        self.entry_price = self.subscription.entry_price
        self.special_levy = self.subscription.special_levy
        self.member_price = self.subscription.member_price
        self.sub_levy = self.subscription.sub_levy

class Package_model(models.Model):
    _name = "package.model" 
    @api.model
    def create(self, vals):
        res = super(Package_model, self).create(vals)
        
        product_search = self.env['product.product'].search([('name', '=', vals['name'])],limit=1)
        if product_search:
            product_search.write({'name': vals['name'],'list_price': vals['package_cost']})
        else:
            product_id =self.env['product.product'].create({'name': vals['name'],
                                                'type': 'service',
                                                'membershipx': True,
                                                'list_price': vals['package_cost'],
                                                'available_in_pos':False,
                                                'taxes_id': []})
            vals['product_id'] = product_id
        return res
    
    @api.multi
    def write(self, vals):
        res = super(Package_model, self).write(vals)
        product_price = self.package_cost

        product_search = self.env['product.product'].search([('name', '=', self.name)])
        if product_search:
            product_search.write({'name': self.name,'list_price': product_price})
        else:
            product_id = self.env['product.product'].create({'name': self.name,
                                                'type': 'service',
                                                'membershipx': True,
                                                'list_price': product_price,
                                                'available_in_pos':False,
                                                'taxes_id': []})
            self.product_id = product_id.id
        return res
     

    @api.multi
    def unlink(self):
        try:
            for xec in self:
                product_ids = self.env['product.product'].search([('name','=ilike',xec.name)])
                for rec in product_ids:
                    rec.unlink()
                     
        except Exception as e:
            raise ValidationError('Please you cannot delete because {}'.format(e))
        return super(Package_model, self).unlink()
    
    name = fields.Char('Package Name', required=True)
    product_id = fields.Many2one('product.product', string='Package Product')
    package_cost = fields.Float(string='Package Price', required=True)
    pdate = fields.Date(
        'Offer Price Date',
        default=fields.Date.today(),
        required=False)
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
    ], 'Period', index=True, required=True, readonly=False, copy=False, 
                                           track_visibility='always')


class ProductMA(models.Model):
    _inherit = 'product.template'

    membershipx = fields.Boolean(
        help='Check if the product is eligible for membership.')
    membershipx_white = fields.Boolean(
        help='Check if the product is eligible for membership.')
    membershipx_green = fields.Boolean()
    membershipx_ord = fields.Boolean()
    membershipx_life = fields.Boolean()
    membership_date_fromx = fields.Date(
        string='Membership Start Date',
        help='Date from which membership becomes active.')
    membership_date_tox = fields.Date(
        string='Membership End Date',
        help='Date until which membership remains active.')
    duration_rangex = fields.Integer('Duration')
    subscription = fields.Many2many(
        'subscription.payment',
        string='Add Membership Subscriptions')

    @api.model
    def fields_view_get(
            self,
            view_id=None,
            view_type='form',
            toolbar=False,
            submenu=False):
        if self._context.get('product') == 'membership_product':
            if view_type == 'form':
                view_id = self.env.ref(
                    'member_app.membership_products_formx').id
            else:
                view_id = self.env.ref(
                    'member_app.membership_products_treex').id
        return super(
            ProductMA,
            self).fields_view_get(
            view_id=view_id,
            view_type=view_type,
            toolbar=toolbar,
            submenu=submenu)


class RegisterSpouseMember(models.Model):
    _name = 'register.spouse.member'
    _description = 'Register Member Dependant'
    _rec_name = "surname"
    _order = "id desc"
    @api.multi
    def name_get(self):
        if not self.ids:
            return []
        res = []
        for field6 in self.browse(self.ids):
            partner = str(field6.partner_id.name)
            res.append((field6.id, partner))
        return res

    image = fields.Binary(
        "Image",
        attachment=True,
        help="This field holds the image used as avatar for this contact, limited to 1024x1024px",
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
        'res.partner', 'Full Name', domain=[
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
    email = fields.Char('Email', store=True)
    occupation = fields.Char('Job title')
    nok = fields.Many2one('res.partner', 'Next of Kin', store=True)
    sex = fields.Selection([('Male', 'Male'),
                                     ('Female', 'Female')],"Sex")
    nok_relationship = fields.Char("NOK Relationship")
    marital_status = fields.Selection([('Single', 'Single'),
                                     ('Married', 'Married')],
                                    "Marital Status")

    title = fields.Many2one('res.partner.title', 'Title', store=True)
    sponsor = fields.Many2one('member.app', string='Parent Member',
    domain=[('is_member', '=', True)], required=False)
    account_id = fields.Many2one('account.account', 'Account')
    invoice_id = fields.Many2one('account.invoice', 'Invoice', store=True)
    biostar_user_id = fields.Integer('BIO-STAR USER ID', readonly=False)
    product_id = fields.Many2one(
        'product.product', string='Related Membership type', domain=[
            ('membershipx', '=', True)], required=False)
    member_price = fields.Float(
        string='Member Price',
        compute="get_section_member_price",
        required=True,
        readonly=False)
    total = fields.Integer('Total Section Amount', compute='get_totals')
    date_order = fields.Datetime('Offer Date', default=fields.Datetime.now())
    member_age = fields.Integer(
        'Age',
        required=True,
        compute="get_duration_age")
    subscription = fields.Many2one(
        'subscription.payment',
        required=False,
        string='Add Sections')
    spouse_subscription = fields.One2many(
        'spouse.subscription.payment',
        'spouse_id',
        string="Spouse Subscription")

    section_line = fields.Many2many('section.line', string='Add Sections')

    package = fields.Many2many('package.model', string='Compulsory Packages')
    package_cost = fields.Float(
        'Package Cost')
    sponsor_pay = fields.Selection([('Dependant', 'Dependant'),
                                     ('Sponsor', 'Sponsor')], default="Sponsor", required=True, string="Deduct Payment from: ")

    payment_ids = fields.Many2many(
        'account.payment',
        string='All Payments', compute="get_payment_ids")

    biostar_user_id = fields.Integer('BioStar User ID', readonly=False)
    biostar_status = fields.Char('BioStar Status Code', readonly=True)
    biostar_start_date = fields.Datetime('BioStar Start Date', default=fields.Datetime.now())
    biostar_expiry_date = fields.Datetime('BioStar Expiry', default=fields.Datetime.now())
    
    @api.one
    @api.depends('invoice_id')
    def get_payment_ids(self):
        payment_list = []
        for ref in self.invoice_id:
            for rec in ref.payment_ids:
                payment_list.append(rec.id)
        self.payment_ids = payment_list
        
    mode = fields.Selection([('jun',
                              'Junior'),
                             ('old',
                              'Adult'),
                             ('new',
                              'Child'),
                             ],
                            'Dependant Status',
                            default='jun',
                            index=True,
                            required=True,
                            readonly=False,
                            copy=False,
                            track_visibility='always')
    state = fields.Selection([('draft',
                               'Draft'),
                              ('wait',
                               'Waiting'),
                              ('account',
                               'Accounts'),
                              ('confirm',
                               'Confimred'),
                              ],
                             'Status',
                             default='draft',
                             index=True,
                             required=True,
                             readonly=False,
                             copy=False,
                             track_visibility='always')
    relationship = fields.Selection([('Child','Child'),('Brother', 'Brother'),
                                     ('Sister', 'Sister'), ('Friend', 'Friend'),
                                     ('Spouse', 'Spouse'),
                                     ], 'Relationship', default='Spouse', index=True,
                                    required=True, readonly=False, copy=False,
                                    track_visibility='always')
    
    active = fields.Boolean(string='Active', default=True, readonly=True) 
    identification = fields.Char('ID No.', related="sponsor.identification")


        
    @api.one
    @api.depends('section_line')
    def get_section_member_price(self):
        member_cost = 0.0
        for rec in self.section_line:
            member_cost += rec.amount
        self.member_price = member_cost
        self.total = member_cost 
            
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
    @api.one
    @api.depends('section_line', 'package_cost')
    def get_totals(self):
        pass

    @api.onchange('sponsor')
    def get_sponsor_account(self):
        if self.sponsor:
            self.account_id = self.sponsor.partner_id.property_account_receivable_id.id
            self.identification = self.sponsor.identification

    @api.multi
    def button_make_wait(self):
        partner = self.env['res.partner']#.search([('id', '=', self.partner_id.id)])
        middle_name = str(self.middle_name) if self.middle_name else ''
        part = partner.create({'street': self.street,
                        'email': self.email,
                        'state_id': self.state_id.id,
                        'title':self.title.id,
                        'city':self.city,
                        'image': self.image,
                        'phone':self.phone,
                        'function': self.occupation,
                        'name': str(self.surname) +' '+ str(self.first_name) +' '+ middle_name,
                        'is_member': True,
                        })
        self.partner_id = part.id
        self.write({'state': 'wait'})

    @api.multi
    def button_cancel(self):
        self.write({'state': 'draft'})

    @api.multi
    def button_make_confirm(self, outstanding):
        self.write({'state': 'confirm'})
        self.sponsor.balance = self.sponsor.balance_total + outstanding
        self.Appendto_Sponsor()
        return True
    
    @api.multi
    def print_receipt(self):
        report = self.env["ir.actions.report.xml"].search(
            [('report_name', '=', 'member_app.spouse_single_receipt_template')], limit=1)
        if report:
            report.write({'report_type': 'qweb-pdf'})
        return self.env['report'].get_action(
            self.id, 'member_app.spouse_single_receipt_template')


    def Appendto_Sponsor(self):
        lists = []
        mem_obj = self.env['member.app']
        membrowse = mem_obj.search([('id', '=', self.sponsor.id)], limit=1)
        if membrowse:
            lists.append(self.id)
            membrowse.write({'depend_name':[(4, lists)]})
            if self.member_age in range(0, 12):
                self.write({'mode':'new'})
            elif self.member_age in range(12, 25):
                self.write({'mode':'jun'})
        else:
            raise ValidationError('You must Add a sponseor')

    @api.multi
    def button_make_payment(self):
        self.write({'state': 'account'})
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

    def create_outstanding_line(self, inv_id):
        invoice_line_obj = self.env["account.invoice.line"] 
        members_search = self.env['member.app'].search([('id', '=', self.sponsor.id)])
        account_obj = self.env['account.invoice']
        accounts = account_obj.browse([inv_id]).journal_id.default_credit_account_id.id
        # income_account = self.env['account.account'].search([('user_type_id.name', '=ilike', 'Income')], limit=1)
        income_account = self.env['account.account'].search([('user_type_id','=',1 )], limit=1)
         
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

    @api.multi
    def create_membership_invoice(self):
        """ Create Customer Invoice of Membership for partners.
        @param datas: datas has dictionary value which consist Id of Membership product and Cost Amount of Membership.
                      datas = {'membership_product_id': None, 'amount': None}
        """
        product = 0
        state_now = str(self.state).replace('_', ' ').capitalize()
        self.write({'product_id': product})
        amount = self.total  #  datas.get('amount', 0.0)
        invoice_list = []
        branch_id = self.env.user.branch_id.id
        if not branch_id:
            raise ValidationError('User does not have a set branch / Section')
 
        line_values = {}
        
        
        invoice = self.env['account.invoice'].create({
                'partner_id': self.partner_id.id, 
                'account_id': self.partner_id.property_account_receivable_id.id, 
                'fiscal_position_id': self.partner_id.property_account_position_id.id,
                'branch_id': branch_id,
                'company_id': self.env.user.company_id.id #self.company_id.id,
            })
        product = 0
        self.create_outstanding_line(invoice.id)
        for each in self.section_line:
            produce = each.section_ids.name
            products = self.env['product.product']
            product_search = products.search(
            [('name', 'ilike', produce)], limit=1)
             
            # income_account = self.env['account.account'].search([('user_type_id.name', '=ilike', 'Income')], limit=1)
             
            line_values['product_id'] = product_search.id if product_search else False
            line_values['price_unit'] = each.amount
            line_values['invoice_id'] = invoice.id,
            line_values['name'] = "Spouse Payment For "+ produce
            line_values['account_id'] = invoice.journal_id.default_credit_account_id.id
            #  create a record in cache, apply onchange then revert back to a dictionary
            invoice_line = self.env['account.invoice.line'].new(line_values)
            invoice_line._onchange_product_id()
            line_values = invoice_line._convert_to_write(
                    {name: invoice_line[name] for name in invoice_line._cache})
            line_values['price_unit'] = each.amount
            invoice.write({'invoice_line_ids': [(0, 0, line_values)]})
        invoice_list.append(invoice.id)
            # invoice.compute_taxes()
        self.invoice_id = invoice.id
        find_id = self.env['account.invoice'].search(
                [('id', '=', invoice.id)])
        # find_id.action_invoice_open()
        self.add_payment_sponsor(invoice.id)
        return invoice_list

    def add_payment_sponsor(self, invoice):
        member_id = self.env['member.app'].search([('id','=', self.sponsor.id)])
        if member_id:
            if self.sponsor_pay == "Sponsor":
                member_id.write({'invoice_id': [(4, [invoice])]})
            
    @api.multi
    def see_breakdown_invoice(self): 
        search_view_ref = self.env.ref(
            'account.view_account_invoice_filter', False)
        form_view_ref = self.env.ref('account.invoice_form', False)
        tree_view_ref = self.env.ref('account.invoice_tree', False)
        return {
            'domain': [('id', '=', self.invoice_id.id)],
            'name': 'Membership Invoices',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            #  'views': [(form_view_ref.id, 'form')],
            'views': [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')],
            'search_view_id': search_view_ref and search_view_ref.id,
        }

class BiostarModel(models.Model):
    _name = 'biostar.model'

    user_id = fields.Char('User ID')
    member_identification = fields.Char('Member ID No.')
    partner_id = fields.Many2one('res.partner', 'Member')
    biostar_status = fields.Char('BioStar Status Code', readonly=True)



class RegisterPaymentMember(models.Model):
    _name = 'register.payment.member'
    _description = 'Register Member Payment'
    _order = "id desc" 

    @api.model
    def _default_journal(self):
        if self._context.get('default_journal_id', False):
            return self.env['account.journal'].browse(
                self._context.get('default_journal_id'))
        inv_type = self._context.get('type', 'out_invoice')
        inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
        company_id = self._context.get(
            'company_id', self.env.user.company_id.id)
        domain = [
            ('type', 'in', filter(None, map(TYPE2JOURNAL.get, inv_types))),
            ('company_id', '=', company_id),
        ]
        return self.env['account.journal'].search(domain, limit=1)

    def compute_zero(self):
        zero = 0.00
        return zero

    partner_id = fields.Many2one('res.partner', 'Customer', required=True)
    filex = fields.Binary("File Upload")
    file_namex = fields.Char("FileName")
    name = fields.Char("Description", readonly=False)
    level = fields.Char("Level", readonly=False)
    users_followers = fields.Many2many('res.users', string='Add followers')
    member_ref = fields.Many2one('member.app', 'Payment Ref.')
    payment_method = fields.Many2one('account.journal', string='Journal',
                                     required=True, readonly=False,
                                     default=_default_journal,)
    bank = fields.Many2one(
        'res.bank',
        string='Bank',
        readonly=False)
    reference =fields.Char('Reference')
    to_pay = fields.Float('Amount to Pay', readonly=True, default=0.0)
    #  , required=True,default=lambda self: self.env['account.account'].search([('name', '=', 'Account Receivable')], limit=1))
    advance_account = fields.Many2one(
        'account.account',
        'Account',
        related='payment_method.default_debit_account_id')
    date = fields.Date('Paid Date', required=True)
    amount = fields.Float('Paid Amount', required=True, readonly=False)
    spouse_amount = fields.Float('Spouse Amount')
    print_memo = fields.Boolean('Print Memo', default=True)
    state = fields.Selection([('draft', 'Draft'),

                              ('pay', 'Paid'),
                              ('can', 'Cancel'),
                              ], default='draft', string='Status')
    p_type = fields.Selection([('sub', 'Subscription'),
                               ('ano', 'Anomaly'),
                               ('normal', 'Normal'),
                               ], default='normal', string='Type')
    
    mode_payment = fields.Selection([('Transfer', 'Transfer'),
                               ('POS', 'POS'),
                               ('CHEQUE', 'CHEQUE'),
                               ('BANK DRAFT', 'BANK DRAFT'),
                               ], default='Transfer', string='Payment Mode')
    num = fields.Float('Number')

    @api.one
    def button_cancel(self):
        return {'type': 'ir.actions.act_window_close'}

    def send_mail_to_accounts(self, pay_id, model, amount):
        base_url = http.request.env['ir.config_parameter'].sudo(
        ).get_param('web.base.url')
        base_url += '/web# id=%d&view_type=form&model=%s' % (pay_id, model)

        email_from = self.env.user.email
        group_user_id2 = self.env.ref('ikoyi_module.account_boss_ikoyi').id
        group_user_id = self.env.ref('member_app.manager_member_ikoyi').id
        group_user_id3 = self.env.ref('ikoyi_module.gm_ikoyi').id
        member = self.env['member.app'].search(
            [('id', '=', self.member_ref.id)])

        model = 'account.payment'
        # pay = payment_schedule.search([('ikoyi_ref','=',self.id)])
        if pay_id:
            bodyx = "Dear Sir/Madam, </br>This is a notification that the member with ID No. {}\
            has made a payment of {} on the {}.</br> Please kindly <a href={}> </b>Click<a/> to Confirm.</br>\
            Regards".format(member.identification, amount, fields.Datetime.now(), base_url,)
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
            print (all_mails)
            email_froms = str(from_browse) + " <" + str(email_from) + ">"
            mail_sender = (', '.join(str(item)for item in all_mails))
            subject = "Payment Notification"
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
