##############################################################################
#
#    Maach Technologies Pvt. Ltd.
#    Copyright (C) 2019-TODAY MAACH Technologies(sperality@gmail.com).
#    Maintainer: Maach Technologies (<sperality@gmail.com>)
#
#############################################################################

from odoo import models, fields, api
from odoo import http


class AccountInvoice(models.Model):
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
        
    def get_url(self, id):
        base_url = http.request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        base_url += '/web/content/%s?download=true' %id
        return "<button><a href={}> </b>Click<a/></button>".format(base_url)
        # http://127.0.0.1:8069/web/content/980?download=True

    @api.multi
    def mass_sendmail_invoice(self):
        template = self.env.ref('account.email_template_edi_invoice', False)
        for order in self:
            attach_lists = []
            
            name = "Ikoyi Club Membership Invoice "
            att_obj = order.env['ir.attachment']
            attch = order.env['ir.attachment'].search([('res_model', '=', 'account.invoice'),
            ('res_id', '=', order.id)])
            for attach in attch:
                attach_lists.append(attach.id)
            body = """Dear Sir, <br/>
                        This is a reminder for payment of subscription. 
                        Kindly {} to download invoice""".format(order.get_url(att_obj.browse([attach_lists[0]]).id) if len(attach_lists) > 0 else "Request")
            email_froms = "Ikoyi Club Notification" + " <" + str(order.env.user.company_id.email) + ">"
            subject = name
            mail_data = {
                'email_from': email_froms,
                'subject': subject,
                'email_to': order.partner_id.email,
                'reply_to': email_froms,
                # 'email_cc': followers_mail,
                'attachment_ids': [(6, 0, attach_lists)],
                'body_html': body,
                        }
            mail_id = order.env['mail.mail'].create(mail_data)
            order.env['mail.mail'].send(mail_id)

    # @api.multi
    # def mass_sendmail_invoice(self):
    #     template = self.env.ref('account.email_template_edi_invoice', False)
    #     for order in self:
    #         attach_lists = []
            
    #         name = "Ikoyi Club Membership Invoice "
    #         att_obj = order.env['ir.attachment']
    #         attch = order.env['ir.attachment'].search([('res_model', '=', 'account.invoice'),
    #         ('res_id', '=', order.id)])
    #         for attach in attch:
    #             attach_lists.append(attach.id)
    #         body = """Dear Sir, <br/>
    #                     This is a reminder for payment of subscription. 
    #                     Kindly {} to download invoice""".format(order.get_url(att_obj.browse([attach_lists[0]]).id) if len(attach_lists) > 0 else "Request")
    #         email_froms = "Ikoyi Club Notification" + " <" + str(order.env.user.company_id.email) + ">"
    #         subject = name
    #         mail_data = {
    #             'email_from': email_froms,
    #             'subject': subject,
    #             'email_to': order.partner_id.email,
    #             'reply_to': email_froms,
    #             # 'email_cc': followers_mail,
    #             'attachment_ids': [(6, 0, attach_lists)],
    #             'body_html': body,
    #                     }
    #         mail_id = order.env['mail.mail'].create(mail_data)
    #         order.env['mail.mail'].send(mail_id)

    # @api.multi
    # def mass_sendmail_invoice(self):
    #     template = self.env.ref('account.email_template_edi_invoice', False)
    #     for order in self:
    #         attach_lists = []
    #         # pdf = order.env.ref('account.email_template_edi_invoice').render_qweb_pdf(order.ids)
    #         # b64_pdf = base64.b64encode(pdf[0])
    #         name = "Ikoyi Club Membership Invoice "
    #         # save pdf as attachment
    #         # ATTACHMENT_NAME = name
    #         # create_attachment = self.env['ir.attachment'].create({
    #         #     'name': ATTACHMENT_NAME,
    #         #     'type': 'binary',
    #         #     'datas': b64_pdf,
    #         #     'datas_fname': ATTACHMENT_NAME + '.pdf',
    #         #     'store_fname': ATTACHMENT_NAME,
    #         #     'res_model': order._name,
    #         #     'res_id': order.id,
    #         #     'mimetype': 'application/x-pdf'
    #         # })
    #         # attach_lists.append(create_attachment.id)
    #         attch = order.env['ir.attachment'].search([('res_model', '=', 'account.invoice'),
    #         ('res_id', '=', order.id)])
    #         body = """Dear Sir, <br/>
    #                     This is a reminder for payment of subscription. 
    #                     Kindly {} to download invoice""".format(order.get_url(attch.id))
    #         email_froms = "Ikoyi Club Notification" + " <" + str(ordr.env.user.company_id.email) + ">"
    #         subject = name
    #         mail_data = {
    #             'email_from': email_froms,
    #             'subject': subject,
    #             'email_to': order.partner_id.email,
    #             'reply_to': email_froms,
    #             # 'email_cc': followers_mail,
    #             'attachment_ids': [(6, 0, [attch.id])],
    #             'body_html': body,
    #                     }
    #         mail_id = order.env['mail.mail'].create(mail_data)
    #         order.env['mail.mail'].send(mail_id)
