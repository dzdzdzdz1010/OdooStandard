# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.tools import format_time
from odoo.tools.date_utils import float_to_time


class ResourceCalendarAttendance(models.Model):
    _name = 'resource.calendar.attendance'
    _description = "Work Detail"
    _order = 'sequence, dayofweek, hour_from'

    dayofweek = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')
        ], 'Day of Week', required=True, index=True, default='0',
        compute="_compute_dayofweek", store=True, readonly=False)
    hour_from = fields.Float(string='Work from', default=0, required=True, index=True,
        help="Start and End time of working.\n"
             "A specific value of 24:00 is interpreted as 23:59:59.999999.")
    hour_to = fields.Float(string='Work to', default=0, required=True)
    # For the hour duration, the compute function is used to compute the value
    # unambiguously, while the duration in days is computed for the default
    # value but can be manually overridden.
    duration_hours = fields.Float(compute='_compute_duration_hours', string='Hours', store=True, readonly=False)
    calendar_id = fields.Many2one("resource.calendar", string="Resource's Calendar", required=True, index=True, ondelete='cascade')
    duration_based = fields.Boolean(compute='_compute_duration_based', store=True)
    day_period = fields.Selection([
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
        ('full_day', 'Full Day')], store=True, compute='_compute_day_period')
    display_type = fields.Selection([
        ('line_section', "Section")], default=False, help="Technical field for UX purpose.")
    sequence = fields.Integer(default=10,
        help="Gives the sequence of this line when displaying the resource calendar.")

    # Variable
    date = fields.Date()

    @api.onchange('hour_from')
    def _onchange_hour_from(self):
        # avoid negative or after midnight
        self.hour_from = min(self.hour_from, 23.99)
        self.hour_from = max(self.hour_from, 0.0)

    @api.onchange('hour_to')
    def _onchange_hour_to(self):
        # avoid negative or after midnight
        self.hour_to = min(self.hour_to, 24)
        self.hour_to = max(self.hour_to, 0.0)

        if self.hour_from and not self.hour_to:
            self.hour_from = 0.0

        # avoid wrong order
        self.hour_to = max(self.hour_to, self.hour_from)

    @api.onchange('duration_hours')
    def _onchange_duration_hours(self):
        self.duration_hours = min(self.duration_hours, 24)
        if self.hour_from or self.hour_to:
            if self.hour_from + self.duration_hours > 24:
                self.hour_from = 24 - self.duration_hours
                self.hour_to = 24
            else:
                self.hour_to = self.hour_from + self.duration_hours

    @api.depends('hour_from', 'hour_to')
    def _compute_duration_based(self):
        for attendance in self:
            attendance.duration_based = not attendance.hour_from and not attendance.hour_to

    @api.depends('duration_hours', 'hour_from', 'hour_to')
    def _compute_day_period(self):
        for attendance in self:
            if attendance.duration_hours > (0.75 * attendance.calendar_id.hours_per_day) or (not attendance.hour_from and not attendance.hour_to):
                attendance.day_period = 'full_day'
            elif attendance.hour_from and attendance.hour_to:
                if attendance.hour_from > 12 or (12 - attendance.hour_from <= attendance.hour_to - 12):
                    attendance.day_period = 'afternoon'
                else:
                    attendance.day_period = 'morning'
            else:
                attendance.day_period = 'morning'

    @api.depends('date')
    def _compute_dayofweek(self):
        for attendance in self:
            if attendance.date:
                attendance.dayofweek = str(attendance.date.weekday())
            elif not attendance.dayofweek:  # default value
                attendance.dayofweek = '0'

    @api.depends('hour_from', 'hour_to')
    def _compute_duration_hours(self):
        for attendance in self.filtered(lambda att: att.hour_from or att.hour_to):
            attendance.duration_hours = max(0, attendance.hour_to - attendance.hour_from)

    def _compute_display_name(self):
        for attendance in self:
            if attendance.duration_based:
                attendance.display_name = self.env._("%(duration)s Attendance", duration=format_time(self.env, float_to_time(attendance.duration_hours), time_format="short"))
            else:
                attendance.display_name = self.env._("%(hour_from)s - %(hour_to)s Attendance",
                                                     hour_from=format_time(self.env, float_to_time(attendance.hour_from), time_format="short"),
                                                     hour_to=format_time(self.env, float_to_time(attendance.hour_to), time_format="short"))

    def _copy_attendance_vals(self):
        self.ensure_one()
        return {
            'date': self.date,
            'dayofweek': self.dayofweek,
            'day_period': self.day_period,
            'duration_hours': self.duration_hours,
            'hour_from': self.hour_from,
            'hour_to': self.hour_to,
            'display_type': self.display_type,
            'sequence': self.sequence,
        }

    def _is_work_period(self):
        return not self.display_type

    def _get_attendances_on_date(self, date):
        return self.filtered(lambda a: (not a.date and a.dayofweek == str(date.weekday())) or (a.date == date))
