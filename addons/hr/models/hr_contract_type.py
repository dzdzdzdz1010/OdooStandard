# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrContractType(models.Model):
    _name = 'hr.contract.type'
    _description = 'Employee Type'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(compute='_compute_code', store=True, readonly=False)
    sequence = fields.Integer()
    country_id = fields.Many2one('res.country', domain=lambda self: [('id', 'in', self.env.companies.country_id.ids)])
    employee_ids = fields.Many2many('hr.employee', compute='_compute_employee_ids')
    employees_count = fields.Integer(compute='_compute_employee_ids', string='Employees')

    @api.depends('name')
    def _compute_code(self):
        for contract_type in self:
            if contract_type.code:
                continue
            contract_type.code = contract_type.name

    def _compute_employee_ids(self):
        for type in self:
            employees = self.env['hr.employee'].search([('contract_type_id', '=', type.id)])
            type.employee_ids = employees
            type.employees_count = len(employees)

    def action_open_employees(self):
        self.ensure_one()
        if self.employees_count > 1:
            return {
                'name': self.env._('Related Employees'),
                'type': 'ir.actions.act_window',
                'res_model': 'hr.employee',
                'view_mode': 'kanban, form',
                'views': [(False, 'kanban'), (False, 'form')],
                'domain': [('id', 'in', self.employee_ids.ids)],
            }
        return {
            'name': self.env._('Employee'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'res_id': self.employee_ids.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
        }
