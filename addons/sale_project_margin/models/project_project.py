from odoo import fields, models


class ProjectProject(models.Model):
    _inherit = 'project.project'

    projected_margin = fields.Monetary(compute='_compute_projected_margin', export_string_translation=False)
    projected_margin_status = fields.Char(compute='_compute_projected_margin', export_string_translation=False)

    def _compute_projected_margin(self):
        margin_per_project = dict(self.env['sale.order']._read_group(
            domain=[('project_id', 'in', self.ids)],
            groupby=['project_id'],
            aggregates=['margin:sum'],
        ))
        for project in self:
            project.projected_margin = margin_per_project.get(project, 0.0)
            project.projected_margin_status = 'off_track' if project.projected_margin < 0 else 'on_track'

    def action_projected_margin(self):
        action = self.env['ir.actions.act_window']._for_xml_id('sale_margin.action_order_report_projected_margins')
        action['display_name'] = self.env._("%(name)s's Projected Margins", name=self.name)
        action['domain'] = [('project_id', '=', self.id)]
        return action
