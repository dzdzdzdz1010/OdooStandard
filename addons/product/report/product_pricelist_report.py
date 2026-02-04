# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain


class ProductPricelistReport(models.AbstractModel):
    _name = 'report.product.report_pricelist'
    _description = 'Pricelist Report'

    def _get_report_values(self, docids, data):
        return self._get_report_data(data, 'pdf')

    @api.readonly
    @api.model
    def get_html(self, data):
        render_values = self._get_report_data(data, 'html')
        return self.env['ir.qweb']._render('product.report_pricelist_page', render_values)

    def _get_report_data(self, data, report_type='html'):
        quantities = data.get('quantities', [1])
        data_pricelist_id = data.get('pricelist_id')
        pricelist_id = data_pricelist_id and int(data_pricelist_id)
        pricelist = self.env['product.pricelist'].browse(pricelist_id).exists()
        if not pricelist:
            pricelist = self.env['product.pricelist'].search([], limit=1)
        date_str = data.get('date')
        date = fields.Date.to_date(date_str) if date_str else fields.Date.today()

        active_model = data.get('active_model', 'product.template')
        active_ids = data.get('active_ids') or []
        is_product_tmpl = active_model == 'product.template'
        ProductClass = self.env[active_model]

        products = ProductClass.browse(active_ids) if active_ids else []

        products_data = []

        for product in products:
            products_data.extend(
                self._get_product_data(is_product_tmpl, product, pricelist, quantities, date),
            )

        # We display a row with the category name in the xml every time
        # the category changes, so we need to make sure that the products list
        # is sorted by category.
        products_data.sort(key=lambda x: x['category'] or '')

        return {
            'is_html_type': report_type == 'html',
            'is_product_tmpl': is_product_tmpl,
            'display_pricelist_title': bool(data.get('display_pricelist_title', False)),
            'pricelist': pricelist,
            'products': products_data,
            'quantities': quantities,
            'docs': pricelist,
            'currency': pricelist.currency_id or self.env.company.currency_id,
            'date': date,
        }

    def _get_product_data(self, is_product_tmpl, product, pricelist, quantities, date, uom=None):
        product = product.with_context(display_default_code=False)

        data = []

        product_uoms = uom or set(
            self._get_related_uoms(pricelist, product, is_product_tmpl)
            + product.uom_id
        )

        for uom in product_uoms:
            data_dict = {
                'id': product.id,
                'name': (is_product_tmpl and product.name) or product.display_name,
                'price': dict.fromkeys(quantities, 0.0),
                'uom': uom.name,
                'default_code': product.default_code,
                'barcode': product.barcode,
                'category': product.categ_id.name,
            }

            for qty in quantities:
                data_dict['price'][qty] = pricelist._get_product_price(product, qty, date=date, uom=uom)

            if is_product_tmpl and product.product_variant_count > 1:
                data_dict['variants'] = []

                for variant in product.product_variant_ids:
                    data_dict['variants'].extend(
                        self._get_product_data(False, variant, pricelist, quantities, date, uom),
                    )

            data.append(data_dict)

        return data

    def _get_related_uoms(self, pricelist, product, is_product_tmpl):
        applied_on_value = '1_product' if is_product_tmpl else '0_product_variant'
        product_field = 'product_tmpl_id' if is_product_tmpl else 'product_id'

        domain = (
            Domain('applied_on', '=', applied_on_value)
            & Domain(product_field, '=', product.id)
        ) | Domain('applied_on', '=', '3_global')

        return pricelist.item_ids.filtered_domain(domain).mapped('uom_ids')
