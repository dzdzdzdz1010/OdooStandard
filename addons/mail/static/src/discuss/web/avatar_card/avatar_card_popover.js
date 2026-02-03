import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { rpc } from "@web/core/network/rpc";
import { Component, useState } from "@odoo/owl";
import { useOpenChat } from "@mail/core/web/open_chat_hook";
import { ImStatus } from "@mail/core/common/im_status";
import { useDynamicInterval } from "@mail/utils/common/misc";
import { formatLocalDateTime } from "@mail/utils/common/dates";
import { useChannelMemberActions } from "@mail/discuss/core/common/channel_member_actions";
import { ActionList } from "@mail/core/common/action_list";

export class AvatarCardPopover extends Component {
    static template = "mail.AvatarCardPopover";
    static components = { ActionList, Dropdown, DropdownItem, ImStatus };
    static props = {
        id: { type: Number, required: true },
        channelMember: { type: Object, optional: true },
        close: { type: Function, required: true },
        model: {
            type: String,
            validate: (m) => ["res.users", "res.partner"].includes(m),
            optional: true,
        },
    };
    static defaultProps = {
        model: "res.users",
    };

    setup() {
        this.actionService = useService("action");
        this.store = useService("mail.store");
        this.dialog = useService("dialog");
        this.openChat = useOpenChat(this.openChatModel);
        this.state = useState({ partnerLocalDateTimeFormatted: "" });
        this.store.fetchStoreData("avatar_card", {
            id: this.props.id,
            model: this.props.model,
        });
        this.chanelMemberActions = useChannelMemberActions({
            member: () => this.props.channelMember,
        });
        useDynamicInterval(
            (...args) => this.onChangeTz(...args),
            () => [this.partner?.tz, this.store.self?.tz]
        );
    }

    /**
     * @param {string} partnerTz
     * @param {string} currentUserTz
     */
    onChangeTz(partnerTz, currentUserTz) {
        this.state.partnerLocalDateTimeFormatted = formatLocalDateTime(partnerTz, currentUserTz);
        if (!this.state.partnerLocalDateTimeFormatted) {
            return;
        }
        return 60000 - (Date.now() % 60000);
    }

    get openChatModel() {
        return this.props.model;
    }

    get canOpenSettingMenu() {
        return this.props.channelMember && this.chanelMemberActions.actions.length;
    }

    /** @deprecated */
    get selfChannelRole() {
        return this.props.channelMember?.selfChannelRole;
    }

    /** @deprecated */
    get currentChannelRole() {
        return this.props.channelMember?.channel_role;
    }

    /** @deprecated */
    get canSetAdmin() {
<<<<<<< cf69bd28bd1b80662fd3c11fb06b7bb179e8a016
        return (
            this.props.channelMember &&
            this.currentChannelRole !== "admin" &&
            (this.store.self_user?.is_admin ||
                (this.selfChannelRole === "owner" && this.currentChannelRole !== "owner") ||
                (this.selfChannelRole === "owner" && this.props.channelMember?.channelAsSelf))
        );
||||||| f77eeb5e2db9325a8be322ae294bab5f0ed91663
        return (
            this.props.channelMember &&
            this.currentChannelRole !== "admin" &&
            (this.store.self_user?.is_admin ||
                (this.selfChannelRole === "owner" && this.currentChannelRole !== "owner") ||
                (this.selfChannelRole === "owner" && this.props.channelMember?.threadAsSelf))
        );
=======
        return this.props.channelMember?.canSetAdmin;
>>>>>>> 0a73141d4db36648540c13d6999590d4e82f5765
    }

    /** @deprecated */
    get canRemoveAdmin() {
        return this.props.channelMember?.canRemoveAdmin;
    }

    /** @deprecated */
    get canSetOwner() {
        return this.props.channelMember?.canSetOwner;
    }

    /** @deprecated */
    get canRemoveOwner() {
<<<<<<< cf69bd28bd1b80662fd3c11fb06b7bb179e8a016
        return (
            this.props.channelMember &&
            this.currentChannelRole === "owner" &&
            (this.store.self_user?.is_admin || this.props.channelMember?.channelAsSelf)
        );
||||||| f77eeb5e2db9325a8be322ae294bab5f0ed91663
        return (
            this.props.channelMember &&
            this.currentChannelRole === "owner" &&
            (this.store.self_user?.is_admin || this.props.channelMember?.threadAsSelf)
        );
=======
        return this.props.channelMember?.canRemoveOwner;
>>>>>>> 0a73141d4db36648540c13d6999590d4e82f5765
    }

    /** @deprecated */
    get canRemoveMember() {
        return this.props.channelMember?.canRemoveMember;
    }

    get user() {
        if (this.props.model === "res.users") {
            return this.store["res.users"].get(this.props.id);
        }
        return undefined;
    }

    get partner() {
        if (this.props.model === "res.partner") {
            return this.store["res.partner"].get(this.props.id);
        }
        return this.user?.partner_id;
    }

    get name() {
        return this.partner?.name;
    }

    get email() {
        return this.partner?.email;
    }

    get phone() {
        return this.partner?.phone;
    }

    get showViewProfileBtn() {
        return this.partner;
    }

    get hasFooter() {
        return false;
    }

    async getProfileAction() {
        return {
            res_id: this.partner.id,
            res_model: "res.partner",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        };
    }

    onSendClick() {
        this.openChat(this.props.id);
        this.props.close();
    }

    /** @deprecated */
    onClickRemove() {
        this.dialog.add(ConfirmationDialog, {
            body: _t('Do you want to remove "%(member_name)s" from this channel?', {
                member_name: this.props.channelMember.name,
            }),
            cancel: () => {},
            confirm: () => {
                rpc("/discuss/channel/remove_member", {
                    member_id: this.props.channelMember.id,
                });
                this.props.close();
            },
        });
    }

    /** @deprecated */
    setChannelRole(role) {
<<<<<<< cf69bd28bd1b80662fd3c11fb06b7bb179e8a016
        if (
            !this.store.self_user?.is_admin &&
            (this.props.channelMember.channelAsSelf || role === "owner")
        ) {
            this.dialog.add(ConfirmationDialog, {
                body: this.props.channelMember.channelAsSelf
                    ? _t(
                          "Do you want to remove owner from yourself? You will no longer have full control over the channel and its settings."
                      )
                    : _t(
                          'Do you want to set "%(member_name)s" as the owner? This means that the member will have full control over the channel and its settings.\n\nThis action cannot be reverted.',
                          { member_name: this.props.channelMember.name }
                      ),
                cancel: () => {},
                confirm: () => this.props.channelMember.setChannelRole(role),
            });
        } else {
            this.props.channelMember.setChannelRole(role);
        }
||||||| f77eeb5e2db9325a8be322ae294bab5f0ed91663
        if (
            !this.store.self_user?.is_admin &&
            (this.props.channelMember.threadAsSelf || role === "owner")
        ) {
            this.dialog.add(ConfirmationDialog, {
                body: this.props.channelMember.threadAsSelf
                    ? _t(
                          "Do you want to remove owner from yourself? You will no longer have full control over the channel and its settings."
                      )
                    : _t(
                          'Do you want to set "%(member_name)s" as the owner? This means that the member will have full control over the channel and its settings.\n\nThis action cannot be reverted.',
                          { member_name: this.props.channelMember.name }
                      ),
                cancel: () => {},
                confirm: () => this.props.channelMember.setChannelRole(role),
            });
        } else {
            this.props.channelMember.setChannelRole(role);
        }
=======
        this.props.channelMember.setChannelRole(role);
>>>>>>> 0a73141d4db36648540c13d6999590d4e82f5765
    }

    async onClickViewProfile(newWindow) {
        const action = await this.getProfileAction();
        if (!action) {
            return;
        }
        this.actionService.doAction(action, { newWindow });
    }
}
