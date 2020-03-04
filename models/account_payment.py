import time
from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import except_orm, ValidationError
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from odoo import http


class account_payment(models.Model):
    _inherit = "account.payment"
    
    balances = fields.Float('Balance')#, compute="_compute_difference")
    amount_to_pay = fields.Float('To pay')#, compute="_compute_difference")
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
        if members_search: 
            members_search.state_payment_inv(self.amount, self.payment_date)  
        else:
            pass
        domain_sub = [('invoice_id', 'in', [item.id for item in self.invoice_ids])]
        sub_search = self.env['subscription.model'].search(domain_sub)
        if sub_search:
            sub_search.state_payment_inv(self.amount, self.payment_date, sub_search, self.payment_difference)
        else:
            pass

        domain_guest = [('invoice_id', 'in', [item.id for item in self.invoice_ids])]
        guest_search = self.env['register.guest'].search(domain_guest)
        if guest_search:
            guest_search.write({'state': 'wait'}) # state_payment_inv(self.amount, self.payment_date, guest_search, self.payment_difference)
        else:
            pass 
        
        domain_suspend = [('invoice_id', 'in', [item.id for item in self.invoice_ids])]
        suspend_search = self.env['suspension.model'].search(domain_suspend)
        if suspend_search:
            suspend_search.state_payment_inv()
        else:
            pass 
        
        domain_spouse = [('invoice_id', 'in', [item.id for item in self.invoice_ids])]
        spouse_search = self.env['register.spouse.member'].search(domain_spouse)
        if spouse_search:
            spouse_search.button_make_confirm()
        else:
            pass 
        return res
 