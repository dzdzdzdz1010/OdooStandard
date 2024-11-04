from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _update_l10n_in_gst_treatment_and_fp_from_iap_autocomplete(self):
        sez_fp = self.env['account.chart.template'].ref('fiscal_position_in_sez', raise_if_not_found=False)
        sez_lut_fp = self.env['account.chart.template'].ref('fiscal_position_in_lut_sez_1', raise_if_not_found=False)
        # Whichever fiscal position is selected to be applied automatically gets priority.
        fiscal_to_apply = (sez_fp.auto_apply and sez_fp) or (sez_lut_fp.auto_apply and sez_lut_fp) or sez_fp

        response = self.env['res.partner'].enrich_by_gst(self.vat) if self.vat else {}

        # Response is empty when GSTIN is invalid or removed.
        if not response:
            self.l10n_in_gst_treatment = 'consumer'
            if self.property_account_position_id == fiscal_to_apply:
                self.property_account_position_id = False
            return

        if response.get('error'):
            return

        gst_treatment = response.get('l10n_in_gst_treatment', 'regular')
        if fiscal_to_apply and (not self.property_account_position_id or self.property_account_position_id == fiscal_to_apply):
            self.property_account_position_id = fiscal_to_apply.id if gst_treatment == 'special_economic_zone' else False
        self.l10n_in_gst_treatment = gst_treatment
