import { DataServiceOptions } from "@point_of_sale/app/models/data_service_options";
import { patch } from "@web/core/utils/patch";

patch(DataServiceOptions.prototype, {
    get databaseTable() {
        return {
            ...super.databaseTable,
            "loyalty.card": {
                key: "id",
                condition: (record) =>
<<<<<<< 736b71202db840ba6a7ed7e7f014b5b7c493d589
                    record
                        .backLink("<-pos.order.line.coupon_id")
                        .find((l) => !(l.order_id?.finalized && typeof l.order_id.id === "number")),
||||||| 4490242c2999f9324038b3acbe5a235e75e1854c
                    record["<-pos.order.line.coupon_id"].find(
                        (l) => !(l.order_id?.finalized && typeof l.order_id.id === "number")
                    ),
=======
                    record["<-pos.order.line.coupon_id"].find(
                        (l) => !(l.order_id?.finalized && typeof l.order_id.id === "number")
                    ),
                getRecordsBasedOnLines: (orderlines) =>
                    orderlines.map((line) => line.coupon_id).filter((c) => c),
>>>>>>> 6c3980da8e3e207b1f1fffc3dd488b960bbe0de2
            },
        };
    },
    get pohibitedAutoLoadedModels() {
        return [
            ...super.pohibitedAutoLoadedModels,
            "loyalty.program",
            "loyalty.rule",
            "loyalty.reward",
        ];
    },
    get cleanupModels() {
        return [...super.cleanupModels, "loyalty.program"];
    },
});
