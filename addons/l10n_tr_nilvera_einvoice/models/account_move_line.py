from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_tr_ctsp_number = fields.Char(
        string="CTSP Number",
        compute="_compute_l10n_tr_ctsp_number",
        store=True,
        readonly=False,
    )

    l10n_tr_original_line_id = fields.Many2one("account.move.line", readonly=True)

    l10n_tr_original_quantity = fields.Float(
        string="Original Quantity",
        digits="Product Unit",
        help="The quantity originally sold for this product.",
    )

    l10n_tr_original_tax_without_withholding = fields.Monetary(
        string="Original Tax After Withholding",
        help="Taxes collected after deducting withholding taxes for this product on the original invoice.",
    )

    @api.depends("l10n_tr_original_line_id")
    def _compute_l10n_tr_original_quantity(self):
        for line in self.filtered(lambda r: r.l10n_tr_original_line_id and r.move_id.state == "draft" and not r.l10n_tr_original_quantity):
            line.l10n_tr_original_quantity = line.l10n_tr_original_line_id.quantity

    @api.depends("l10n_tr_original_line_id")
    def _compute_l10n_tr_original_tax_without_withholding(self):
        for line in self.filtered(lambda r: r.l10n_tr_original_line_id and r.move_id.state == "draft" and not r.l10n_tr_original_tax_without_withholding):
            line.l10n_tr_original_tax_without_withholding = line.l10n_tr_original_line_id.price_total - line.l10n_tr_original_line_id.price_subtotal

    @api.depends("product_id.l10n_tr_ctsp_number")
    def _compute_l10n_tr_ctsp_number(self):
        for record in self:
            record.l10n_tr_ctsp_number = record.product_id.l10n_tr_ctsp_number

    @api.constrains("l10n_tr_ctsp_number")
    def _check_l10n_tr_ctsp_number(self):
        for record in self:
            if record.l10n_tr_ctsp_number and len(record.l10n_tr_ctsp_number) > 12:
                raise ValidationError(_("CTSP Number must be 12 digits or fewer."))
