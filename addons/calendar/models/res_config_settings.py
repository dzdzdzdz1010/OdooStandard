from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    generate_videolink_on_meeting_creation = fields.Boolean("Generate meeting link automatically",
        config_parameter="calendar.generate_videolink_on_meeting_creation")
