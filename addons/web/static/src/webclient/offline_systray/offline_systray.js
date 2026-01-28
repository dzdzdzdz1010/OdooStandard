import { Component, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { groupBy, sortBy } from "@web/core/utils/arrays";
import { _t } from "../../core/l10n/translation";

class OfflineSystray extends Component {
    static template = "web.OfflineSystray";
    static props = {};
    static components = { Dropdown, DropdownItem };

    setup() {
        this.offlineService = useService("offline");
        this.actionService = useService("action");
        this.menuService = useService("menu");
        useEffect(this.env.redrawNavbar, () => [
            this.offlineService.offline,
            this.offlineService.hasScheduledCalls,
        ]);
    }

    _getStatus(error, ids) {
        if (error) {
            if (ids.length) {
                return _t("cannot be edited");
            }
            return _t("cannot be created");
        }
        if (ids.length) {
            return _t("to be edited");
        }
        return _t("to be created");
    }

    get groupEntries() {
        const items = [];
        for (const { key, value } of Object.values(this.offlineService.scheduledORM)) {
            // OfflineSystray for the moment only support web_save!
            if (value.method === "web_save") {
                items.push({
                    id: key,
                    actionName: value.extras.actionName,
                    displayName: value.extras.displayName,
                    viewType: value.extras.viewType,
                    status: this._getStatus(value.extras.error, value.args[0]),
                });
            }
        }
        const sections = groupBy(items, (item) => item.actionName || "");
        return sortBy(Object.entries(sections), ([section]) => section);
    }

    get inError() {
        return Object.values(this.offlineService.scheduledORM).find(
            ({ value }) => value.extras.error
        );
    }

    get classNames() {
        return {
            fa: true,
            "fa-chain-broken": !this.inError,
            "fa-exclamation": this.inError,
            o_nav_entry: true,
            "text-danger": true,
        };
    }

    get labelText() {
        if (this.inError) {
            return _t("Sync Issues");
        }
        return _t("Working offline");
    }

    async openView(id) {
        const { value } = this.offlineService.scheduledORM[id];
        const allMenus = this.menuService.getAll();
        const menu = allMenus.find((x) => x.actionID === value.extras.actionId).id;
        if (menu) {
            this.menuService.setCurrentMenu(menu);
        }
        const resId = value.args[0]?.[0];
        await this.actionService.doAction(value.extras.actionId, {
            viewType: "form",
            props: { offlineId: id, resId },
            clearBreadcrumbs: true,
        });
        this.offlineService.removeScheduledORM(id);
    }
}

const offlineSystrayItem = {
    Component: OfflineSystray,
};

registry.category("systray").add("offline", offlineSystrayItem, { sequence: 1000 });
