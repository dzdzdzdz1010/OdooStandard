import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";

export class OfflineErrorPopup extends Component {
    static template = "point_of_sale.OfflineErrorPopup";
    static components = { Dialog };
    static props = {
        close: { type: Function },
        confirmText: { type: String, optional: true },
        title: { type: String, optional: true },
        body: { type: String, optional: true },
    };

    static defaultProps = {
        confirmText: _t("Continue with limited functionalities"),
        title: _t("You're offline"),
        body: _t(
            "Meanwhile connection is back, Odoo Point of Sale will operate limited operations. Check your connection or continue with limited functionalities"
        ),
    };
    confirm() {
        this.props.close();
    }
}
