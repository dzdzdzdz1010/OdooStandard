from odoo.addons.website_sale.controllers.cart import Cart as WebsiteSaleCart


class Cart(WebsiteSaleCart):

    def _get_line_data(self, line):
        line_data = super()._get_line_data(line)
        line_data['max_quantity'] = line._get_max_line_qty()

        return line_data
