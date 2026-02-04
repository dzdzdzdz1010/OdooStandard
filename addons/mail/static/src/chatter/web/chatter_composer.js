import { Composer } from "@mail/core/common/composer";
import { RecipientsInput } from "@mail/core/web/recipients_input";

import { useRef, useEffect } from "@odoo/owl";

export class ChatterComposer extends Composer {
    static props = Composer.props.concat(["thread"]);
    static template = "mail.ChatterComposer";

    setup() {
        this.subjectInputRef = useRef("subjectInput");
        // fill in the "default subject" so it's clear it isn't the original default.
        useEffect(
            () => {
                const thread = this.props.thread;
                let defaultSubjectStart = thread.default_subject;
                if (defaultSubjectStart && defaultSubjectStart.slice(-3) === "...") {
                    defaultSubjectStart = defaultSubjectStart.slice(0, -3);
                }
                if (
                    defaultSubjectStart &&
                    thread.display_name &&
                    !thread.display_name.startsWith(defaultSubjectStart) &&
                    this.subjectInputRef.el
                ) {
                    this.subjectInputRef.el.value = this.props.thread.default_subject;
                }
            },
            () => [this.subjectInputRef.el]
        );
        return super.setup();
    }

    async onClickFullComposerGetAction() {
        const res = await super.onClickFullComposerGetAction();
        if (this.subject) {
            res.action.context.default_subject = this.subject;
        }
        return res;
    }

    get postData() {
        const postData = super.postData;
        if (this.subject) {
            postData.subject = this.subject;
        }
        return postData;
    }

    get subject() {
        return this.subjectInputRef.el?.value;
    }
}
Object.assign(ChatterComposer.components, {
    RecipientsInput,
});
