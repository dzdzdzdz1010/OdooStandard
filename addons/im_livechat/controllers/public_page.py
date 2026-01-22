# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.mail.controllers.discuss.public_page import PublicPageController


class LivechatPublicPageController(PublicPageController):
    def _response_discuss_channel_invitation(self, store, channel, guest_email=None):
        if channel.channel_type == "livechat":
            if not request.env.user._is_internal():
                raise request.not_found()
            if channel.livechat_end_dt:
                return request.redirect(
                    f"/odoo/action-mail.action_discuss?active_id={channel.id}",
                )
        return super()._response_discuss_channel_invitation(store, channel, guest_email)
