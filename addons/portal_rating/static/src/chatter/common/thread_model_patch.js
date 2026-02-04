import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup();
        /** @type {{ avg: number, total: number, percent: Object<number, number>}}*/
        this.rating_stats;
    },
});
