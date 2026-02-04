# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.mail.tools.discuss import Store


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _store_im_status_fields(self, res: Store.FieldList):
        super()._store_im_status_fields(res)
        if res.is_for_internal_users():
            # sudo: res.users - internal users can access work location of user
            res.one(
                "main_user_id",
                lambda res: res.many("employee_ids", ["work_location_type"], sudo=True),
            )
