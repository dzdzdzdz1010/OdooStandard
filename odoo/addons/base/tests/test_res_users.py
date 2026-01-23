# Part of Odoo. See LICENSE file for full copyright and licensing details.

from types import SimpleNamespace
from unittest.mock import patch

from odoo.api import SUPERUSER_ID
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command
from odoo.http.requestlib import _request_stack
from odoo.tests import (
    Form,
    HttpCase,
    TransactionCase,
    freeze_time,
    new_test_user,
    tagged,
    users,
    warmup,
)
from odoo.tools import mute_logger


class UsersCommonCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        users = cls.env['res.users'].create([
            {
                'name': 'Internal',
                'login': 'user_internal',
                'password': 'password',
                'group_ids': [cls.env.ref('base.group_user').id],
                'tz': 'UTC',
            },
            {
                'name': 'Portal 1',
                'login': 'portal_1',
                'password': 'portal_1',
                'group_ids': [cls.env.ref('base.group_portal').id],
            },
            {
                'name': 'Portal 2',
                'login': 'portal_2',
                'password': 'portal_2',
                'group_ids': [cls.env.ref('base.group_portal').id],
            },
        ])

        cls.user_internal, cls.user_portal_1, cls.user_portal_2 = users

        # Remove from the cache the values filled with admin rights for the users/partners that have just been created
        # So unit tests reading/writing these partners/users
        # as other low-privileged users do not have their cache polluted with values fetched with admin rights
        users.partner_id.invalidate_recordset()
        users.invalidate_recordset()


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestUsers(UsersCommonCase):

    def test_name_search(self):
        """ Check name_search on user. """
        User = self.env['res.users']

        test_user = User.create({'name': 'Flad the Impaler', 'login': 'vlad'})
        like_user = User.create({'name': 'Wlad the Impaler', 'login': 'vladi'})
        other_user = User.create({'name': 'Nothing similar', 'login': 'nothing similar'})
        all_users = test_user | like_user | other_user

        res = User.name_search('vlad', operator='ilike')
        self.assertEqual(User.browse(i[0] for i in res) & all_users, test_user)

        res = User.name_search('vlad', operator='not ilike')
        self.assertEqual(User.browse(i[0] for i in res) & all_users, all_users)

        res = User.name_search('', operator='ilike')
        self.assertEqual(User.browse(i[0] for i in res) & all_users, all_users)

        res = User.name_search('', operator='not ilike')
        self.assertEqual(User.browse(i[0] for i in res) & all_users, User)

        res = User.name_search('lad', operator='ilike')
        self.assertEqual(User.browse(i[0] for i in res) & all_users, test_user | like_user)

        res = User.name_search('lad', operator='not ilike')
        self.assertEqual(User.browse(i[0] for i in res) & all_users, other_user)

    def test_user_partner(self):
        """ Check that the user partner is well created """

        User = self.env['res.users']
        Partner = self.env['res.partner']
        Company = self.env['res.company']

        company_1 = Company.create({'name': 'company_1'})
        company_2 = Company.create({'name': 'company_2'})

        partner = Partner.create({
            'name': 'Bob Partner',
            'company_id': company_2.id
        })

        # case 1 : the user has no partner
        test_user = User.create({
            'name': 'John Smith',
            'login': 'jsmith',
            'company_ids': [company_1.id],
            'company_id': company_1.id
        })

        self.assertFalse(
            test_user.partner_id.company_id,
            "The partner_id linked to a user should be created without any company_id")

        # case 2 : the user has a partner
        test_user = User.create({
            'name': 'Bob Smith',
            'login': 'bsmith',
            'company_ids': [company_1.id],
            'company_id': company_1.id,
            'partner_id': partner.id
        })

        self.assertEqual(
            test_user.partner_id.company_id,
            company_1,
            "If the partner_id of a user has already a company, it is replaced by the user company"
        )


    def test_change_user_company(self):
        """ Check the partner company update when the user company is changed """

        User = self.env['res.users']
        Company = self.env['res.company']

        test_user = User.create({'name': 'John Smith', 'login': 'jsmith'})
        company_1 = Company.create({'name': 'company_1'})
        company_2 = Company.create({'name': 'company_2'})

        test_user.company_ids += company_1
        test_user.company_ids += company_2

        # 1: the partner has no company_id, no modification
        test_user.write({
            'company_id': company_1.id
        })

        self.assertFalse(
            test_user.partner_id.company_id,
            "On user company change, if its partner_id has no company_id,"
            "the company_id of the partner_id shall NOT be updated")

        # 2: the partner has a company_id different from the new one, update it
        test_user.partner_id.write({
            'company_id': company_1.id
        })

        test_user.write({
            'company_id': company_2.id
        })

        self.assertEqual(
            test_user.partner_id.company_id,
            company_2,
            "On user company change, if its partner_id has already a company_id,"
            "the company_id of the partner_id shall be updated"
        )

    @mute_logger('odoo.sql_db')
    def test_deactivate_portal_users_access(self):
        """Test that only a portal users can deactivate his account."""
        with self.assertRaises(UserError, msg='Internal users should not be able to deactivate their account'):
            self.user_internal._deactivate_portal_user()

    @mute_logger('odoo.sql_db', 'odoo.addons.base.models.res_users_deletion')
    def test_deactivate_portal_users_archive_and_remove(self):
        """Test that if the account can not be removed, it's archived instead
        and sensitive information are removed.

        In this test, the deletion of "portal_user" will succeed,
        but the deletion of "portal_user_2" will fail.
        """
        User = self.env['res.users']
        portal_user = User.create({
            'name': 'Portal',
            'login': 'portal_user',
            'password': 'password',
            'group_ids': [self.env.ref('base.group_portal').id],
        })
        portal_partner = portal_user.partner_id

        portal_user_2 = User.create({
            'name': 'Portal',
            'login': 'portal_user_2',
            'password': 'password',
            'group_ids': [self.env.ref('base.group_portal').id],
        })
        portal_partner_2 = portal_user_2.partner_id

        (portal_user | portal_user_2)._deactivate_portal_user()

        self.assertTrue(portal_user.exists() and not portal_user.active, 'Should have archived the user 1')

        self.assertEqual(portal_user.name, 'Portal', 'Should have kept the user name')
        self.assertEqual(portal_user.partner_id.name, 'Portal', 'Should have kept the partner name')
        self.assertNotEqual(portal_user.login, 'portal_user', 'Should have removed the user login')

        asked_deletion_1 = self.env['res.users.deletion'].search([('user_id', '=', portal_user.id)])
        asked_deletion_2 = self.env['res.users.deletion'].search([('user_id', '=', portal_user_2.id)])

        self.assertTrue(asked_deletion_1, 'Should have added the user 1 in the deletion queue')
        self.assertTrue(asked_deletion_2, 'Should have added the user 2 in the deletion queue')

        # The deletion will fail for "portal_user_2",
        # because of the absence of "ondelete=cascade"
        self.cron = self.env['ir.cron'].create({
            'name': 'Test Cron',
            'user_id': portal_user_2.id,
            'model_id': self.env.ref('base.model_res_partner').id,
        })

        with self.enter_registry_test_mode():
            self.env.ref('base.ir_cron_res_users_deletion').method_direct_trigger()

        self.assertFalse(portal_user.exists(), 'Should have removed the user')
        self.assertFalse(portal_partner.exists(), 'Should have removed the partner')
        self.assertEqual(asked_deletion_1.state, 'done', 'Should have marked the deletion as done')

        self.assertTrue(portal_user_2.exists(), 'Should have kept the user')
        self.assertTrue(portal_partner_2.exists(), 'Should have kept the partner')
        self.assertEqual(asked_deletion_2.state, 'fail', 'Should have marked the deletion as failed')

    def test_delete_public_user(self):
        """Test that the public user cannot be deleted."""
        public_user = self.env.ref('base.public_user')
        public_partner = public_user.partner_id

        # Attempt to delete the public user
        with self.assertRaises(UserError, msg="Public user should not be deletable"):
            public_user.unlink()

        # Ensure the public user still exists and is inactive
        self.assertTrue(public_user.exists() and not public_user.active, "Public user should still exist and be inactive")
        self.assertTrue(public_partner.exists() and not public_partner.active, "Public partner should still exist and be inactive")

    def test_user_home_action_restriction(self):
        test_user = new_test_user(self.env, 'hello world')

        # Find an action that contains restricted context ('active_id')
        restricted_action = self.env['ir.actions.act_window'].search([('context', 'ilike', 'active_id')], limit=1)
        with self.assertRaises(ValidationError):
            test_user.action_id = restricted_action.id

        # Find an action without restricted context
        allowed_action = self.env['ir.actions.act_window'].search(['!', ('context', 'ilike', 'active_id')], limit=1)

        test_user.action_id = allowed_action.id
        self.assertEqual(test_user.action_id.id, allowed_action.id)

    def test_context_get_lang(self):
        self.env['res.lang'].with_context(active_test=False).search([
            ('code', 'in', ['fr_FR', 'es_ES', 'de_DE', 'en_US'])
        ]).write({'active': True})

        user = new_test_user(self.env, 'jackoneill')
        user = user.with_user(user)
        user.lang = 'fr_FR'

        company = user.company_id.partner_id.sudo()
        company.lang = 'de_DE'

        request = SimpleNamespace()
        request.best_lang = 'es_ES'
        request_patch = patch('odoo.addons.base.models.res_users.request', request)
        self.addCleanup(request_patch.stop)
        request_patch.start()

        self.assertEqual(user.context_get()['lang'], 'fr_FR')
        self.env.registry.clear_cache()
        user.lang = False

        self.assertEqual(user.context_get()['lang'], 'es_ES')
        self.env.registry.clear_cache()
        request_patch.stop()

        self.assertEqual(user.context_get()['lang'], 'de_DE')
        self.env.registry.clear_cache()
        company.lang = False

        self.assertEqual(user.context_get()['lang'], 'en_US')

    def test_user_self_update(self):
        """ Check that the user has access to write his phone. """
        test_user = self.env['res.users'].create({'name': 'John Smith', 'login': 'jsmith'})
        self.assertFalse(test_user.phone)
        test_user.with_user(test_user).write({'phone': '2387478'})

        self.assertEqual(
            test_user.partner_id.phone,
            '2387478',
            "The phone of the partner_id shall be updated."
        )

    def test_session_non_existing_user(self):
        """
        Test to check the invalidation of session bound to non existing (or deleted) users.
        """
        User = self.env['res.users']
        last_user_id = User.with_context(active_test=False).search([], limit=1, order="id desc")
        non_existing_user = User.browse(last_user_id.id + 1)
        self.assertFalse(non_existing_user._compute_session_token('session_id'))


@tagged('post_install', '-at_install', 'groups')
class TestUsers2(UsersCommonCase):

    def test_change_user_login(self):
        """ Check that partner email is updated when changing user's login """

        User = self.env['res.users']
        with Form(User, view='base.view_users_simple_form') as UserForm:
            UserForm.name = "Test User"
            UserForm.login = "test-user1"
            self.assertFalse(UserForm.email)

            UserForm.login = "test-user1@mycompany.example.org"
            self.assertEqual(
                UserForm.email, "test-user1@mycompany.example.org",
                "Setting a valid email as login should update the partner's email"
            )

    def test_default_groups(self):
        """ The groups handler doesn't use the "real" view with pseudo-fields
        during installation, so it always works (because it uses the normal
        group_ids field).
        """
        default_group = self.env.ref('base.default_user_group')
        test_group = self.env['res.groups'].create({'name': 'test_group'})
        default_group.implied_ids = test_group

        # use the specific views which has the pseudo-fields
        f = Form(self.env['res.users'], view='base.view_users_form')
        f.name = "bob"
        f.login = "bob"
        user = f.save()

        group_user = self.env.ref('base.group_user')

        self.assertIn(group_user, user.group_ids)
        self.assertEqual(default_group.implied_ids + group_user, user.group_ids)

    def test_selection_groups(self):
        # create 3 groups that should be in a selection
        app = self.env['res.groups.privilege'].create({'name': 'Foo'})
        group_user, group_manager, group_visitor = self.env['res.groups'].create([
            {'name': name, 'privilege_id': app.id}
            for name in ('User', 'Manager', 'Visitor')
        ])
        # THIS PART IS NECESSARY TO REPRODUCE AN ISSUE: group1.id < group2.id < group0.id
        self.assertLess(group_user.id, group_manager.id)
        self.assertLess(group_manager.id, group_visitor.id)
        # implication order is group0 < group1 < group2
        group_manager.implied_ids = group_user
        group_user.implied_ids = group_visitor
        groups = group_visitor + group_user + group_manager

        # create a user
        user = self.env['res.users'].create({'name': 'foo', 'login': 'foo'})

        # put user in group_visitor, and check field value
        user.write({'group_ids': [Command.set([group_visitor.id])]})
        self.assertEqual(user.group_ids & groups, group_visitor)
        self.assertEqual(user.all_group_ids & groups, group_visitor)
        self.assertEqual(user.read(['group_ids'])[0]['group_ids'], [group_visitor.id])
        self.assertEqual(user.read(['all_group_ids'])[0]['all_group_ids'], [group_visitor.id])

        # remove group_visitor
        user.write({'group_ids': [Command.unlink(group_visitor.id)]})
        self.assertEqual(user.group_ids & groups, self.env['res.groups'])

        # put user in group_manager, and check field value
        user.write({'group_ids': [Command.set([group_manager.id])]})
        self.assertEqual(user.group_ids & groups, group_manager)
        self.assertEqual(user.all_group_ids & groups, group_visitor + group_manager + group_user)
        self.assertEqual(user.read(['group_ids'])[0]['group_ids'], [group_manager.id])
        self.assertEqual(set(user.read(['all_group_ids'])[0]['all_group_ids']), set((group_visitor + group_manager + group_user).ids))

        # add user in group_user, and check field value
        user.write({'group_ids': [Command.link(group_user.id)]})
        self.assertEqual(user.group_ids & groups, group_manager + group_user)
        self.assertEqual(user.all_group_ids & groups, group_visitor + group_manager + group_user)
        self.assertEqual(set(user.read(['group_ids'])[0]['group_ids']), set((group_manager + group_user).ids))
        self.assertEqual(set(user.read(['all_group_ids'])[0]['all_group_ids']), set((group_visitor + group_manager + group_user).ids))

        groups = self.env['res.groups'].search([('all_user_ids', '=', user.id)])
        self.assertEqual(groups, user.all_group_ids)

    def test_implied_groups_on_change(self):
        """Test that a change on a reified fields trigger the onchange of group_ids."""
        group_public = self.env.ref('base.group_public')
        group_portal = self.env.ref('base.group_portal')
        group_user = self.env.ref('base.group_user')

        app = self.env['res.groups.privilege'].create({'name': 'Foo'})
        group_contain_user = self.env['res.groups'].create({
            'name': 'Small user group',
            'privilege_id': app.id,
            'implied_ids': [group_user.id],
        })

        user_form = Form(self.env['res.users'], view='base.view_users_form')
        user_form.name = "Test"
        user_form.login = "Test"
        self.assertFalse(user_form.share)

        user_form['group_ids'] = group_portal
        self.assertTrue(user_form.share, 'The group_ids onchange should have been triggered')

        user = user_form.save()

        # in debug mode, show the group widget for external user

        with self.debug_mode():
            user_form = Form(user, view='base.view_users_form')

            user_form['group_ids'] = group_user
            self.assertFalse(user_form.share, 'The group_ids onchange should have been triggered')

            user_form['group_ids'] = group_public
            self.assertTrue(user_form.share, 'The group_ids onchange should have been triggered')

            user_form['group_ids'] = group_user
            user_form['group_ids'] = group_user + group_contain_user

            user_form.save()

        # in debug mode, allow extra groups

        with self.debug_mode():
            user_form = Form(self.env['res.users'], view='base.view_users_form')
            user_form.name = "Test-2"
            user_form.login = "Test-2"

            user_form['group_ids'] = group_portal
            self.assertTrue(user_form.share)

            # for portal user, the view_group_extra_ids is only show in debug mode
            user_form['group_ids'] = group_portal + group_contain_user
            self.assertFalse(user_form.share, 'The group_ids onchange should have been triggered')

            with self.assertRaises(ValidationError, msg="The user cannot be at the same time in groups: ['Membre', 'Portal', 'Foo / Small user group']"):
                user_form.save()

    def test_view_group_hierarchy(self):
        """Test that the group hierarchy shows up in the correct language of the user."""
        self.env['res.lang']._activate_lang('fr_FR')
        group_system = self.env.ref('base.group_system')
        group_system.with_context(lang='fr_FR').name = 'Administrateur'

        view_group_hierarchy_en = self.env['res.groups']._get_view_group_hierarchy()
        view_group_hierarchy_fr = self.env['res.groups'].with_context(lang='fr_FR')._get_view_group_hierarchy()
        self.assertNotEqual(view_group_hierarchy_en['groups'][group_system.id]['name'], 'Administrateur')
        self.assertEqual(view_group_hierarchy_fr['groups'][group_system.id]['name'], 'Administrateur')

        # Should work the other way around too
        self.env.registry.clear_cache('groups')
        view_group_hierarchy_fr = self.env['res.groups'].with_context(lang='fr_FR')._get_view_group_hierarchy()
        view_group_hierarchy_en = self.env['res.groups']._get_view_group_hierarchy()
        self.assertNotEqual(view_group_hierarchy_en['groups'][group_system.id]['name'], 'Administrateur')
        self.assertEqual(view_group_hierarchy_fr['groups'][group_system.id]['name'], 'Administrateur')

        with patch('odoo.addons.base.models.res_groups.ResGroups._get_view_group_hierarchy') as mock:
            self.user_portal_1.copy_data()
            self.assertFalse(mock.called)

    @users('user_internal', 'portal_1')
    @mute_logger('odoo.addons.base.models.ir_model')
    def test_user_writeable_fields(self):
        """ Check for writeable fields.

        Check that a normal user: can write only on user_writeable fields.
        Check that a portal user: cannot write on themselves.
        """
        self.assertIn(
            "post_install",
            self.test_tags,
            "This test **must** be `post_install` to ensure the expected behavior despite other modules",
        )
        user_writeable_fields = [
            name
            for name, field in self.env["res.users"]._fields.items()
            if getattr(field, 'user_writeable', False)
        ]
        self.assertIn(
            "email",
            user_writeable_fields,
            "For this test to make sense, 'email' must be `user_writeable`",
        )
        self.assertNotIn(
            "login",
            user_writeable_fields,
            "For this test to make sense, 'login' must not be `user_writeable`",
        )

        me = self.env.user.with_env(self.env)
        other = self.user_portal_2.with_env(self.env)

        # Allow to write a field in the user_writeable_fields for internal users
        # only
        if self.env.user._has_group('base.group_user'):
            me.email = "foo@bar.com"
            self.assertEqual(me.email, "foo@bar.com")
        else:
            with self.assertRaises(AccessError):
                me.email = "foo@bar.com"
        # Disallow to write a field not in the user_writeable_fields
        with self.assertRaises(AccessError):
            me.login = "foo"

        # Disallow to write a field in the user_writeable_fields on another user
        with self.assertRaises(AccessError):
            other.email = "foo@bar.com"
        # Disallow to write a field not in the user_writeable_fields on another user
        with self.assertRaises(AccessError):
            other.login = "foo"

    @warmup
    def test_write_group_ids_performance(self):
        contact_creation_group = self.env.ref("base.group_partner_manager")
        self.assertNotIn(contact_creation_group, self.user_internal.group_ids)

        # all modules: 23, base: 10; nightly: +1
        with self.assertQueryCount(24):
            self.user_internal.write({
                "group_ids": [Command.link(contact_creation_group.id)],
            })

    def test_portal_user_manager_access(self):
        # groups
        group_portal = self.env.ref('base.group_portal')
        group_user = self.env.ref('base.group_user')
        group_partner_manager = self.env.ref('base.group_partner_manager')
        group_portal_user_manager = self.env['res.groups'].create({
            'name': 'Portal User Manager',
            'user_ids': [],
        })

        # ACL
        self.env['ir.model.access'].create({
            'name': 'Allow user profile update',
            'model_id': self.env['ir.model']._get('res.users').id,
            'group_id': group_portal_user_manager.id,
            'perm_write': True,
        })

        # Rules
        self.env['ir.rule'].create({
            'name': 'Allow updates by Portal Managers on PORTAL users (only)',
            'model_id': self.env['ir.model']._get('res.users').id,
            'groups': [group_portal_user_manager.id],
            'domain_force': [('share', '=', True)],
            'perm_write': True,
        })

        # Users
        portal_user_manager = self.env['res.users'].create({
            'name': 'Portal User Manager',
            'login': 'maintainer',
            'password': 'password',
            'group_ids': [group_user.id, group_partner_manager.id, group_portal_user_manager.id],
        })
        user = self.env['res.users'].create({
            'name': 'User',
            'login': 'user_',
            'password': 'password',
            'group_ids': [group_user.id, group_partner_manager.id],
        })
        portal = self.env['res.users'].create({
            'name': 'Portal',
            'login': 'portal_',
            'password': 'password',
            'group_ids': [group_portal.id],
        })

        # A UPM cannot update the user profile of another USER
        with self.assertRaises(AccessError):
            user.with_user(portal_user_manager).write({
                'name': 'New name for you'
            })
        # A UPM can update the user profile of a PORTAL user
        portal.with_user(portal_user_manager).write({
            'name': 'New name for you'
        })

        # A UPM cannot update the partner profile of another USER
        with self.assertRaises(AccessError):
            user.partner_id.with_user(portal_user_manager).write({
                'name': 'New name for you'
            })
        # A UPM can update the partner profile of a PORTAL user
        portal.partner_id.with_user(portal_user_manager).write({
            'name': 'New name for you'
        })

        # A USER cannot update the user profile of another USER
        with self.assertRaises(AccessError):
            self.user_internal.with_user(user).write({
                'name': 'New name for you'
            })
        # A USER cannot update the user profile of a PORTAL user
        with self.assertRaises(AccessError):
            portal.with_user(user).write({
                'name': 'New name for you'
            })

        # A USER cannot update the partner profile of another USER
        with self.assertRaises(AccessError):
            self.user_internal.partner_id.with_user(user).write({
                'name': 'New name for you'
            })
        # A USER can update the partner profile of a PORTAL user
        portal.partner_id.with_user(user).write({
            'name': 'New name for you'
        })


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestUsersTweaks(TransactionCase):
    def test_superuser(self):
        """ The superuser is inactive and must remain as such. """
        user = self.env['res.users'].browse(SUPERUSER_ID)
        self.assertFalse(user.active)
        with self.assertRaises(UserError):
            user.write({'active': True})


@tagged('post_install', '-at_install')
class TestUsersIdentitycheck(HttpCase):

    def _rpc(self, model, method, *args, **kwargs):
        return self.url_open(
            "/web/dataset/call_kw", json={"params": {"model": model, "method": method, "args": args, "kwargs": kwargs}}
        ).json()

    def test_change_password(self):
        """Test that the change of users' password is correctly done and allowed by an identity check."""
        user_internal = self.env['res.users'].create({
            'name': 'Internal',
            'login': 'user_internal',
            'password': 'oldpassword',
            'group_ids': [self.env.ref('base.group_user').id],
        })
        user_admin = self.env.ref('base.user_admin')
        self.authenticate(user_admin.login, user_admin.password)

        with freeze_time('2025-10-14 00:00:00'):
            # Check that an identity check is triggered when clicking the "Change Password" button in the user form of user_internal.
            wizard_action_result = self._rpc('res.users', 'action_change_password_wizard', user_internal.id)['result']
            self.assertEqual(wizard_action_result['res_model'], 'res.users.identitycheck')
            identitycheck_result = self._rpc(
                wizard_action_result['res_model'],
                'run_check',
                wizard_action_result['res_id'],
                context={'password': user_admin.login}
            )['result']

        # Wait 10 minutes that the first identity check, triggered at the opening of the form, expire before the submission
        # to ensure that an identity check protect the method changing the passwords.
        with freeze_time('2025-10-14 00:10:00'):
            wizard_id = self._rpc(identitycheck_result['res_model'], 'create', {}, context=identitycheck_result['context'])['result']
            self.env['change.password.user'].search([('wizard_id', '=', wizard_id), ('user_id', '=', user_internal.id)]).write({'new_passwd': 'newpassword'})
            change_password_result = self._rpc(identitycheck_result['res_model'], 'change_password_button', wizard_id)['result']
            self.assertEqual(change_password_result['res_model'], 'res.users.identitycheck')
            self._rpc(
                change_password_result['res_model'],
                'run_check',
                change_password_result['res_id'],
                context={'password': user_admin.login}
            )['result']

        # To check that the password of user_internal has been modified.
        self.env['res.users'].with_user(user_internal)._check_credentials(
            {'login': 'user_internal', 'password': 'newpassword', 'type': 'password'},
            {'interactive': False}
        )

    @users('admin')
    def test_revoke_all_devices(self):
        """
        Test to check the revoke all devices by changing the current password as a new password
        """
        # Change the password to 8 characters for security reasons
        self.env.user.password = "admin@odoo"

        # Create a first session that will be used to revoke other sessions
        session = self.authenticate('admin', 'admin@odoo')

        # Create a second session that will be used to check it has been revoked
        self.authenticate('admin', 'admin@odoo')
        # Test the session is valid
        # Valid session -> not redirected from /web to /web/login
        self.assertTrue(self.url_open('/web').url.endswith('/web'))

        # Push a fake request to the request stack, because @check_identity requires a request.
        # Use the first session created above, used to invalid other sessions than itself.
        _request_stack.push(SimpleNamespace(session=session, env=self.env))
        self.addCleanup(_request_stack.pop)
        # The user clicks the button logout from all devices from his profile
        action = self.env.user.action_revoke_all_devices()
        # The form of the check identity wizard opens
        form = Form(self.env[action['res_model']].browse(action['res_id']), action.get('view_id'))
        # The user fills his password
        form.password = 'admin@odoo'
        # The user clicks the button "Log out from all devices", which triggers a save then a call to the button method
        user_identity_check = form.save()
        action = user_identity_check.with_context(password=form.password).run_check()

        # Test the session is no longer valid
        # Invalid session -> redirected from /web to /web/login
        self.assertTrue(self.url_open('/web').url.endswith('/web/login?redirect=%2Fweb%3F'))

        # In addition, the password must have been emptied from the wizard
        self.assertFalse(user_identity_check.password)


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestHasGroup(TransactionCase):
    def setUp(self):
        super().setUp()

        self.group0 = 'test_user_has_group.group0'
        self.group1 = 'test_user_has_group.group1'
        group0, _group1 = self.env['res.groups']._load_records([
            dict(xml_id=self.group0, values={'name': 'group0'}),
            dict(xml_id=self.group1, values={'name': 'group1'}),
        ])

        self.test_user = self.env['res.users'].create({
            'login': 'testuser',
            'partner_id': self.env['res.partner'].create({
                'name': "Strawman Test User"
            }).id,
            'group_ids': [Command.set([group0.id])]
        })

        self.grp_internal_xml_id = 'base.group_user'
        self.grp_internal = self.env.ref(self.grp_internal_xml_id)
        self.grp_portal_xml_id = 'base.group_portal'
        self.grp_portal = self.env.ref(self.grp_portal_xml_id)
        self.grp_public_xml_id = 'base.group_public'
        self.grp_public = self.env.ref(self.grp_public_xml_id)
        self.grp_everyone_xml_id = 'base.group_everyone'
        self.grp_everyone = self.env.ref(self.grp_everyone_xml_id)

    def test_env_uid(self):
        Partner = self.env['res.partner'].with_user(self.test_user)
        self.assertTrue(
            Partner.env.user.has_group(self.group0),
            "the test user should belong to group0"
        )
        self.assertFalse(
            Partner.env.user.has_group(self.group1),
            "the test user should *not* belong to group1"
        )

    def test_record(self):
        self.assertTrue(
            self.test_user.has_group(self.group0),
            "the test user should belong to group0",
        )
        self.assertFalse(
            self.test_user.has_group(self.group1),
            "the test user shoudl not belong to group1"
        )

    def test_other_user(self):
        internal_user = self.test_user.copy({'group_ids': self.grp_internal})
        internal_user = internal_user.with_user(internal_user)
        test_user = self.env['res.users'].with_user(self.test_user).browse(self.test_user.id)

        test_user.has_group(self.group0)
        with self.assertRaises(AccessError):
            test_user.browse(internal_user.id).has_group(self.group0)
        test_user.sudo().browse(internal_user.id).has_group(self.group0)

        internal_user.has_group(self.group0)
        internal_user.browse(test_user.id).has_group(self.group0)

    def test_portal_creation(self):
        """Here we check that portal user creation fails if it tries to create a user
           who would also have group_user by implied_group.
           Otherwise, it succeeds with the groups we asked for.
        """
        grp_test_portal_xml_id = 'test_user_has_group.portal_implied_group'
        grp_test_portal = self.env['res.groups']._load_records([
            dict(xml_id=grp_test_portal_xml_id, values={'name': 'Test Group Portal'})
        ])
        grp_test_internal1 = self.env['res.groups']._load_records([
            dict(xml_id='test_user_has_group.internal_implied_group1', values={'name': 'Test Group Itnernal 1'})
        ])
        grp_test_internal2_xml_id = 'test_user_has_group.internal_implied_group2'
        grp_test_internal2 = self.env['res.groups']._load_records([
            dict(xml_id=grp_test_internal2_xml_id, values={'name': 'Test Group Internal 2'})
        ])

        self.grp_portal.implied_ids = grp_test_portal

        grp_test_internal1.implied_ids = False
        grp_test_internal2.implied_ids = False

        portal_user = self.env['res.users'].create({
            'login': 'portalTest',
            'name': 'Portal test',
            'group_ids': [self.grp_portal.id, grp_test_internal2.id],
        })

        self.assertTrue(
            portal_user.has_group(self.grp_portal_xml_id),
            "The portal user should belong to '%s'" % self.grp_portal_xml_id,
        )
        self.assertTrue(
            portal_user.has_group(grp_test_portal_xml_id),
            "The portal user should belong to '%s'" % grp_test_portal_xml_id,
        )
        self.assertTrue(
            portal_user.has_group(grp_test_internal2_xml_id),
            "The portal user should belong to '%s'" % grp_test_internal2_xml_id
        )
        self.assertFalse(
            portal_user.has_group(self.grp_internal_xml_id),
            "The portal user should not belong to '%s'" % self.grp_internal_xml_id
        )

        portal_user.unlink()  # otherwise, badly modifying the implication would raise

        grp_test_internal1.implied_ids = self.grp_internal
        grp_test_internal2.implied_ids = self.grp_internal

        with self.assertRaises(ValidationError): # current group implications forbid to create a portal user
            portal_user = self.env['res.users'].create({
                'login': 'portalFail',
                'name': 'Portal fail',
                'group_ids': [self.grp_portal.id, grp_test_internal2.id],
            })

    def test_portal_write(self):
        """Check that adding a new group to a portal user works as expected,
           except if it implies group_user/public, in chich case it should raise.
        """
        grp_test_portal = self.env["res.groups"].create({"name": "implied by portal"})
        self.grp_portal.implied_ids = grp_test_portal

        portal_user = self.env['res.users'].create({
            'login': 'portalTest2',
            'name': 'Portal test 2',
            'group_ids': [Command.set([self.grp_portal.id])],
            })

        self.assertEqual(portal_user.group_ids, self.grp_portal)
        self.assertEqual(
            portal_user.all_group_ids, (self.grp_portal + grp_test_portal),
            "The portal user should have the implied group.",
        )

        grp_fail = self.env["res.groups"].create(
            {"name": "fail", "implied_ids": [Command.set([self.grp_internal.id])]})

        with self.assertRaises(ValidationError):
            portal_user.write({'group_ids': [Command.link(grp_fail.id)]})

    def test_two_user_types(self):
        #Create a user with two groups of user types kind (Internal and Portal)
        grp_test = self.env['res.groups']._load_records([
            dict(xml_id='test_two_user_types.implied_groups', values={'name': 'Test Group'})
        ])
        grp_test.implied_ids += self.grp_internal

        with self.assertRaises(ValidationError):
            self.env['res.users'].create({
                'login': 'test_two_user_types',
                'name': "Test User with two user types",
                'group_ids': [Command.set([grp_test.id, self.grp_portal.id])]
            })

        #Add a user with portal to the group Internal
        test_user = self.env['res.users'].create({
                'login': 'test_user_portal',
                'name': "Test User with two user types",
                'group_ids': [Command.set([self.grp_portal.id])]
             })
        with self.assertRaises(ValidationError):
            self.grp_internal.user_ids = [Command.link(test_user.id)]

    def test_two_user_types_implied_groups(self):
        """Contrarily to test_two_user_types, we simply add an implied_id to a group.
           This will trigger the addition of the relevant users to the relevant groups;
           if, say, this was done in SQL and thus bypassing the ORM, it would bypass the constraints
           and field recomputations, and thus give us a case uncovered by the aforementioned test.
        """
        grp_test = self.env["res.groups"].create(
            {"name": "test", "implied_ids": [Command.set([self.grp_internal.id])]})

        test_user = self.env['res.users'].create({
            'login': 'test_user_portal',
            'name': "Test User with one user types",
            'group_ids': [Command.set([grp_test.id])]
        })

        with self.assertRaises(ValidationError, msg="Test user belongs to two user types."):
            grp_test.write({'implied_ids': [Command.link(self.grp_portal.id)]})

        self.env["ir.model.fields"].create(
            {
                "name": "x_group_names",
                "model_id": self.env.ref("base.model_res_users").id,
                "state": "manual",
                "field_description": "A computed field that depends on all_group_ids",
                "compute": "for r in self: r['x_group_names'] = ', '.join(r.all_group_ids.mapped('name'))",
                "depends": "all_group_ids",
                "store": True,
                "ttype": "char",
            }
        )
        self.env["ir.model.fields"].create(
            {
                "name": "x_user_names",
                "model_id": self.env.ref("base.model_res_groups").id,
                "state": "manual",
                "field_description": "A computed field that depends on users",
                "compute": "for r in self: r['x_user_names'] = ', '.join(r.all_user_ids.mapped('name'))",
                "depends": "all_user_ids",
                "store": True,
                "ttype": "char",
            }
        )

        grp_additional = self.env["res.groups"].create({"name": "additional"})
        grp_test.write({'implied_ids': [Command.link(grp_additional.id)]})

        self.assertIn(grp_additional.name, test_user.x_group_names)
        self.assertIn(test_user.name, grp_additional.x_user_names)

    def test_demote_user(self):
        """When a user is demoted to the status of portal/public,
           we should strip him of all his (previous) rights
        """
        group_0 = self.env.ref(self.group0)  # the group to which test_user already belongs
        group_U = self.env["res.groups"].create({"name": "U", "implied_ids": [Command.set([self.grp_internal.id])]})

        self.grp_internal.implied_ids = False  # only there to simplify the test

        self.assertEqual(self.test_user.group_ids, group_0)
        self.assertEqual(self.test_user.all_group_ids, group_0)

        self.test_user.write({'group_ids': [Command.link(group_U.id)]})

        self.assertEqual(
            self.test_user.group_ids, (group_0 + group_U),
            "We should have our 2 groups",
        )
        self.assertEqual(
            self.test_user.all_group_ids, (group_0 + group_U + self.grp_internal),
            "We should have our 2 groups and the implied user group",
        )

        with self.assertRaises(ValidationError):
            # A group may be (transitively) implying group_user or a portal, then it would raise an exception
            self.test_user.write({'group_ids': [
                Command.unlink(self.grp_internal.id),
                Command.unlink(self.grp_public.id),
                Command.link(self.grp_portal.id),
            ]})

        # Now we demote him. The JS framework sends 3 and 4 commands,
        # which is what we write here, but it should work even with a 5 command or whatever.
        self.test_user.write({'group_ids': [
            Command.unlink(group_U.id),
            Command.unlink(self.grp_public.id),
            Command.link(self.grp_portal.id),
        ]})

        # if we screw up the removing groups/adding the implied ids, we could end up in two situations:
        # 1. we have a portal user with way too much rights (e.g. 'Contact Creation', which does not imply any other group)
        # 2. a group may be (transitively) implying group_user or a portal, then it would raise an exception
        self.assertEqual(
            self.test_user.all_group_ids, (group_0 + self.grp_portal + self.grp_everyone),
            "Here the portal group does not imply any other group, so we should only have this group.",
        )

    def test_implied_groups(self):
        """ We check that the adding of implied ids works correctly for normal users and portal users.
            In the second case, working normally means raising if a group implies to give 'group_user'
            rights to a portal user.
        """
        U = self.env["res.users"]
        G = self.env["res.groups"]
        group_everyone = self.grp_everyone
        group_user = self.grp_internal
        group_portal = self.grp_portal
        group_no_one = self.env.ref('base.group_no_one')

        group_A = G.create({"name": "A"})
        group_AA = G.create({"name": "AA", "implied_ids": [Command.set([group_A.id])]})
        group_B = G.create({"name": "B"})
        group_BB = G.create({"name": "BB", "implied_ids": [Command.set([group_B.id])]})

        # user_a is a normal user, so we expect groups to be added when we add them,
        # as well as 'implied_groups'; otherwise nothing else should happen.
        # By contrast, for a portal user we want implied groups not to be added
        # if and only if it would not give group_user (or group_public) privileges
        user_a = U.create({"name": "a", "login": "a", "group_ids": [Command.set([group_AA.id, group_user.id])]})
        self.assertEqual(user_a.all_group_ids, (group_AA + group_A + group_user + group_no_one + group_everyone))
        self.assertEqual(user_a.group_ids, (group_AA + group_user))

        user_b = U.create({"name": "b", "login": "b", "group_ids": [Command.set([group_portal.id, group_AA.id])]})
        self.assertEqual(user_b.all_group_ids, (group_AA + group_A + group_portal + group_everyone))
        self.assertEqual(user_b.group_ids, (group_AA + group_portal))

        # user_b is not an internal user, but giving it a new group just added a new group
        (user_a + user_b).write({"group_ids": [Command.link(group_BB.id)]})
        self.assertEqual(user_a.all_group_ids, (group_AA + group_A + group_BB + group_B + group_user + group_no_one + group_everyone))
        self.assertEqual(user_b.all_group_ids, (group_AA + group_A + group_BB + group_B + group_portal + group_everyone))
        self.assertEqual(user_a.group_ids, (group_AA + group_BB + group_user))
        self.assertEqual(user_b.group_ids, (group_AA + group_BB + group_portal))

        # now we create a group that implies the group_user
        # adding it to a user should work normally, whereas adding it to a portal user should raise
        group_C = G.create({"name": "C", "implied_ids": [Command.set([group_user.id])]})

        user_a.write({"group_ids": [Command.link(group_C.id)]})
        self.assertEqual(user_a.all_group_ids, (group_AA + group_A + group_BB + group_B + group_C + group_user + group_no_one + group_everyone))
        self.assertEqual(user_a.group_ids, (group_AA + group_BB + group_C + group_user))

        with self.assertRaises(ValidationError):
            user_b.write({"group_ids": [Command.link(group_C.id)]})

    def test_has_group_cleared_cache_on_write(self):
        self.env.registry.clear_cache()
        self.assertFalse(self.registry._Registry__caches['default'], "Ensure ormcache is empty")

        def populate_cache():
            self.test_user.has_group('test_user_has_group.group0')
            self.assertTrue(self.registry._Registry__caches['default'], "user._has_group cache must be populated")

        populate_cache()

        self.env.ref(self.group0).write({"share": True})
        self.assertFalse(self.registry._Registry__caches['default'], "Writing on group must invalidate user._has_group cache")

        populate_cache()
        # call_cache_clearing_methods is called in res.groups.write to invalidate
        # cache before calling its parent class method (`odoo.models.Model.write`)
        # as explain in the `res.group.write` comment.
        # This verifies that calling `call_cache_clearing_methods()` invalidates
        # the ormcache of method `user._has_group()`
        self.env['ir.model.access'].call_cache_clearing_methods()
        self.assertFalse(
            self.registry._Registry__caches['default'],
            "call_cache_clearing_methods() must invalidate user._has_group cache"
        )

    def test_has_group_with_new_id(self):
        user = self.env['res.users'].new({'partner_id': self.test_user.partner_id.id})
        self.assertEqual(user.has_group(self.group0), False)
        self.assertEqual(user.has_group(self.group1), False)

        user2 = self.env['res.users'].new({'partner_id': self.test_user.partner_id.id}, origin=self.test_user)
        self.assertEqual(user2.has_group(self.group0), True)
        self.assertEqual(user2.has_group(self.group1), False)


@tagged('-at_install', 'post_install')
class TestFormCreate(TransactionCase):
    def test_create_res_users(self):
        user_form = Form(self.env['res.users'])
        user_form.login = 'a user login'
        user_form.name = 'a user name'
        user_form.save()
