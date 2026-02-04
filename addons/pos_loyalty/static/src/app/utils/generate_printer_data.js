import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/generate_printer_data";
import { _t } from "@web/core/l10n/translation";

/**
 * This class is a JS copy of the class PosOrderReceipt in Python.
 */
patch(GeneratePrinterData.prototype, {
    generateData() {
        const data = super.generateData(...arguments);
        const points = this.order.getLoyaltyPoints();
        data.extra_data.loyalties = [];

        for (const coupon of points) {
            data.extra_data.loyalties.push({
                name: coupon.program.portal_point_name,
                type: coupon.points.won >= 0 ? _t("Won:") : _t("Spent:"),
                points: coupon.points.won || coupon.points.spent,
            });
            data.extra_data.loyalties.push({
                name: coupon.program.portal_point_name,
                type: _t("Balance:"),
                points: coupon.points.balance,
            });
        }

        data.extra_data.new_coupons = (this.order.new_coupon_info || []).map((coupon) => ({
            name: coupon.program_name,
            code: coupon.code,
            barcode_base64: coupon.barcode_base64,
        }));

        return data;
    },
});
