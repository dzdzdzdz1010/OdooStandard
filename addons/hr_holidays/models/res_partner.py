# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.addons.mail.tools.discuss import Store


class ResPartner(models.Model):
    _inherit = 'res.partner'

    leave_date_to = fields.Date(compute="_compute_leave_date_to")

    def _compute_leave_date_to(self):
        for partner in self:
            # in the rare case of multi-user partner, return the earliest
            # possible return date
            dates = partner.user_ids.mapped("leave_date_to")
            partner.leave_date_to = min(dates) if dates and all(dates) else False

    def _store_im_status_fields(self, res: Store.FieldList):
        super()._store_im_status_fields(res)
        if res.is_for_internal_users():
            # sudo: res.users - internal users can access leave date of user
            res.one("main_user_id", lambda res: res.many("employee_ids", ["leave_date_to"], sudo=True))
