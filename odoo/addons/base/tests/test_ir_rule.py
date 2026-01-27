# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo.tests.common import tagged
from odoo import Command


@tagged('at_install', '-post_install')
class TestIrRule(TransactionCaseWithUserDemo):

    def test_ir_rule(self):
        model_res_partner = self.env.ref('base.model_res_partner')
        group_user = self.env.ref('base.group_user')

        # create an ir_rule for the Employee group with an blank domain
        rule1 = self.env['ir.rule'].create({
            'name': 'test_rule1',
            'model_id': model_res_partner.id,
            'domain_force': False,
            'groups': [Command.set(group_user.ids)],
        })

        # read as demo user the partners (one blank domain)
        partners_demo = self.env['res.partner'].with_user(self.user_demo)
        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partner.")

        # same with domain 1=1
        rule1.domain_force = "[(1,'=',1)]"
        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partner.")

        # same with domain []
        rule1.domain_force = "[]"
        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partner.")

        # create another ir_rule for the Employee group (to test multiple rules)
        rule2 = self.env['ir.rule'].create({
            'name': 'test_rule2',
            'model_id': model_res_partner.id,
            'domain_force': False,
            'groups': [Command.set(group_user.ids)],
        })

        # read as demo user with domains [] and blank
        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partner.")

        # same with domains 1=1 and blank
        rule1.domain_force = "[(1,'=',1)]"
        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partner.")

        # same with domains 1=1 and 1=1
        rule2.domain_force = "[(1,'=',1)]"
        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partner.")

        # create another ir_rule for the Employee group (to test multiple rules)
        rule3 = self.env['ir.rule'].create({
            'name': 'test_rule3',
            'model_id': model_res_partner.id,
            'domain_force': False,
            'groups': [Command.set(group_user.ids)],
        })

        # read the partners as demo user
        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partner.")

        # same with domains 1=1, 1=1 and 1=1
        rule3.domain_force = "[(1,'=',1)]"
        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partner.")

        # modify the global rule on res_company which triggers a recursive check
        # of the rules on company
        global_rule = self.env.ref('base.res_company_rule_public')
        global_rule.domain_force = "[('id','in', company_ids)]"

        # read as demo user (exercising the global company rule)
        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partner.")

        # Modify the ir_rule for employee to have a rule that fordids seeing any
        # record. We use a domain with implicit AND operator for later tests on
        # normalization.
        rule2.domain_force = "[('id','=',False),('name','=',False)]"

        # check that demo user still sees partners, because group-rules are OR'ed
        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partner.")

        # create a new group with demo user in it, and a complex rule
        group_test = self.env['res.groups'].create({
            'name': 'Test Group',
            'user_ids': [Command.set(self.user_demo.ids)],
        })

        # add the rule to the new group, with a domain containing an implicit
        # AND operator, which is more tricky because it will have to be
        # normalized before combining it
        rule3.write({
            'domain_force': "[('name','!=',False),('id','!=',False)]",
            'groups': [Command.set(group_test.ids)],
        })

        # read the partners again as demo user, which should give results
        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see partners even with the combined rules.")

        # delete global domains (to combine only group domains)
        self.env['ir.rule'].search([('groups', '=', False)]).unlink()

        # read the partners as demo user (several group domains, no global domain)
        partners = partners_demo.search([])
        self.assertTrue(partners, "Demo user should see some partners.")
