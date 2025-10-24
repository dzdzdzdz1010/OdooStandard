from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def get_discount_and_net_price(self):
        self.ensure_one()
        discount_amount = (
            (self.price_subtotal * 100) / (100 - self.discount)
            if self.discount != 100
            else (self.price_unit * self.quantity)
        ) - self.price_subtotal

        net_unit_price = self.price_unit * (1 - (self.discount / 100))

        return {
            'discount_amount': discount_amount,
            'net_unit_price': net_unit_price,
        }
