from odoo import fields, models


class NemhandelRejectionWizard(models.TransientModel):
    _name = 'nemhandel.rejection.wizard'
    _description = "Nemhandel Rejection wizard"

    move_ids = fields.Many2many(
        comodel_name='account.move',
        required=True,
    )
    note = fields.Text('Additional note')

    def button_send(self):
        moves_by_company = self.move_ids.grouped('company_id')
        for company in moves_by_company:
            edi_user = company.account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == 'nemhandel')
            edi_user._nemhandel_send_response(moves_by_company[company], 'BusinessReject', self.note)
        return self.env.context.get('cancel_res', True)
