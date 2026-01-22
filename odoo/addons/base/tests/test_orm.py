# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, tagged
from odoo import Command


@tagged('post_install', '-at_install')
class TestCompanyDependent(TransactionCase):
    def test_orm_ondelete_restrict(self):
        # model_A
        #  | field_a                           company dependent many2one is
        #  | company dependent many2one        stored as jsonb and doesn't
        #  | (ondelete='restrict')             have db ON DELETE action
        #  v
        # model_B
        #  | field_b                           if a row for model_B is deleted
        #  | many2one (ondelete='cascade')     because of ON DELETE CASCADE,
        #  v                                   model_A will reference a deleted
        # model_C                              row and logically be NULL when read
        #
        #                                      this test asks you to move the
        #                                      ON DELETE CASCADE logic of model_B
        #                                      to ORM and remove ondelete='cascade'

        for model in self.env.registry.values():
            for field in model._fields.values():
                if field.company_dependent and field.type == 'many2one' and field.ondelete.lower() == 'restrict':
                    for comodel_field in self.env[field.comodel_name]._fields.values():
                        self.assertFalse(
                            comodel_field.type == 'many2one' and comodel_field.ondelete == 'cascade',
                            (f'when a row for {comodel_field.comodel_name} is deleted, a row for {comodel_field.model_name} '
                             f'may also be deleted for sake of on delete cascade field {comodel_field}, which will '
                             f'bypass the ORM ondelete="restrict" check for a company dependent many2one field {field}. '
                             f'Please override the unlink method of {comodel_field.comodel_name} and do the ORM on '
                             f'delete cascade logic and remove/override the ondelete="cascade" of {comodel_field}')
                        )
