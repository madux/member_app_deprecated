# -*- coding: utf-8 -*-

from odoo import api, fields, models

from dateutil.relativedelta import relativedelta
import datetime
import time

class SalespersonWizardho(models.TransientModel):
    _name = "mandate.wizardho"
    _description = "Mandate wizard"

    salesperson_id = fields.Many2one('res.users', string='Salesperson', required=True)#, default=self.create_uid)
    date_from = fields.Date(string='Date', default=fields.Date.today())
    date_to = fields.Date(string='End Date',default=fields.today())#,default=lambda *a: (datetime.datetime.now() + relativedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S'))
    #default= fields.Datetime.now)

    @api.multi
    def check_report(self):
        data = {}
        data['form'] = self.read(['salesperson_id', 'date_from'])[0]
        return self._print_report(data)

    def _print_report(self, data):
        data['form'].update(self.read(['salesperson_id', 'date_from'])[0])
        return self.env['report'].get_action(self, 'ikoyi_module.report_mandate', data=data)
