import { Message } from "@mail/core/common/message";
import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    get showMessageActions() {
        return this.props.thread?.livechat_end_dt
            ? super.showMessageActions && this.store.has_access_livechat
            : super.showMessageActions;
    },
});
