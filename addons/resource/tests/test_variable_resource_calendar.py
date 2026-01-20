# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, date, timedelta, UTC

from odoo.tests.common import TransactionCase
from zoneinfo import ZoneInfo


class TestVariableResourceCalendar(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar = cls.env['resource.calendar'].create({
            'name': 'Test Variable Calendar',
            'resource_type': 'variable',
        })

    def test_attendance_intervals_batch_variable_calendar(self):
        """Test that _attendance_intervals_batch returns only attendances in the selected date range"""
        start = date(2025, 11, 1)
        self.calendar.attendance_ids = [(6, 0, 0)] + [
            (0, 0,
                {
                    'date': start + timedelta(days=day),
                    'hour_from': hour,
                    'hour_to': hour + 4,
                })
            for day in range(0, 31)
            for hour in [8, 13]
        ] + [
            (0, 0,
                {
                    'dayofweek': str(weekday),
                    'hour_from': hour,
                    'hour_to': hour + 4,
                })
            for weekday in range(0, 5)
            for hour in [3, 18]
        ]

        tz = ZoneInfo('UTC')
        start_dt = datetime(2025, 11, 10, 0, 0, 0, tzinfo=tz)
        end_dt = datetime(2025, 11, 20, 23, 59, 59, tzinfo=tz)

        intervals = self.calendar._attendance_intervals_batch(start_dt, end_dt)[False]

        # Should only take attendance with date between Nov 10 and Nov 20 (22 attendances)
        # Attendances based on dayofweek are ignored in variable calendars
        self.assertEqual(len(intervals), 22, "Should have 22 attendance in range")
        self.assertEqual(intervals._items[0][0:2], (datetime(2025, 11, 10, 8, 0, tzinfo=tz), datetime(2025, 11, 10, 12, 0, tzinfo=tz)))
        self.assertEqual(intervals._items[-1][0:2], (datetime(2025, 11, 20, 13, 0, tzinfo=tz), datetime(2025, 11, 20, 17, 0, tzinfo=tz)))

    def test_copy_from_week(self):
        """Test copying attendances from one week to another"""
        source_date = date(2026, 1, 7)
        target_date = date(2026, 1, 14)

        source_monday = date(2026, 1, 5)
        self.calendar.attendance_ids = [(6, 0, 0)] + [
            (0, 0,
                {
                    'date': source_monday + timedelta(days=weekday),
                    'hour_from': 8,
                    'hour_to': 17,
                })
            for weekday in range(0, 5)
        ]

        self.assertEqual(len(self.calendar.attendance_ids.filtered_domain([
            ('date', '>=', date(2026, 1, 12)),
            ('date', '<=', date(2026, 1, 18)),
        ])), 0, "Should have 0 attendances in target week")

        self.calendar.copy_from('WEEK', source_date, target_date)

        target_attendances = self.calendar.attendance_ids.filtered_domain([
            ('date', '>=', date(2026, 1, 12)),
            ('date', '<=', date(2026, 1, 18)),
        ])

        self.assertEqual(len(target_attendances), 5, "Should have 5 attendances in target week")

        target_monday = date(2026, 1, 12)
        for weekday in range(0, 5):
            att_date = target_monday + timedelta(days=weekday)
            matching_atts = target_attendances.filtered(lambda att: att.date == att_date and att.hour_from == 8 and att.hour_to == 17)
            self.assertEqual(len(matching_atts), 1, f"Should have attendance on {att_date} from 8 to 17")
        self.assertFalse(target_attendances.filtered(lambda att: int(att.dayofweek) >= 5), "Should have no attendance on weekends")

    def test_copy_from_month_date(self):
        """Test copying attendances from one month to another by date number"""
        source_date = date(2025, 12, 15)
        target_date = date(2026, 2, 15)

        source_day1 = source_date.replace(day=1)
        self.calendar.attendance_ids = [(6, 0, 0)] + [
            (0, 0,
                {
                    'date': source_day1 + timedelta(days=day),
                    'hour_from': 8,
                    'hour_to': 17,
                })
            for day in range(0, 31, 2)
        ]

        self.assertEqual(len(self.calendar.attendance_ids.filtered_domain([
            ('date', '>=', date(2026, 2, 1)),
            ('date', '<=', date(2026, 2, 28)),
        ])), 0, "Should have 0 attendances in target month")

        self.calendar.copy_from('MONTH', source_date, target_date, copy_type='DATE')

        target_attendances = self.calendar.attendance_ids.filtered_domain([
            ('date', '>=', date(2026, 2, 1)),
            ('date', '<=', date(2026, 2, 28)),
        ])

        self.assertEqual(len(target_attendances), 14, "Should have 14 attendances in target month")

        target_day1 = target_date.replace(day=1)
        for day in range(0, 28, 2):
            att_date = target_day1 + timedelta(days=day)
            matching_atts = target_attendances.filtered(lambda att: att.date == att_date and att.hour_from == 8 and att.hour_to == 17)
            self.assertEqual(len(matching_atts), 1, f"Should have attendance on {att_date} from 8 to 17")
        self.assertFalse(self.calendar.attendance_ids.filtered(lambda att: att.date and att.date.month == 3), "Attendances should not overflow to march")

    def test_copy_from_month_weekday_1st_case(self):
        """
        Test copying attendances from one month to another by weekday.
        First case: source month starts earlier than the target month (weekday speaking)
        """
        source_date = date(2024, 7, 15)  # Chosen because its the earliest month starting on a Monday and having 31 days (and is not December 2025)
        target_date = date(2026, 1, 15)

        # 1st July 2024 is a Monday
        source_day1 = source_date.replace(day=1)
        self.calendar.attendance_ids = [(6, 0, 0)] + [
            (0, 0,
                {
                    'date': source_day1 + timedelta(days=day),
                    'hour_from': 8,
                    'hour_to': 17,
                })
            for day in range(0, 31) if day % 7 < 5
        ]

        self.assertEqual(len(self.calendar.attendance_ids.filtered_domain([
            ('date', '>=', date(2026, 1, 1)),
            ('date', '<=', date(2026, 1, 31)),
        ])), 0, "Should have 0 attendances in target month")

        self.calendar.copy_from('MONTH', source_date, target_date, copy_type='WEEKDAY')

        target_attendances = self.calendar.attendance_ids.filtered_domain([
            ('date', '>=', date(2026, 1, 1)),
            ('date', '<=', date(2026, 1, 31)),
        ]).sorted('date')

        self.assertEqual(target_attendances[0].date, date(2026, 1, 1), "First attendance should be on Jan 1, 2026")
        self.assertFalse(target_attendances.filtered(lambda att: int(att.dayofweek) >= 5), "Should have no attendance on weekends")
        self.assertFalse(self.calendar.attendance_ids.filtered(lambda att: att.date and att.date.month == 12), "Attendances should not overflow to December")
        self.assertFalse(self.calendar.attendance_ids.filtered(lambda att: att.date and att.date.month == 2), "Attendances should not overflow to February")

    def test_copy_from_month_weekday_2nd_case(self):
        """
        Test copying attendances from one month to another by weekday.
        Second case: source month starts later than the target month (weekday speaking)
        """
        source_date = date(2025, 10, 15)
        target_date = date(2025, 12, 15)

        # 1st October 2025 is a Wednesday
        source_day1 = source_date.replace(day=1)
        self.calendar.attendance_ids = [(6, 0, 0)] + [
            (0, 0,
                {
                    'date': source_day1 + timedelta(days=day),
                    'hour_from': 8,
                    'hour_to': 17,
                })
            for day in range(0, 31) if (day + 2) % 7 < 5
        ]

        self.assertEqual(len(self.calendar.attendance_ids.filtered_domain([
            ('date', '>=', date(2025, 12, 1)),
            ('date', '<=', date(2025, 12, 31)),
        ])), 0, "Should have 0 attendances in target month")

        self.calendar.copy_from('MONTH', source_date, target_date, copy_type='WEEKDAY')

        target_attendances = self.calendar.attendance_ids.filtered_domain([
            ('date', '>=', date(2025, 12, 1)),
            ('date', '<=', date(2025, 12, 31)),
        ]).sorted('date')

        self.assertEqual(target_attendances[0].date, date(2025, 12, 3), "First attendance should be on Dec 3, 2025")
        self.assertFalse(target_attendances.filtered(lambda att: int(att.dayofweek) >= 5), "Should have no attendance on weekends")
        self.assertFalse(self.calendar.attendance_ids.filtered(lambda att: att.date and att.date.month == 1), "Attendances should not overflow to January")

    def test_copy_from_month_weekday_3rd_case(self):
        """
        Test copying attendances from one month to another by weekday.
        Third case: source and target month start on the same weekday (essentially a date copy)
        """
        source_date = date(2025, 9, 15)
        target_date = date(2025, 12, 15)

        # 1st September 2025 is a Monday
        source_day1 = source_date.replace(day=1)
        self.calendar.attendance_ids = [(6, 0, 0)] + [
            (0, 0,
                {
                    'date': source_day1 + timedelta(days=day),
                    'hour_from': 8,
                    'hour_to': 17,
                })
            for day in range(0, 30) if day % 7 < 5
        ]

        self.assertEqual(len(self.calendar.attendance_ids.filtered_domain([
            ('date', '>=', date(2025, 12, 1)),
            ('date', '<=', date(2025, 12, 31)),
        ])), 0, "Should have 0 attendances in target month")

        self.calendar.copy_from('MONTH', source_date, target_date, copy_type='WEEKDAY')

        target_attendances = self.calendar.attendance_ids.filtered_domain([
            ('date', '>=', date(2025, 12, 1)),
            ('date', '<=', date(2025, 12, 31)),
        ]).sorted('date')

        self.assertEqual(target_attendances[0].date, date(2025, 12, 1), "First attendance should be on Dec 1, 2025")
        self.assertFalse(target_attendances.filtered(lambda att: att.date == date(2025, 12, 31)), "Should have no attendance on this day as september is shorter than december")
        self.assertFalse(target_attendances.filtered(lambda att: int(att.dayofweek) >= 5), "Should have no attendance on weekends")
