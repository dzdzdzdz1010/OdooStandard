# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def get_attendace_data_by_employee(self, date_start, date_stop):
        attendance_data = super().get_attendace_data_by_employee(date_start, date_stop)
        for employee_id in self.ids:
            attendance_data[employee_id]["unspent_compensable_overtime"] = 0
        unspent_overtime = (
            self.env["hr.leave"]._get_deductible_employee_overtime(self)
        )
        for employee in unspent_overtime:
            attendance_data[employee.id]["unspent_compensable_overtime"] = max(0, unspent_overtime[employee])
        return attendance_data
