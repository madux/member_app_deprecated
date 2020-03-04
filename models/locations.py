from odoo import models, fields


class Locations(models.Model):
    _name = 'member.locations'
    name = fields.Char(string='Name', required=True, index=True)
    code = fields.Char(string='Code', required=True, index=True)
    eid = fields.Integer()
    parent_id = fields.Integer(string='Parent Location')
    level = fields.Integer(string='Location Level')
