import time
from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import except_orm, ValidationError
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from odoo import http
import re

class SectionLine(models.Model):
    _name = "section.product"
    _rec_name = "name"

    name = fields.Char("Name", required=True)
    product_id = fields.Many2one('product.product', string="Sections")

    
class SectionLine(models.Model):
    _name = "section.line"

    dependent_type = fields.Many2one('dependent.type', string="Dependent type")
    section_id = fields.Many2one('section.product', string="Sections")
    sub_payment_id = fields.Many2one('subscription.payment', string="Fee")
    amount = fields.Float('Amount', required=True)

    @api.onchange('dependent_type', 'sub_payment_id')
    def domain_sections(self):
        if self.dependent_type and self.sub_payment_id:
            sections = []
            subobj = self.env['subscription.payment'].search([('id', '=', self.sub_payment_id.id)])
            sub_mapped = subobj.mapped('section_line').filtered(lambda x : x.dependent_type == self.dependent_type)
            for rec in sub_mapped:
                sections.append(rec.section_id.id)
            domain = {'section_id': [('id', 'in', sections)]}
            return {'domain': domain}

    @api.onchange('section_id')
    def get_sub_id(self):
        """Finds all subscription payments where the section exists"""
        if self.section_id:
            subobj = self.env['subscription.payment'].search([('id', '=', self.sub_payment_id.id)])
            sub_mapped = subobj.mapped('section_line').filtered(lambda x : x.dependent_type == self.dependent_type and x.section_id == self.section_id)
            if sub_mapped:
                amount = sub_mapped[0].amount
                self.amount = amount

            


class App_subscription_Line(models.Model):
    _name = "subscription.payment"
    
    section_line = fields.One2many('section.line', "section_id", string="Section Lines")
