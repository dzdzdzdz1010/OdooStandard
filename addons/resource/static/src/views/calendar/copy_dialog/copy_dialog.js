import { Dialog } from "@web/core/dialog/dialog";
import { useChildRef } from "@web/core/utils/hooks";

import {Component, useState} from "@odoo/owl";

export class CopyDialog extends Component {
    static template = "resource.CopyDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        copyMethod: Function,
    };

    setup() {
        this.env.dialogData.dismiss = () => this._dismiss();
        this.modalRef = useChildRef();
        this.isProcess = false;
        this.state = useState({copyType: 'WEEKDAY'})
    }

    onChange(copyType) {
        this.state.copyType = copyType;
    }

    async _confirm() {
        await this.props.copyMethod(this.state.copyType);
        return this.props.close();
    }

    async _dismiss() {
        return this.props.close();
    }
}
