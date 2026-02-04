from odoo import _, api, models
from odoo.exceptions import ValidationError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _default_payment_methods(self):
        base = super()._default_payment_methods()
        return base.filtered_domain(['|', ('payment_provider', '!=', 'payconiq'), ('payconiq_usage', '!=', 'sticker')])

    @api.constrains('payment_method_ids')
    def _check_payconiq_payment_methods(self):
        for config in self:
            payconiq_sticker_methods = config.payment_method_ids.filtered_domain(
                [
                    ('payment_provider', '=', 'payconiq'),
                    ('payconiq_usage', '=', 'sticker'),
                ],
            )
            for method in payconiq_sticker_methods:
                other_configs = method.config_ids - config
                if other_configs:
                    raise ValidationError(
                        _(
                            "The Payconiq sticker payment method '%(method_name)s' is already used in another POS configuration (%(config_names)s). One sticker can only be assigned to one POS at a time.",
                            method_name=method.name,
                            config_names=", ".join(other_configs.mapped('name')),
                        ),
                    )
