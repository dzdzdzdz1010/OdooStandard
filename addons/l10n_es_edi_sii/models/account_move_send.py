from odoo import api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def l10n_es_is_edi_sii_applicable(self, move):
        return move.l10n_es_edi_is_required and move.l10n_es_edi_sii_state != 'sent'

    def _get_all_extra_edis(self) -> dict:
        # EXTENDS 'account'
        res = super()._get_all_extra_edis()
        res.update({
            'es_edi_sii': {
                'label': self.env._("Send to SII"),
                'is_applicable': self.l10n_es_is_edi_sii_applicable,
                'help': self.env._("Send the e-invoice data to SII"),
            }
        })
        return res

    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        for invoice, invoice_data in invoices_data.items():
            if 'es_edi_sii' in invoice_data['extra_edis']:
                res = self.env['l10n_es.sii.service']._send_sii_invoice(invoice)

                if res.get(invoice, {}).get('error'):
                    invoice_data['error'] = {
                        'error_title': self.env._("Error when sending the invoice to SII"),
                        'errors': [res[invoice]['error']],
                    }
