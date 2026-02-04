# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CrmIapLeadIndustry(models.Model):
    """ Industry Tags of Acquisition Rules """
    _name = 'crm.iap.lead.industry'
    _description = 'CRM IAP Lead Industry'
    _order = 'sequence,id'

    name = fields.Char(string='Industry', required=True, translate=True)
    sic_group = fields.Integer(required=True, help="Industry's Major Group Code as per SIC")
    division_id = fields.Many2one(
        'crm.iap.lead.industry.division',
        required=True,
        ondelete='restrict',
        help="SIC Division code to which Major Group belongs.",
    )
    color = fields.Integer(string='Color Index')
    sequence = fields.Integer('Sequence')

    _name_uniq = models.Constraint(
        'unique (name)',
        'Industry name already exists!',
    )

    @api.depends('name', 'division_id')
    @api.depends_context('formatted_display_name')
    def _compute_display_name(self):
        needs_markdown = self.env.context.get('formatted_display_name')
        for industry in self:
            industry.display_name = f"{industry.name} \v--{industry.division_id.name}--" if needs_markdown else industry.name
