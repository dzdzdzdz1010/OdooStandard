import { Component, onWillRender, toRaw, useRef } from "@odoo/owl";

import { isMobileOS } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useCallActions } from "@mail/discuss/call/common/call_actions";
import { usePopover } from "@web/core/popover/popover_hook";
import { Tooltip } from "@web/core/tooltip/tooltip";
import { ActionList } from "@mail/core/common/action_list";
import { ACTION_TAGS } from "@mail/core/common/action";

const PIP_THREAD_ACTION_IDS = ["invite-people", "meeting-chat"];

export class CallActionList extends Component {
    static components = { ActionList };
    static props = ["channel", "className?", "compact?", "threadActions?"];
    static template = "discuss.CallActionList";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.rtc = useService("discuss.rtc");
        this.pipService = useService("discuss.pip_service");
        this.callActions = useCallActions({ channel: () => this.props.channel });
        this.more = useRef("more");
        this.root = useRef("root");
        this.popover = usePopover(Tooltip, {
            position: "top-middle",
        });
        onWillRender(() => {
            const partition = toRaw(this.callActions).partition;
            const isNotLayoutAction = (a) => !a.tags.includes(ACTION_TAGS.CALL_LAYOUT);
            const other = partition.other.filter(isNotLayoutAction);
            const group2 = [];
            for (const groupActions of partition.group) {
                const filtered = groupActions.filter(isNotLayoutAction);
                const sequenceGroup = filtered[0].sequenceGroup;
                const maxQuickActions = sequenceGroup === 200 ? 1 : 4;
                const quickActions = filtered.slice(0, maxQuickActions);
                let moreActions = filtered.slice(maxQuickActions);
                if (this.rtc.isPipMode && sequenceGroup === 200 && this.props.threadActions) {
                    const actions = toRaw(this.props.threadActions)?.actions;
                    if (actions) {
                        const pipActions = actions.filter((a) =>
                            PIP_THREAD_ACTION_IDS.includes(a.id)
                        );
                        if (pipActions.length > 0) {
                            moreActions = [...pipActions, ...moreActions];
                        }
                    }
                }
                let newGroup = quickActions;
                if (moreActions.length === 1) {
                    newGroup = [...quickActions, ...moreActions];
                } else if (moreActions.length > 1) {
                    newGroup = [
                        ...quickActions,
                        this.callActions.more(
                            {
                                actions: moreActions,
                                dropdownMenuClass: "m-0 mb-1 overflow-x-hidden",
                                dropdownPosition: "top-end",
                                name: this.MORE,
                            },
                            sequenceGroup
                        ),
                    ];
                }
                group2.push(newGroup);
            }
            this.actions = [...group2, other];
        });
    }

    get MORE() {
        return _t("More");
    }

    get isOfActiveCall() {
        return Boolean(this.props.channel.eq(this.rtc.channel));
    }

    get isSmall() {
        return Boolean(this.props.compact && this.rtc.isFullscreen);
    }

    get isMobileOS() {
        return isMobileOS();
    }
}
