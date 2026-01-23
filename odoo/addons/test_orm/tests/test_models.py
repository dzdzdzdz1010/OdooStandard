# Part of Odoo. See LICENSE file for full copyright and licensing details.

import inspect

from odoo.exceptions import AccessError, LockError, UserError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger
from odoo import Command

DEPRECATED_MODEL_ATTRIBUTES = [
    'view_init',
    '_needaction',
    '_sql',
    '_execute_sql',
]


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestORM(TransactionCase):
    """ test special behaviors of ORM CRUD functions """

    @mute_logger('odoo.models')
    def test_access_deleted_records(self):
        """ Verify that accessing deleted records works as expected """
        c1 = self.env['res.partner.category'].create({'name': 'W'})
        c2 = self.env['res.partner.category'].create({'name': 'Y'})
        c1.unlink()

        # read() is expected to skip deleted records because our API is not
        # transactional for a sequence of search()->read() performed from the
        # client-side... a concurrent deletion could therefore cause spurious
        # exceptions even when simply opening a list view!
        # /!\ Using unprileged user to detect former side effects of ir.rules!
        user = self.env['res.users'].create({
            'name': 'test user',
            'login': 'test2',
            'group_ids': [Command.set([self.ref('base.group_user')])],
        })
        cs = (c1 + c2).with_user(user)
        self.assertEqual([{'id': c2.id, 'name': 'Y'}], cs.read(['name']), "read() should skip deleted records")
        self.assertEqual([], cs[0].read(['name']), "read() should skip deleted records")

        # Deleting an already deleted record should be simply ignored
        self.assertTrue(c1.unlink(), "Re-deleting should be a no-op")

    @mute_logger('odoo.models')
    def test_access_partial_deletion(self):
        """ Check accessing a record from a recordset where another record has been deleted. """
        Model = self.env['res.country']
        display_name_field = Model._fields['display_name']
        self.assertTrue(display_name_field.compute and not display_name_field.store, "test assumption not satisfied")

        # access regular field when another record from the same prefetch set has been deleted
        records = Model.create([{'name': name[0], 'code': name[1]} for name in (['Foo', 'ZV'], ['Bar', 'ZX'], ['Baz', 'ZY'])])
        for record in records:
            record.name
            record.unlink()

        # access computed field when another record from the same prefetch set has been deleted
        records = Model.create([{'name': name[0], 'code': name[1]} for name in (['Foo', 'ZV'], ['Bar', 'ZX'], ['Baz', 'ZY'])])
        for record in records:
            record.display_name
            record.unlink()

    @mute_logger('odoo.models', 'odoo.addons.base.models.ir_rule')
    def test_access_filtered_records(self):
        """ Verify that accessing filtered records works as expected for non-admin user """
        p1 = self.env['res.partner'].create({'name': 'W'})
        p2 = self.env['res.partner'].create({'name': 'Y'})
        user = self.env['res.users'].create({
            'name': 'test user',
            'login': 'test2',
            'group_ids': [Command.set([self.ref('base.group_user')])],
        })

        partner_model = self.env['ir.model'].search([('model','=','res.partner')])
        self.env['ir.rule'].create({
            'name': 'Y is invisible',
            'domain_force': [('id', '!=', p1.id)],
            'model_id': partner_model.id,
        })

        # search as unprivileged user
        partners = self.env['res.partner'].with_user(user).search([])
        self.assertNotIn(p1, partners, "W should not be visible...")
        self.assertIn(p2, partners, "... but Y should be visible")

        # read as unprivileged user
        with self.assertRaises(AccessError):
            p1.with_user(user).read(['name'])
        # write as unprivileged user
        with self.assertRaises(AccessError):
            p1.with_user(user).write({'name': 'foo'})
        # unlink as unprivileged user
        with self.assertRaises(AccessError):
            p1.with_user(user).unlink()

        # Prepare mixed case
        p2.unlink()
        # read mixed records: some deleted and some filtered
        with self.assertRaises(AccessError):
            (p1 + p2).with_user(user).read(['name'])
        # delete mixed records: some deleted and some filtered
        with self.assertRaises(AccessError):
            (p1 + p2).with_user(user).unlink()

    def test_read(self):
        partner = self.env['res.partner'].create({'name': 'MyPartner1'})
        result = partner.read()
        self.assertIsInstance(result, list)

    @mute_logger('odoo.models')
    def test_search_read(self):
        partner = self.env['res.partner']

        # simple search_read
        partner.create({'name': 'MyPartner1'})
        found = partner.search_read([('name', '=', 'MyPartner1')], ['name'])
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]['name'], 'MyPartner1')
        self.assertIn('id', found[0])

        # search_read correct order
        partner.create({'name': 'MyPartner2'})
        found = partner.search_read([('name', 'like', 'MyPartner')], ['name'], order="name")
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0]['name'], 'MyPartner1')
        self.assertEqual(found[1]['name'], 'MyPartner2')
        found = partner.search_read([('name', 'like', 'MyPartner')], ['name'], order="name desc")
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0]['name'], 'MyPartner2')
        self.assertEqual(found[1]['name'], 'MyPartner1')

        # search_read that finds nothing
        found = partner.search_read([('name', '=', 'Does not exists')], ['name'])
        self.assertEqual(len(found), 0)

        # search_read with an empty array of fields
        found = partner.search_read([], [], limit=1)
        self.assertEqual(len(found), 1)
        self.assertTrue(field in list(found[0]) for field in ['id', 'name', 'display_name', 'email'])

        # search_read without fields
        found = partner.search_read([], False, limit=1)
        self.assertEqual(len(found), 1)
        self.assertTrue(field in list(found[0]) for field in ['id', 'name', 'display_name', 'email'])

    @mute_logger('odoo.sql_db')
    def test_exists(self):
        partner = self.env['res.partner']

        # check that records obtained from search exist
        recs = partner.search([])
        self.assertTrue(recs)
        self.assertEqual(recs.exists(), recs)

        # check that new records exist by convention
        recs = partner.new({})
        self.assertTrue(recs.exists())

        # check that there is no record with id -1
        # (it is technically valid, but should not exist)
        recs = partner.browse([-1])
        self.assertFalse(recs.exists())

    def test_lock_for_update(self):
        partner = self.env['res.partner']
        p1, p2 = partner.search([], limit=2)

        # lock p1
        p1.lock_for_update(allow_referencing=True)
        p1.lock_for_update(allow_referencing=False)

        with self.env.registry.cursor() as cr:
            recs = (p1 + p2).with_env(partner.env(cr=cr))
            with self.assertRaises(LockError):
                recs.lock_for_update()
            sub_p2 = recs[1]
            sub_p2.lock_for_update()

            # parent transaction and read, but cannot lock the p2 records
            p2.invalidate_model()
            self.assertTrue(p2.name)
            with self.assertRaises(LockError):
                p2.lock_for_update()

            # can still read from parent after locks and lock failures
            p1.invalidate_model()
            self.assertTrue(p1.name)

        # can lock p2 now
        p2.lock_for_update()

        # cannot lock inexisting record
        inexisting = partner.create({'name': 'inexisting'})
        inexisting.unlink()
        self.assertFalse(inexisting.exists())
        with self.assertRaises(LockError):
            inexisting.lock_for_update()

    def test_try_lock_for_update(self):
        partner = self.env['res.partner']
        p1, p2, *_other = recs = partner.search([], limit=4)

        # lock p1
        self.assertEqual(p1.try_lock_for_update(allow_referencing=True), p1)
        self.assertEqual(p1.try_lock_for_update(allow_referencing=False), p1)

        with self.env.registry.cursor() as cr:
            sub_recs = (p1 + p2).with_env(partner.env(cr=cr))
            self.assertEqual(sub_recs.try_lock_for_update(), sub_recs[1])

        self.assertEqual(recs.try_lock_for_update(limit=1), p1)
        self.assertEqual(recs.try_lock_for_update(), recs)

        # check that order is preserved when limiting
        self.assertEqual(recs[::-1].try_lock_for_update(limit=1), recs[-1])

    def test_write_duplicate(self):
        p1 = self.env['res.partner'].create({'name': 'W'})
        (p1 + p1).write({'name': 'X'})

    def test_m2m_store_trigger(self):
        group_user = self.env.ref('base.group_user')

        user = self.env['res.users'].create({
            'name': 'test',
            'login': 'test_m2m_store_trigger',
            'group_ids': [Command.set([])],
        })
        self.assertTrue(user.share)

        group_user.write({'user_ids': [Command.link(user.id)]})
        self.assertFalse(user.share)

        group_user.write({'user_ids': [Command.unlink(user.id)]})
        self.assertTrue(user.share)

    def test_create_multi(self):
        """ create for multiple records """
        # create countries and states
        vals_list = [{
            'name': 'Foo',
            'state_ids': [
                Command.create({'name': 'North Foo', 'code': 'NF'}),
                Command.create({'name': 'South Foo', 'code': 'SF'}),
                Command.create({'name': 'West Foo', 'code': 'WF'}),
                Command.create({'name': 'East Foo', 'code': 'EF'}),
            ],
            'code': 'ZV',
        }, {
            'name': 'Bar',
            'state_ids': [
                Command.create({'name': 'North Bar', 'code': 'NB'}),
                Command.create({'name': 'South Bar', 'code': 'SB'}),
            ],
            'code': 'ZX',
        }]
        foo, bar = self.env['res.country'].create(vals_list)
        self.assertEqual(foo.name, 'Foo')
        self.assertCountEqual(foo.mapped('state_ids.code'), ['NF', 'SF', 'WF', 'EF'])
        self.assertEqual(bar.name, 'Bar')
        self.assertCountEqual(bar.mapped('state_ids.code'), ['NB', 'SB'])


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestInherits(TransactionCase):
    """ test the behavior of the orm for models that use _inherits;
        specifically: res.users, that inherits from res.partner
    """

    def test_default(self):
        """ `default_get` cannot return a dictionary or a new id """
        defaults = self.env['res.users'].default_get(['partner_id'])
        if 'partner_id' in defaults:
            self.assertIsInstance(defaults['partner_id'], (bool, int))

    def test_create(self):
        """ creating a user should automatically create a new partner """
        partners_before = self.env['res.partner'].search([])
        user_foo = self.env['res.users'].create({'name': 'Foo', 'login': 'foo'})

        self.assertNotIn(user_foo.partner_id, partners_before)

    def test_create_with_ancestor(self):
        """ creating a user with a specific 'partner_id' should not create a new partner """
        partner_foo = self.env['res.partner'].create({'name': 'Foo'})
        partners_before = self.env['res.partner'].search([])
        user_foo = self.env['res.users'].create({'partner_id': partner_foo.id, 'login': 'foo'})
        partners_after = self.env['res.partner'].search([])

        self.assertEqual(partners_before, partners_after)
        self.assertEqual(user_foo.name, 'Foo')
        self.assertEqual(user_foo.partner_id, partner_foo)

    @mute_logger('odoo.models')
    def test_read(self):
        """ inherited fields should be read without any indirection """
        user_foo = self.env['res.users'].create({'name': 'Foo', 'login': 'foo'})
        user_values, = user_foo.read()
        partner_values, = user_foo.partner_id.read()

        self.assertEqual(user_values['name'], partner_values['name'])
        self.assertEqual(user_foo.name, user_foo.partner_id.name)

    @mute_logger('odoo.models')
    def test_copy(self):
        """ copying a user should automatically copy its partner, too """
        user_foo = self.env['res.users'].create({
            'name': 'Foo',
            'login': 'foo',
            'employee': True,
        })
        foo_before, = user_foo.read()
        del foo_before['create_date']
        del foo_before['write_date']
        user_bar = user_foo.copy({'login': 'bar'})
        foo_after, = user_foo.read()
        del foo_after['create_date']
        del foo_after['write_date']
        self.assertEqual(foo_before, foo_after)

        self.assertEqual(user_bar.name, 'Foo (copy)')
        self.assertEqual(user_bar.login, 'bar')
        self.assertEqual(user_foo.employee, user_bar.employee)
        self.assertNotEqual(user_foo.id, user_bar.id)
        self.assertNotEqual(user_foo.partner_id.id, user_bar.partner_id.id)

    @mute_logger('odoo.models')
    def test_copy_with_ancestor(self):
        """ copying a user with 'parent_id' in defaults should not duplicate the partner """
        user_foo = self.env['res.users'].create({'login': 'foo', 'name': 'Foo', 'signature': 'Foo'})
        partner_bar = self.env['res.partner'].create({'name': 'Bar'})

        foo_before, = user_foo.read()
        del foo_before['create_date']
        del foo_before['write_date']
        del foo_before['login_date']
        partners_before = self.env['res.partner'].search([])
        user_bar = user_foo.copy({'partner_id': partner_bar.id, 'login': 'bar'})
        foo_after, = user_foo.read()
        del foo_after['create_date']
        del foo_after['write_date']
        del foo_after['login_date']
        partners_after = self.env['res.partner'].search([])

        self.assertEqual(foo_before, foo_after)
        self.assertEqual(partners_before, partners_after)

        self.assertNotEqual(user_foo.id, user_bar.id)
        self.assertEqual(user_bar.partner_id.id, partner_bar.id)
        self.assertEqual(user_bar.login, 'bar', "login is given from copy parameters")
        self.assertFalse(user_bar.password, "password should not be copied from original record")
        self.assertEqual(user_bar.name, 'Bar', "name is given from specific partner")
        self.assertEqual(user_bar.signature, user_foo.signature, "signature should be copied")

    @mute_logger('odoo.models')
    def test_write_date(self):
        """ modifying inherited fields must update write_date """
        user = self.env.user
        write_date_before = user.write_date

        # write base64 image
        user.write({'image_1920': 'R0lGODlhAQABAIAAAP///////yH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=='})
        write_date_after = user.write_date
        self.assertNotEqual(write_date_before, write_date_after)


@tagged('-at_install', 'post_install')
class TestOverrides(TransactionCase):

    # Ensure all main ORM methods behavior works fine even on empty recordset
    # and that their returned value(s) follow the expected format.

    def test_creates(self):
        for model_env in self.env.values():
            if model_env._abstract:
                continue
            # with self.assertQueryCount(0):
            self.assertEqual(
                model_env.create([]), model_env.browse(),
                "Invalid create return value for model %s" % model_env._name)

    def test_writes(self):
        for model_env in self.env.values():
            if model_env._abstract:
                continue
            try:
                # with self.assertQueryCount(0):
                self.assertEqual(
                    model_env.browse().write({}), True,
                    "Invalid write return value for model %s" % model_env._name)
            except UserError:
                # skip models that should never be modified
                continue

    def test_default_get(self):
        for model_env in self.env.values():
            if model_env._transient:
                continue
            try:
                # with self.assertQueryCount(1):  # allow one query for the call to get_model_defaults.
                self.assertEqual(
                    model_env.browse().default_get([]), {},
                    "Invalid default_get return value for model %s" % model_env._name)
            except UserError:
                # skip "You must be logged in a Belgian company to use this feature" errors
                continue

    def test_unlink(self):
        for model_env in self.env.values():
            if model_env._abstract:
                continue
            # with self.assertQueryCount(0):
            self.assertEqual(
                model_env.browse().unlink(), True,
                "Invalid unlink return value for model %s" % model_env._name)


@tagged('at_install', '-post_install')  # LEGACY at_install
class test_search(TransactionCase):

    def patch_order(self, model, order):
        self.patch(self.registry[model], '_order', order)

    def test_00_search_order(self):
        # Create 6 partners with a given name, and a given creation order to
        # ensure the order of their ID. Some are set as inactive to verify they
        # are by default excluded from the searches and to provide a second
        # `order` argument.

        Partner = self.env['res.partner']
        c = Partner.create({'name': 'test_search_order_C'})
        d = Partner.create({'name': 'test_search_order_D', 'active': False})
        a = Partner.create({'name': 'test_search_order_A'})
        b = Partner.create({'name': 'test_search_order_B'})
        ab = Partner.create({'name': 'test_search_order_AB'})
        e = Partner.create({'name': 'test_search_order_E', 'active': False})

        # The tests.

        # The basic searches should exclude records that have active = False.
        # The order of the returned ids should be given by the `order`
        # parameter of search().

        name_asc = Partner.search([('name', 'like', 'test_search_order%')], order="name asc")
        self.assertEqual([a, ab, b, c], list(name_asc), "Search with 'NAME ASC' order failed.")
        name_desc = Partner.search([('name', 'like', 'test_search_order%')], order="name desc")
        self.assertEqual([c, b, ab, a], list(name_desc), "Search with 'NAME DESC' order failed.")
        id_asc = Partner.search([('name', 'like', 'test_search_order%')], order="id asc")
        self.assertEqual([c, a, b, ab], list(id_asc), "Search with 'ID ASC' order failed.")
        id_desc = Partner.search([('name', 'like', 'test_search_order%')], order="id desc")
        self.assertEqual([ab, b, a, c], list(id_desc), "Search with 'ID DESC' order failed.")

        # The inactive records shouldn't be excluded as soon as a condition on
        # that field is present in the domain. The `order` parameter of
        # search() should support any legal coma-separated values.

        active_asc_id_asc = Partner.search([('name', 'like', 'test_search_order%'), '|', ('active', '=', True), ('active', '=', False)], order="active asc, id asc")
        self.assertEqual([d, e, c, a, b, ab], list(active_asc_id_asc), "Search with 'ACTIVE ASC, ID ASC' order failed.")
        active_desc_id_asc = Partner.search([('name', 'like', 'test_search_order%'), '|', ('active', '=', True), ('active', '=', False)], order="active desc, id asc")
        self.assertEqual([c, a, b, ab, d, e], list(active_desc_id_asc), "Search with 'ACTIVE DESC, ID ASC' order failed.")
        active_asc_id_desc = Partner.search([('name', 'like', 'test_search_order%'), '|', ('active', '=', True), ('active', '=', False)], order="active asc, id desc")
        self.assertEqual([e, d, ab, b, a, c], list(active_asc_id_desc), "Search with 'ACTIVE ASC, ID DESC' order failed.")
        active_desc_id_desc = Partner.search([('name', 'like', 'test_search_order%'), '|', ('active', '=', True), ('active', '=', False)], order="active desc, id desc")
        self.assertEqual([ab, b, a, c, e, d], list(active_desc_id_desc), "Search with 'ACTIVE DESC, ID DESC' order failed.")
        id_asc_active_asc = Partner.search([('name', 'like', 'test_search_order%'), '|', ('active', '=', True), ('active', '=', False)], order="id asc, active asc")
        self.assertEqual([c, d, a, b, ab, e], list(id_asc_active_asc), "Search with 'ID ASC, ACTIVE ASC' order failed.")
        id_asc_active_desc = Partner.search([('name', 'like', 'test_search_order%'), '|', ('active', '=', True), ('active', '=', False)], order="id asc, active desc")
        self.assertEqual([c, d, a, b, ab, e], list(id_asc_active_desc), "Search with 'ID ASC, ACTIVE DESC' order failed.")
        id_desc_active_asc = Partner.search([('name', 'like', 'test_search_order%'), '|', ('active', '=', True), ('active', '=', False)], order="id desc, active asc")
        self.assertEqual([e, ab, b, a, d, c], list(id_desc_active_asc), "Search with 'ID DESC, ACTIVE ASC' order failed.")
        id_desc_active_desc = Partner.search([('name', 'like', 'test_search_order%'), '|', ('active', '=', True), ('active', '=', False)], order="id desc, active desc")
        self.assertEqual([e, ab, b, a, d, c], list(id_desc_active_desc), "Search with 'ID DESC, ACTIVE DESC' order failed.")

        a.ref = "ref1"
        c.ref = "ref2"
        ids = (a | b | c).ids
        for order, result in [
            ('ref', a | c | b),
            ('ref desc', b | c | a),
            ('ref asc nulls first', b | a | c),
            ('ref asc nulls last', a | c | b),
            ('ref desc nulls first', b | c | a),
            ('ref desc nulls last', c | a | b)
        ]:
            with self.subTest(order):
                self.assertEqual(
                    Partner.search([('id', 'in', ids)], order=order).mapped('name'),
                    result.mapped('name'))

        # sorting by an m2o should alias to the natural order of the m2o
        self.patch_order('res.country', 'phone_code')
        a.country_id, c.country_id = self.env['res.country'].create([{
            'name': "Country 1",
            'code': 'C1',
            'phone_code': '01',
        }, {
            'name': 'Country 2',
            'code': 'C2',
            'phone_code': '02'
        }])

        for order, result in [
            ('country_id', a | c | b),
            ('country_id desc', b | c | a),
            ('country_id asc nulls first', b | a | c),
            ('country_id asc nulls last', a | c | b),
            ('country_id desc nulls first', b | c | a),
            ('country_id desc nulls last', c | a | b)
        ]:
            with self.subTest(order):
                self.assertEqual(
                    Partner.search([('id', 'in', ids)], order=order).mapped('name'),
                    result.mapped('name'))

        # NULLS applies to the m2o itself, not its sub-fields, so a null `phone_code`
        # will sort normally (larger than non-null codes)
        b.country_id = self.env['res.country'].create({'name': "Country X", 'code': 'C3'})

        for order, result in [
            ('country_id', a | c | b),
            ('country_id desc', b | c | a),
            ('country_id asc nulls first', a | c | b),
            ('country_id asc nulls last', a | c | b),
            ('country_id desc nulls first', b | c | a),
            ('country_id desc nulls last', b | c | a)
        ]:
            with self.subTest(order):
                self.assertEqual(
                    Partner.search([('id', 'in', ids)], order=order).mapped('name'),
                    result.mapped('name'))

        # a field DESC should reverse the nested behaviour (and thus the inner
        # NULLS clauses), but the outer NULLS clause still has no effect
        self.patch_order('res.country', 'phone_code NULLS FIRST')
        for order, result in [
            ('country_id', b | a | c),
            ('country_id desc', c | a | b),
            ('country_id asc nulls first', b | a | c),
            ('country_id asc nulls last', b | a | c),
            ('country_id desc nulls first', c | a | b),
            ('country_id desc nulls last', c | a | b)
        ]:
            with self.subTest(order):
                self.assertEqual(
                    Partner.search([('id', 'in', ids)], order=order).mapped('name'),
                    result.mapped('name'))

    def test_10_inherits_m2order(self):
        Users = self.env['res.users']

        # Find Employee group
        group_employee = self.env.ref('base.group_user')

        # Get country/state data
        country_be = self.env.ref('base.be')
        country_us = self.env.ref('base.us')
        states_us = country_us.state_ids[:2]

        # Create test users
        u = Users.create({'name': '__search', 'login': '__search', 'group_ids': [Command.set([group_employee.id])]})
        a = Users.create({'name': '__test_A', 'login': '__test_A', 'country_id': country_be.id, 'state_id': country_be.id})
        b = Users.create({'name': '__test_B', 'login': '__a_test_B', 'country_id': country_us.id, 'state_id': states_us[1].id})
        c = Users.create({'name': '__test_B', 'login': '__z_test_B', 'country_id': country_us.id, 'state_id': states_us[0].id})

        # Search as search user
        Users = Users.with_user(u)

        # Do: search on res.users, order on a field on res.partner to try inherits'd fields, then res.users
        expected_ids = [u.id, a.id, c.id, b.id]
        user_ids = Users.search([('id', 'in', expected_ids)], order='name asc, login desc').ids
        self.assertEqual(user_ids, expected_ids, 'search on res_users did not provide expected ids or expected order')

        # Do: order on many2one and inherits'd fields
        expected_ids = [c.id, b.id, a.id, u.id]
        user_ids = Users.search([('id', 'in', expected_ids)], order='state_id asc, country_id desc, name asc, login desc').ids
        self.assertEqual(user_ids, expected_ids, 'search on res_users did not provide expected ids or expected order')

        # Do: order on many2one and inherits'd fields
        expected_ids = [u.id, b.id, c.id, a.id]
        user_ids = Users.search([('id', 'in', expected_ids)], order='country_id desc, state_id desc, name asc, login desc').ids
        self.assertEqual(user_ids, expected_ids, 'search on res_users did not provide expected ids or expected order')

        # Do: order on many2one, but not by specifying in order parameter of search, but by overriding _order of res_users
        self.patch_order('res.users', 'country_id desc, name asc, login desc')
        expected_ids = [u.id, c.id, b.id, a.id]
        user_ids = Users.search([('id', 'in', expected_ids)]).ids
        self.assertEqual(user_ids, expected_ids, 'search on res_users did not provide expected ids or expected order')

    def test_11_indirect_inherits_m2o_order(self):
        Cron = self.env['ir.cron']
        Users = self.env['res.users']

        user_ids = {}
        cron_ids = {}
        for u in 'BAC':
            user_ids[u] = Users.create({'name': u, 'login': u}).id
            cron_ids[u] = Cron.create({'name': u, 'model_id': self.env.ref('base.model_res_partner').id, 'user_id': user_ids[u]}).id

        ids = Cron.search([('id', 'in', list(cron_ids.values()))], order='user_id').ids
        expected_ids = [cron_ids[l] for l in 'ABC']
        self.assertEqual(ids, expected_ids)

    def test_12_m2o_order_loop_self(self):
        Cats = self.env['ir.module.category']
        cat_ids = {}
        def create(name, **kw):
            cat_ids[name] = Cats.create(dict(kw, name=name)).id

        self.patch_order('ir.module.category', 'parent_id desc, name')

        create('A')
        create('B', parent_id=cat_ids['A'])
        create('C', parent_id=cat_ids['A'])
        create('D')
        create('E', parent_id=cat_ids['D'])
        create('F', parent_id=cat_ids['D'])

        expected_ids = [cat_ids[x] for x in 'ADEFBC']
        found_ids = Cats.search([('id', 'in', list(cat_ids.values()))]).ids
        self.assertEqual(found_ids, expected_ids)

    def test_13_m2o_order_loop_multi(self):
        Users = self.env['res.users']

        # will sort by login desc of the creator, then by name
        self.patch_order('res.partner', 'create_uid, name')
        self.patch_order('res.users', 'partner_id, login desc')

        kw = dict(group_ids=[Command.set([self.ref('base.group_system'),
                                     self.ref('base.group_partner_manager')])])

        # When creating with the superuser, the ordering by 'create_uid' will
        # compare user logins with the superuser's login "__system__", which
        # may give different results, because "_" may come before or after
        # letters, depending on the database's locale.  In order to avoid this
        # issue, use a user with a login that doesn't include "_".
        u0 = Users.create(dict(name='A system', login='a', **kw)).id

        u1 = Users.with_user(u0).create(dict(name='Q', login='m', **kw)).id
        u2 = Users.with_user(u1).create(dict(name='B', login='f', **kw)).id
        u3 = Users.with_user(u0).create(dict(name='C', login='c', **kw)).id
        u4 = Users.with_user(u2).create(dict(name='D', login='z', **kw)).id

        expected_ids = [u2, u4, u3, u1]
        found_ids = Users.search([('id', 'in', expected_ids)]).ids
        self.assertEqual(found_ids, expected_ids)

    def test_20_x_active(self):
        """Check the behaviour of the x_active field."""
        # test that a custom field x_active filters like active
        # we take the model res.country as a test model as it is included in base and does
        # not have an active field
        self.addCleanup(self.registry.reset_changes) # reset the registry to avoid polluting other tests

        model_country = self.env['res.country']
        self.assertNotIn('active', model_country._fields)  # just in case someone adds the active field in the model
        self.env['ir.model.fields'].create({
            'name': 'x_active',
            'model_id': self.env.ref('base.model_res_country').id,
            'ttype': 'boolean',
        })
        self.assertEqual('x_active', model_country._active_name)
        country_ussr = model_country.create({'name': 'USSR', 'x_active': False, 'code': 'ZV'})
        ussr_search = model_country.search([('name', '=', 'USSR')])
        self.assertFalse(ussr_search)
        ussr_search = model_country.with_context(active_test=False).search([('name', '=', 'USSR')])
        self.assertIn(country_ussr, ussr_search, "Search with active_test on a custom x_active field failed")
        ussr_search = model_country.search([('name', '=', 'USSR'), ('x_active', '=', False)])
        self.assertIn(country_ussr, ussr_search, "Search with active_test on a custom x_active field failed")

    def test_21_search_count(self):
        Partner = self.env['res.partner']
        count_partner_before = Partner.search_count([])
        partners = Partner.create([
            {'name': 'abc'},
            {'name': 'zer'},
            {'name': 'christope'},
            {'name': 'runbot'},
        ])
        self.assertEqual(len(partners) + count_partner_before, Partner.search_count([]))
        self.assertEqual(3, Partner.search_count([], limit=3))

    def test_22_like_folding(self):
        Model = self.env['res.country']

        # there is just one query for the first search as it matches all
        # the second search does not run, because the domain is False
        with self.assertQueries(["""
            SELECT "res_country"."id"
            FROM "res_country"
            ORDER BY "res_country"."name"->>%s, "res_country"."id"
        """]):
            Model.search([('code', 'ilike', '')])
            Model.search([('code', 'not ilike', '')])


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestParentStore(TransactionCase):
    """ Verify that parent_store computation is done right """

    def setUp(self):
        super(TestParentStore, self).setUp()

        # force res_partner_category.copy() to copy children
        category = self.env['res.partner.category']
        self.patch(category._fields['child_ids'], 'copy', True)

        # setup categories
        self.root = category.create({'name': 'Root category'})
        self.cat0 = category.create({'name': 'Parent category', 'parent_id': self.root.id})
        self.cat1 = category.create({'name': 'Child 1', 'parent_id': self.cat0.id})
        self.cat2 = category.create({'name': 'Child 2', 'parent_id': self.cat0.id})
        self.cat21 = category.create({'name': 'Child 2-1', 'parent_id': self.cat2.id})

    def test_duplicate_parent(self):
        """ Duplicate the parent category and verify that the children have been duplicated too """
        new_cat0 = self.cat0.copy()
        new_struct = new_cat0.search([('parent_id', 'child_of', new_cat0.id)])
        self.assertEqual(len(new_struct), 4, "After duplication, the new object must have the childs records")
        old_struct = new_cat0.search([('parent_id', 'child_of', self.cat0.id)])
        self.assertEqual(len(old_struct), 4, "After duplication, previous record must have old childs records only")
        self.assertFalse(new_struct & old_struct, "After duplication, nodes should not be mixed")

    def test_missing_parent(self):
        """ Missing parent id should not raise an error. """
        # Missing parent with _parent_store
        new_cat0 = self.cat0.copy()
        records = new_cat0.search([('parent_id', 'parent_of', 999999999)])
        self.assertEqual(len(records), 0)

        # Missing parent without _parent_store
        category = self.env['res.partner.category']
        self.patch(self.env.registry['res.partner.category'], '_parent_store', False)
        records = category.search([('parent_id', 'child_of', 999999999)])
        self.assertEqual(len(records), 0)

    def test_missing_child(self):
        """ Missing child id should not raise an error. """
        # Missing child with _parent_store
        new_cat0 = self.cat0.copy()
        records = new_cat0.search([('parent_id', 'child_of', 999999999)])
        self.assertEqual(len(records), 0)

        # Missing child without _parent_store
        category = self.env['res.partner.category']
        self.patch(self.env.registry['res.partner.category'], '_parent_store', False)
        records = category.search([('parent_id', 'child_of', 999999999)])
        self.assertEqual(len(records), 0)

    def test_duplicate_children_01(self):
        """ Duplicate the children then reassign them to the new parent (1st method). """
        new_cat1 = self.cat1.copy()
        new_cat2 = self.cat2.copy()
        new_cat0 = self.cat0.copy({'child_ids': []})
        (new_cat1 + new_cat2).write({'parent_id': new_cat0.id})
        new_struct = new_cat0.search([('parent_id', 'child_of', new_cat0.id)])
        self.assertEqual(len(new_struct), 4, "After duplication, the new object must have the childs records")
        old_struct = new_cat0.search([('parent_id', 'child_of', self.cat0.id)])
        self.assertEqual(len(old_struct), 4, "After duplication, previous record must have old childs records only")
        self.assertFalse(new_struct & old_struct, "After duplication, nodes should not be mixed")

    def test_duplicate_children_02(self):
        """ Duplicate the children then reassign them to the new parent (2nd method). """
        new_cat1 = self.cat1.copy()
        new_cat2 = self.cat2.copy()
        new_cat0 = self.cat0.copy({'child_ids': [Command.set((new_cat1 + new_cat2).ids)]})
        new_struct = new_cat0.search([('parent_id', 'child_of', new_cat0.id)])
        self.assertEqual(len(new_struct), 4, "After duplication, the new object must have the childs records")
        old_struct = new_cat0.search([('parent_id', 'child_of', self.cat0.id)])
        self.assertEqual(len(old_struct), 4, "After duplication, previous record must have old childs records only")
        self.assertFalse(new_struct & old_struct, "After duplication, nodes should not be mixed")

    def test_duplicate_children_03(self):
        """ Duplicate the children then reassign them to the new parent (3rd method). """
        new_cat1 = self.cat1.copy()
        new_cat2 = self.cat2.copy()
        new_cat0 = self.cat0.copy({'child_ids': []})
        new_cat0.write({'child_ids': [Command.link(new_cat1.id), Command.link(new_cat2.id)]})
        new_struct = new_cat0.search([('parent_id', 'child_of', new_cat0.id)])
        self.assertEqual(len(new_struct), 4, "After duplication, the new object must have the childs records")
        old_struct = new_cat0.search([('parent_id', 'child_of', self.cat0.id)])
        self.assertEqual(len(old_struct), 4, "After duplication, previous record must have old childs records only")
        self.assertFalse(new_struct & old_struct, "After duplication, nodes should not be mixed")


@tagged('-at_install', 'post_install', 'deprecation')
class TestModelDeprecations(TransactionCase):

    def test_model_attributes(self):
        for model_name, Model in self.registry.items():
            for attr in DEPRECATED_MODEL_ATTRIBUTES:
                with self.subTest(model=model_name, attr=attr):
                    value = getattr(Model, attr, None)
                    if value is None:
                        continue
                    msg = f"Deprecated method/attribute {model_name}.{attr}"
                    module = inspect.getmodule(value)
                    if module:
                        msg += f" in {module}"
                    self.fail(msg)

    def test_name_get(self):
        for model_name, Model in self.registry.items():
            with self.subTest(model=model_name):
                if not hasattr(Model, 'name_get'):
                    continue
                module = inspect.getmodule(Model.name_get)
                self.fail(f"Deprecated name_get method found on {model_name} in {module.__name__}, you should override `_compute_display_name` instead")
