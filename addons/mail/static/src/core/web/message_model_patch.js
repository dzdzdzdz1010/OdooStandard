import { Message } from "@mail/core/common/message_model";
import { fields } from "@mail/model/export";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Message} */
const messagePatch = {
    setup(){
        super.setup();
        this.is_bookmarked = fields.Attr(false, {
            onUpdate() {
                const bookmarks = this.store.bookmark;
                if (this.is_bookmarked) {
                    bookmarks.counter++;
                    bookmarks.messages.add(this);
                } else {
                    bookmarks.counter--;
                    bookmarks.messages.delete(this);
                }
            },
        });
    },
    /** @param {import("models").Thread} thread the thread where the message is shown */
    canReplyAll(thread) {
        return this.canForward(thread) && !this.isNote;
    },
    /** @param {import("models").Thread} thread */
    canForward(thread) {
        if (!thread) {
            return false;
        }
        return (
            !["discuss.channel", "mail.box"].includes(thread.model) &&
            ["comment", "email"].includes(this.message_type)
        );
    },
};
patch(Message.prototype, messagePatch);
