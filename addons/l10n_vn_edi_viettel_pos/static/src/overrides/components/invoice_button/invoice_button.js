import { InvoiceButton } from "@point_of_sale/app/screens/ticket_screen/invoice_button/invoice_button";
import { patch } from "@web/core/utils/patch";

patch(InvoiceButton.prototype, {
    async _downloadInvoice(orderId) {
        if (
            this.pos.isVietnamCompany() &&
            this.props.order.l10n_vn_sinvoice_state == "sent" &&
            !this.props.order.l10n_vn_has_sinvoice_pdf &&
            this.props.order.raw.account_move
        ) {
            await this.pos.data.call(
                "account.move",
                "l10n_vn_edi_fetch_invoice_files",
                [this.props.order.raw.account_move]
            );
        }
        return await super._downloadInvoice(...arguments);
    }
});
