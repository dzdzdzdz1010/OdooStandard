# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    tracking_method = fields.Selection([
        ('calendar', 'Time Off'),
        ('work_entry', "Work Entries")
    ], default='calendar', required=True, groups="base.group_system,hr.group_hr_manager")
