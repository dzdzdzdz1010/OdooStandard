import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { SelectMenu } from "@web/core/select_menu/select_menu";

export class LocalPrinterSelector extends Component {
    static template = "point_of_sale.LocalPrinterSelector";
    static components = { SelectMenu };
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        this.state = useState({ printers: [] });
        onWillStart(() => this._loadPrinters());
    }

    async _loadPrinters() {
        const { status, devices = [] } = window.isNativeApp
            ? await window.devices({ device_type: "printer" })
            : {};
        this.state.printers = status ? devices : [];
    }

    get value() {
        return this.props.record.data.local_printer_data?.display_name || null;
    }

    get choices() {
        return this.state.printers.map((printer) => ({
            value: printer.display_name,
            label: printer.display_name,
        }));
    }

    onChange(choice) {
        const printer = this.state.printers.find((p) => p.display_name === choice);
        this.props.record.update({
            local_printer_data: printer || false,
        });
    }
}

registry.category("fields").add("local_printer_selector", {
    component: LocalPrinterSelector,
});
