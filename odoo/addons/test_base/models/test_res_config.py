from odoo import fields, models


class ResConfigTest(models.Model):
    _name = 'res.config.test'
    _inherit = ['res.config.settings']

    _description = 'Config test'

    param1 = fields.Integer(
        string='Test parameter 1',
        config_parameter='resConfigTest.parameter1',
        default=1000)

    param2 = fields.Many2one(
        'res.config',
        config_parameter="resConfigTest.parameter2")
