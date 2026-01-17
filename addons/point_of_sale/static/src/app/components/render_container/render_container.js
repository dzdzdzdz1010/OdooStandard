import { Component, onPatched, useRef } from "@odoo/owl";
import { ErrorHandler } from "@web/core/utils/components";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";
import { debounce } from "@web/core/utils/timing";

const CONSOLE_COLOR = "#ff2525";

export class RenderContainer extends Component {
    static template = "l10n_it_pos.RenderContainer";
    static components = { ErrorHandler };
    static props = ["component"];

    setup() {
        this.root = useRef("root");
        this.debounceCallback = debounce(this.debounceCallbackFn.bind(this), 200);
        onPatched(() => {
            this.debounceCallback(this.root.el);
        });
    }

    reset() {
        this.props.component.component = undefined;
        this.props.component.data = undefined;
        this.props.component.onRendered = undefined;
    }

    debounceCallbackFn(el) {
        if (!this.props.component.onRendered) {
            return;
        }

        const html = el?.innerHTML;
        logPosMessage("RenderContainer", "debounceCallbackFn", "Sending...", CONSOLE_COLOR, [html]);
        this.props.component.onRendered(el);
        this.reset();
    }

    handleError(error) {
        this.reset();
        logPosMessage("RenderContainer", "handleError", "Error", CONSOLE_COLOR, [error]);
        Promise.resolve().then(() => false);
    }
}
