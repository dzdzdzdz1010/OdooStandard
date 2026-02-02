from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user
from odoo.exceptions import UserError, AccessError
from odoo.fields import Command
from odoo.tests.common import HttpCase, JsonRpcException, users
from odoo.tools.misc import mute_logger


class TestDiscussChannelReadonly(MailCommon, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_user = mail_new_test_user(
            cls.env,
            login="test_user",
            email=False,
            groups="base.group_user",
            name="Test User",
            notification_type="inbox",
        )
        cls.test_channel = cls.env["discuss.channel"].create(
            {
                "name": "Readonly Channel",
                "channel_type": "channel",
                "is_readonly": True,
                "channel_member_ids": [
                    Command.create({
                            "partner_id": cls.test_user.partner_id.id,
                    }),
                    Command.create({
                            "partner_id": cls.partner_employee.id,
                            "channel_role": "owner",
                    }),
                ],
            }
        )

    def test_only_admin_can_set_readonly(self):
        with self.assertRaises(UserError):
            self.test_channel.with_user(self.test_user).write({"is_readonly": False})
        self.test_channel.with_user(self.user_employee).write({"is_readonly": False})
        self.assertFalse(self.test_channel.is_readonly)
        with self.assertRaises(UserError):
            self.test_channel.with_user(self.test_user).write({"is_readonly": True})
        self.test_channel.with_user(self.user_employee).write({"is_readonly": True})
        self.assertTrue(self.test_channel.is_readonly)

    @users("employee")
    def test_readonly_channel_no_join_call(self):
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request(
                "/mail/rtc/channel/join_call",
                {"channel_id": self.test_channel.id},
            )

    @users("employee")
    def test_readonly_channel_admin_can_post_comment(self):
        message = self.test_channel.message_post(
            body="Admin message in readonly channel",
            message_type="comment",
        )
        self.assertEqual(str(message.body), "<p>Admin message in readonly channel</p>")

    def test_readonly_channel_user_cannot_post_comment(self):
        with self.assertRaises(UserError):
            self.test_channel.with_user(self.test_user).message_post(
                body="User message in readonly channel",
                message_type="comment",
            )

    def test_readonly_channel_user_can_post_notification_message(self):
        self.env = self.env(user=self.test_user)
        message = self.test_channel.message_post(body="User message in readonly channel")
        self.assertEqual(str(message.body), "<p>User message in readonly channel</p>")

    def test_readonly_channel_user_can_edit_own_message(self):
        self.test_channel.is_readonly = False
        message = self.test_channel.with_user(self.test_user).message_post(
            body="Original message", message_type="comment"
        )
        self.test_channel.is_readonly = True
        self.authenticate(self.test_user.login, self.test_user.login)
        self.make_jsonrpc_request("/mail/message/update_content", {
            "message_id": message.id,
            "update_data": {"body": "<p>Edited message</p>"},
        })
        self.assertEqual(
            str(message.body), '<p>Edited message <span class="o-mail-Message-edited"></span></p>'
        )

    def test_readonly_channel_user_can_star_message(self):
        message = self.test_channel.message_post(body="Message to star")
        message.with_user(self.test_user).toggle_message_starred()
        self.assertIn(self.test_user.partner_id, message.starred_partner_ids)

    def test_readonly_channel_user_can_react(self):
        message = self.test_channel.message_post(body="Message to react")
        self.authenticate(self.test_user.login, self.test_user.login)
        self.make_jsonrpc_request(
            "/mail/message/reaction",
            {
                "message_id": message.id,
                "content": "❤️",
                "action": "add",
            },
        )
        self.assertTrue(
            message.reaction_ids.filtered(
                lambda r: r.partner_id == self.test_user.partner_id and r.content == "❤️"
            )
        )

    def test_readonly_channel_admin_can_create_subchannel(self):
        message = self.test_channel.message_post(body="Message to create subchannel")
        self.authenticate(self.user_employee.login, self.user_employee.login)
        self.make_jsonrpc_request(
            "/discuss/channel/sub_channel/create",
            {
                "parent_channel_id": self.test_channel.id,
                "from_message_id": message.id,
                "name": "Subchannel created by user",
            },
        )
        subchannel = self.env["discuss.channel"].search(
            [
                ("name", "=", "Subchannel created by user"),
                ("parent_channel_id", "=", self.test_channel.id),
                ("from_message_id", "=", message.id),
            ]
        )
        self.assertFalse(subchannel.is_readonly)

    @mute_logger("odoo.http")
    def test_readonly_channel_user_cannot_create_subchannel(self):
        message = self.test_channel.message_post(body="Message to create subchannel")
        self.authenticate(self.test_user.login, self.test_user.login)
        with self.assertRaises(JsonRpcException) as cm:
            self.make_jsonrpc_request(
                "/discuss/channel/sub_channel/create",
                {
                    "parent_channel_id": self.test_channel.id,
                    "from_message_id": message.id,
                    "name": "Subchannel created by user",
                },
            )
        self.assertTrue(cm.exception, AccessError)

    def test_readonly_channel_user_cannot_pin_message(self):
        message = self.test_channel.message_post(body="Message to pin")
        with self.assertRaises(UserError):
            self.test_channel.with_user(self.test_user).set_message_pin(message.id, True)
        self.test_channel.with_user(self.user_employee).set_message_pin(message.id, True)
        with self.assertRaises(UserError):
            self.test_channel.with_user(self.test_user).set_message_pin(message.id, False)
        self.test_channel.with_user(self.user_employee).set_message_pin(message.id, True)
