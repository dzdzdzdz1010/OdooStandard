import { AvatarStack } from "@mail/discuss/core/common/avatar_stack";

import { Component } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class CallPresentationBar extends Component {
    static template = "discuss.CallPresentationBar";
    static props = {};
    static components = { AvatarStack };

    setup() {
        this.rtc = useService("discuss.rtc");
    }

    get isSelfPresenting() {
        return this.rtc.selfSession?.is_screen_sharing_on;
    }

    get presenterPersonas() {
        return this.presenterSessions.map((s) => s.channel_member_id.persona);
    }

    get presenterSessions() {
        if (this.isSelfPresenting) {
            return [this.rtc.selfSession];
        }
        const activeSession = this.rtc.channel?.activeRtcSession;
        if (activeSession?.mainVideoStreamType === "screen") {
            return [activeSession];
        }
        return this.rtc.channel?.rtc_session_ids?.filter((s) => s.is_screen_sharing_on) ?? [];
    }

    get presenterText() {
        const presenterNames = this.presenterSessions.map((s) => s.channel_member_id.name);
        const count = presenterNames.length;
        if (this.isSelfPresenting) {
            return _t("You are presenting");
        }
        if (count === 1) {
            return _t("%(name)s is presenting", { name: presenterNames[0] });
        } else if (count === 2) {
            return _t("%(name1)s and %(name2)s are presenting", {
                name1: presenterNames[0],
                name2: presenterNames[1],
            });
        }
        return _t("%(name1)s, %(name2)s and %(more)s more are presenting", {
            name1: presenterNames[0],
            name2: presenterNames[1],
            more: String(count - 2),
        });
    }

    onClickStopPresentation() {
        this.rtc.toggleVideo("screen", false);
    }

    togglePresentationAudio() {
        this.rtc.screenAudioTrack.enabled = !this.rtc.screenAudioTrack.enabled;
    }
}
