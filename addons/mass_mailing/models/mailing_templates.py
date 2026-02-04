# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailingTempplates(models.Model):
    """Mailing templates are customizable, ready to use, templates that speeds up email writing."""
    _name = 'mailing.templates'
    _description = 'Mailing Templates'
    _order = "name ASC"

    name = fields.Char('Mailing Template', required=True)
    description = fields.Char('Description')
    user_id = fields.Many2one(
        'res.users', string='Creator',
        default=lambda self: self.env.user)
