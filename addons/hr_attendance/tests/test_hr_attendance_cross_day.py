# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime

from odoo import Command
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('at_install', '-post_install')
class TestAttendanceCrossDay(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ruleset = cls.env['hr.attendance.overtime.ruleset'].create({
        'name': 'Ruleset for overtime testing',
        'rule_ids': [Command.create({
                'name': 'Ruleset for overtime testing - Rule 1',
                'base_off': 'quantity',
                'expected_hours_from_contract': True,
                'quantity_period': 'day',
            })],
        })
        cls.company = cls.env['res.company'].create({
            'name': 'SweatChipChop Inc.',
            'attendance_overtime_validation': 'no_validation',
        })
        cls.company.resource_calendar_id.tz = 'Europe/Brussels'
        cls.attendance = cls.env['hr.attendance']
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Youssef Ahmed',
            'company_id': cls.company.id,
            'date_version': date(2020, 1, 1),
            'contract_date_start': date(2020, 1, 1),
            'ruleset_id': cls.ruleset.id,
            'resource_calendar_id': cls.company.resource_calendar_id.id,
        })

    def test_01_single_normal_day_attendance(self):
        """
        check-in -> O9:00 Mon
        check-out-> 17:00 Mon
        no split
        """
        normal_attendance = self.attendance.create([{
            'employee_id': self.employee.id,
            'check_in': datetime(2025, 11, 3, 9, 0),
            'check_out': datetime(2025, 11, 3, 17, 0),
        }])
        self.assertEqual(len(normal_attendance), 1)
        self.assertEqual(normal_attendance.check_in, datetime(2025, 11, 3, 9, 0))
        self.assertEqual(normal_attendance.check_out, datetime(2025, 11, 3, 17, 0))

    def test_02_standard_overnight_checkout(self):
        """
        check-in -> 4/11 08:00 (UTC)
        check-out-> 5/11 11:00 (UTC)
        split using the write() method
        Attendnace splitted acording to employee local midnight into 2 records:
        1st record : 4/11 08:00 (UTC) -> 4/11 23:00 (UTC) (15 - 1 = 14 hours worked, 6 hours overtime)
        2nd record : 4/11 23:00 (UTC) -> 5/11 11:00 (UTC) (13 - 1 = 12 hours worked, 4 hours overtime)
        """
        cross_day_attendance = self.attendance.create({
            'employee_id': self.employee.id,
            'check_in': datetime(2025, 11, 4, 8, 0, 0),
        })
        cross_day_attendance.write({
            'check_out': datetime(2025, 11, 5, 11, 0, 0)
        })

        attendance_records = self.attendance.search([
            ('employee_id', '=', self.employee.id),
        ], order='check_in asc')

        self.assertEqual(len(attendance_records), 2, "The overnight shift should result in exactly 2 separate attendance records.")

        self.assertEqual(attendance_records[0].check_in, datetime(2025, 11, 4, 8, 0, 0))
        self.assertEqual(attendance_records[0].check_out, datetime(2025, 11, 4, 23, 0))
        self.assertEqual(attendance_records[0].worked_hours, 14.0)
        self.assertEqual(attendance_records[0].overtime_hours, 6.0)

        self.assertEqual(attendance_records[1].check_in, datetime(2025, 11, 4, 23, 0, 0))
        self.assertEqual(attendance_records[1].check_out, datetime(2025, 11, 5, 11, 0))
        self.assertEqual(attendance_records[1].worked_hours, 12.0)
        self.assertEqual(attendance_records[1].overtime_hours, 4.0)

    def test_03_multi_day_manual_entry(self):
        """
        check-in -> 20:00 5/11 (UTC)
        check-out-> 10:00 7/11 (UTC)
        split using the create() method
        Attendnace splitted acording to employee local midnight into 3 records:
        1st record : 5/11 20:00 (UTC) -> 5/11 23:00 (UTC) (3 hours worked "No Lunch", 0 hours overtime)
        2nd record : 5/11 23:00 (UTC) -> 6/11 23:00 (UTC) (24 - 1 = 23 hours worked, 15 hours overtime)
        3rd record : 6/11 23:00 (UTC) -> 7/11 10:00 (UTC) (13 - 1 = 12 hours worked, 4 hours overtime)
        """
        cross_day_attendance = self.attendance.create({
            'employee_id': self.employee.id,
            'check_in': datetime(2025, 11, 5, 20, 0, 0),
            'check_out': datetime(2025, 11, 7, 12, 0, 0),
        })

        self.assertEqual(len(cross_day_attendance), 3, "The overnight shift should result in exactly 3 separate attendance records.")

        self.assertEqual(cross_day_attendance[0].check_in, datetime(2025, 11, 5, 20, 0, 0))
        self.assertEqual(cross_day_attendance[0].check_out, datetime(2025, 11, 5, 23, 0))
        self.assertEqual(cross_day_attendance[0].worked_hours, 3.0)
        self.assertEqual(cross_day_attendance[0].overtime_hours, 0.0)

        self.assertEqual(cross_day_attendance[1].check_in, datetime(2025, 11, 5, 23, 0, 0))
        self.assertEqual(cross_day_attendance[1].check_out, datetime(2025, 11, 6, 23, 0))
        self.assertEqual(cross_day_attendance[1].worked_hours, 23.0)
        self.assertEqual(cross_day_attendance[1].overtime_hours, 15.0)

        self.assertEqual(cross_day_attendance[2].check_in, datetime(2025, 11, 6, 23, 0, 0))
        self.assertEqual(cross_day_attendance[2].check_out, datetime(2025, 11, 7, 12, 0))
        self.assertEqual(cross_day_attendance[2].worked_hours, 12.0)
        self.assertEqual(cross_day_attendance[2].overtime_hours, 4.0)
