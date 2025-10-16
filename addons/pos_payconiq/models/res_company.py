from odoo import api, models
from odoo.exceptions import ValidationError

from odoo.addons.pos_payconiq import const


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.constrains('currency_id')
    def _check_currency(self):
        """
        Ensure that Payconiq payment methods use a supported currency.
        """
        for record in self:
            # Currency already supported by Payconiq
            if record.currency_id.name in const.SUPPORTED_CURRENCIES:
                return

            # If unsupported, check if any Payconiq payment methods are using a journal with no currency set
            payment_method_ids = self.env['pos.payment.method'].search_count(
                [
                    ('company_id', '=', record.id),
                    ('journal_id.currency_id', '=', False),
                    ('payment_provider', '=', 'payconiq'),
                ], limit=1,
            )
            if payment_method_ids:
                raise ValidationError(
                    self.env._(
                        "This company has a journal using the default currency of the company, and it's linked to a Payconiq payment method, which only supports the following currencies: %s.\n"
                        "Please either set a supported currency on the journal or remove Payconiq from the associated payment method.",
                    )
                    % ', '.join(const.SUPPORTED_CURRENCIES),
                )
