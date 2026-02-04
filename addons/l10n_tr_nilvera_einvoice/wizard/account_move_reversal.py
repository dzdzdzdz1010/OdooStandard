from odoo import Command, models


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def _prepare_default_reversal(self, move):
        res = super()._prepare_default_reversal(move)
        if self.country_code != 'TR':
            return res

        line_vals = move.line_ids.copy_data()
        for line, vals in zip(move.line_ids, line_vals):
            vals.update(
                {
                    "l10n_tr_original_line_id": line.id,
                    "l10n_tr_original_quantity": line.quantity,
                    "l10n_tr_original_tax_without_withholding": line.price_total - line.price_subtotal,
                },
            )

        res.update(
            {
                'ref': move.name,
                'l10n_tr_gib_invoice_scenario': 'TEMELFATURA',
                'l10n_tr_gib_invoice_type': 'TEVKIFATIADE' if move.l10n_tr_gib_invoice_type == "TEVKIFAT" else "IADE",
                'line_ids': [Command.create(vals) for vals in line_vals],
            },
        )
        return res
