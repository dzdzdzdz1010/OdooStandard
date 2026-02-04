import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import {
    booleanFavoriteField,
    BooleanFavoriteField,
} from "@web/views/fields/boolean_favorite/boolean_favorite_field";

class MassMailingBooleanFavoriteField extends BooleanFavoriteField {
    setup() {
        super.setup();
        this.action = useService("action");
    }
    async update() {
        await super.update();
        if (this.props.readonly) {
            return;
        }
        let notificationMessage = "";
        if (this.props.record.data[this.props.name]) {
            notificationMessage = _t("Design added to the templates.");
        } else {
            notificationMessage = _t("Design removed from the templates.");
        }
        this.action.doAction({
            type: "ir.actions.client",
            tag: "display_notification",
            params: {
                message: notificationMessage,
                next: { type: "ir.actions.act_window_close" },
                sticky: false,
                type: "info",
            },
        });
    }
}

registry.category("fields").add("mass_mailing_boolean_favorite", {
    ...booleanFavoriteField,
    component: MassMailingBooleanFavoriteField,
});
