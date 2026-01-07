import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    get composerHidden() {
        return this.channel?.channel_type === "livechat" && this.channel.livechat_end_dt;
    },

    /**
     * @override
     * @param {import("models").Persona} persona
     */
    getPersonaName(persona) {
        if (this.channel?.channel_type === "livechat" && persona?.user_livechat_username) {
            return persona.user_livechat_username;
        }
        return super.getPersonaName(persona);
    },
});
