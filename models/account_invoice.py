##############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2017-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Maintainer: Cybrosys Technologies (<https://www.cybrosys.com>)
#
#############################################################################

from odoo import models, fields, api


class MembershipInvoices(models.Model):
    _inherit = 'account.invoice'

    is_member_invoice = fields.Boolean(string="Is membership Invoice")
    member_id = fields.Many2one('member.app', string="Membership Ref", help="Source Document")
    
    @api.multi
    def print_membership_invoice_receipt(self):
        report = self.env["ir.actions.report.xml"].search(
            [('report_name', '=', 'member_app.receipt_invoice_template')], limit=1)
        if report:
            report.write({'report_type': 'qweb-pdf'})
        return self.env['report'].get_action(
            self.id, 'member_app.receipt_invoice_template')


    # @api.multi
    # def action_invoice_paid(self):
    #     res = super(MembershipInvoices, self).action_invoice_paid()
    #     mem_obj = self.env['member.app'].search([('id', '=', self.member_id.id)])
    #     for obj in mem_obj:
    #         obj.write({'state': 'wait'})
            
    #     return res
    
    @api.multi
    def action_view_payments(self):
        """
        This function returns an action that display existing payments of given
        account invoices.
        When only one found, show the payment immediately.
        """
        if self.type in ('in_invoice', 'in_refund'):
            action = self.env.ref('account.action_account_payments_payable')
        else:
            action = self.env.ref('account.action_account_payments')

        result = action.read()[0]

        # choose the view_mode accordingly
        if len(self.payment_ids) != 1:
            result['domain'] = "[('id', 'in', " + str(
                self.payment_ids.ids) + ")]"
        elif len(self.payment_ids) == 1:
            res = self.env.ref('account.view_account_payment_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = self.payment_ids.id
        return result

