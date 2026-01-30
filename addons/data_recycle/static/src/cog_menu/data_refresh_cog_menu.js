import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const cogMenuRegistry = registry.category("cogMenu");

export class DataRefreshCogMenu extends Component {
    static template = "data_recycle.DataRefreshCogMenu";
    static components = { DropdownItem };
    static props = {};

    setup() {
        this.action = useService("action");
    }

    async refreshData() {
        const model = this.action.currentController.props.resModel;

        if (model === "data_recycle.record") {
            await this.action.doActionButton({
                type: "object",
                resModel: "data_recycle.model",
                name: "refresh_recycle_records",
            });
        }
    }
}

export const DataRefreshCogMenuItem = {
    Component: DataRefreshCogMenu,
    isDisplayed: ({ searchModel }) => {
        return searchModel.resModel === "data_recycle.record";
    },
    groupNumber: 50,
};

cogMenuRegistry.add("data_refresh_menu", DataRefreshCogMenuItem, { sequence: 10 });
