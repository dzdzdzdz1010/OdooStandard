# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests.common import TransactionCase, new_test_user

class DashboardTestCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = cls.env["res.groups"].create({"name": "test group"})
        cls.user = new_test_user(cls.env, login="Raoul")
<<<<<<< 7c8de60b9eb243dcbd41bb439c6a98240f4ecade
        cls.user.group_ids |= cls.group
||||||| c4b1ca0d3948f830b78193df9a4d95c2b68b8a72
        cls.user.groups_id |= cls.group
=======
        cls.user.groups_id |= cls.group + cls.env.ref('base.group_allow_export', raise_if_not_found=False)
>>>>>>> 9df2f8890384481775a258a1d7c7f09ec613506e

    def create_dashboard(self, group=None):
        dashboard_group = group or self.env["spreadsheet.dashboard.group"].create({
            "name": "Dashboard group"
        })
        dashboard = self.env["spreadsheet.dashboard"].create(
            {
                "name": "a dashboard",
                "group_ids": [Command.set(self.group.ids)],
                "dashboard_group_id": dashboard_group.id,
            }
        )
        return dashboard

    def share_dashboard(self, dashboard):
        share = self.env["spreadsheet.dashboard.share"].create(
            {
                "dashboard_id": dashboard.id,
                "spreadsheet_data": dashboard.spreadsheet_data,
            }
        )
        return share
