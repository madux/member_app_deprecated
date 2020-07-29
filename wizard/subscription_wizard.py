import time
from odoo import models, fields, api, _
from odoo.exceptions import except_orm, ValidationError
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta


class Subscription_WizardExcel(models.Model):
    _name = "subscription.excel"

    datefrom = fields.Datetime('Date', required=False)
    dateto = fields.Datetime('Date', required=False)

    # def get_subscription_record(self):
    #     sub_ren = self.env['subscription.model'].search([('date', '>=', self.datefrom), ('date', '<=', self.to)])
        # domain = self.datefrom <= s.purchase_date and self.dateto >= s.purchase_date
    @api.multi
    def button_register_spouse(self):  #  Send memo back
        lists = []
        for rec in self.subscription:
            lists.append(rec.id)
        return {
            'name': "Register Dependant",
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'register.spouse.member',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {
                'default_product_id': self.product_id.id,
                'default_sponsor': self.id,
                #'default_subscription': [(6, 0, lists)]
            },
        }


    @api.one
    def generate_records(self):  # verify,
        search_view_ref = self.env.ref(
            'member_app.memapp_search_subscription', False)
        form_view_ref = self.env.ref('member_app.subscription_formxfvv', False)
        tree_view_ref = self.env.ref('member_app.subscription_maintreex', False)
        return {
            'domain': [('date', '>=', self.datefrom), ('date', '=', self.to)],
            'name': 'Subscription Renewal',
            'res_model': 'subscription.model',
            'type': 'ir.actions.act_window',
            'views': [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')],
            'search_view_id': search_view_ref and search_view_ref.id,
        }


