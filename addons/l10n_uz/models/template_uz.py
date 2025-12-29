# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template("uz")
    def _get_uz_template_data(self):
        return {
            "property_account_receivable_id": "uz4890",
            "property_account_payable_id": "uz6710",
            "property_stock_valuation_account_id": "uz1080",
        }

    @template("uz", "res.company")
    def _get_uz_res_company(self):
        return {
            self.env.company.id: {
                "account_fiscal_country_id": "base.uz",
                "bank_account_code_prefix": "10100",
                "cash_account_code_prefix": "10110",
                "transfer_account_code_prefix": "10120",
                "transfer_account_id": "uz5710",
                "account_sale_tax_id": "l10n_uz_tax_sale_18",
                "account_purchase_tax_id": "l10n_uz_tax_purchase_18",
                "income_account_id": "uz9010",
                "expense_account_id": "uz9110",
            },
        }
