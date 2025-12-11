# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizard

from odoo.addons.payment import reset_payment_provider, setup_provider


def post_init_hook(env):
    setup_provider(env, 'custom', custom_mode='cash_on_delivery')
    _assign_default_mail_template_picking_id(env)


def uninstall_hook(env):
    reset_payment_provider(env, 'custom', custom_mode='cash_on_delivery')


def _assign_default_mail_template_picking_id(env):
    company_ids_without_default_mail_template_id = env['res.company'].search([
        ('delivery_mail_confirmation_template_id', '=', False)
    ])
    default_mail_template_id = env.ref('delivery.mail_template_data_delivery_confirmation', raise_if_not_found=False)
    if default_mail_template_id:
        company_ids_without_default_mail_template_id.write({
            'delivery_mail_confirmation_template_id': default_mail_template_id.id,
        })
