from odoo import api, models


class IrActionsActions(models.Model):
    _inherit = "ir.actions.actions"

    @api.model
    def get_bindings(self, model_name):
        """ Adds "Send Email" binding action if _mailing_enabled is set on the requested model """
        bindings = super().get_bindings(model_name)
        if hasattr(self.env[model_name], '_mailing_enabled') and self.env[model_name]._mailing_enabled \
            and model_name != 'hr.applicant':
            action_sudo = self.env.ref('mass_mailing.action_toolbar_mass_mail', raise_if_not_found=False).sudo()
            if action_sudo:
                bindings.setdefault('action', [])
                new_action = {
                    'id': action_sudo.id,
                    'name': action_sudo.name,
                    'binding_view_types': action_sudo.binding_view_types,
                    'sequence': 4,
                }
                idx = 0
                for action in bindings['action']:
                    if action.get('sequence', 0) < 4:
                        idx += 1
                bindings['action'].insert(idx, new_action)
        return bindings
