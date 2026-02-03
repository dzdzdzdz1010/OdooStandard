from odoo import fields, models


class AccountMoveTicafaturaResponseWizard(models.TransientModel):
    _name = 'l10n_tr_nilvera_einvoice.ticafatura.response.wizard'
    _description = 'Response Wizard for Bills of type Ticafatura E-Invoice'

    move_id = fields.Many2one('account.move', string='Bill', required=True)
    response_note = fields.Text(string='Response Note', required=True)

    def action_reject(self):
        self.ensure_one()
        self.move_id.action_send_ticarifatura_response('rejected', self.response_note)
        return {'type': 'ir.actions.act_window_close'}
